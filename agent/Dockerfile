FROM python:3.9

# To prevent cv2 import error
RUN apt update
RUN apt -y install libgl1-mesa-glx

WORKDIR /agent
COPY . .

RUN pip install -r yolov9/requirements.txt
RUN pip install -r requirements.txt


