from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import structlog

from app.core.config import settings
from app.models.database import get_db
from app.models.schemas import Model, ModelCreate, ModelUpdate
from app.services.model_service import ModelService

router = APIRouter()
logger = structlog.get_logger()


@router.get("/models", response_model=List[Model])
async def get_models(
    model_type: str = Query(None, regex="^(diffusion|upscaler|processor)$"),
    active_only: bool = Query(True, description="Show only active models"),
    db: Session = Depends(get_db),
):
    """
    Get all available models.
    """
    try:
        model_service = ModelService(db)
        models = await model_service.get_models(
            model_type=model_type,
            active_only=active_only
        )
        return models
    except Exception as e:
        logger.error("Failed to fetch models", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch models")


@router.get("/models/{model_id}", response_model=Model)
async def get_model(
    model_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific model by ID.
    """
    try:
        model_service = ModelService(db)
        model = await model_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch model", model_id=str(model_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch model")


@router.post("/models", response_model=Model)
async def create_model(
    model_data: ModelCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new model.
    """
    try:
        model_service = ModelService(db)
        model = await model_service.create_model(model_data)
        logger.info("Model created", model_id=str(model.id), name=model.name)
        return model
    except Exception as e:
        logger.error("Failed to create model", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to create model")


@router.put("/models/{model_id}", response_model=Model)
async def update_model(
    model_id: UUID,
    model_data: ModelUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing model.
    """
    try:
        model_service = ModelService(db)
        model = await model_service.update_model(model_id, model_data)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        logger.info("Model updated", model_id=str(model_id))
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update model", model_id=str(model_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to update model")


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a model (soft delete by setting is_active=False).
    """
    try:
        model_service = ModelService(db)
        success = await model_service.delete_model(model_id)
        if not success:
            raise HTTPException(status_code=404, detail="Model not found")
        logger.info("Model deleted", model_id=str(model_id))
        return {"message": "Model deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete model", model_id=str(model_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to delete model")


@router.get("/models/stats")
async def get_model_stats(db: Session = Depends(get_db)):
    """
    Get model usage statistics.
    """
    try:
        model_service = ModelService(db)
        stats = await model_service.get_model_stats()
        return stats
    except Exception as e:
        logger.error("Failed to fetch model stats", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch model statistics")