"""
Health Check Endpoints for Qubes System

Provides FastAPI endpoints for system health monitoring:
- /health - Basic liveness check
- /health/ready - Readiness check with dependency validation
- /health/metrics - Prometheus metrics endpoint

From docs/22_DevOps_Guide.md Part IV
"""

import os
import psutil
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from monitoring.metrics import MetricsRecorder
from utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Qubes Health API",
    description="Health check and metrics endpoints for Qubes orchestrator",
    version="1.0.0"
)


class HealthChecker:
    """System health checker with dependency validation"""

    def __init__(self):
        self.start_time = time.time()
        self.dependencies: Dict[str, callable] = {}

    def register_dependency(self, name: str, check_func: callable):
        """Register a dependency health check function

        Args:
            name: Dependency name (e.g., "storage", "ai_provider")
            check_func: Async function that returns True if healthy, False otherwise
        """
        self.dependencies[name] = check_func
        logger.info("health_dependency_registered", dependency=name)

    async def check_all_dependencies(self) -> Dict[str, Any]:
        """Check all registered dependencies

        Returns:
            Dict with dependency statuses
        """
        results = {}
        all_healthy = True

        for name, check_func in self.dependencies.items():
            try:
                is_healthy = await check_func()
                results[name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "healthy": is_healthy
                }
                if not is_healthy:
                    all_healthy = False
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "healthy": False,
                    "error": str(e)
                }
                all_healthy = False
                logger.error("health_check_failed", dependency=name, error=str(e))

        return {
            "all_healthy": all_healthy,
            "dependencies": results
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics

        Returns:
            Dict with CPU, memory, disk metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent
                },
                "process": {
                    "pid": os.getpid(),
                    "memory_mb": round(psutil.Process().memory_info().rss / (1024**2), 2)
                }
            }
        except Exception as e:
            logger.error("system_metrics_failed", error=str(e))
            return {"error": str(e)}


# Global health checker instance
health_checker = HealthChecker()


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    Basic liveness check

    Returns 200 if service is running. Used by load balancers
    and container orchestrators to determine if the service is alive.

    Returns:
        200: Service is alive
        500: Service is not responding
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(time.time() - health_checker.start_time)
        }
    )


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> JSONResponse:
    """
    Readiness check with dependency validation

    Checks if the service is ready to accept traffic by validating
    all critical dependencies (database, AI providers, P2P network, etc.)

    Returns:
        200: Service is ready (all dependencies healthy)
        503: Service is not ready (one or more dependencies unhealthy)
    """
    try:
        # Check all dependencies
        dependency_status = await health_checker.check_all_dependencies()

        # Get system metrics
        system_metrics = health_checker.get_system_metrics()

        # Determine overall status
        is_ready = dependency_status["all_healthy"]
        status_code = 200 if is_ready else 503

        response = {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(time.time() - health_checker.start_time),
            "dependencies": dependency_status["dependencies"],
            "system": system_metrics
        }

        if not is_ready:
            logger.warning("readiness_check_failed", dependencies=dependency_status)

        return JSONResponse(
            status_code=status_code,
            content=response
        )

    except Exception as e:
        logger.error("readiness_check_error", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
        )


@app.get("/health/metrics", tags=["Health"])
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus exposition format for scraping
    by Prometheus server. Includes all custom application metrics
    (AI costs, memory chain stats, P2P stats, etc.)

    Returns:
        200: Metrics in Prometheus format
    """
    try:
        # Generate Prometheus metrics
        metrics_data = generate_latest()

        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )

    except Exception as e:
        logger.error("metrics_endpoint_error", exc_info=True)
        return PlainTextResponse(
            content=f"# Error generating metrics: {str(e)}",
            status_code=500
        )


@app.get("/health/info", tags=["Health"])
async def info_endpoint() -> JSONResponse:
    """
    System information endpoint

    Returns detailed system information including version,
    configuration, and runtime statistics.

    Returns:
        200: System information
    """
    try:
        system_metrics = health_checker.get_system_metrics()

        return JSONResponse(
            status_code=200,
            content={
                "version": "1.0.0",
                "service": "qubes-orchestrator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": int(time.time() - health_checker.start_time),
                "system": system_metrics,
                "dependencies_registered": list(health_checker.dependencies.keys())
            }
        )

    except Exception as e:
        logger.error("info_endpoint_error", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# Example dependency check functions
async def check_storage() -> bool:
    """Check if JSON storage is accessible"""
    try:
        # Try to access storage directory
        import os
        storage_dir = "data/qubes"
        return os.path.exists(storage_dir) and os.access(storage_dir, os.W_OK)
    except Exception as e:
        logger.error("storage_health_check_failed", error=str(e))
        return False


async def check_ai_providers() -> bool:
    """Check if AI providers are available"""
    try:
        # Example: Check if API keys are configured
        from dotenv import load_dotenv
        load_dotenv()

        # Check for at least one AI provider API key
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
        has_google = bool(os.getenv("GOOGLE_API_KEY"))

        return has_openai or has_anthropic or has_google
    except Exception as e:
        logger.error("ai_provider_health_check_failed", error=str(e))
        return False


async def check_metrics_system() -> bool:
    """Check if metrics system is working"""
    try:
        # Try to record a test metric
        from monitoring.metrics import active_qubes
        # Just check if the metric exists
        return active_qubes is not None
    except Exception as e:
        logger.error("metrics_health_check_failed", error=str(e))
        return False


# Register default health checks
health_checker.register_dependency("storage", check_storage)
health_checker.register_dependency("ai_providers", check_ai_providers)
health_checker.register_dependency("metrics_system", check_metrics_system)


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("🏥 Qubes Health Check Server")
    print("=" * 70)
    print("\nEndpoints:")
    print("  GET /health         - Liveness check")
    print("  GET /health/ready   - Readiness check")
    print("  GET /health/metrics - Prometheus metrics")
    print("  GET /health/info    - System information")
    print("\nStarting server on http://0.0.0.0:8080")
    print("=" * 70 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
