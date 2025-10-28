import os
import uuid
import aiofiles
from PIL import Image
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import io

# Configuration
UPLOAD_DIR = "static/uploads/profile_pictures"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGE_SIZE = (800, 800)  # Max width, height in pixels
THUMBNAIL_SIZE = (150, 150)  # Thumbnail size

# Ensure upload directory exists
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"✅ Upload directory ready: {UPLOAD_DIR}")
except Exception as e:
    print(f"⚠️ Warning: Could not create upload directory: {e}")

class ImageProcessor:
    """Handle image upload, validation, and processing"""
    
    @staticmethod
    def validate_image_file(file: UploadFile) -> None:
        """Validate uploaded image file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        # Check file extension
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
    
    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        file_ext = os.path.splitext(original_filename.lower())[1]
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_ext}"
    
    @staticmethod
    def resize_image(image: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        # Calculate new size maintaining aspect ratio
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    @staticmethod
    def create_thumbnail(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Create square thumbnail with center crop"""
        # Get current dimensions
        width, height = image.size
        
        # Calculate crop box for center square
        if width > height:
            # Landscape - crop width
            left = (width - height) // 2
            top = 0
            right = left + height
            bottom = height
        else:
            # Portrait or square - crop height
            left = 0
            top = (height - width) // 2
            right = width
            bottom = top + width
        
        # Crop to square and resize
        cropped = image.crop((left, top, right, bottom))
        cropped.thumbnail(size, Image.Resampling.LANCZOS)
        return cropped
    
    @staticmethod
    async def process_and_save_image(file: UploadFile, user_id: str) -> dict:
        """Process uploaded image and save multiple versions"""
        try:
            # Validate file
            ImageProcessor.validate_image_file(file)
            
            # Read file content
            content = await file.read()
            
            # Open image with PIL
            image = Image.open(io.BytesIO(content))
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Generate filenames
            original_filename = ImageProcessor.generate_unique_filename(file.filename)
            thumbnail_filename = f"thumb_{original_filename}"
            
            # Create file paths
            original_path = os.path.join(UPLOAD_DIR, original_filename)
            thumbnail_path = os.path.join(UPLOAD_DIR, thumbnail_filename)
            
            # Process images
            # 1. Resize main image
            main_image = ImageProcessor.resize_image(image.copy(), MAX_IMAGE_SIZE)
            
            # 2. Create thumbnail
            thumbnail_image = ImageProcessor.create_thumbnail(image.copy(), THUMBNAIL_SIZE)
            
            # Save images
            main_image.save(original_path, "JPEG", quality=85, optimize=True)
            thumbnail_image.save(thumbnail_path, "JPEG", quality=85, optimize=True)
            
            # Return file information
            return {
                "success": True,
                "original_filename": file.filename,
                "saved_filename": original_filename,
                "thumbnail_filename": thumbnail_filename,
                "file_path": f"/static/uploads/profile_pictures/{original_filename}",
                "thumbnail_path": f"/static/uploads/profile_pictures/{thumbnail_filename}",
                "file_size": len(content),
                "image_dimensions": main_image.size
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    @staticmethod
    def delete_profile_images(filename: str) -> bool:
        """Delete profile image and its thumbnail"""
        try:
            # Delete main image
            main_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(main_path):
                os.remove(main_path)
            
            # Delete thumbnail
            thumbnail_filename = f"thumb_{filename}"
            thumb_path = os.path.join(UPLOAD_DIR, thumbnail_filename)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            
            return True
        except Exception as e:
            print(f"Error deleting images: {e}")
            return False
    
    @staticmethod
    def get_image_info(file_path: str) -> Optional[dict]:
        """Get information about an image file"""
        try:
            if not os.path.exists(file_path):
                return None
            
            with Image.open(file_path) as img:
                return {
                    "size": img.size,
                    "format": img.format,
                    "mode": img.mode,
                    "file_size": os.path.getsize(file_path)
                }
        except Exception:
            return None

# Helper functions for easy access
async def upload_profile_picture(file: UploadFile, user_id: str) -> dict:
    """Upload and process profile picture"""
    return await ImageProcessor.process_and_save_image(file, user_id)

def delete_profile_picture(filename: str) -> bool:
    """Delete profile picture files"""
    return ImageProcessor.delete_profile_images(filename)

def validate_image(file: UploadFile) -> None:
    """Validate image file"""
    ImageProcessor.validate_image_file(file)
