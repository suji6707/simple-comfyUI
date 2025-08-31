import uuid
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import settings

# 데이터베이스 연결
engine = create_engine(settings.DATABASE_URL)
# Session 클래스 생성. 트랜잭션 등 작업단위 관리: 수동커밋 후 db.flush -> 트랜잭션 명시적으로 관리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

'''
모든 ORM 모델이 Base를 상속.
테이블 메타데이터를 관리하고 매핑된 클래스를 데이터베이스 스키마에 연결하는 역할
'''
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Template(Base):
    __tablename__ = "templates" # 이 클래스가 매핑될 데이터베이스 테이블의 이름을 지정

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # default로 생성
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(50), index=True)
    workflow_config = Column(JSON, nullable=False)
    example_images = Column(JSON, default=list)
    parameters = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    generation_jobs = relationship("GenerationJob", back_populates="template")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    parameters = Column(JSON, default=dict)
    status = Column(String(20), default="queued", index=True)
    progress = Column(Integer, default=0)
    queue_position = Column(Integer)
    celery_task_id = Column(String(100), index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    error_details = Column(Text)

    # Relationships
    template = relationship("Template", back_populates="generation_jobs")
    results = relationship("GenerationResult", back_populates="job", cascade="all, delete-orphan")


class GenerationResult(Base):
    __tablename__ = "generation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("generation_jobs.job_id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    result_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("GenerationJob", back_populates="results")


class Model(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True, index=True)
    model_type = Column(String(50), nullable=False)  # 'diffusion', 'upscaler', 'processor'
    version = Column(String(50))
    huggingface_id = Column(String(200))
    local_path = Column(String(500))
    is_active = Column(Boolean, default=True)
    resource_requirements = Column(JSON, default=dict)  # GPU memory, compute requirements
    supported_parameters = Column(JSON, default=dict)
    average_inference_time = Column(Integer)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, index=True)
    is_active = Column(Boolean, default=True)