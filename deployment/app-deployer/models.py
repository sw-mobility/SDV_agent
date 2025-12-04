# models.py
from pydantic import BaseModel, constr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime 

# --- Cluster 모델 ---
class ClusterBase(BaseModel):
    name: str
    node_ip: str # NodePort 접근 IP (예: 192.168.8.199)

class ClusterCreate(ClusterBase):
    kubeconfig_data: str # kubeconfig 파일의 전체 내용

class ClusterInfo(ClusterBase):
    id: int
    status: str # "Connected", "Unreachable" 등

    model_config = ConfigDict(from_attributes=True)

# --- Application 모델 ---
class AppBase(BaseModel):
    name: str
    # registry.suredatalab.kr로 시작해야 함
    image_registry: constr(pattern=r"^registry\.suredatalab\.kr/.*$")
    service_node_port: int # 예: 30501

class AppCreate(AppBase):
    deployment_manifest: str # 배포 YAML의 전체 내용

class AppInfo(AppBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

# --- Deploy 모델 ---
class DeployRequest(BaseModel):
    app_id: int
    cluster_id: int

class DeployResponse(BaseModel):
    status: str # "success" or "failed"
    message: str
    service_url: Optional[str] = None

# --- S3 Bucket 모델 ---
class BucketCreate(BaseModel):
    """버킷 생성을 위한 입력 모델"""
    bucket_name: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")

class BucketInfo(BaseModel):
    """버킷 목록 조회를 위한 응답 모델"""
    name: str
    creation_date: datetime

class BucketResponse(BaseModel):
    """버킷 생성/삭제 응답을 위한 모델"""
    name: str
    message: str
