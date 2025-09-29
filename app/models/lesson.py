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
    """Main lesson model - contains pages and metadata"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Basic lesson info
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    slug: Optional[str] = Field(None, description="URL-friendly slug")
    
    # Academic classification
    subject_id: PyObjectId = Field(..., description="Subject this lesson belongs to")
    grade_level: int = Field(..., ge=1, le=12, description="Target grade level")
    topic_tags: List[str] = Field(default_factory=list, description="Topik tags untuk categorization")
    
    # Content structure
    pages: List[LessonPage] = Field(default_factory=list, description="Lesson pages")
    
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
    
    def calculate_metadata(self) -> LessonMetadata:
        """Calculate and update lesson metadata"""
        metadata = LessonMetadata()
        
        # Basic counts
        metadata.total_pages = len(self.pages)
        metadata.total_duration = sum(page.estimated_duration for page in self.pages)
        
        # Component analysis
        all_components = []
        all_media = []
        difficulty_count = {"easy": 0, "medium": 0, "hard": 0}
        
        for page in self.pages:
            all_components.extend(page.embedded_components)
            all_media.extend(page.media_references)
            difficulty_count[page.difficulty_level] += 1
        
        metadata.total_components = len(all_components)
        metadata.total_media = len(all_media)
        
        # Breakdown analysis
        metadata.component_breakdown = {}
        for component in all_components:
            metadata.component_breakdown[component.type] = metadata.component_breakdown.get(component.type, 0) + 1
        
        metadata.media_breakdown = {}
        for media in all_media:
            metadata.media_breakdown[media.file_type] = metadata.media_breakdown.get(media.file_type, 0) + 1
        
        metadata.difficulty_distribution = difficulty_count
        metadata.calculated_at = datetime.utcnow()
        
        self.metadata = metadata
        return metadata
    
    def add_page(self, page: LessonPage) -> None:
        """Add new page to lesson"""
        # Auto-assign page number
        if not page.page_number:
            page.page_number = len(self.pages) + 1
        
        self.pages.append(page)
        self.updated_at = datetime.utcnow()
        self.calculate_metadata()
    
    def reorder_pages(self, new_order: List[int]) -> None:
        """Reorder pages based on new page numbers"""
        if len(new_order) != len(self.pages):
            raise ValueError("New order must include all pages")
        
        # Reorder pages
        reordered_pages = [None] * len(self.pages)
        for i, new_pos in enumerate(new_order):
            self.pages[i].page_number = new_pos
            reordered_pages[new_pos - 1] = self.pages[i]
        
        self.pages = reordered_pages
        self.updated_at = datetime.utcnow()
    
    def get_page_by_number(self, page_number: int) -> Optional[LessonPage]:
        """Get page by its number"""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None
    
    def is_editable_by(self, user_id: PyObjectId) -> bool:
        """Check if user can edit this lesson"""
        return (
            self.created_by == user_id or 
            user_id in self.collaborators
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
