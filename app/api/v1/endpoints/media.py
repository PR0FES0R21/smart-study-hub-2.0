# ==============================================================================
# File: app/api/v1/endpoints/media.py
# Deskripsi: Media upload endpoints dengan pre-signed URLs untuk semua tipe file
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum

from app.api.v1 import deps
from app.core.db import db
from app.core.r2_setup import s3_client
from app.core.config import settings

router = APIRouter()

# ==================== ENUMS & SCHEMAS ====================

class MediaCategory(str, Enum):
    """Kategori media untuk organization"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    ARCHIVE = "archive"
    OTHER = "other"

class MediaType(BaseModel):
    """Mapping MIME types ke categories dan validations"""
    category: MediaCategory
    mime_types: List[str]
    max_size_mb: int
    extensions: List[str]

# Comprehensive media type definitions
MEDIA_TYPES = {
    MediaCategory.IMAGE: MediaType(
        category=MediaCategory.IMAGE,
        mime_types=[
            "image/jpeg", "image/jpg", "image/png", "image/gif", 
            "image/webp", "image/svg+xml", "image/bmp", "image/tiff"
        ],
        max_size_mb=10,  # 10MB for images
        extensions=["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff"]
    ),
    MediaCategory.VIDEO: MediaType(
        category=MediaCategory.VIDEO,
        mime_types=[
            "video/mp4", "video/webm", "video/ogg", "video/quicktime",
            "video/x-msvideo", "video/x-matroska"
        ],
        max_size_mb=500,  # 500MB for videos
        extensions=["mp4", "webm", "ogv", "mov", "avi", "mkv"]
    ),
    MediaCategory.AUDIO: MediaType(
        category=MediaCategory.AUDIO,
        mime_types=[
            "audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg",
            "audio/webm", "audio/aac", "audio/flac"
        ],
        max_size_mb=50,  # 50MB for audio
        extensions=["mp3", "wav", "ogg", "oga", "webm", "aac", "flac"]
    ),
    MediaCategory.DOCUMENT: MediaType(
        category=MediaCategory.DOCUMENT,
        mime_types=[
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain", "text/markdown", "text/html"
        ],
        max_size_mb=20,  # 20MB for documents
        extensions=["pdf", "doc", "docx", "txt", "md", "html"]
    ),
    MediaCategory.SPREADSHEET: MediaType(
        category=MediaCategory.SPREADSHEET,
        mime_types=[
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv"
        ],
        max_size_mb=10,  # 10MB for spreadsheets
        extensions=["xls", "xlsx", "csv"]
    ),
    MediaCategory.PRESENTATION: MediaType(
        category=MediaCategory.PRESENTATION,
        mime_types=[
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ],
        max_size_mb=50,  # 50MB for presentations
        extensions=["ppt", "pptx"]
    ),
    MediaCategory.ARCHIVE: MediaType(
        category=MediaCategory.ARCHIVE,
        mime_types=[
            "application/zip", "application/x-zip-compressed",
            "application/x-rar-compressed", "application/x-7z-compressed"
        ],
        max_size_mb=100,  # 100MB for archives
        extensions=["zip", "rar", "7z"]
    )
}

def detect_media_category(content_type: str, filename: str) -> MediaCategory:
    """Auto-detect media category dari content type atau file extension"""
    # Try by content type first
    for category, media_type in MEDIA_TYPES.items():
        if content_type in media_type.mime_types:
            return category
    
    # Fallback to extension
    ext = filename.split('.')[-1].lower()
    for category, media_type in MEDIA_TYPES.items():
        if ext in media_type.extensions:
            return category
    
    return MediaCategory.OTHER

# ==================== REQUEST/RESPONSE SCHEMAS ====================

class PresignedUrlRequest(BaseModel):
    """Request untuk generate pre-signed URL"""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., description="MIME type of file")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    category: Optional[MediaCategory] = Field(None, description="Optional: specify category")
    context: Optional[str] = Field(None, description="Optional: lesson_id, course_id, etc")
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename doesn't contain dangerous characters"""
        dangerous_chars = ['/', '\\', '..', '<', '>', '|', ':', '*', '?', '"']
        if any(char in v for char in dangerous_chars):
            raise ValueError('Filename contains invalid characters')
        return v

