import os
import uuid
from typing import Optional, Dict, Any
from PIL import Image
import io
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class StorageService:
    """
    Handles image storage to local filesystem or S3.
    """
    
    def __init__(self):
        self.use_s3 = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        self.local_storage_path = "/tmp/generated_images"
        
        # Create local storage directory
        os.makedirs(self.local_storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.local_storage_path, "thumbnails"), exist_ok=True)
        
        if self.use_s3:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                self.bucket_name = settings.AWS_BUCKET_NAME
                
                # Test S3 connection
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info("S3 storage initialized", bucket=self.bucket_name)
                
            except (NoCredentialsError, ClientError) as e:
                logger.warning("S3 initialization failed, using local storage", error=str(e))
                self.use_s3 = False
        
        storage_type = "S3" if self.use_s3 else "Local"
        logger.info(f"Storage service initialized", type=storage_type)
    
    def generate_filename(self, job_id: str, index: int, file_type: str = "image") -> str:
        """
        Generate unique filename for image storage.
        """
        prefix = "thumb_" if file_type == "thumbnail" else ""
        return f"{prefix}{job_id}_{index}_{uuid.uuid4().hex[:8]}.jpg"
    
    def create_thumbnail(self, image: Image.Image, max_size: tuple = (300, 300)) -> Image.Image:
        """
        Create a thumbnail from PIL image.
        """
        thumbnail = image.copy()
        thumbnail.thumbnail(max_size, Image.Resampling.LANCZOS)
        return thumbnail
    
    async def save_image_local(
        self, 
        image: Image.Image, 
        filename: str, 
        is_thumbnail: bool = False
    ) -> str:
        """
        Save image to local filesystem.
        """
        try:
            folder = "thumbnails" if is_thumbnail else ""
            file_path = os.path.join(self.local_storage_path, folder, filename)
            
            # Save image
            image.save(file_path, "JPEG", quality=95, optimize=True)
            
            # Return URL - in production this would be your CDN/static file server URL
            base_url = os.getenv("STATIC_FILES_URL", "http://localhost:8000/static/images")
            url_path = f"thumbnails/{filename}" if is_thumbnail else filename
            return f"{base_url}/{url_path}"
            
        except Exception as e:
            logger.error("Failed to save image locally", filename=filename, error=str(e))
            raise
    
    async def save_image_s3(
        self, 
        image: Image.Image, 
        filename: str, 
        is_thumbnail: bool = False
    ) -> str:
        """
        Save image to S3 bucket.
        """
        try:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=95, optimize=True)
            img_byte_arr.seek(0)
            
            # S3 key (path)
            folder = "thumbnails/" if is_thumbnail else "images/"
            s3_key = f"{folder}{filename}"
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                img_byte_arr,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'CacheControl': 'max-age=31536000',  # 1 year cache
                    'ACL': 'public-read'
                }
            )
            
            # Return S3 URL
            if settings.CDN_URL:
                return f"{settings.CDN_URL}/{s3_key}"
            else:
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
                
        except Exception as e:
            logger.error("Failed to save image to S3", filename=filename, error=str(e))
            raise
    
    async def save_image(
        self, 
        image: Image.Image, 
        job_id: str, 
        index: int
    ) -> Dict[str, str]:
        """
        Save both full image and thumbnail. Returns URLs for both.
        """
        try:
            # Generate filenames
            image_filename = self.generate_filename(job_id, index, "image")
            thumb_filename = self.generate_filename(job_id, index, "thumbnail")
            
            # Create thumbnail
            thumbnail = self.create_thumbnail(image)
            
            # Save images based on storage type
            if self.use_s3:
                image_url = await self.save_image_s3(image, image_filename, False)
                thumbnail_url = await self.save_image_s3(thumbnail, thumb_filename, True)
            else:
                image_url = await self.save_image_local(image, image_filename, False)
                thumbnail_url = await self.save_image_local(thumbnail, thumb_filename, True)
            
            logger.info(
                "Images saved successfully",
                job_id=job_id,
                index=index,
                storage_type="S3" if self.use_s3 else "Local",
                image_filename=image_filename
            )
            
            return {
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "filename": image_filename
            }
            
        except Exception as e:
            logger.error(
                "Failed to save images",
                job_id=job_id,
                index=index,
                error=str(e)
            )
            raise
    
    async def delete_image(self, image_url: str) -> bool:
        """
        Delete image from storage.
        """
        try:
            if self.use_s3:
                # Extract S3 key from URL
                if settings.CDN_URL and image_url.startswith(settings.CDN_URL):
                    s3_key = image_url.replace(f"{settings.CDN_URL}/", "")
                else:
                    # Extract from S3 URL
                    s3_key = image_url.split(f"{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/")[-1]
                
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                logger.info("Image deleted from S3", s3_key=s3_key)
            else:
                # Extract filename from local URL and delete
                filename = os.path.basename(image_url)
                file_path = os.path.join(self.local_storage_path, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info("Image deleted locally", filename=filename)
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete image", image_url=image_url, error=str(e))
            return False


# Global storage service instance
storage_service = StorageService()