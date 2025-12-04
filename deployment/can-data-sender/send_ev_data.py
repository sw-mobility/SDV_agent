import requests
import json
import time
import re
import os
import glob
import logging
from typing import Generator, Dict, Any
from datetime import datetime

# ==============================================================================
# 🌟 로깅 설정 🌟
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(asctime)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🌟 환경 변수 및 설정 (K8S Deployment에서 주입됨) 🌟
# ==============================================================================

# 서버의 BASE URL (예: http://192.168.8.131:30888)
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://127.0.0.1:5000")

# API 엔드포인트 경로 (예: /api/vehicle/realtime)
SERVER_END_POINT = os.environ.get("SERVER_END_POINT", "/api/vehicle/realtime")

# 최종 전송 URL 구성
SERVER_URL = f"{SERVER_BASE_URL}{SERVER_END_POINT}" 

# 데이터가 저장된 루트 디렉토리 경로 (HostPath 마운트 경로)
DATA_ROOT_DIR = os.environ.get("DATA_ROOT_DIR", "./daily_data")

# 시뮬레이션 전송 주기 (초)
TRANSMISSION_INTERVAL = int(os.environ.get("TRANSMISSION_INTERVAL", 10))
# ==============================================================================

def preprocess_mongo_json(line: str) -> str:
    """MongoDB Ext JSon 문자열에서 파이썬 JSON으로 파싱 가능한 형태로 변환합니다."""
    line = re.sub(r'ObjectId\("([0-9a-fA-F]+)"\)', r'"\1"', line)
    line = re.sub(r'ISODate\("([^"]+)"\)', r'"\1"', line)
    line = re.sub(r'NumberLong\(([\d-]+)\)', r'\1', line)
    line = re.sub(r'DBRef\("[^"]+", "([^"]+)"\)', r'"\1"', line)
    return line

def load_data_generator(file_path: str) -> Generator[Dict[str, Any], None, None]:
    """단일 파일에서 라인별 JSON 데이터를 읽고 파싱하여 제너레이터로 반환합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if not line.strip(): continue
                try:
                    processed_line = preprocess_mongo_json(line.strip())
                    document = json.loads(processed_line)
                    yield document
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 파싱 오류 (파일: {file_path}, 라인 {i+1}): {e}")
                    continue
    except FileNotFoundError:
        logger.error(f"오류: 파일을 찾을 수 없습니다: {file_path}")
    except Exception as e:
        logger.error(f"오류: 파일 로딩 중 예상치 못한 오류: {e}")


def get_sorted_daily_files(root_dir: str) -> list[str]:
    """지정된 루트 디렉토리 내의 모든 파일을 찾아 날짜순으로 정렬합니다."""
    file_paths = glob.glob(os.path.join(root_dir, '**', '*.txt'), recursive=True)
    if not file_paths:
        logger.warning(f"경고: 데이터 디렉토리 '{root_dir}'에서 파일을 찾을 수 없습니다.")
    file_paths.sort() 
    return file_paths


def extract_fields(full_doc: Dict[str, Any]) -> Dict[str, Any]:
    """원본 문서에서 요구되는 필드만 추출하여 서버 전송용 JSON을 생성합니다."""
    extracted = {
        "time": full_doc.get("time"),
        "vin": full_doc.get("vin"),
        "stateChanged": full_doc.get("stateChanged"),
        "car_data": full_doc.get("car_data", {}),
        "location_data": full_doc.get("location_data", {}),
        "extremeValue_data": full_doc.get("extremeValue_data", {}),
    }
    
    info_set_data = full_doc.get("powerBatteryInfoSet_data", {})
    if 'powerBatteryInfos' in info_set_data:
        # 셀 전류값(cellAmperes) 제외
        cleaned_infos = []
        for info in info_set_data['powerBatteryInfos']:
            info_copy = info.copy() 
            if 'cellAmperes' in info_copy:
                del info_copy['cellAmperes']
            cleaned_infos.append(info_copy)
        info_set_data['powerBatteryInfos'] = cleaned_infos

    extracted["powerBatteryInfoSet_data"] = info_set_data
    return extracted


def send_data_to_server(payload: Dict[str, Any]):
    """추출된 데이터를 서버로 HTTP POST 요청을 보냅니다."""
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            logger.info(f"전송 성공 (URL: {SERVER_URL}, VIN: {payload.get('vin')}, Time: {payload.get('time')})")
        else:
            logger.warning(f"전송 실패 (상태 코드: {response.status_code}, 응답: {response.text})")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"서버 연결 오류 발생: {e} (URL: {SERVER_URL})")


if __name__ == "__main__":
    logger.info("--- 엣지 디바이스 시뮬레이션 시작 ---")
    logger.info(f"서버 URL: {SERVER_URL}")
    logger.info(f"데이터 루트 디렉토리: {DATA_ROOT_DIR}")
    
    sorted_files = get_sorted_daily_files(DATA_ROOT_DIR)

    if not sorted_files:
        logger.warning("시뮬레이션을 시작할 데이터 파일이 없습니다. 종료합니다.")
    else:
        logger.info(f"총 {len(sorted_files)}개의 데이터 파일을 찾았습니다. 순차 처리 시작.")
        
        for file_path in sorted_files:
            logger.info(f"\n--- 파일 처리 시작: {file_path} ---")
            
            data_gen = load_data_generator(file_path)
            
            for full_document in data_gen:
                try:
                    transmission_payload = extract_fields(full_document)
                    send_data_to_server(transmission_payload)
                    
                except Exception as e:
                    logger.error(f"시뮬레이션 중 예기치 않은 오류: {e}")
                time.sleep(TRANSMISSION_INTERVAL)
            logger.info(f"--- 파일 처리 완료: {file_path} ---")
        logger.info("\n=== 모든 파일의 데이터 전송 완료. 시뮬레이션 종료. ===")
