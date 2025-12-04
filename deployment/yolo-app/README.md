# YOLO Object Detection Web Application

This project is a web-based application for performing object detection on images using a YOLO (You Only Look Once) model. It provides a simple interface to browse images stored in an S3-compatible object storage, run a pre-trained YOLO model on them, and save the results back to S3.

The application is built with Streamlit and is designed to be deployed as a containerized service on a Kubernetes cluster, specifically targeting GPU-accelerated edge devices like the NVIDIA Jetson.

## Features

- **Web-based UI:** A user-friendly interface built with Streamlit for easy interaction.
- **S3 Integration:** Fetches source images from and uploads detection results to an S3-compatible object storage.
- **YOLOv8 Inference:** Utilizes the `ultralytics` library to run a YOLO model for object detection.
- **Image Navigation:** Allows users to easily navigate through a list of images from the S3 bucket.
- **Metadata Storage:** Saves detection metadata (model version, number of detected objects, class names) along with the annotated images.
- **Containerized Deployment:** Packaged as a Docker container and deployed using Kubernetes manifests.
- **Edge-Optimized:** Designed to run on `arm64` architectures with GPU acceleration (e.g., NVIDIA Jetson).

## How It Works

1.  **Image Loading:** The application lists and loads images from a pre-configured S3 bucket and prefix.
2.  **User Interaction:** The user selects an image and clicks the "Run Object Detection" button.
3.  **Object Detection:** The YOLO model processes the image to detect objects.
4.  **Display Results:** The original image and the annotated image (with bounding boxes) are displayed in the web UI.
5.  **Save Results:** The annotated image and associated metadata are uploaded back to a specified location in the S3 bucket.

## Technical Stack

- **Application Framework:** [Streamlit](https://streamlit.io/)
- **Machine Learning Model:** [YOLOv8 (Ultralytics)](https://ultralytics.com/)
- **S3 Communication:** [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- **Containerization:** [Docker](https://www.docker.com/)
- **Orchestration:** [Kubernetes](https://kubernetes.io/)

## Deployment

The application is deployed using the provided Kubernetes manifest (`deploy/yolo-detection-deploy.yaml`).

- A `Deployment` manages the application pod.
- A `Service` of type `NodePort` exposes the application on a specific port on the cluster nodes.
- The deployment is configured to run on a node with the `arm64` architecture and a GPU, identified by the `nodeSelector`.
- S3 credentials are injected into the pod using a Kubernetes secret.

## Usage

To run this application:

1.  **Build and Push the Docker Image:**
    Build the Docker image using the provided `Dockerfile` and push it to a container registry.

2.  **Configure the Deployment:**
    Update the `image` field in `deploy/yolo-detection-deploy.yaml` to point to your container image. Ensure the S3 secret (`sdv-user-rgw-secret`) is created in the `sdv` namespace with the required `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

3.  **Deploy to Kubernetes:**
    ```sh
    kubectl apply -f deploy/yolo-detection-deploy.yaml
    ```

4.  **Access the Application:**
    The application will be accessible at `http://<NODE_IP>:<NODE_PORT>`, where `NODE_PORT` is `30501` as defined in the service manifest.