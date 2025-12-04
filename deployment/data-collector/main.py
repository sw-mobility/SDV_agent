# main.py

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json
import os 
from typing import Dict, Any # 타입 힌트 추가

# S3 객체 저장을 위한 boto3 import
import boto3
from botocore.exceptions import NoCredentialsError, ClientError 

# 로컬 모듈 import
from database import get_db, create_db_tables
from models import VehicleData, VehicleRealtimeData

# ==============================================================================
# 🌟 S3 접속 정보 환경 변수 설정 🌟
# ==============================================================================

# RGW(S3) 엔드포인트
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://s3.suredatalab.kr") 

# S3 버킷 이름 (원시 데이터를 저장할 버킷)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "sdv-ml-data")

# 인증 정보 (K8S Secret에서 환경 변수로 주입된다고 가정)
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "6A6NQZLGORPSM7IBWYM1")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "UarBUtVrfqdWANb5cZL3ZVbpAXj0I7JWIwAqzOxU")

# ==============================================================================

app = FastAPI(
    title="Realtime Vehicle Data Collector",
    version="1.0.0"
)

# ==============================================================================
# 1. 앱 시작 이벤트: 테이블 생성 및 S3 클라이언트 초기화
# ==============================================================================

# S3 클라이언트를 전역 변수로 초기화
s3_client = None

@app.on_event("startup")
def on_startup():
    """애플리케이션 시작 시 DB 테이블 및 S3 클라이언트를 준비합니다."""
    global s3_client
    try:
        create_db_tables()
        
        # S3 클라이언트 초기화
        if not S3_ACCESS_KEY or not S3_SECRET_KEY:
            raise ValueError("S3_ACCESS_KEY 또는 S3_SECRET_KEY가 설정되지 않았습니다.")
            
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            verify=False # 자체 서명된 인증서를 사용하는 경우 (필요에 따라 제거 가능)
        )
        print(f"✅ S3 클라이언트 초기화 완료: {S3_ENDPOINT_URL}")
        
    except Exception as e:
        print(f"❌ 데이터베이스/S3 클라이언트 준비 실패: {e}")
        # 실패 시 서버 시작을 중단할 수 있도록 예외를 다시 발생시킬 수 있습니다.
        raise e 

# ==============================================================================
# 2. 유틸리티: 원시 데이터 S3 저장 함수 수정
# ==============================================================================

def save_raw_data(data: VehicleData, record_time: datetime):
    """
    수신된 Pydantic 데이터를 JSON 파일로 변환하여 Rook-Ceph RGW(S3)에 업로드합니다.
    """
    if s3_client is None:
        print("❌ S3 클라이언트가 초기화되지 않았습니다. 저장 실패.")
        return False
        
    try:
        # S3 키(경로/파일명) 형식: ev_data/[YYYY]/[MM]/[DD]/[HH]/[VIN]_[TIME].json
        # Object Key 생성 (파티셔닝 구조를 고려)
        key_format = record_time.strftime("%Y-%m-%d-%H")
        timestamp_str = record_time.strftime("%Y%m%d%H%M%S_%f")
        object_key = f"ev_data/{key_format}/{data.vin}_{timestamp_str}.json"

        # Pydantic 모델을 JSON 문자열(bytes)로 변환
        json_data = json.dumps(data.model_dump(), indent=2, ensure_ascii=False).encode('utf-8')

        # S3에 업로드
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=json_data,
            ContentType='application/json'
        )

        print(f"💾 원시 데이터 S3 저장 성공: s3://{S3_BUCKET_NAME}/{object_key}")
        return True
        
    except ClientError as e:
        # S3 관련 오류 (예: 버킷 없음, 권한 거부 등)
        print(f"❌ S3 Client 오류 발생: {e}")
        return False
    except Exception as e:
        print(f"❌ 원시 데이터 S3 저장 중 예상치 못한 오류: {e}")
        return False

# ==============================================================================
# 3. API 엔드포인트 (로직은 동일하며, 파일 저장 호출만 S3 저장으로 대체)
# ==============================================================================

@app.post('/api/vehicle/realtime')
async def receive_vehicle_data(
    data: VehicleData, 
    db: Session = Depends(get_db)
):
    """데이터 수신, 중복 확인 후 DB 저장 및 원시 데이터 S3 저장을 처리합니다."""
    
    # 1. 'time' 문자열을 datetime 객체로 변환
    try:
        record_dt = datetime.fromisoformat(data.time.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=422, detail="잘못된 'time' 형식입니다.")

    # 2. 중복 데이터 확인 (VIN과 record_time이 모두 일치하는 레코드가 있는지 확인)
    exists = db.query(VehicleRealtimeData.id).filter(
        VehicleRealtimeData.vin == data.vin,
        VehicleRealtimeData.record_time == record_dt
    ).first()

    if exists:
        print(f"⚠️ 중복 데이터 무시: VIN={data.vin}, Time={data.time}. 이미 저장되었습니다.")
        return {"message": "중복 데이터, 무시됨", "vin": data.vin}

    # 3. 원시 데이터 S3 저장 (DB 저장 시도 전에 수행)
    # S3 저장이 실패하더라도 DB 저장은 시도하도록 예외를 잡고 처리합니다.
    save_raw_data(data, record_dt) 

    # 4. DB 저장
    try:
        # DB 저장 로직은 이전과 동일
        new_record = VehicleRealtimeData(
            record_time=record_dt,
            vin=data.vin,
            state_changed=data.stateChanged,
            car_state=data.car_data.state,
            soc=data.car_data.soc,
            speed=data.car_data.speed,
            total_volt=data.car_data.totalVolt,
            total_ampere=data.car_data.totalAmpere,
            longitude=data.location_data.longitude,
            latitude=data.location_data.latitude,
            max_volt=data.extremeValue_data.batteryMaxVolt,
            min_volt=data.extremeValue_data.batteryMinVolt,
            max_temp=data.extremeValue_data.batteryMaxTemp,
            min_temp=data.extremeValue_data.batteryMinTemp,
        )
        
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        return {"message": "데이터 수신 및 DB 저장 성공", "vin": new_record.vin, "id": new_record.id}
        
    except Exception as e:
        db.rollback() 
        print(f"❌ DB 저장 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 오류: {e}")

# ==============================================================================
# 4. Uvicorn 실행 (로컬 테스트용)
# ==============================================================================
if __name__ == '__main__':
    # 로컬 테스트를 위해 ACCESS KEY와 SECRET을 환경 변수로 임시 설정
    if "S3_ACCESS_KEY" not in os.environ:
        os.environ["S3_ACCESS_KEY"] = "dummy_access_key" 
    if "S3_SECRET_KEY" not in os.environ:
        os.environ["S3_SECRET_KEY"] = "dummy_secret_key"
        
    import uvicorn
    uvicorn.run("main:app", host='0.0.0.0', port=5000, reload=True)
