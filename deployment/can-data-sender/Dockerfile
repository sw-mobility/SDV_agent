# 1. Python 3.12 Slim 버전 기반 이미지 사용
FROM python:3.12-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 필요한 Python 패키지 설치
RUN pip install --no-cache-dir requests

# 4. 애플리케이션 코드 복사
COPY send_ev_data.py /app/

# 5. 실행 명령 정의
CMD ["python", "send_ev_data.py"]
