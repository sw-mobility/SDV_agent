# Dockerfile

# Python 3.12-slim 기반 이미지 사용
FROM python:3.12-slim

# --- [수정] ---
# YOLOv8/ultralytics 구동에 필요한 시스템 의존성 설치
# (libgl1-mesa-glx -> libgl1, libxrender-dev -> libxrender1)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*
# --- [수정 완료] ---

WORKDIR /app

# Python 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app.py .

# 학습된 모델 파일(best11m.pt)을 이미지 안으로 복사
COPY best.pt .

# Streamlit 기본 포트
EXPOSE 8501

# Streamlit 앱 실행
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
