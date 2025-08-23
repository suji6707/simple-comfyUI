import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import structlog

from app.models.database import GenerationJob as GenerationJobModel, GenerationResult as GenerationResultModel
from app.models.schemas import (
    GenerationRequest, GenerationJob, GenerationJobCreate, GenerationJobUpdate,
    GenerationResult
)
from app.services.template_service import TemplateService
from app.workers.celery_worker import generate_image

logger = structlog.get_logger()


class GenerationService:
    def __init__(self, db: Session):
        self.db = db
        self.template_service = TemplateService(db)

    async def submit_generation(
        self, 
        user_id: str, 
        request_data: GenerationRequest,
        client_ip: str = None
    ) -> GenerationJob:
        """
        Submit a new generation request to the queue.
        """
        # Validate template exists and is active
        template = await self.template_service.get_template(request_data.template_id)
        if not template or not template.is_active:
            raise ValueError("Template not found or inactive")
        
        # Create job record
        job_data = GenerationJobCreate(
            user_id=user_id,
            template_id=request_data.template_id,
            prompt=request_data.prompt,
            parameters=request_data.parameters,
            status="queued"
        )
        
        db_job = GenerationJobModel(**job_data.model_dump())
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        
        # Submit to Celery queue
        task = generate_image.delay(
            job_id=str(db_job.job_id),
            template_config=template.workflow_config,
            prompt=request_data.prompt,
            parameters=request_data.parameters
        )
        
        logger.info(
            "Generation job submitted to queue",
            job_id=str(db_job.job_id),
            user_id=user_id,
            template_id=str(request_data.template_id),
            celery_task_id=task.id
        )
        
        # Update queue position
        queue_position = await self._calculate_queue_position(db_job.job_id)
        db_job.queue_position = queue_position
        self.db.commit()
        self.db.refresh(db_job)
        
        return GenerationJob.model_validate(db_job)

    async def get_job(self, job_id: UUID, user_id: str = None) -> Optional[GenerationJob]:
        """
        Get a generation job by ID.
        """
        query = self.db.query(GenerationJobModel).filter(
            GenerationJobModel.job_id == job_id
        )
        
        # Add user filtering for non-admin requests
        if user_id and user_id != "admin":
            query = query.filter(GenerationJobModel.user_id == user_id)
        
        db_job = query.first()
        if not db_job:
            return None
        
        return GenerationJob.model_validate(db_job)

    async def update_job_status(
        self, 
        job_id: UUID, 
        update_data: GenerationJobUpdate
    ) -> Optional[GenerationJob]:
        """
        Update job status and progress.
        """
        db_job = self.db.query(GenerationJobModel).filter(
            GenerationJobModel.job_id == job_id
        ).first()
        
        if not db_job:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(db_job, field, value)
        
        # Set timestamps based on status
        if update_data.status == "processing" and not db_job.started_at:
            db_job.started_at = datetime.utcnow()
        elif update_data.status in ["completed", "failed"] and not db_job.completed_at:
            db_job.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_job)
        
        logger.info(
            "Job status updated",
            job_id=str(job_id),
            status=update_data.status,
            progress=update_data.progress
        )
        
        return GenerationJob.model_validate(db_job)

    async def add_job_result(
        self, 
        job_id: UUID, 
        image_url: str, 
        thumbnail_url: str = None,
        metadata: Dict[str, Any] = None
    ) -> GenerationResult:
        """
        Add a generated image result to a job.
        """
        db_result = GenerationResultModel(
            job_id=job_id,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            metadata=metadata or {}
        )
        
        self.db.add(db_result)
        self.db.commit()
        self.db.refresh(db_result)
        
        logger.info(
            "Result added to job",
            job_id=str(job_id),
            result_id=str(db_result.id)
        )
        
        return GenerationResult.model_validate(db_result)

    async def get_user_jobs(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[GenerationJob]:
        """
        Get user's generation history.
        """
        query = self.db.query(GenerationJobModel).filter(
            GenerationJobModel.user_id == user_id
        )
        
        if status_filter:
            query = query.filter(GenerationJobModel.status == status_filter)
        
        db_jobs = query.order_by(desc(GenerationJobModel.created_at)).offset(offset).limit(limit).all()
        
        return [GenerationJob.model_validate(job) for job in db_jobs]

    async def cancel_job(self, job_id: UUID, user_id: str) -> bool:
        """
        Cancel a queued or processing job.
        """
        db_job = self.db.query(GenerationJobModel).filter(
            and_(
                GenerationJobModel.job_id == job_id,
                GenerationJobModel.user_id == user_id,
                GenerationJobModel.status.in_(["queued", "processing"])
            )
        ).first()
        
        if not db_job:
            return False
        
        # TODO: Cancel Celery task
        # from app.core.config import celery_app
        # celery_app.control.revoke(task_id, terminate=True)
        
        db_job.status = "failed"
        db_job.error_details = "Cancelled by user"
        db_job.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info("Job cancelled", job_id=str(job_id), user_id=user_id)
        return True

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get current queue statistics.
        """
        # Count jobs by status
        queued_count = self.db.query(GenerationJobModel).filter(
            GenerationJobModel.status == "queued"
        ).count()
        
        processing_count = self.db.query(GenerationJobModel).filter(
            GenerationJobModel.status == "processing"
        ).count()
        
        completed_today = self.db.query(GenerationJobModel).filter(
            and_(
                GenerationJobModel.status == "completed",
                GenerationJobModel.completed_at >= datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            )
        ).count()
        
        # Calculate average processing time
        avg_processing_time = self._calculate_average_processing_time()
        
        # Estimate wait time based on queue position
        estimated_wait_time = queued_count * avg_processing_time if avg_processing_time else None
        
        return {
            "queued_jobs": queued_count,
            "processing_jobs": processing_count,
            "completed_today": completed_today,
            "average_processing_time": avg_processing_time,
            "estimated_wait_time": estimated_wait_time
        }

    async def _calculate_queue_position(self, job_id: UUID) -> int:
        """
        Calculate queue position for a job.
        """
        # Count jobs that were created before this job and are still queued
        db_job = self.db.query(GenerationJobModel).filter(
            GenerationJobModel.job_id == job_id
        ).first()
        
        if not db_job:
            return 0
        
        position = self.db.query(GenerationJobModel).filter(
            and_(
                GenerationJobModel.status == "queued",
                GenerationJobModel.created_at < db_job.created_at
            )
        ).count()
        
        return position + 1

    def _calculate_average_processing_time(self) -> Optional[float]:
        """
        Calculate average processing time in seconds.
        """
        # Get completed jobs from last 24 hours
        since = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        completed_jobs = self.db.query(GenerationJobModel).filter(
            and_(
                GenerationJobModel.status == "completed",
                GenerationJobModel.completed_at >= since,
                GenerationJobModel.started_at.isnot(None),
                GenerationJobModel.completed_at.isnot(None)
            )
        ).all()
        
        if not completed_jobs:
            return None
        
        total_time = sum(
            (job.completed_at - job.started_at).total_seconds()
            for job in completed_jobs
        )
        
        return total_time / len(completed_jobs)