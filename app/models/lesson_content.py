# ==============================================================================
# File: app/models/lesson_content.py
# Deskripsi: Database models untuk Content Management dalam LMS
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class RichContent(BaseModel):
    """Rich text content dengan HTML support"""
    html: str = Field(..., description="HTML content dari rich editor")
    plain_text: str = Field(..., description="Plain text version untuk search dan preview")
    word_count: int = Field(default=0, description="Jumlah kata untuk estimasi waktu baca")
    reading_time: int = Field(default=0, description="Estimasi waktu baca dalam menit")
    has_media: bool = Field(default=False, description="Apakah ada embedded media")
    
    @validator('plain_text', pre=True, always=True)
    def extract_plain_text(cls, v, values):
        """Extract plain text from HTML if not provided"""
        if not v and 'html' in values:
            # Simple HTML tag removal - dalam implementasi nyata gunakan library seperti BeautifulSoup
            import re
            html = values['html']
            plain = re.sub('<[^<]+?>', '', html)
            return plain.strip()
        return v
    
    @validator('word_count', pre=True, always=True)
    def calculate_word_count(cls, v, values):
        """Calculate word count from plain text"""
        if not v and 'plain_text' in values:
            return len(values['plain_text'].split())
        return v
    
    @validator('reading_time', pre=True, always=True)
    def calculate_reading_time(cls, v, values):
        """Calculate reading time (assume 200 words per minute)"""
        if not v and 'word_count' in values:
            return max(1, values['word_count'] // 200)
        return v

class MediaContent(BaseModel):
    """Media content (images, videos, audio, files)"""
    file_url: str = Field(..., description="URL file di storage")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="Size dalam bytes")
    file_name: str = Field(..., description="Original filename")
    
    # Media-specific properties
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL untuk preview")
    duration: Optional[int] = Field(None, description="Duration untuk video/audio dalam detik")
    dimensions: Optional[Dict[str, int]] = Field(None, description="Width/height untuk images/videos")
    
    # Processing status
    processing_status: str = Field(default="pending", description="pending | processing | completed | failed")
    processed_content: Optional[str] = Field(None, description="Converted content (untuk PDF/DOC)")
    processing_error: Optional[str] = Field(None, description="Error message jika processing gagal")
    
    # Metadata
    alt_text: Optional[str] = Field(None, description="Alt text untuk accessibility")
    caption: Optional[str] = Field(None, description="Caption/description")
    copyright_info: Optional[str] = Field(None, description="Copyright information")

class EmbedContent(BaseModel):
    """Embedded content (YouTube, Vimeo, etc)"""
    embed_type: str = Field(..., description="youtube | vimeo | iframe | custom")
    embed_url: str = Field(..., description="URL sumber")
    embed_code: str = Field(..., description="Embed HTML code")
    
    # Embed metadata
    title: Optional[str] = Field(None, description="Title dari embedded content")
    description: Optional[str] = Field(None, description="Description")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    duration: Optional[int] = Field(None, description="Duration dalam detik")
    provider: Optional[str] = Field(None, description="Provider name (YouTube, Vimeo, etc)")
    
    # Settings
    autoplay: bool = Field(default=False, description="Auto-play setting")
    controls: bool = Field(default=True, description="Show controls")
    responsive: bool = Field(default=True, description="Responsive embedding")

class InteractiveContent(BaseModel):
    """Interactive content (polls, quizzes, interactive elements)"""
    interaction_type: str = Field(..., description="poll | quiz | survey | interactive_media")
    configuration: Dict[str, Any] = Field(..., description="Configuration untuk interactive element")
    
    # For polls/surveys
    questions: Optional[List[Dict[str, Any]]] = Field(None, description="Questions untuk polls/surveys")
    allow_multiple_responses: bool = Field(default=False, description="Allow multiple responses")
    show_results: bool = Field(default=True, description="Show results to users")
    
    # Statistics
    total_responses: int = Field(default=0, description="Total responses received")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Aggregated response data")

