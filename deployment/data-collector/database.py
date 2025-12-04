# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ⚠️ 환경 변수에서 DB 설정 읽어오기
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "database": os.environ.get("DB_DATABASE", "sdv_ev"),
    "user": os.environ.get("DB_USER", "sdv"),
    "password": os.environ.get("DB_PASSWORD", "password"),
    "port": os.environ.get("DB_PORT", "5432")
}

# PostgreSQL URL 생성: postgresql://user:password@host:port/database
# DB 설정 정보가 환경 변수에 설정되어 있지 않으면 기본값 사용
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# SQLAlchemy 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 세션 관리자 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 (모든 ORM 모델의 기본 클래스)
Base = declarative_base()

def create_db_tables():
    """DB에 연결하여 SQLAlchemy 모델 기반으로 테이블이 없으면 생성합니다."""
    # Base.metadata.create_all(engine) 호출 시 models.py에 정의된 모든 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 테이블 생성이 완료되었습니다 (이미 존재하면 건너뜀).")

def get_db():
    """FastAPI Dependency Injection을 위한 DB 세션 생성 및 해제 제너레이터입니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
