from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
import structlog

from app.models.database import Model as ModelModel
from app.models.schemas import Model, ModelCreate, ModelUpdate

logger = structlog.get_logger()


class ModelService:
    def __init__(self, db: Session):
        self.db = db

    async def get_models(
        self, 
        model_type: Optional[str] = None, 
        active_only: bool = True
    ) -> List[Model]:
        """
        Get all models with optional filtering.
        """
        query = self.db.query(ModelModel)
        
        filters = []
        if active_only:
            filters.append(ModelModel.is_active == True)
        if model_type:
            filters.append(ModelModel.model_type == model_type)
        
        if filters:
            query = query.filter(and_(*filters))
        
        db_models = query.order_by(ModelModel.created_at.desc()).all()
        return [Model.model_validate(model) for model in db_models]

    async def get_model(self, model_id: UUID) -> Optional[Model]:
        """
        Get a specific model by ID.
        """
        db_model = self.db.query(ModelModel).filter(
            ModelModel.id == model_id
        ).first()
        
        if db_model:
            return Model.model_validate(db_model)
        return None

    async def get_model_by_name(self, name: str) -> Optional[Model]:
        """
        Get a model by name.
        """
        db_model = self.db.query(ModelModel).filter(
            ModelModel.name == name
        ).first()
        
        if db_model:
            return Model.model_validate(db_model)
        return None

    async def create_model(self, model_data: ModelCreate) -> Model:
        """
        Create a new model.
        """
        db_model = ModelModel(**model_data.model_dump())
        self.db.add(db_model)
        self.db.commit()
        self.db.refresh(db_model)
        
        logger.info("Model created", model_id=str(db_model.id), name=db_model.name)
        return Model.model_validate(db_model)

    async def update_model(
        self, 
        model_id: UUID, 
        model_data: ModelUpdate
    ) -> Optional[Model]:
        """
        Update an existing model.
        """
        db_model = self.db.query(ModelModel).filter(
            ModelModel.id == model_id
        ).first()
        
        if not db_model:
            return None
        
        update_data = model_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_model, field, value)
        
        self.db.commit()
        self.db.refresh(db_model)
        
        logger.info("Model updated", model_id=str(model_id))
        return Model.model_validate(db_model)

    async def delete_model(self, model_id: UUID) -> bool:
        """
        Soft delete a model by setting is_active=False.
        """
        db_model = self.db.query(ModelModel).filter(
            ModelModel.id == model_id
        ).first()
        
        if not db_model:
            return False
        
        db_model.is_active = False
        self.db.commit()
        
        logger.info("Model deleted", model_id=str(model_id))
        return True

    async def get_model_stats(self) -> Dict[str, Any]:
        """
        Get model usage statistics.
        """
        # Count models by type
        model_counts = {}
        for model_type in ["diffusion", "upscaler", "processor"]:
            count = self.db.query(ModelModel).filter(
                and_(
                    ModelModel.model_type == model_type,
                    ModelModel.is_active == True
                )
            ).count()
            model_counts[model_type] = count
        
        # Get total active models
        total_active = self.db.query(ModelModel).filter(
            ModelModel.is_active == True
        ).count()
        
        # Get models with fastest average inference time
        fastest_models = self.db.query(ModelModel).filter(
            and_(
                ModelModel.is_active == True,
                ModelModel.average_inference_time.isnot(None)
            )
        ).order_by(ModelModel.average_inference_time).limit(5).all()
        
        return {
            "total_active_models": total_active,
            "models_by_type": model_counts,
            "fastest_models": [
                {
                    "name": model.name,
                    "type": model.model_type,
                    "average_time": model.average_inference_time
                }
                for model in fastest_models
            ]
        }

    async def get_compatible_models(
        self, 
        workflow_config: Dict[str, Any]
    ) -> List[Model]:
        """
        Get models compatible with a specific workflow configuration.
        """
        # This would contain logic to match models to workflow requirements
        # For now, return all active diffusion models
        return await self.get_models(model_type="diffusion", active_only=True)

    async def update_model_performance(
        self, 
        model_name: str, 
        inference_time: float
    ):
        """
        Update model performance statistics.
        """
        db_model = self.db.query(ModelModel).filter(
            ModelModel.name == model_name
        ).first()
        
        if not db_model:
            return
        
        # Calculate rolling average
        if db_model.average_inference_time:
            # Simple exponential moving average (alpha = 0.1)
            new_average = (0.9 * db_model.average_inference_time) + (0.1 * inference_time)
        else:
            new_average = inference_time
        
        db_model.average_inference_time = int(new_average)
        self.db.commit()
        
        logger.debug(
            "Model performance updated",
            model_name=model_name,
            inference_time=inference_time,
            new_average=new_average
        )