import os
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Server Configuration
    BACKEND_HOST: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    BACKEND_PORT: int = Field(default=8000, env="BACKEND_PORT")
    PROJECT_NAME: str = Field(default="ComfyUI-like Service", env="PROJECT_NAME")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=["http://localhost:3000", "http://localhost:8080", "https://localhost:3000"],
        env="BACKEND_CORS_ORIGINS"
    )

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database Configuration
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis Configuration
    REDIS_URL: str = Field(..., env="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")
    
    # Storage Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_BUCKET_NAME: str = Field(default="comfyui-images", env="AWS_BUCKET_NAME")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    CDN_URL: Optional[str] = Field(default=None, env="CDN_URL")
    
    # Model Configuration
    HUGGINGFACE_TOKEN: Optional[str] = Field(default=None, env="HUGGINGFACE_TOKEN")
    MODEL_CACHE_DIR: str = Field(default="/tmp/models", env="MODEL_CACHE_DIR")
    DEFAULT_MODEL: str = Field(
        default="stabilityai/stable-diffusion-xl-base-1.0", 
        env="DEFAULT_MODEL"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="RATE_LIMIT_PER_MINUTE")
    PREMIUM_RATE_LIMIT_PER_MINUTE: int = Field(default=50, env="PREMIUM_RATE_LIMIT_PER_MINUTE")
    
    # Environment
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="info", env="LOG_LEVEL")
    
    # Generation Defaults
    DEFAULT_IMAGE_SIZE: str = Field(default="1024x1024", env="DEFAULT_IMAGE_SIZE")
    MAX_BATCH_SIZE: int = Field(default=4, env="MAX_BATCH_SIZE")
    DEFAULT_STEPS: int = Field(default=50, env="DEFAULT_STEPS")
    DEFAULT_CFG_SCALE: float = Field(default=7.5, env="DEFAULT_CFG_SCALE")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# Celery Configuration
def make_celery():
    from celery import Celery
    
    celery_app = Celery(
        "comfyui_service",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.workers.celery_worker"]
    )
    
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_routes={
            "app.workers.celery_worker.generate_image": {"queue": "generation"},
            "app.workers.celery_worker.cleanup_old_jobs": {"queue": "maintenance"},
        },
        beat_schedule={
            "cleanup-old-jobs": {
                "task": "app.workers.celery_worker.cleanup_old_jobs",
                "schedule": 3600.0,  # Run every hour
            },
        },
    )
    
    return celery_app


celery_app = make_celery()