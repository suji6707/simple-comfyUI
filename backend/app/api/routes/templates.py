from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import structlog

from app.core.config import settings
from app.models.database import get_db
from app.models.schemas import Template, TemplateCreate, TemplateUpdate
from app.services.template_service import TemplateService

router = APIRouter()
logger = structlog.get_logger()


@router.get("/templates", response_model=List[Template])
async def get_templates(
    category: str = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Show only active templates"),
    db: Session = Depends(get_db),
):
    """
    Get all available generation templates.
    """
    try:
        template_service = TemplateService(db)
        templates = await template_service.get_templates(
            category=category,
            active_only=active_only
        )
        return templates
    except Exception as e:
        logger.error("Failed to fetch templates", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch templates")


@router.get("/templates/{template_id}", response_model=Template)
async def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific template by ID.
    """
    try:
        template_service = TemplateService(db)
        template = await template_service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch template", template_id=str(template_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch template")


@router.post("/templates", response_model=Template)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new generation template.
    """
    try:
        template_service = TemplateService(db)
        template = await template_service.create_template(template_data)
        logger.info("Template created", template_id=str(template.id), name=template.name)
        return template
    except Exception as e:
        logger.error("Failed to create template", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to create template")


@router.put("/templates/{template_id}", response_model=Template)
async def update_template(
    template_id: UUID,
    template_data: TemplateUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing template.
    """
    try:
        template_service = TemplateService(db)
        template = await template_service.update_template(template_id, template_data)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        logger.info("Template updated", template_id=str(template_id))
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update template", template_id=str(template_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to update template")


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a template (soft delete by setting is_active=False).
    """
    try:
        template_service = TemplateService(db)
        success = await template_service.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        logger.info("Template deleted", template_id=str(template_id))
        return {"message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete template", template_id=str(template_id), exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to delete template")


@router.get("/templates/categories")
async def get_template_categories(db: Session = Depends(get_db)):
    """
    Get all available template categories.
    """
    try:
        template_service = TemplateService(db)
        categories = await template_service.get_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error("Failed to fetch template categories", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch categories")