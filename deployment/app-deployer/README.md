# App Deployer

Edge Cluster Application Deployer는 Host Cluster에서 다수의 Member Cluster로 애플리케이션을 배포하고 관리하기 위한 REST API 서버이다.

FastAPI를 기반으로 구현되었으며, Member Cluster의 Kubeconfig 정보와 배포할 애플리케이션의 정보를 받아 `kubectl` 명령을 실행하여 배포를 수행한다. 데이터는 SQLite DB에 저장되며, S3 호환 오브젝트 스토리지 관리를 위한 부가 기능도 포함한다.

## 주요 기능

*   **클러스터 관리**: Member Cluster의 Kubeconfig를 등록, 조회, 삭제한다.
*   **애플리케이션 관리**: 배포할 컨테이너 애플리케이션의 정보(이미지 주소, Manifest 등)를 등록 및 조회한다.
*   **애플리케이션 배포**: 등록된 애플리케이션을 지정된 Member Cluster에 배포한다.
*   **S3 버킷 관리**: S3 호환 오브젝트 스토리지의 버킷을 생성, 조회, 삭제한다.

## 기술 스택

*   **Backend**: Python, FastAPI
*   **Database**: SQLite
*   **Container**: Docker
*   **Deployment**: Kubernetes
*   **주요 라이브러리**: Uvicorn, SQLAlchemy, Boto3, Pydantic

## 필수 요구사항

*   Python 3.10 이상
*   Docker
*   kubectl

## 로컬 환경 설정 및 실행

### 1. 소스 코드 복제

```bash
git clone <repository-url>
cd app-deployer
```

### 2. Python 가상환경 생성 및 의존성 설치

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (선택사항)

S3 관련 기능을 사용하려면 아래 환경 변수를 설정해야 한다. 설정하지 않으면 S3 API 호출 시 오류가 발생한다.

```bash
export AWS_ENDPOINT_URL="http://s3.example.com"
export AWS_ACCESS_KEY_ID="<your-access-key>"
export AWS_SECRET_KEY="<your-secret-key>"
```

데이터베이스 파일 경로를 변경하려면 `DB_PATH` 환경 변수를 설정한다. 기본값은 `app-registry.db`이다.

```bash
export DB_PATH="/path/to/database.db"
```

### 4. 애플리케이션 실행

`uvicorn`을 사용하여 FastAPI 애플리케이션을 실행한다.

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

실행 후 브라우저에서 `http://localhost:8000/docs` 로 접속하면 Swagger UI를 통해 API를 테스트할 수 있다.

## Docker 이미지 빌드

프로젝트 루트 디렉토리에서 아래 명령을 실행하여 Docker 이미지를 빌드한다.

```bash
docker build -t registry.suredatalab.kr/etri/sdv/app-deployer:latest .
```
*   `t` 태그는 `deploy/app-deployer.yaml` 파일의 이미지 경로와 일치시켜야 한다.

빌드된 이미지를 컨테이너 레지스트리에 푸시한다.

```bash
docker push registry.suredatalab.kr/etri/sdv/app-deployer:latest
```

## Kubernetes 배포

`deploy/app-deployer.yaml` 파일은 Host Cluster에 App Deployer를 배포하기 위한 Kubernetes 매니페스트이다.

### 배포 전제 조건

1.  **컨테이너 이미지**: App Deployer 이미지가 `app-deployer.yaml`에 명시된 레지스트리 경로에 푸시되어 있어야 한다.
2.  **이미지 Pull Secret**: 프라이빗 레지스트리를 사용하는 경우, Host Cluster에 `gitlab-registry-secret`이라는 이름의 Secret이 존재해야 한다. (필요시 `app-deployer.yaml` 파일의 `imagePullSecrets` 필드 수정)
3.  **스토리지 클래스**: `app-deployer.yaml`은 `rook-ceph-block` 스토리지 클래스를 사용하는 PVC를 정의한다. 클러스터에 해당 스토리지 클래스가 없거나 다른 클래스를 사용하려면 `persistentVolumeClaim`의 `storageClassName`을 수정해야 한다.

### 배포 절차

1.  필요한 경우 `deploy/app-deployer.yaml` 파일을 환경에 맞게 수정한다.
2.  `kubectl`을 사용하여 매니페스트를 Host Cluster에 적용한다.

    ```bash
    kubectl apply -f deploy/app-deployer.yaml
    ```

3.  배포 상태를 확인한다.

    ```bash
    kubectl get all -n sdv
    ```

### 서비스 접속

배포가 완료되면 App Deployer API는 `NodePort` 타입의 서비스를 통해 노출된다. `app-deployer.yaml`의 기본 설정에 따라 Host Cluster의 아무 노드 IP와 `30508` 포트를 통해 접속할 수 있다.

*   **API 서버 URL**: `http://<host-cluster-node-ip>:30508`
*   **Swagger UI**: `http://<host-cluster-node-ip>:30508/docs`
