from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import structlog
import json
import asyncio

from app.core.config import settings
from app.models.database import get_db
from app.models.schemas import (
    GenerationRequest, GenerationJob, GenerationJobUpdate, SSEProgressMessage
)
from app.services.generation_service import GenerationService
from app.api.dependencies import get_current_user, rate_limit

router = APIRouter()
logger = structlog.get_logger()


@router.post("/generate", response_model=GenerationJob)
async def submit_generation(
    request_data: GenerationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    _: None = Depends(rate_limit),
):
    """
    Submit a new image generation request.
    """
    try:
        generation_service = GenerationService(db)
        job = await generation_service.submit_generation(
            user_id=current_user,
            request_data=request_data,
            client_ip=request.client.host
        )
        
        logger.info(
            "Generation job submitted",
            job_id=str(job.job_id),
            user_id=current_user,
            template_id=str(request_data.template_id)
        )
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit generation", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to submit generation request")


@router.get("/generate/{job_id}/status", response_model=GenerationJob)
async def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Get the status of a specific generation job.
    """
    try:
        generation_service = GenerationService(db)
        job = await generation_service.get_job(job_id, user_id=current_user)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch job status", job_id=str(job_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch job status")


@router.get("/generate/{job_id}/stream")
async def stream_job_progress(
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Server-Sent Events endpoint for real-time job progress updates.
    """
    try:
        generation_service = GenerationService(db)
        job = await generation_service.get_job(job_id, user_id=current_user)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        async def event_generator():
            try:
                # Send initial status
                initial_message = SSEProgressMessage(
                    job_id=job_id,
                    status=job.status,
                    progress=job.progress,
                    queue_position=job.queue_position,
                    message="Connected to job stream"
                )
                yield f"data: {initial_message.model_dump_json()}\n\n"
                
                # Stream updates until job is completed or failed
                while job.status in ["queued", "processing"]:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.info("Client disconnected from SSE stream", job_id=str(job_id))
                        break
                    
                    # Fetch updated job status
                    updated_job = await generation_service.get_job(job_id, user_id=current_user)
                    if updated_job and (updated_job.status != job.status or updated_job.progress != job.progress):
                        job = updated_job
                        message = SSEProgressMessage(
                            job_id=job_id,
                            status=job.status,
                            progress=job.progress,
                            queue_position=job.queue_position,
                            results=job.results if job.status == "completed" else None,
                            error=job.error_details if job.status == "failed" else None
                        )
                        yield f"data: {message.model_dump_json()}\n\n"
                        
                        # If job is completed or failed, send final message and break
                        if job.status in ["completed", "failed"]:
                            break
                    
                    await asyncio.sleep(1)  # Poll every second
                
                # Send final status
                final_message = SSEProgressMessage(
                    job_id=job_id,
                    status=job.status,
                    progress=job.progress,
                    message="Stream ended",
                    results=job.results if job.status == "completed" else None,
                    error=job.error_details if job.status == "failed" else None
                )
                yield f"data: {final_message.model_dump_json()}\n\n"
                
            except Exception as e:
                logger.error("Error in SSE stream", job_id=str(job_id), exc_info=e)
                error_message = SSEProgressMessage(
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    error="Stream error occurred"
                )
                yield f"data: {error_message.model_dump_json()}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create SSE stream", job_id=str(job_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to create progress stream")


@router.get("/history", response_model=List[GenerationJob])
async def get_generation_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, regex="^(queued|processing|completed|failed|cancelled)$"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Get user's generation history with pagination.
    """
    try:
        generation_service = GenerationService(db)
        jobs = await generation_service.get_user_jobs(
            user_id=current_user,
            limit=limit,
            offset=offset,
            status_filter=status
        )
        return jobs
    except Exception as e:
        logger.error("Failed to fetch generation history", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch generation history")


@router.delete("/generate/{job_id}")
async def cancel_generation(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Cancel a queued or processing generation job.
    """
    try:
        generation_service = GenerationService(db)
        success = await generation_service.cancel_job(job_id, user_id=current_user)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Job not found or cannot be cancelled"
            )
        
        logger.info("Generation job cancelled", job_id=str(job_id), user_id=current_user)
        return {"message": "Job cancelled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel job", job_id=str(job_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/queue/stats")
async def get_queue_stats(db: Session = Depends(get_db)):
    """
    Get current queue statistics.
    """
    try:
        generation_service = GenerationService(db)
        stats = await generation_service.get_queue_stats()
        return stats
    except Exception as e:
        logger.error("Failed to fetch queue stats", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch queue statistics")