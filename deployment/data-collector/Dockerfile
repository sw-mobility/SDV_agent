FROM python:3.12-slim

# 1. 작업 디렉토리 설정
WORKDIR /app

# 2. 필요한 빌드 종속성 설치 및 Python 패키지 설치
# psycopg2-binary는 C 헤더 파일과 컴파일러가 필요하므로 apt-get을 사용합니다.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    # FastAPI, Uvicorn, SQLAlchemy, Boto3, Psycopg2-binary 설치
    pip install --no-cache-dir fastapi uvicorn pydantic sqlalchemy boto3 psycopg2-binary && \
    # 빌드에 사용된 패키지 제거 및 캐시 정리로 이미지 크기 최소화
    apt-get purge -y --auto-remove gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 3 애플리케이션 코드 복사: 필요한 파일만 복사
COPY main.py /app
COPY database.py /app
COPY models.py /app

# 4. FastAPI 기본 포트 8000 노출
EXPOSE 8000

# 6. 컨테이너 시작 시 실행될 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--access-log"]
