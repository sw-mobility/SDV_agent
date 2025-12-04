import subprocess
import tempfile
import os, boto3, urllib3
from botocore.exceptions import ClientError
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# 로컬 파일 import
import database
import models

# --- App 및 DB 초기화 ---
app = FastAPI(
    title="Edge Cluster Application Deployer",
    description="Host Cluster에서 Edge Cluster로 앱을 배포한다."
)

# DB 테이블 생성 (최초 실행 시)
@app.on_event("startup")
def on_startup():
    database.init_db()


# --- S3 Boto3 Client Dependency ---
def get_s3_client():
    """
    환경 변수에서 S3 접속 정보를 읽어 boto3 클라이언트를 주입합니다.
    """
    s3_endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "http://s3.suredatalab.kr")
    s3_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "6A6NQZLGORPSM7IBWYM1")
    s3_secret_key = os.environ.get("AWS_SECRET_KEY", "UarBUtVrfqdWANb5cZL3ZVbpAXj0I7JWIwAqzOxU")
    s3_region = os.environ.get("AWS_REGION", "us-east-1")

    if not all([s3_endpoint_url, s3_access_key, s3_secret_key]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="S3 environment variables are not properly configured."
        )
    
    try:
        client = boto3.client(
            's3',
            endpoint_url=s3_endpoint_url,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            region_name=s3_region,
            verify=False  
        )
        yield client
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to create S3 client: {e}"
        )


# --- 헬퍼 함수 (Kubectl 실행) ---
def run_kubectl(kubeconfig_path: str, command: List[str]) -> (bool, str):
    """지정된 Kubeconfig와 명령어로 kubectl을 실행"""
    # 환경 변수에 KUBECONFIG 경로 설정
    env = os.environ.copy()
    env["KUBECONFIG"] = kubeconfig_path
    
    try:
        process = subprocess.run(
            ["kubectl"] + command,
            env=env,
            check=True,  # 실패 시 예외 발생
            capture_output=True,
            text=True,
            timeout=30 # 30초 타임아웃
        )
        return True, process.stdout
    except subprocess.CalledProcessError as e:
        # 명령 실패 시
        return False, e.stderr
    except Exception as e:
        # 기타 오류 (타임아웃 등)
        return False, str(e)

# --- 1. Member Cluster 추가 ---
@app.post("/clusters/", 
          response_model=models.ClusterInfo, 
          status_code=status.HTTP_201_CREATED,
          summary="1. Member Cluster 추가")
def create_cluster(
    cluster: models.ClusterCreate, db: Session = Depends(database.get_db)
):
    db_cluster = db.query(database.MemberCluster).filter_by(name=cluster.name).first()
    if db_cluster:
        raise HTTPException(status_code=400, detail="Cluster name already exists")
        
    db_cluster = database.MemberCluster(**cluster.dict())
    db.add(db_cluster)
    db.commit()
    db.refresh(db_cluster)
    
    # 생성 직후 상태 확인
    status_str = "Checking..."
    return models.ClusterInfo(
        id=db_cluster.id,
        name=db_cluster.name,
        node_ip=db_cluster.node_ip,
        status=status_str
    )


# --- 2. Member Cluster 목록 조회 (sdv 네임스페이스 확인) ---
@app.get("/clusters/", 
         response_model=List[models.ClusterInfo],
         summary="2. Member Cluster 목록 조회 (sdv NS 상태 포함)")
def list_clusters(db: Session = Depends(database.get_db)):
    clusters = db.query(database.MemberCluster).all()
    response_list = []

    for cluster in clusters:
        # Kubeconfig를 임시 파일에 쓰기
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp_config:
            temp_config.write(cluster.kubeconfig_data)
            temp_config.flush()
            
            # 'sdv' 네임스페이스 확인
            success, output = run_kubectl(temp_config.name, ["get", "ns", "sdv"])
            
            status_str = "Connected (sdv OK)" if success else f"Unreachable or no 'sdv' NS: {output[:50]}..."

        # 응답 모델에 status 추가
        cluster_info = models.ClusterInfo(
            id=cluster.id,
            name=cluster.name,
            node_ip=cluster.node_ip,
            status=status_str
        )
        response_list.append(cluster_info)
        
    return response_list


# --- 3. 배포 대상 응용 생성 ---
@app.post("/apps/", 
          response_model=models.AppInfo, 
          status_code=status.HTTP_201_CREATED,
          summary="3. 배포 대상 응용 생성")
def create_application(
    app: models.AppCreate, db: Session = Depends(database.get_db)
):
    db_app = db.query(database.Application).filter_by(name=app.name).first()
    if db_app:
        raise HTTPException(status_code=400, detail="Application name already exists")
        
    # Pydantic 모델이 이미 registry.suredatalab.kr 검증을 수행함
    db_app = database.Application(**app.dict())
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return models.AppInfo.from_orm(db_app)


