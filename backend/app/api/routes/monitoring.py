from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST
import structlog

from app.core.monitoring import get_metrics, health_checker, monitoring_service
from app.api.dependencies import get_admin_user

router = APIRouter()
logger = structlog.get_logger()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.
    """
    return PlainTextResponse(
        content=get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status.
    """
    try:
        results = await health_checker.run_all_checks()
        overall_status = await health_checker.get_overall_status()
        
        return {
            "status": overall_status,
            "components": results,
            "timestamp": "2023-01-01T00:00:00Z"  # TODO: Use actual timestamp
        }
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2023-01-01T00:00:00Z"
        }


@router.get("/stats")
async def system_stats():
    """
    Get system statistics (admin only).
    """
    # This would typically require admin authentication
    # For now, we'll return basic stats
    
    return {
        "message": "System statistics endpoint",
        "note": "This would show detailed system metrics in production"
    }


@router.post("/test/error")
async def test_error(admin: str = Depends(get_admin_user)):
    """
    Test endpoint to trigger an error for monitoring testing.
    """
    monitoring_service.record_error("test_error", "monitoring_test")
    
    logger.error("Test error triggered by admin", admin_user=admin)
    
    raise Exception("This is a test error for monitoring")


@router.post("/test/generation")
async def test_generation_metrics(admin: str = Depends(get_admin_user)):
    """
    Test endpoint to simulate generation metrics.
    """
    import time
    import random
    
    template_name = "test_template"
    
    # Simulate generation start
    monitoring_service.record_generation_start(template_name)
    
    # Simulate processing time
    processing_time = random.uniform(10, 60)  # 10-60 seconds
    time.sleep(0.1)  # Just a brief pause for demo
    
    # Simulate completion
    status = random.choice(["completed", "failed"])
    error_type = "test_error" if status == "failed" else None
    
    monitoring_service.record_generation_complete(
        template_name=template_name,
        duration=processing_time,
        status=status,
        error_type=error_type
    )
    
    return {
        "message": "Test generation metrics recorded",
        "template": template_name,
        "duration": processing_time,
        "status": status
    }