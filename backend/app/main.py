import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.api.routes import templates, generation, models, health
from app.models.database import engine, Base


# Configure structured logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper()))
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up ComfyUI Service API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Initialize default templates
    from app.services.template_service import TemplateService
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        template_service = TemplateService(db)
        await template_service.initialize_default_templates()
    finally:
        db.close()
    logger.info("Default templates initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ComfyUI Service API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="A ComfyUI-like image generation service with template-based workflows",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(
        "Global exception handler",
        exc_info=exc,
        request_url=str(request.url),
        request_method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        }
    )


# Include routers
app.include_router(
    health.router,
    prefix=settings.API_V1_STR,
    tags=["health"]
)

app.include_router(
    templates.router,
    prefix=settings.API_V1_STR,
    tags=["templates"]
)

app.include_router(
    generation.router,
    prefix=settings.API_V1_STR,
    tags=["generation"]
)

app.include_router(
    models.router,
    prefix=settings.API_V1_STR,
    tags=["models"]
)


@app.get("/")
async def root():
    return {
        "message": "ComfyUI-like Image Generation Service",
        "version": "1.0.0",
        "docs_url": f"{settings.API_V1_STR}/docs"
    }