# --- 4. 배포 대상 응용 목록 조회 ---
@app.get("/apps/", 
         response_model=List[models.AppInfo],
         summary="4. 배포 대상 응용 목록 조회")
def list_applications(db: Session = Depends(database.get_db)):
    apps = db.query(database.Application).all()
    return [models.AppInfo.from_orm(app) for app in apps]


# --- 5. 응용 배포 ---
@app.post("/deploy/", 
          response_model=models.DeployResponse,
          summary="5. 응용 배포 (App ID, Cluster ID)")
def deploy_application(
    req: models.DeployRequest, db: Session = Depends(database.get_db)
):
    # 1. DB에서 앱과 클러스터 정보 조회
    db_app = db.query(database.Application).get(req.app_id)
    db_cluster = db.query(database.MemberCluster).get(req.cluster_id)
    
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    if not db_cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 2. 임시 파일에 Kubeconfig와 Manifest 작성
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as temp_manifest:
            temp_manifest.write(db_app.deployment_manifest)
            manifest_path = temp_manifest.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_config:
            temp_config.write(db_cluster.kubeconfig_data)
            config_path = temp_config.name

        # 3. Kubectl apply 실행
        success, output = run_kubectl(config_path, ["apply", "-f", manifest_path])

        # 4. 임시 파일 정리
        os.remove(manifest_path)
        os.remove(config_path)

        # 5. 결과 반환
        if success:
            # 성공 시 NodePort URL 생성
            service_url = f"http://{db_cluster.node_ip}:{db_app.service_node_port}"
            return models.DeployResponse(
                status="success",
                message=f"Deployment '{db_app.name}' applied to '{db_cluster.name}'.\nOutput: {output}",
                service_url=service_url
            )
        else:
            return models.DeployResponse(
                status="failed",
                message=f"Deployment failed.\nError: {output}"
            )
            
    except Exception as e:
        # 파일 생성/삭제 오류 등
        return models.DeployResponse(status="failed", message=f"Internal error: {e}")


@app.delete("/clusters/{cluster_id}", 
            status_code=status.HTTP_204_NO_CONTENT,
            summary="6. Member Cluster 삭제")
def delete_cluster(
    cluster_id: int, 
    db: Session = Depends(database.get_db)
):
    """
    지정된 ID의 Member Cluster를 DB에서 삭제합니다.
    """
    # 1. DB에서 클러스터 조회
    db_cluster = db.query(database.MemberCluster).get(cluster_id)
    
    # 2. 클러스터가 없는 경우 404 반환
    if not db_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Cluster with id {cluster_id} not found"
        )
        
    # 3. 클러스터 삭제
    db.delete(db_cluster)
    db.commit()
    
    # 4. 성공 시 204 No Content (내용 없음) 응답 반환
    return


# === S3 Bucket Management APIs ===

@app.get("/buckets/",
         response_model=List[models.BucketInfo],
         summary="7. S3 버킷 목록 조회")
def list_buckets(s3_client: boto3.client = Depends(get_s3_client)):
    """
    현재 S3 엔드포인트의 모든 버킷 목록을 조회합니다.
    """
    try:
        response = s3_client.list_buckets()
        buckets = [
            models.BucketInfo(
                name=b['Name'],
                creation_date=b['CreationDate']
            ) for b in response.get('Buckets', [])
        ]
        return buckets
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 Error: {e}"
        )


@app.post("/buckets/",
          response_model=models.BucketResponse,
          status_code=status.HTTP_201_CREATED,
          summary="8. S3 버킷 생성")
def create_s3_bucket(
    bucket: models.BucketCreate,
    s3_client: boto3.client = Depends(get_s3_client)
):
    """
    새로운 S3 버킷을 생성합니다.
    """
    try:
        # RGW(Ceph)는 LocationConstraint가 필요 없는 경우가 많습니다.
        s3_client.create_bucket(Bucket=bucket.bucket_name)
        return models.BucketResponse(
            name=bucket.bucket_name,
            message="Bucket created successfully"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bucket '{bucket.bucket_name}' already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 Error: {e}"
        )


@app.delete("/buckets/{bucket_name}",
            response_model=models.BucketResponse,
            summary="9. S3 버킷 삭제")
def delete_s3_bucket(
    bucket_name: str,
    s3_client: boto3.client = Depends(get_s3_client)
):
    """
    S3 버킷을 삭제합니다. (버킷이 비어 있어야 함)
    """
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        return models.BucketResponse(
            name=bucket_name,
            message="Bucket deleted successfully"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found."
            )
        if e.response['Error']['Code'] == 'BucketNotEmpty':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bucket '{bucket_name}' is not empty. Cannot delete."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 Error: {e}"
        )
