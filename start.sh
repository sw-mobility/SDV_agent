#! /bin/bash

read -p "Enter value for AWS_ACCESS_KEY_ID: " a
export AWS_ACCESS_KEY_ID=$a
read -p "Enter value for AWS_SECRET_ACCESS_KEY: " b
export AWS_SECRET_ACCESS_KEY=$b
read -p "Enter value for S3_BUCKET_NAME: " c
export S3_BUCKET_NAME=$c

Y_FILE="./agent/yolov9"
if [ ! -d $Y_FILE ]; then
    git clone https://github.com/WongKinYiu/yolov9.git ./agent/yolov9
fi
P_FILE="./agent/yolov9-s.pt"
if [ ! -e $P_FILE ]; then
    wget https://github.com/WongKinYiu/yolov9/releases/download/v0.1/yolov9-s.pt -P ./agent/
fi

docker compose build --no-cache
if [ $? -ne 0 ]; then
    echo "docker compose build --no-cache failed, trying docker-compose build --no-cache"
    docker-compose build --no-cache
fi
docker compose up -d
if [ $? -ne 0 ]; then
    echo "docker compose up -d failed, trying docker-compose up -d"
    docker-compose up -d
fi
