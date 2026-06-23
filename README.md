# Grafana LGTM Playground Stack

> ⚠️ **Local-only / playground usage** — Run this stack **only on your local machine**. Do not run it on a VPS, cloud server, or any host reachable from the internet.
>
> - Services are exposed without authentication (Loki, Mimir, Tempo, Grafana)
> - Grafana anonymous access as **Admin** is enabled by default
> - Alloy mounts the host Docker socket (`/var/run/docker.sock`) to collect container telemetry — review this carefully before adapting for production

An observability playground stack using Grafana Labs components:

| Pillar | Component | Purpose | Port |
|---|---|---|---|
| Logs | Grafana Loki | Log aggregation backend | 3100 |
| Metrics | Grafana Mimir | Metrics TSDB | 9009 |
| Traces | Grafana Tempo | Distributed tracing backend | 3200 |
| Collection | Grafana Alloy | OpenTelemetry Collector | 12345 |
| UI | Grafana | Unified observability UI | 3000 |

## Architecture

```
┌──────────────────┐     ┌─────────────────┐
│   Demo App       │────▶│                 │
│   (Python/Flask) │     │     Alloy       │
├──────────────────┤     │  (Collector)    │
│   Demo App Go    │────▶│                 │
│   (Go/net-http)  │     └────────┬────────┘
└──────────────────┘              │
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       ┌──────────┐        ┌──────────┐        ┌──────────┐
       │   Loki   │        │  Mimir   │        │  Tempo   │
       │  (Logs)  │        │(Metrics) │        │ (Traces) │
       └────┬─────┘        └────┬─────┘        └────┬─────┘
            │                   │                   │
            └───────────────────┴───────────────────┘
                                │
                           ┌────▼────┐
                           │ Grafana │
                           │  (UI)   │
                           └─────────┘
```

## Quick start

### Requirements

- Docker Engine
- Docker Compose **v2** (comando `docker compose`)

### 1. Clone and configure

```bash
cp .env.example .env
```

### 2. Start the stack

```bash
docker compose up -d
```

### 3. Open the UIs

| Service | URL | Credentials |
|--------------------|----------------------------|-------------|
| Grafana | http://localhost:3000 | admin/admin |
| Alloy UI | http://localhost:12345 | - |
| Demo app (Python) | http://localhost:8080 | - |
| Demo app (Go) | http://localhost:8081 | - |

### 4. Generate test data

#### Python demo app (port 8080)

```bash
# Normal requests
curl http://localhost:8080/api/users
curl http://localhost:8080/api/orders

# Slow request (~1s)
curl http://localhost:8080/api/slow

# Error request (HTTP 500)
curl http://localhost:8080/api/error
```

#### Go demo app (port 8081)

```bash
# Service info
curl http://localhost:8081/

# Simulate work with nested spans
curl http://localhost:8081/api/work
```

### 5. Continuous load generator

```bash
# Linux/WSL:
./scripts/load.sh 100
```

```powershell
# Windows PowerShell:
.\scripts\load.ps1 -Count 100
```

## Exploring in Grafana

### Logs (Loki)
1. Go to **Explore**
2. Select **Loki** as the data source
3. Use the query: `{job="docker"}`

### Metrics (Mimir)
1. Go to **Explore**
2. Select **Mimir** as the data source
3. Try queries like:
   - `app_requests_total` — Total request count
   - `rate(app_requests_total[5m])` — Request rate
   - `histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))` — P95 latency

### Traces (Tempo)
1. Go to **Explore**
2. Select **Tempo** as the data source
3. Filter by Service Name: `demo-app` or `demo-app-go`
4. Open a trace to inspect spans

### Service map
1. Go to **Explore** > **Tempo**
2. Open the **Service Graph** tab
3. Inspect service topology

## Useful commands

```bash
# Follow logs from all containers
docker compose logs -f

# Follow logs for a single service
docker compose logs -f grafana

# Restart a service
docker compose restart alloy

# Stop the stack
docker compose down

# Stop and remove volumes (wipe all data)
docker compose down -v

# Rebuild and restart a demo app
docker compose build demo-app && docker compose up -d demo-app
docker compose build demo-app-go  && docker compose up -d demo-app-go
```

## Configuration via `.env`

Create your `.env` file from the example (already done in step 1):

```bash
cp .env.example .env
```

`.env.example` documents all available variables: ports, Grafana credentials, and the OTLP endpoint.

## Folder structure

```
docker-lgtm-grafana-stack/
├── docker-compose.yml
├── README.md
├── .env.example
├── config/
│   ├── alloy/
│   │   └── config.alloy          # Alloy running as a Docker container
│   ├── grafana/
│   │   └── provisioning/
│   │       └── datasources/
│   │           └── datasources.yaml
│   ├── loki/
│   │   └── loki-config.yaml
│   ├── mimir/
│   │   └── mimir-config.yaml
│   └── tempo/
│       └── tempo-config.yaml
├── demo-app-python/              # Python demo app (Flask + OpenTelemetry)
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── demo-app-go/                  # Go demo app (net/http + OpenTelemetry)
│   ├── Dockerfile
│   ├── main.go
│   ├── go.mod
│   └── go.sum
└── scripts/
    ├── load.sh                   # Load generator (Linux/WSL)
    └── load.ps1                  # Load generator (Windows PowerShell)
```


## Ports

| Service | Port | Description |
|----------------|-------|-----------------------------------|
| Grafana | 3000 | Web UI |
| Loki | 3100 | HTTP API |
| Mimir | 9009 | HTTP API |
| Tempo | 3200 | HTTP API |
| Tempo | 4317 | OTLP gRPC receiver |
| Tempo | 4318 | OTLP HTTP receiver |
| Alloy | 12345 | Web UI |
| Demo app (Python) | 8080 | HTTP API |
| Demo app (Go) | 8081 | HTTP API |

## Troubleshooting

### `ContainerConfig` error when using `docker-compose`

This project does **not** support legacy `docker-compose` (Python, v1.x). If you use it, you may see errors such as `ContainerConfig`.
Use **Docker Compose v2** (`docker compose`):

```bash
docker compose up -d
```

### Loki is not receiving logs

```bash
# Verify Alloy can access the Docker socket
docker compose logs alloy | grep -i error
```

### Mimir is not receiving metrics

```bash
# Check connectivity
docker compose exec alloy wget -qO- http://mimir:9009/ready
```

### Tempo is not receiving traces

```bash
# Check Tempo readiness
curl http://localhost:3200/ready

## Security and vulnerability scanning

This repository is meant for local testing, but you can still scan it regularly.

### Scan the repository (filesystem)

If you have Trivy installed:

```bash
trivy fs --scanners vuln,secret,misconfig .
```

Or using Docker (no local install):

```bash
docker run --rm -v "$PWD:/work" -w /work aquasec/trivy:latest fs --scanners vuln,secret,misconfig .
```

### Scan the built demo images

```bash
docker compose build

# Compose image names depend on your project directory name, so list resolved images
# and scan them (no placeholders):
docker compose config --images | while read -r img; do docker run --name trivy-scan --rm aquasec/trivy:latest image "$img"; done
```

## Author

Created by **Luiz Alberto Aude**.

## License

[MIT](LICENSE)
