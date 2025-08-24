import os
import time
from typing import Dict, Optional, Any
from diffusers import StableDiffusionXLPipeline, StableDiffusionPipeline, DPMSolverMultistepScheduler, EulerAncestralDiscreteScheduler, DDIMScheduler
import torch
import structlog
from PIL import Image
import io
import base64

logger = structlog.get_logger()


class ModelManager:
    """
    Manages loading, caching, and inference of AI models.
    """
    
    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_cache_dir = os.getenv("MODEL_CACHE_DIR", "/tmp/models")
        
        # Create cache directory
        os.makedirs(self.model_cache_dir, exist_ok=True)
        
        logger.info(f"ModelManager initialized", device=self.device, cache_dir=self.model_cache_dir)
    
    def get_scheduler(self, scheduler_name: str, pipeline):
        """
        Get scheduler by name and configure it for the pipeline.
        """
        schedulers = {
            "DPMSolverMultistep": DPMSolverMultistepScheduler,
            "EulerAncestral": EulerAncestralDiscreteScheduler,
            "DDIM": DDIMScheduler,
        }
        
        if scheduler_name not in schedulers:
            logger.warning(f"Unknown scheduler {scheduler_name}, using default")
            return pipeline.scheduler
        
        scheduler_class = schedulers[scheduler_name]
        return scheduler_class.from_config(pipeline.scheduler.config)
    
    async def load_model(self, model_name: str, model_type: str = "diffusion") -> Any:
        """
        Load and cache a model. Returns the loaded pipeline.
        """
        if model_name in self.loaded_models:
            logger.info(f"Using cached model: {model_name}")
            return self.loaded_models[model_name]
        
        logger.info(f"Loading model: {model_name}")
        start_time = time.time()
        
        try:
            # Determine pipeline type based on model name
            if "xl" in model_name.lower():
                pipeline = StableDiffusionXLPipeline.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    use_safetensors=True,
                    cache_dir=self.model_cache_dir
                )
            else:
                pipeline = StableDiffusionPipeline.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    use_safetensors=True,
                    cache_dir=self.model_cache_dir
                )
            
            # Move to GPU if available
            if self.device == "cuda":
                pipeline = pipeline.to("cuda")
                
                # Enable memory efficient attention if available
                try:
                    pipeline.enable_xformers_memory_efficient_attention()
                    logger.info("Enabled xformers memory efficient attention")
                except Exception:
                    logger.info("xformers not available, using default attention")
                
                # Enable CPU offloading for large models
                try:
                    pipeline.enable_model_cpu_offload()
                    logger.info("Enabled model CPU offloading")
                except Exception:
                    logger.info("CPU offloading not available")
            
            # Cache the model
            self.loaded_models[model_name] = pipeline
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully", model=model_name, load_time=load_time, device=self.device)
            
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}", error=str(e), exc_info=e)
            raise
    
    async def generate_image(
        self,
        model_name: str,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        num_images_per_prompt: int = 1,
        scheduler_name: str = "DPMSolverMultistep",
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate images using the specified model.
        """
        start_time = time.time()
        
        try:
            # Load model
            pipeline = await self.load_model(model_name)
            
            # Set scheduler
            pipeline.scheduler = self.get_scheduler(scheduler_name, pipeline)
            
            # Set random seed for reproducibility
            if seed is not None:
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
            else:
                seed = torch.randint(0, 2**32 - 1, (1,)).item()
                torch.manual_seed(seed)
            
            logger.info(
                "Starting image generation",
                model=model_name,
                prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
                size=f"{width}x{height}",
                steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=seed
            )
            
            # Generate images
            with torch.inference_mode():
                result = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    num_images_per_prompt=num_images_per_prompt,
                    generator=torch.Generator(device=pipeline.device).manual_seed(seed)
                )
            
            generation_time = time.time() - start_time
            
            # Convert PIL images to base64 strings for storage
            generated_images = []
            for i, image in enumerate(result.images):
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG', quality=95)
                img_byte_arr.seek(0)
                
                # Convert to base64 for storage/transmission
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                generated_images.append({
                    "image_data": img_base64,
                    "pil_image": image,  # Keep PIL image for saving
                    "seed": seed,
                    "model_used": model_name,
                    "generation_time": generation_time,
                    "index": i
                })
            
            logger.info(
                "Image generation completed",
                model=model_name,
                generation_time=generation_time,
                images_count=len(generated_images),
                seed=seed
            )
            
            return {
                "generated_images": generated_images,
                "generation_metadata": {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "steps": num_inference_steps,
                    "cfg_scale": guidance_scale,
                    "scheduler": scheduler_name,
                    "model": model_name,
                    "seed": seed,
                    "generation_time": generation_time,
                    "device": self.device
                }
            }
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(
                "Image generation failed",
                model=model_name,
                error=str(e),
                generation_time=generation_time,
                exc_info=e
            )
            raise
    
    def unload_model(self, model_name: str):
        """
        Unload a model from memory.
        """
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Unloaded model: {model_name}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current GPU/CPU memory usage.
        """
        memory_info = {
            "device": self.device,
            "loaded_models": list(self.loaded_models.keys()),
            "model_count": len(self.loaded_models)
        }
        
        if torch.cuda.is_available():
            memory_info.update({
                "gpu_memory_allocated": torch.cuda.memory_allocated() / 1024**3,  # GB
                "gpu_memory_reserved": torch.cuda.memory_reserved() / 1024**3,   # GB
                "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            })
        
        return memory_info


# Global model manager instance
model_manager = ModelManager()