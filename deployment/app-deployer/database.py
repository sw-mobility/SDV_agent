# database.py
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# sqlite db file
DEFAULT_DB_PATH = "app-registry.db"
DB_FILE_PATH = os.getenv("DB_PATH", DEFAULT_DB_PATH)
DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

Base = declarative_base()
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class MemberCluster(Base):
    """Member Cluster 정보 (Kubeconfig 포함)"""
    __tablename__ = "clusters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    # Member 클러스터의 NodePort 접속용 IP
    node_ip = Column(String, nullable=False)
    # Kubeconfig 파일 내용(Text)
    kubeconfig_data = Column(Text, nullable=False)

class Application(Base):
    """배포할 응용 프로그램 정보"""
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    image_registry = Column(String, nullable=False)
    # 배포 Manifest YAML 내용(Text)
    deployment_manifest = Column(Text, nullable=False)
    # 응용의 고정 NodePort (링크 생성용)
    service_node_port = Column(Integer, nullable=False)

# DB 및 테이블 생성
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