class PresignedUrlResponse(BaseModel):
    """Response dengan pre-signed URL"""
    upload_url: str = Field(..., description="Pre-signed URL untuk upload (valid 1 hour)")
    file_key: str = Field(..., description="Unique file key di R2")
    public_url: str = Field(..., description="Public URL setelah upload selesai")
    category: MediaCategory
    expires_in: int = Field(3600, description="URL expiry dalam detik")
    max_file_size: int = Field(..., description="Maximum allowed file size in bytes")

class ConfirmUploadRequest(BaseModel):
    """Request untuk confirm upload berhasil"""
    file_key: str = Field(..., description="File key dari presigned URL response")
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., gt=0)
    content_type: str
    category: MediaCategory
    context: Optional[str] = Field(None, description="lesson_id, course_id, etc")
    alt_text: Optional[str] = Field(None, description="Alt text untuk accessibility")

class MediaFileResponse(BaseModel):
    """Response setelah confirm upload"""
    id: str
    file_key: str
    file_name: str
    file_size: int
    content_type: str
    category: MediaCategory
    public_url: str
    uploaded_by: str
    uploaded_at: datetime
    context: Optional[str] = None
    alt_text: Optional[str] = None

class MediaListResponse(BaseModel):
    """Response untuk list media files"""
    items: List[MediaFileResponse]
    total: int
    page: int
    per_page: int

# ==================== ENDPOINTS ====================