class LessonContent(BaseModel):
    """Main content model untuk lessons"""
    id: Optional[str] = Field(None, alias="_id")
    lesson_id: PyObjectId = Field(..., description="Parent lesson")
    granularity_id: Optional[PyObjectId] = Field(None, description="Parent granularity (optional)")
    
    # Content identification
    title: str = Field(..., description="Judul content")
    content_type: str = Field(..., description="text | image | video | audio | file | embed | interactive")
    content_order: int = Field(..., description="Urutan dalam lesson/granularity")
    
    # Content data (one of these will be populated based on content_type)
    rich_content: Optional[RichContent] = Field(None, description="Rich text content")
    media_content: Optional[MediaContent] = Field(None, description="Media content")
    embed_content: Optional[EmbedContent] = Field(None, description="Embedded content")
    interactive_content: Optional[InteractiveContent] = Field(None, description="Interactive content")
    
    # Content settings
    is_required: bool = Field(default=True, description="Apakah content ini wajib dilihat")
    is_downloadable: bool = Field(default=False, description="Allow download")
    view_tracking: bool = Field(default=True, description="Track viewing analytics")
    
    # Access control
    visibility: str = Field(default="all", description="all | enrolled_only | premium")
    access_restrictions: Optional[Dict[str, Any]] = Field(None, description="Additional access restrictions")
    
    # SEO and discovery
    tags: List[str] = Field(default_factory=list, description="Tags untuk search")
    keywords: List[str] = Field(default_factory=list, description="Keywords untuk search")
    
    # Status
    status: str = Field(default="draft", description="draft | published | archived")
    is_published: bool = Field(default=False)
    published_at: Optional[datetime] = Field(None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Statistics
    view_count: int = Field(default=0, description="Total views")
    unique_viewers: int = Field(default=0, description="Unique viewers count")
    average_view_time: int = Field(default=0, description="Average view time in seconds")
    engagement_score: float = Field(default=0.0, description="Engagement score (0-100)")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['text', 'image', 'video', 'audio', 'file', 'embed', 'interactive']
        if v not in allowed_types:
            raise ValueError(f'content_type must be one of {allowed_types}')
        return v
    
    @validator('rich_content', 'media_content', 'embed_content', 'interactive_content')
    def validate_content_data(cls, v, values):
        """Ensure appropriate content data is provided based on content_type"""
        content_type = values.get('content_type')
        field_name = cls.__fields__[cls.__name__].name  # This is a simplified approach
        
        # Content type validation logic would go here
        # For now, just basic validation
        return v
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    def to_mongo(self) -> dict:
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

class ContentComment(BaseModel):
    """Comments pada content"""
    id: Optional[str] = Field(None, alias="_id")
    content_id: PyObjectId = Field(..., description="Content yang di-comment")
    user_id: PyObjectId = Field(..., description="User yang comment")
    
    # Comment data
    comment_text: str = Field(..., description="Comment content")
    comment_type: str = Field(default="general", description="general | question | suggestion | issue")
    parent_comment_id: Optional[PyObjectId] = Field(None, description="Parent comment untuk replies")
    
    # Status
    is_approved: bool = Field(default=True, description="Comment approval status")
    is_pinned: bool = Field(default=False, description="Pinned comment")
    is_edited: bool = Field(default=False, description="Has been edited")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Engagement
    likes_count: int = Field(default=0, description="Number of likes")
    replies_count: int = Field(default=0, description="Number of replies")
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class ContentView(BaseModel):
    """Tracking content views untuk analytics"""
    id: Optional[str] = Field(None, alias="_id")
    content_id: PyObjectId = Field(..., description="Content yang dilihat")
    user_id: PyObjectId = Field(..., description="User yang melihat")
    lesson_id: PyObjectId = Field(..., description="Parent lesson")
    
    # View details
    view_started: datetime = Field(default_factory=datetime.utcnow)
    view_ended: Optional[datetime] = Field(None)
    view_duration: int = Field(default=0, description="Duration dalam detik")
    
    # View context
    device_type: Optional[str] = Field(None, description="desktop | mobile | tablet")
    browser: Optional[str] = Field(None, description="Browser information")
    ip_address: Optional[str] = Field(None, description="IP address")
    
    # Engagement metrics
    scroll_percentage: int = Field(default=0, description="Scroll percentage (0-100)")
    interactions: int = Field(default=0, description="Number of interactions")
    completed: bool = Field(default=False, description="Content fully viewed")
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

# Response Models untuk API
class ContentSummary(BaseModel):
    """Summary untuk content lists"""
    id: str
    title: str
    content_type: str
    content_order: int
    is_published: bool
    view_count: int
    created_at: datetime
    
    # Preview data based on content type
    preview_text: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None

class ContentDetail(LessonContent):
    """Detailed content dengan populated data"""
    lesson_title: Optional[str] = None
    granularity_title: Optional[str] = None
    comments_count: int = 0
    user_has_viewed: bool = False
    user_view_progress: float = 0.0
