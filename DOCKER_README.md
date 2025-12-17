# Docker Development Environment

## Quick Start

### Prerequisites
- Docker Desktop installed
- Docker Compose installed
- `.env` file with API keys (copy from `.env.example`)

### Start Development Stack

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### Access Services

- **Qubes Health API**: http://localhost:8080
  - Health check: http://localhost:8080/health
  - Readiness: http://localhost:8080/health/ready
  - Metrics: http://localhost:8080/health/metrics

- **Prometheus**: http://localhost:9090
  - Query metrics and view targets

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  - Prometheus datasource pre-configured

### Common Commands

```bash
# View logs
docker-compose logs -f qubes

# Stop all services
docker-compose down

# Stop and remove volumes (clears data)
docker-compose down -v

# Restart a specific service
docker-compose restart qubes

# Execute command in container
docker-compose exec qubes python examples/create_my_qube.py

# Access container shell
docker-compose exec qubes bash
```

### Development Workflow

1. **Code Changes**: Edit files locally - they're mounted in the container
2. **Restart Service**: `docker-compose restart qubes` to apply changes
3. **View Logs**: `docker-compose logs -f qubes`
4. **Run Tests**: `docker-compose exec qubes pytest`

### Volume Management

Persistent data is stored in Docker volumes:
- `qubes-data`: Qube databases and sessions
- `prometheus-data`: Prometheus time-series data
- `grafana-data`: Grafana dashboards and settings

### Troubleshooting

**Port conflicts:**
```bash
# Change ports in docker-compose.yml if needed
ports:
  - "8081:8080"  # Use 8081 instead of 8080
```

**View container logs:**
```bash
docker-compose logs qubes
docker-compose logs prometheus
docker-compose logs grafana
```

**Reset everything:**
```bash
docker-compose down -v
docker-compose up --build
```

## Production Deployment

For production, use `Dockerfile` (not `Dockerfile.dev`) with optimized settings.
See `docs/22_DevOps_Guide.md` for full deployment guide.