@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_upload_url(
    request: PresignedUrlRequest,
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Generate pre-signed URL untuk upload file langsung ke R2.
    
    **Workflow:**
    1. Request pre-signed URL dari backend (endpoint ini)
    2. Upload file LANGSUNG ke R2 menggunakan URL yang diberikan
    3. Confirm upload ke backend (endpoint /confirm-upload)
    
    **Supported file types:**
    - Images: JPG, PNG, GIF, WebP, SVG (max 10MB)
    - Videos: MP4, WebM, MOV (max 500MB)
    - Audio: MP3, WAV, OGG (max 50MB)
    - Documents: PDF, DOC, DOCX, TXT (max 20MB)
    - Spreadsheets: XLS, XLSX, CSV (max 10MB)
    - Presentations: PPT, PPTX (max 50MB)
    - Archives: ZIP, RAR, 7Z (max 100MB)
    """
    try:
        # Auto-detect category if not provided
        category = request.category or detect_media_category(
            request.content_type, 
            request.filename
        )
        
        # Get media type configuration
        media_config = MEDIA_TYPES.get(category)
        if not media_config:
            # Use default limits for OTHER category
            max_size_mb = 20
            allowed_types = [request.content_type]
        else:
            max_size_mb = media_config.max_size_mb
            allowed_types = media_config.mime_types
        
        # Validate file size
        max_size_bytes = max_size_mb * 1024 * 1024
        if request.file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size for {category.value} is {max_size_mb}MB"
            )
        
        # Validate content type
        if media_config and request.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type for {category.value}. Allowed: {', '.join(allowed_types)}"
            )
        
        # Generate unique file key dengan organized structure
        file_extension = request.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Organize by category and date
        date_folder = datetime.utcnow().strftime("%Y/%m")
        file_key = f"media/{category.value}/{date_folder}/{unique_filename}"
        
        # Generate pre-signed URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': settings.R2_BUCKET_NAME,
                'Key': file_key,
                'ContentType': request.content_type,
            },
            ExpiresIn=3600  # 1 hour
        )
        
        # Generate public URL
        public_url = f"{settings.R2_PUBLIC_URL}/{file_key}"
        
        return PresignedUrlResponse(
            upload_url=presigned_url,
            file_key=file_key,
            public_url=public_url,
            category=category,
            expires_in=3600,
            max_file_size=max_size_bytes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate pre-signed URL: {str(e)}"
        )


@router.post("/confirm-upload", response_model=MediaFileResponse)
async def confirm_media_upload(
    request: ConfirmUploadRequest,
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Confirm bahwa upload ke R2 berhasil dan save metadata ke database.
    
    **Call this after successfully uploading file to pre-signed URL.**
    """
    try:
        # Verify file exists in R2 (optional - adds latency)
        # try:
        #     s3_client.head_object(Bucket=settings.R2_BUCKET_NAME, Key=request.file_key)
        # except:
        #     raise HTTPException(404, "File not found in storage")
        
        # Generate public URL
        public_url = f"{settings.R2_PUBLIC_URL}/{request.file_key}"
        
        # Create media document
        media_doc = {
            "file_key": request.file_key,
            "file_name": request.file_name,
            "file_size": request.file_size,
            "content_type": request.content_type,
            "category": request.category.value,
            "public_url": public_url,
            "uploaded_by": current_user["id"],
            "uploaded_at": datetime.utcnow(),
            "context": request.context,
            "alt_text": request.alt_text,
            "status": "active"
        }
        
        # Save to database
        result = await db["media_files"].insert_one(media_doc)
        media_doc["id"] = str(result.inserted_id)
        
        return MediaFileResponse(
            id=media_doc["id"],
            file_key=media_doc["file_key"],
            file_name=media_doc["file_name"],
            file_size=media_doc["file_size"],
            content_type=media_doc["content_type"],
            category=MediaCategory(media_doc["category"]),
            public_url=media_doc["public_url"],
            uploaded_by=media_doc["uploaded_by"],
            uploaded_at=media_doc["uploaded_at"],
            context=media_doc.get("context"),
            alt_text=media_doc.get("alt_text")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm upload: {str(e)}"
        )


@router.get("/my-uploads", response_model=MediaListResponse)
async def get_my_media_files(
    category: Optional[MediaCategory] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Get list of media files uploaded by current user.
    
    **Optional filtering by category.**
    """
    try:
        # Build query
        query = {
            "uploaded_by": current_user["id"],
            "status": "active"
        }
        if category:
            query["category"] = category.value
        
        # Get total count
        total = await db["media_files"].count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * per_page
        cursor = db["media_files"].find(query).sort("uploaded_at", -1).skip(skip).limit(per_page)
        media_files = await cursor.to_list(per_page)
        
        # Format response
        items = []
        for media in media_files:
            items.append(MediaFileResponse(
                id=str(media["_id"]),
                file_key=media["file_key"],
                file_name=media["file_name"],
                file_size=media["file_size"],
                content_type=media["content_type"],
                category=MediaCategory(media["category"]),
                public_url=media["public_url"],
                uploaded_by=media["uploaded_by"],
                uploaded_at=media["uploaded_at"],
                context=media.get("context"),
                alt_text=media.get("alt_text")
            ))
        
        return MediaListResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch media files: {str(e)}"
        )


@router.delete("/{file_key:path}")
async def delete_media_file(
    file_key: str,
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Delete media file from R2 and database.
    
    **Only owner can delete their own files.**
    """
    try:
        # Find media file
        media = await db["media_files"].find_one({
            "file_key": file_key,
            "uploaded_by": current_user["id"]
        })
        
        if not media:
            raise HTTPException(
                status_code=404,
                detail="Media file not found or you don't have permission"
            )
        
        # Delete from R2
        try:
            s3_client.delete_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=file_key
            )
        except Exception as e:
            print(f"Warning: Failed to delete from R2: {e}")
        
        # Mark as deleted in database (soft delete)
        await db["media_files"].update_one(
            {"file_key": file_key},
            {"$set": {
                "status": "deleted",
                "deleted_at": datetime.utcnow(),
                "deleted_by": current_user["id"]
            }}
        )
        
        return {
            "success": True,
            "message": "Media file deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete media file: {str(e)}"
        )


@router.get("/supported-types")
async def get_supported_media_types():
    """
    Get list of all supported media types dan limits.
    
    **Useful untuk frontend validation.**
    """
    return {
        "categories": [
            {
                "category": category.value,
                "mime_types": config.mime_types,
                "extensions": config.extensions,
                "max_size_mb": config.max_size_mb,
                "max_size_bytes": config.max_size_mb * 1024 * 1024
            }
            for category, config in MEDIA_TYPES.items()
        ]
    }
