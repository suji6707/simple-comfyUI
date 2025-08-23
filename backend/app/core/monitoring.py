import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import structlog

logger = structlog.get_logger()

# Prometheus metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

generation_count = Counter(
    'generation_jobs_total',
    'Total generation jobs',
    ['status', 'template']
)

generation_duration = Histogram(
    'generation_duration_seconds',
    'Generation duration in seconds',
    ['template', 'status']
)

active_jobs = Gauge(
    'active_generation_jobs',
    'Number of active generation jobs'
)

queue_size = Gauge(
    'queue_size',
    'Current queue size',
    ['queue_name']
)

model_usage = Counter(
    'model_usage_total',
    'Model usage count',
    ['model_name', 'model_type']
)

error_count = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'component']
)

# Circuit breaker state
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 0.5=half-open)',
    ['service']
)


class MetricsMiddleware:
    """
    Middleware to collect HTTP request metrics.
    """
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = time.time()
        
        # Skip metrics endpoint to avoid infinite recursion
        if request.url.path == "/metrics":
            await self.app(scope, receive, send)
            return

        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = 500
            error_count.labels(
                error_type=type(e).__name__,
                component="http_middleware"
            ).inc()
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            method = request.method
            path = request.url.path
            
            # Normalize path for metrics (remove IDs, etc.)
            normalized_path = self._normalize_path(path)
            
            request_count.labels(
                method=method,
                endpoint=normalized_path,
                status_code=status_code
            ).inc()
            
            request_duration.labels(
                method=method,
                endpoint=normalized_path
            ).observe(duration)

    def _normalize_path(self, path: str) -> str:
        """
        Normalize paths by replacing IDs with placeholders.
        """
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path
        )
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


class MonitoringService:
    """
    Service for tracking application metrics and health.
    """
    
    @staticmethod
    def record_generation_start(template_name: str):
        """Record when a generation job starts."""
        active_jobs.inc()
        logger.info("Generation started", template=template_name)

    @staticmethod
    def record_generation_complete(
        template_name: str, 
        duration: float, 
        status: str,
        error_type: Optional[str] = None
    ):
        """Record when a generation job completes."""
        active_jobs.dec()
        
        generation_count.labels(
            status=status,
            template=template_name
        ).inc()
        
        generation_duration.labels(
            template=template_name,
            status=status
        ).observe(duration)
        
        if error_type:
            error_count.labels(
                error_type=error_type,
                component="generation"
            ).inc()
        
        logger.info(
            "Generation completed",
            template=template_name,
            duration=duration,
            status=status,
            error_type=error_type
        )

    @staticmethod
    def record_model_usage(model_name: str, model_type: str):
        """Record model usage."""
        model_usage.labels(
            model_name=model_name,
            model_type=model_type
        ).inc()

    @staticmethod
    def update_queue_size(queue_name: str, size: int):
        """Update queue size metric."""
        queue_size.labels(queue_name=queue_name).set(size)

    @staticmethod
    def record_error(error_type: str, component: str):
        """Record an error occurrence."""
        error_count.labels(
            error_type=error_type,
            component=component
        ).inc()
        
        logger.error(
            "Error recorded",
            error_type=error_type,
            component=component
        )

    @staticmethod
    def set_circuit_breaker_state(service: str, state: float):
        """Set circuit breaker state (0=closed, 1=open, 0.5=half-open)."""
        circuit_breaker_state.labels(service=service).set(state)


def get_metrics():
    """Get Prometheus metrics."""
    return generate_latest()


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        """
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker moving to half-open state")
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            
            # Reset on success
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed")
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(
                    "Circuit breaker opened",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )
            
            raise


class HealthChecker:
    """
    Health check service for system components.
    """
    
    def __init__(self):
        self.checks = {}

    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                result = await check_func()
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "details": result
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.error(f"Health check failed for {name}", exc_info=e)
        
        return results

    async def get_overall_status(self) -> str:
        """Get overall system health status."""
        results = await self.run_all_checks()
        
        if all(r["status"] == "healthy" for r in results.values()):
            return "healthy"
        elif any(r["status"] == "error" for r in results.values()):
            return "error"
        else:
            return "degraded"


# Global instances
monitoring_service = MonitoringService()
health_checker = HealthChecker()

# Circuit breakers for external services
model_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
storage_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)