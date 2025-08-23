import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID
import structlog

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from sqlalchemy.orm import Session

# Import after Celery setup to avoid circular imports
from app.core.config import settings, celery_app
from app.core.workflow_engine import WorkflowEngine, ExecutionContext
from app.models.database import get_db, GenerationJob as GenerationJobModel, GenerationResult as GenerationResultModel
from app.services.generation_service import GenerationService

logger = structlog.get_logger()

# Initialize workflow engine
workflow_engine = WorkflowEngine()


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handler called before task execution."""
    logger.info("Task started", task_id=task_id, task_name=task.name)


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handler called after task execution."""
    logger.info("Task completed", task_id=task_id, task_name=task.name, state=state)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, traceback=None, **kwds):
    """Handler called on task failure."""
    logger.error("Task failed", task_id=task_id, exception=str(exception), traceback=traceback)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_image(
    self,
    job_id: str,
    template_config: Dict[str, Any],
    prompt: str,
    parameters: Dict[str, Any] = None
):
    """
    Main task for generating images using the workflow engine.
    """
    parameters = parameters or {}
    start_time = time.time()
    
    logger.info(
        "Starting image generation",
        job_id=job_id,
        task_id=self.request.id,
        prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt
    )
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Update job status to processing
        generation_service = GenerationService(db)
        asyncio.run(generation_service.update_job_status(
            UUID(job_id),
            {"status": "processing", "progress": 0}
        ))
        
        # Create execution context
        context = ExecutionContext(
            job_id=job_id,
            user_id="worker",  # TODO: Get actual user_id from job
            initial_data={
                "prompt": prompt,
                "parameters": parameters
            }
        )
        
        # Create workflow from template config
        workflow = workflow_engine.create_workflow_from_config(template_config)
        
        # Progress callback to update job progress
        async def progress_callback(progress: int, message: str = None):
            try:
                await generation_service.update_job_status(
                    UUID(job_id),
                    {
                        "progress": progress,
                        "status": "processing" if progress < 100 else "processing"
                    }
                )
                logger.info(
                    "Generation progress update",
                    job_id=job_id,
                    progress=progress,
                    message=message
                )
            except Exception as e:
                logger.error("Failed to update progress", job_id=job_id, error=str(e))
        
        # Execute workflow
        logger.info("Executing workflow", job_id=job_id)
        outputs = asyncio.run(workflow.execute(context, progress_callback))
        
        # Process results
        saved_images = outputs.get("saved_images", [])
        if not saved_images:
            raise ValueError("No images were generated")
        
        # Save results to database
        for image_data in saved_images:
            asyncio.run(generation_service.add_job_result(
                UUID(job_id),
                image_data["image_url"],
                image_data.get("thumbnail_url"),
                image_data.get("metadata", {})
            ))
        
        # Update job to completed
        asyncio.run(generation_service.update_job_status(
            UUID(job_id),
            {
                "status": "completed",
                "progress": 100
            }
        ))
        
        generation_time = time.time() - start_time
        logger.info(
            "Image generation completed",
            job_id=job_id,
            generation_time=generation_time,
            images_generated=len(saved_images)
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "images_generated": len(saved_images),
            "generation_time": generation_time,
            "results": saved_images
        }
    
    except Exception as exc:
        generation_time = time.time() - start_time
        error_message = str(exc)
        
        logger.error(
            "Image generation failed",
            job_id=job_id,
            error=error_message,
            generation_time=generation_time,
            exc_info=exc
        )
        
        # Update job to failed
        try:
            asyncio.run(generation_service.update_job_status(
                UUID(job_id),
                {
                    "status": "failed",
                    "error_details": error_message
                }
            ))
        except Exception as db_error:
            logger.error("Failed to update job status to failed", error=str(db_error))
        
        # Retry logic
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)  # Exponential backoff
            logger.info(
                "Retrying image generation",
                job_id=job_id,
                retry_count=self.request.retries + 1,
                retry_delay=retry_delay
            )
            raise self.retry(countdown=retry_delay, exc=exc)
        
        # Max retries reached
        raise exc
    
    finally:
        db.close()


