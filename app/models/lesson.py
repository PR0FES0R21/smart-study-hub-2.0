# ==============================================================================
# File: app/models/lesson.py
# Deskripsi: Lesson model dengan pages dan metadata (Modular Architecture)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
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
    """Individual page dalam lesson"""
    page_number: int = Field(..., ge=1, description="Page number dalam lesson")
    title: str = Field(..., min_length=1, max_length=200, description="Page title")
    content_markdown: str = Field(..., description="Main content dalam markdown format")
    
    # Media dan components dalam page
    media_references: List[MediaReference] = Field(default_factory=list)
    embedded_components: List[EmbeddedComponent] = Field(default_factory=list)
    
    # Page metadata
    estimated_duration: int = Field(default=10, description="Estimated reading time (minutes)")
    difficulty_level: str = Field(default="medium", description="easy | medium | hard")
    learning_objectives: List[str] = Field(default_factory=list)
    
    # Page status
    is_published: bool = Field(default=True, description="Page visibility status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LessonMetadata(BaseModel):
    """Auto-calculated metadata untuk lesson"""
    total_pages: int = Field(default=0, description="Total number of pages")
    total_duration: int = Field(default=0, description="Total estimated duration (minutes)")
    total_components: int = Field(default=0, description="Total embedded components")
    total_media: int = Field(default=0, description="Total media files")
    
    # Content analysis
    component_breakdown: Dict[str, int] = Field(default_factory=dict, description="Components by type")
    media_breakdown: Dict[str, int] = Field(default_factory=dict, description="Media files by type")
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict, description="Pages by difficulty")
    
    # Usage statistics
    usage_count: int = Field(default=0, description="Times used in modules")
    average_completion_time: Optional[float] = Field(None, description="Actual completion time (minutes)")
    completion_rate: float = Field(default=0.0, description="Student completion rate (0-100)")
    
    # Quality metrics
    rating: float = Field(default=0.0, description="Average rating from teachers/students")
    review_count: int = Field(default=0, description="Number of reviews")
    
    # Last calculated
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class Lesson(BaseModel):
    """Main lesson model - metadata only (pages stored separately)"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Basic lesson info
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    slug: Optional[str] = Field(None, description="URL-friendly slug")
    
    # Academic classification
    subject_id: PyObjectId = Field(..., description="Subject this lesson belongs to")
    grade_level: int = Field(..., ge=1, le=12, description="Target grade level")
    topic_tags: List[str] = Field(default_factory=list, description="Topik tags untuk categorization")
    
    # NOTE: Pages are NOW stored in separate 'lesson_pages' collection!
    # This field is REMOVED for performance (was: List[LessonPage])
    # Use /lessons/{id}/pages endpoints to access page content
    
    # Lesson settings
    difficulty_level: str = Field(default="medium", description="Overall lesson difficulty")
    learning_objectives: List[str] = Field(default_factory=list, description="Main learning objectives")
    prerequisites: List[str] = Field(default_factory=list, description="Required prior knowledge")
    
    # Sharing dan visibility
    visibility: str = Field(default="public", description="public | private | shared")
    created_by: PyObjectId = Field(..., description="Teacher who created this lesson")
    collaborators: List[PyObjectId] = Field(default_factory=list, description="Teachers who can edit")
    
    # Auto-calculated metadata
    metadata: LessonMetadata = Field(default_factory=LessonMetadata)
    
    # Status dan lifecycle
    status: str = Field(default="draft", description="draft | published | archived")
    published_at: Optional[datetime] = Field(None)
    archived_at: Optional[datetime] = Field(None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # NOTE: Metadata calculation is now handled by lesson_page_crud
    # when pages are added/updated/deleted in lesson_pages collection
    
    def is_editable_by(self, user_id) -> bool:
        """Check if user can edit this lesson
        
        Args:
            user_id: Can be string or PyObjectId
        
        Returns:
            bool: True if user can edit, False otherwise
        """
        # Convert to string for comparison (handles both string and ObjectId)
        user_id_str = str(user_id)
        created_by_str = str(self.created_by)
        collaborators_str = [str(c) for c in self.collaborators]
        
        return (
            created_by_str == user_id_str or 
            user_id_str in collaborators_str
        )
    
    @validator('visibility')
    def validate_visibility(cls, v):
        allowed_values = ['public', 'private', 'shared']
        if v not in allowed_values:
            raise ValueError(f'Visibility must be one of {allowed_values}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_values = ['draft', 'published', 'archived']
        if v not in allowed_values:
            raise ValueError(f'Status must be one of {allowed_values}')
        return v
    
    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB document to Pydantic model"""
        if '_id' in data:
            data['id'] = str(data['_id'])
            del data['_id']  # Remove _id after converting to id
        
        # Convert all ObjectId fields to strings
        if 'subject_id' in data and data['subject_id']:
            data['subject_id'] = str(data['subject_id'])
        if 'created_by' in data and data['created_by']:
            data['created_by'] = str(data['created_by'])
        if 'collaborators' in data:
            data['collaborators'] = [str(c) for c in data['collaborators']]
        
        return cls(**data)
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        data = self.dict(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = ObjectId(self.id)
        return data
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
