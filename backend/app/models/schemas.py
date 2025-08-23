from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=50)
    workflow_config: Dict[str, Any]
    example_images: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    workflow_config: Optional[Dict[str, Any]] = None
    example_images: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Template(TemplateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerationRequestBase(BaseModel):
    template_id: UUID
    prompt: str = Field(..., min_length=1, max_length=2000)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @validator('parameters')
    def validate_parameters(cls, v):
        # Add parameter validation logic here
        allowed_keys = {
            'width', 'height', 'num_images', 'steps', 'cfg_scale', 
            'seed', 'negative_prompt', 'scheduler', 'style_strength'
        }
        for key in v.keys():
            if key not in allowed_keys:
                raise ValueError(f'Parameter "{key}" is not allowed')
        
        # Validate specific parameter ranges
        if 'num_images' in v and not 1 <= v['num_images'] <= 4:
            raise ValueError('num_images must be between 1 and 4')
        if 'steps' in v and not 1 <= v['steps'] <= 150:
            raise ValueError('steps must be between 1 and 150')
        if 'cfg_scale' in v and not 1.0 <= v['cfg_scale'] <= 20.0:
            raise ValueError('cfg_scale must be between 1.0 and 20.0')
        
        return v


class GenerationRequest(GenerationRequestBase):
    pass


class GenerationResultBase(BaseModel):
    image_url: str
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerationResult(GenerationResultBase):
    id: UUID
    job_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GenerationJobBase(BaseModel):
    user_id: str
    template_id: UUID
    prompt: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "queued"
    progress: int = 0
    queue_position: Optional[int] = None


class GenerationJobCreate(GenerationJobBase):
    pass


class GenerationJobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    queue_position: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None


class GenerationJob(GenerationJobBase):
    job_id: UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    error_details: Optional[str] = None
    results: List[GenerationResult] = Field(default_factory=list)
    template: Optional[Template] = None

    class Config:
        from_attributes = True


class SSEProgressMessage(BaseModel):
    job_id: UUID
    status: str
    progress: int
    queue_position: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None
    results: Optional[List[GenerationResult]] = None


class ModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    model_type: str = Field(..., pattern="^(diffusion|upscaler|processor)$")
    version: Optional[str] = Field(None, max_length=50)
    huggingface_id: Optional[str] = Field(None, max_length=200)
    local_path: Optional[str] = Field(None, max_length=500)
    is_active: bool = True
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    supported_parameters: Dict[str, Any] = Field(default_factory=dict)
    average_inference_time: Optional[int] = None


class ModelCreate(ModelBase):
    pass


class ModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    model_type: Optional[str] = Field(None, pattern="^(diffusion|upscaler|processor)$")
    version: Optional[str] = Field(None, max_length=50)
    huggingface_id: Optional[str] = Field(None, max_length=200)
    local_path: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    supported_parameters: Optional[Dict[str, Any]] = None
    average_inference_time: Optional[int] = None


class Model(ModelBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthCheck(BaseModel):
    status: str = "healthy"
    timestamp: datetime
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)