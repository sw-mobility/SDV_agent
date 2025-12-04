# app.py
import streamlit as st
import os, boto3, cv2
from botocore.client import Config
import numpy as np
from PIL import Image
import io, tempfile
from ultralytics import YOLO
import urllib.parse


# --- 1. 환경 변수에서 S3 접속 정보 로드 ---
S3_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "https://s3.suredatalab.kr")
S3_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "6A6NQZLGORPSM7IBWYM1")
S3_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "UarBUtVrfqdWANb5cZL3ZVbpAXj0I7JWIwAqzOxU")
MODEL_FILE_PATH = os.environ.get("MODEIL_FILE_PATH", "best.pt")

# --- 2. S3 클라이언트 초기화 ---

config = Config (
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        signature_version='s3v4')

try:
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=config,
        verify=False  # s3.suredatalab.kr이 사설 인증서 사용 시
    )
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception as e:
    st.error(f"S3 클라이언트 초기화 실패: {e}")
    st.stop()


# --- 3. YOLO 모델 로드 ---
@st.cache_resource
def load_model():
    model = YOLO(MODEL_FILE_PATH) 
    return model

model = load_model()

# --- 4. S3 헬퍼 함수 ---
@st.cache_data(ttl=600) 
def list_s3_images(bucket, prefix):
    images = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.lower().endswith(('.png', '.jpg', '.jpeg')):
                        images.append(key)
    except Exception as e:
        st.error(f"S3 목록 조회 실패: {e}")
    return images

def load_image_from_s3(bucket, key):
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        img_data = obj['Body'].read()
        pil_image = Image.open(io.BytesIO(img_data))
        img_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return img_bgr
    except Exception as e:
        st.error(f"이미지 로드 실패: {e}")
        return None


def upload_image_to_s3(bucket, key, image_data_bgr, detection_results, model_name):
    """OpenCV 이미지(BGR)를 메모리에서 S3에 직접 업로드 (태그 및 메타데이터 포함)"""
    try:
        # 1. 메타데이터 생성
        num_detections = len(detection_results[0].boxes)
        detected_cls_indices = detection_results[0].boxes.cls.cpu().numpy().astype(int)
        class_map = detection_results[0].names
        unique_class_names = set([class_map[i] for i in detected_cls_indices])
        
        metadata = {
            'model-version': model_name,
            'detection-count': str(num_detections),
            'detected-classes': ", ".join(unique_class_names) if unique_class_names else "None"
        }

        # 2. 태그 생성
        tag_string = 'SDV-YOLO'
        #tag_string = urllib.parse.urlencode(tags)

        # 3. 이미지를 메모리 내 버퍼로 인코딩
        is_success, buffer = cv2.imencode(".png", image_data_bgr)
        if not is_success:
            st.error("이미지 인코딩 실패")
            return False
        
        # 4. 버퍼를 파일과 유사한 객체로 변환
        in_mem_file = io.BytesIO(buffer)
        print (f"in_mem_file: {in_mem_file.getbuffer().nbytes}")
        in_mem_file.seek(0)
        
        # 5. S3에 upload_fileobj로 업로드
        s3_client.upload_fileobj(
            in_mem_file,
            bucket,
            key,
            ExtraArgs={
                "Metadata": metadata,
                "Tagging": tag_string,
                "ContentType": "image/png"
            }
        )
        return True
    except Exception as e:
        st.error(f"결과 업로드 실패: {e}")
        return False




# --- 5. Streamlit UI ---
st.title("🛰️ YOLO 객체 탐지 애플리케이션 (v2)")

# S3 경로 설정
BUCKET_NAME = 'sdv-ml-data'
SOURCE_PREFIX = 'data/Synthetic_Drone_Classification_Dataset/val/'
DEST_PREFIX = 'detected/'

# --- [수정 1] 경로 유지 기능을 위한 기준 경로 ---
# S3 키에서 제거할 부분 (예: 'data/Synthetic_Drone_Classification_Dataset/')
STRIP_PREFIX = "data/Synthetic_Drone_Classification_Dataset/" 


# 이미지 목록 로드
image_keys = list_s3_images(BUCKET_NAME, SOURCE_PREFIX)
if not image_keys:
    st.warning(f"S3 경로에서 이미지를 찾을 수 없습니다: s3://{BUCKET_NAME}/{SOURCE_PREFIX}")
    st.stop()

# --- [수정 1] 세션 상태를 이용한 이미지 인덱스 관리 ---
# 세션 상태 초기화 (현재 이미지 인덱스)
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# 콜백 함수: selectbox가 변경되면 세션 상태 인덱스를 업데이트
def on_select_change():
    st.session_state.current_index = image_keys.index(st.session_state.selector)

# 이미지 선택 selectbox
selected_key_from_box = st.selectbox(
    "탐색할 이미지를 선택하세요:", 
    image_keys, 
    index=st.session_state.current_index,
    key='selector', # 상태 저장을 위한 key
    on_change=on_select_change # 변경 시 콜백 실행
)

# 좌우 버튼
col1, col2 = st.columns(2)
with col1:
    if st.button("⬅️ 이전 (Prev)"):
        if st.session_state.current_index > 0:
            st.session_state.current_index -= 1
        else:
            st.session_state.current_index = len(image_keys) - 1 # 처음으로 순환
        st.rerun() # 스크립트를 다시 실행하여 selectbox와 이미지 갱신

with col2:
    if st.button("다음 (Next) ➡️"):
        if st.session_state.current_index < len(image_keys) - 1:
            st.session_state.current_index += 1
        else:
            st.session_state.current_index = 0 # 마지막으로 순환
        st.rerun() # 스크립트를 다시 실행하여 selectbox와 이미지 갱신

# 현재 인덱스를 기준으로 실제 선택된 이미지 키를 가져옴
selected_key = image_keys[st.session_state.current_index]

if selected_key:
    # 원본 이미지 로드 및 표시
    img_bgr = load_image_from_s3(BUCKET_NAME, selected_key)
    
    if img_bgr is not None:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        st.image(img_rgb, caption="원본 이미지", width="content")

        # 탐지 버튼
        if st.button(" 🔍 객체 탐지 실행"):
            with st.spinner("YOLO 모델이 추론 중입니다..."):
                
                results = model(img_bgr)
                annotated_img_bgr = results[0].plot()
                
                annotated_img_rgb = cv2.cvtColor(annotated_img_bgr, cv2.COLOR_BGR2RGB)
                st.image(annotated_img_rgb, caption="탐지 결과", width="content")

                # S3 저장 경로 설정
                relative_path = selected_key.replace(STRIP_PREFIX, "")
                upload_key = f"{DEST_PREFIX}{relative_path}"

                # 수정된 함수 호출: 이미지 데이터를 직접 전달
                success = upload_image_to_s3(
                    BUCKET_NAME,
                    upload_key,
                    annotated_img_bgr, # <-- 이미지 데이터 직접 전달
                    detection_results=results,
                    model_name=MODEL_FILE_PATH
                )
                    
                if success:
                    st.success(f"탐지 결과가 S3에 저장되었습니다: s3://{BUCKET_NAME}/{upload_key}")

