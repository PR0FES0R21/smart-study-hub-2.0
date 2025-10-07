# ==============================================================================
# File: app/models/lesson_page.py
# Deskripsi: Individual lesson page model (separated from lesson)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class MediaReference(BaseModel):
    """Reference ke media file"""
    media_key: str = Field(..., description="Key untuk reference dalam content")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="image | video | audio | document")
    file_size: int = Field(..., description="File size in bytes")
    url: str = Field(..., description="Full URL dari storage")
    alt_text: Optional[str] = Field(None, description="Alt text untuk accessibility")
    duration: Optional[int] = Field(None, description="Duration untuk video/audio (seconds)")

class EmbeddedComponent(BaseModel):
    """Component yang di-embed dalam page content"""
    component_id: str = Field(..., description="Unique component ID")
    type: str = Field(..., description="quiz | assignment | interactive | survey")
    position: int = Field(..., description="Position dalam content")
    title: str = Field(..., description="Component title")
    required: bool = Field(default=True, description="Required untuk completion")
    estimated_duration: int = Field(default=10, description="Estimated completion time (minutes)")
    data: Dict[str, Any] = Field(..., description="Component specific configuration")
    
    @validator('type')
    def validate_component_type(cls, v):
        allowed_types = ['quiz', 'assignment', 'interactive', 'survey', 'reflection', 'discussion']
        if v not in allowed_types:
            raise ValueError(f'Component type must be one of {allowed_types}')
        return v

class LessonPage(BaseModel):
    """Individual page dalam lesson - SEPARATED from lesson document"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Reference to parent lesson
    lesson_id: PyObjectId = Field(..., description="Parent lesson ID")
    
    # Page identification
    page_number: int = Field(..., ge=1, description="Page number dalam lesson")
    title: str = Field(..., min_length=1, max_length=200, description="Page title")
    
    # Content
    content_markdown: str = Field(..., description="Main content dalam markdown format")
    
    # Media dan components dalam page
    media_references: List[MediaReference] = Field(default_factory=list)
    embedded_components: List[EmbeddedComponent] = Field(default_factory=list)
    
    # Page metadata
    estimated_duration: int = Field(default=10, description="Estimated reading time (minutes)")
    difficulty_level: str = Field(default="medium", description="easy | medium | hard")
    learning_objectives: List[str] = Field(default_factory=list)
    
    # Status and versioning
    status: str = Field(default="published", description="draft | published | archived")
    version: int = Field(default=1, description="Version number")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = Field(None, description="When it was published")
    
    # Author tracking
    created_by: Optional[PyObjectId] = Field(None, description="User who created this page")
    updated_by: Optional[PyObjectId] = Field(None, description="User who last updated")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def from_mongo(cls, data: dict) -> "LessonPage":
        """Convert MongoDB document to LessonPage model"""
        if not data:
            return None
        
        # Convert ObjectId fields to strings
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        
        if "lesson_id" in data:
            data["lesson_id"] = str(data["lesson_id"])
        
        if "created_by" in data and data["created_by"]:
            data["created_by"] = str(data["created_by"])
        
        if "updated_by" in data and data["updated_by"]:
            data["updated_by"] = str(data["updated_by"])
        
        return cls(**data)

class LessonPageSummary(BaseModel):
    """Summary of page (untuk list pages tanpa full content)"""
    page_number: int
    title: str
    estimated_duration: int
    difficulty_level: str
    status: str
    has_media: bool = Field(default=False)
    has_components: bool = Field(default=False)
    media_count: int = Field(default=0)
    component_count: int = Field(default=0)
    created_at: datetime
    updated_at: datetime
