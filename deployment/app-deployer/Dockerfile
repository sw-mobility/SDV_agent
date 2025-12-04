# Dockerfile

# 1. Python 3.9을 기반으로 시작
FROM python:3.12-slim

# 2. 시스템 패키지 업데이트 및 kubectl 다운로드에 필요한 curl 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. kubectl 설치 (arm64/amd64 아키텍처 자동 감지)
RUN ARCH=$(dpkg --print-architecture | sed 's/amd64/amd64/g;s/arm64/arm64/g') && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 4. 애플리케이션 작업 디렉토리 설정
WORKDIR /app

# 5. Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 앱 코드 복사
COPY . .

# 7. FastAPI 서버 실행 (uvicorn)
# 8000 포트로 외부에 노출
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