@celery_app.task(bind=True)
def upscale_image(
    self,
    job_id: str,
    image_url: str,
    scale_factor: int = 4,
    model: str = "RealESRGAN_x4plus"
):
    """
    Task for upscaling images.
    """
    logger.info("Starting image upscaling", job_id=job_id, image_url=image_url, scale_factor=scale_factor)
    
    # TODO: Implement actual image upscaling
    # For now, return mock result
    time.sleep(5)  # Simulate processing time
    
    upscaled_url = image_url.replace(".jpg", "_upscaled.jpg")
    
    return {
        "success": True,
        "original_url": image_url,
        "upscaled_url": upscaled_url,
        "scale_factor": scale_factor,
        "model": model
    }


@celery_app.task(bind=True)
def process_batch_generation(
    self,
    user_id: str,
    job_ids: list[str],
    batch_config: Dict[str, Any]
):
    """
    Task for processing multiple image generations in a batch.
    """
    logger.info("Starting batch generation", user_id=user_id, job_count=len(job_ids))
    
    results = []
    for job_id in job_ids:
        try:
            # Submit individual generation task
            result = generate_image.delay(
                job_id=job_id,
                template_config=batch_config["template_config"],
                prompt=batch_config["prompt"],
                parameters=batch_config.get("parameters", {})
            )
            results.append({"job_id": job_id, "task_id": result.id, "status": "submitted"})
        except Exception as e:
            logger.error("Failed to submit batch job", job_id=job_id, error=str(e))
            results.append({"job_id": job_id, "status": "failed", "error": str(e)})
    
    return {
        "batch_id": self.request.id,
        "user_id": user_id,
        "total_jobs": len(job_ids),
        "results": results
    }


@celery_app.task
def cleanup_old_jobs():
    """
    Periodic task to cleanup old completed/failed jobs.
    """
    logger.info("Starting job cleanup task")
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Delete jobs older than 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        old_jobs = db.query(GenerationJobModel).filter(
            GenerationJobModel.created_at < cutoff_date,
            GenerationJobModel.status.in_(["completed", "failed"])
        ).all()
        
        deleted_count = 0
        for job in old_jobs:
            # Delete associated results first
            db.query(GenerationResultModel).filter(
                GenerationResultModel.job_id == job.job_id
            ).delete()
            
            # Delete the job
            db.delete(job)
            deleted_count += 1
        
        db.commit()
        
        logger.info("Job cleanup completed", deleted_jobs=deleted_count)
        return {"deleted_jobs": deleted_count}
    
    except Exception as e:
        logger.error("Job cleanup failed", error=str(e))
        db.rollback()
        raise
    
    finally:
        db.close()


@celery_app.task
def health_check():
    """
    Simple health check task for monitoring worker status.
    """
    return {
        "status": "healthy",
        "worker_id": os.environ.get("HOSTNAME", "unknown"),
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task
def model_warmup(model_name: str):
    """
    Task to warm up a model by loading it into memory.
    """
    logger.info("Starting model warmup", model=model_name)
    
    # TODO: Implement actual model loading/warming
    time.sleep(10)  # Simulate model loading time
    
    logger.info("Model warmup completed", model=model_name)
    return {
        "model": model_name,
        "status": "warmed_up",
        "timestamp": datetime.utcnow().isoformat()
    }


# Task routing configuration
celery_app.conf.task_routes = {
    "app.workers.celery_worker.generate_image": {"queue": "generation"},
    "app.workers.celery_worker.upscale_image": {"queue": "upscaling"},
    "app.workers.celery_worker.process_batch_generation": {"queue": "batch"},
    "app.workers.celery_worker.cleanup_old_jobs": {"queue": "maintenance"},
    "app.workers.celery_worker.health_check": {"queue": "health"},
    "app.workers.celery_worker.model_warmup": {"queue": "models"},
}


# Additional Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Monitoring
    send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Memory management
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=500000,  # 500MB
)