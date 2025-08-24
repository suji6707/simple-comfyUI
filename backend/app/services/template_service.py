import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from app.models.database import Template as TemplateModel
from app.models.schemas import Template, TemplateCreate, TemplateUpdate

logger = structlog.get_logger()


class TemplateService:
    def __init__(self, db: Session = None):
        self.db = db

    async def get_templates(
        self, 
        category: Optional[str] = None, 
        active_only: bool = True
    ) -> List[Template]:
        """
        Get all templates with optional filtering.
        """
        query = self.db.query(TemplateModel)
        
        filters = []
        if active_only:
            filters.append(TemplateModel.is_active == True)
        if category:
            filters.append(TemplateModel.category == category)
        
        if filters:
            query = query.filter(and_(*filters))
        
        db_templates = query.order_by(TemplateModel.created_at.desc()).all()
        return [Template.model_validate(template) for template in db_templates]

    async def get_template(self, template_id: UUID) -> Optional[Template]:
        """
        Get a specific template by ID.
        """
        db_template = self.db.query(TemplateModel).filter(
            TemplateModel.id == template_id
        ).first()
        
        if db_template:
            return Template.model_validate(db_template)
        return None

    async def create_template(self, template_data: TemplateCreate) -> Template:
        """
        Create a new template.
        """
        db_template = TemplateModel(**template_data.model_dump())
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        
        return Template.model_validate(db_template)

    async def update_template(
        self, 
        template_id: UUID, 
        template_data: TemplateUpdate
    ) -> Optional[Template]:
        """
        Update an existing template.
        """
        db_template = self.db.query(TemplateModel).filter(
            TemplateModel.id == template_id
        ).first()
        
        if not db_template:
            return None
        
        update_data = template_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_template, field, value)
        
        self.db.commit()
        self.db.refresh(db_template)
        
        return Template.model_validate(db_template)

    async def delete_template(self, template_id: UUID) -> bool:
        """
        Soft delete a template by setting is_active=False.
        """
        db_template = self.db.query(TemplateModel).filter(
            TemplateModel.id == template_id
        ).first()
        
        if not db_template:
            return False
        
        db_template.is_active = False
        self.db.commit()
        
        return True

    async def get_categories(self) -> List[str]:
        """
        Get all unique template categories.
        """
        categories = self.db.query(TemplateModel.category).distinct().all()
        return [category[0] for category in categories if category[0]]

    async def initialize_default_templates(self):
        """
        Initialize default templates if none exist.
        """
        existing_count = self.db.query(TemplateModel).count()
        if existing_count > 0:
            logger.info("Templates already exist, skipping initialization")
            return
        
        default_templates = [
            {
                "name": "Photorealistic Portrait",
                "description": "Generate high-quality photorealistic human portraits",
                "category": "Portrait",
                "workflow_config": {
                    "model": "stabilityai/stable-diffusion-xl-base-1.0",
                    "scheduler": "DPMSolverMultistep",
                    "steps": 50,
                    "cfg_scale": 7.5,
                    "width": 1024,
                    "height": 1024,
                    "pipeline": [
                        {
                            "node_type": "prompt_enhancement",
                            "parameters": {
                                "style_prompts": ["photorealistic", "high detail", "professional lighting"]
                            }
                        },
                        {
                            "node_type": "generation",
                            "parameters": {
                                "model_type": "diffusion",
                                "negative_prompt": "cartoon, anime, painting, drawing, illustration, low quality, blurry"
                            }
                        }
                    ]
                },
                "example_images": [
                    "https://www.telegraph.co.uk/multimedia/archive/02635/photorealistic_2635731k.jpg?imwidth=680"
                ],
                "parameters": {
                    "style_strength": {"type": "slider", "min": 0.1, "max": 1.0, "default": 0.7},
                    "age_range": {"type": "select", "options": ["child", "young_adult", "middle_aged", "elderly"], "default": "young_adult"},
                    "gender": {"type": "select", "options": ["male", "female", "non_binary"], "default": "female"}
                }
            },
            {
                "name": "Anime Style",
                "description": "Create beautiful anime-style illustrations",
                "category": "Anime",
                "workflow_config": {
                    "model": "runwayml/stable-diffusion-v1-5",
                    "scheduler": "EulerAncestral",
                    "steps": 30,
                    "cfg_scale": 12.0,
                    "width": 768,
                    "height": 1024,
                    "pipeline": [
                        {
                            "node_type": "prompt_enhancement", 
                            "parameters": {
                                "style_prompts": ["anime", "manga style", "cel shading", "vibrant colors"]
                            }
                        },
                        {
                            "node_type": "generation",
                            "parameters": {
                                "model_type": "diffusion",
                                "negative_prompt": "realistic, photograph, 3d render, low quality"
                            }
                        }
                    ]
                },
                "example_images": [
                    "https://photo.coolenjoy.co.kr/data/editor/1610/thumb-Bimg_20161015030009_ptegolgm.jpg"
                ],
                "parameters": {
                    "art_style": {"type": "select", "options": ["shoujo", "shounen", "seinen", "chibi"], "default": "shoujo"},
                    "color_scheme": {"type": "select", "options": ["vibrant", "pastel", "dark", "monochrome"], "default": "vibrant"}
                }
            },
            {
                "name": "Oil Painting",
                "description": "Classical oil painting style artwork",
                "category": "Art",
                "workflow_config": {
                    "model": "stabilityai/stable-diffusion-xl-base-1.0",
                    "scheduler": "DDIM",
                    "steps": 40,
                    "cfg_scale": 8.0,
                    "width": 1024,
                    "height": 768,
                    "pipeline": [
                        {
                            "node_type": "prompt_enhancement",
                            "parameters": {
                                "style_prompts": ["oil painting", "classical art", "renaissance style", "rich textures"]
                            }
                        },
                        {
                            "node_type": "generation",
                            "parameters": {
                                "model_type": "diffusion",
                                "negative_prompt": "digital art, photograph, cartoon, low quality"
                            }
                        }
                    ]
                },
                "example_images": [
                    "https://afremov.com/media/catalog/product/image_675_1.jpeg"
                ],
                "parameters": {
                    "brush_style": {"type": "select", "options": ["smooth", "textured", "impasto"], "default": "textured"},
                    "color_palette": {"type": "select", "options": ["warm", "cool", "earth_tones", "vibrant"], "default": "warm"}
                }
            },
            {
                "name": "3D Render",
                "description": "Modern 3D rendered scenes and objects",
                "category": "3D",
                "workflow_config": {
                    "model": "stabilityai/stable-diffusion-xl-base-1.0",
                    "scheduler": "DPMSolverMultistep", 
                    "steps": 35,
                    "cfg_scale": 9.0,
                    "width": 1024,
                    "height": 1024,
                    "pipeline": [
                        {
                            "node_type": "prompt_enhancement",
                            "parameters": {
                                "style_prompts": ["3d render", "octane render", "blender", "high quality", "professional lighting"]
                            }
                        },
                        {
                            "node_type": "generation",
                            "parameters": {
                                "model_type": "diffusion",
                                "negative_prompt": "2d, flat, painting, sketch, low quality, pixelated"
                            }
                        }
                    ]
                },
                "example_images": [
                    "https://cdn.mos.cms.futurecdn.net/4365c5720b2f0aac43cc632b5694eda9-1200-80.jpg.webp"
                ],
                "parameters": {
                    "render_engine": {"type": "select", "options": ["cycles", "octane", "arnold", "vray"], "default": "cycles"},
                    "lighting_setup": {"type": "select", "options": ["studio", "natural", "dramatic", "soft"], "default": "studio"}
                }
            },
            {
                "name": "Sketch to Art",
                "description": "Transform sketches into detailed artwork",
                "category": "Transformation",
                "workflow_config": {
                    "model": "runwayml/stable-diffusion-v1-5",
                    "scheduler": "DDIM",
                    "steps": 20,
                    "cfg_scale": 7.0,
                    "width": 768,
                    "height": 768,
                    "pipeline": [
                        {
                            "node_type": "image_input",
                            "parameters": {
                                "input_type": "sketch",
                                "preprocessing": "edge_detection"
                            }
                        },
                        {
                            "node_type": "img2img_generation",
                            "parameters": {
                                "model_type": "diffusion",
                                "strength": 0.8
                            }
                        }
                    ]
                },
                "example_images": [
                    "https://images.squarespace-cdn.com/content/v1/57d5444be58c62ac0e2b4f95/1473599946759-0OR1TXLW0SSCXACKGRSS/TheAstronomer_Small.jpg"
                ],
                "parameters": {
                    "transformation_strength": {"type": "slider", "min": 0.1, "max": 1.0, "default": 0.8},
                    "target_style": {"type": "select", "options": ["realistic", "artistic", "cartoon", "painterly"], "default": "artistic"}
                }
            }
        ]
        
        for template_data in default_templates:
            db_template = TemplateModel(**template_data)
            self.db.add(db_template)
        
        self.db.commit()
        logger.info(f"Initialized {len(default_templates)} default templates")