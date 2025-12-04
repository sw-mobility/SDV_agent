# CAN Data Sender

## 1. Description

This project is designed to simulate an edge device that sends vehicle CAN data to a central server. The script reads data from files, processes it, and transmits it to a specified API endpoint. This is particularly useful for testing and development in a simulated vehicle environment.

## 2. Features

- **Real-time Simulation**: Simulates the real-time transmission of vehicle data.
- **Data Source**: Reads data from text files, supporting formats like JSON.
- **Configurable**: Key parameters such as server URL, data directory, and transmission intervals can be easily configured via environment variables.
- **Containerized**: Includes a `Dockerfile` for easy deployment and execution in a containerized environment.

## 3. Configuration

The application is configured using the following environment variables:

| Variable                | Description                                     | Default Value                  |
| ----------------------- | ----------------------------------------------- | ------------------------------ |
| `SERVER_BASE_URL`       | The base URL of the server                      | `http://127.0.0.1:5000`        |
| `SERVER_END_POINT`      | The API endpoint for data transmission          | `/api/vehicle/realtime`        |
| `DATA_ROOT_DIR`         | The root directory where data files are located | `./daily_data`                 |
| `TRANSMISSION_INTERVAL` | The data transmission interval in seconds       | `10`                           |

## 4. Usage

### 4.1. Direct Execution

To run the script directly, set the required environment variables and execute the Python script:

```bash
export SERVER_BASE_URL="http://your-server-url"
export SERVER_END_POINT="/api/endpoint"
export DATA_ROOT_DIR="/path/to/your/data"
export TRANSMISSION_INTERVAL=5

python send_ev_data.py
```

### 4.2. Docker

#### Build the Docker Image

```bash
docker build -t can-data-sender .
```

#### Run the Docker Container

When running the Docker container, you must provide the necessary environment variables. Additionally, you need to mount the directory containing the data files into the container.

```bash
docker run -d \
  --name can-data-sender-container \
  -e SERVER_BASE_URL="http://your-server-url" \
  -e SERVER_END_POINT="/api/endpoint" \
  -e DATA_ROOT_DIR="/data" \
  -e TRANSMISSION_INTERVAL=5 \
  -v /path/to/your/data:/data \
  can-data-sender
```

- **`-d`**: Runs the container in detached mode.
- **`--name`**: Assigns a name to the container.
- **`-e`**: Sets environment variables.
- **`-v`**: Mounts a host directory (`/path/to/your/data`) to a container directory (`/data`).

## 5. Dockerfile

The `Dockerfile` defines the environment for running the `can-data-sender` application.

- **Base Image**: `python:3.12-slim`
- **Dependencies**: `requests`
- **Working Directory**: `/app`
- **Command**: `python send_ev_data.py`

```