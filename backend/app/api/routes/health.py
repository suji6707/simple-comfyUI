from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis
import structlog

from app.core.config import settings
from app.models.database import get_db
from app.models.schemas import HealthCheck

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies all critical services are running.
    """
    services: Dict[str, str] = {}
    
    try:
        # Check database connection
        db.execute("SELECT 1")
        services["database"] = "healthy"
    except Exception as e:
        logger.error("Database health check failed", exc_info=e)
        services["database"] = "unhealthy"
    
    try:
        # Check Redis connection
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        services["redis"] = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", exc_info=e)
        services["redis"] = "unhealthy"
    
    # Check Celery (basic connection test)
    try:
        from app.core.config import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            services["celery"] = "healthy"
        else:
            services["celery"] = "no_workers"
    except Exception as e:
        logger.error("Celery health check failed", exc_info=e)
        services["celery"] = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "degraded"
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services
    )


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.
    """
    try:
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}, 503


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    """
    return {"status": "alive"}