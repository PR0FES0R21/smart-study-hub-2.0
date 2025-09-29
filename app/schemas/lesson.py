# ==============================================================================
# File: app/schemas/lesson.py
# Deskripsi: Pydantic schemas untuk Lesson API (Modular Architecture)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.base import PyObjectId
from app.schemas.pagination import PaginatedResponse

# ==================== REQUEST SCHEMAS ====================

class MediaReferenceRequest(BaseModel):
    """Schema untuk media reference request"""
    media_key: str = Field(..., description="Key untuk reference dalam content")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="image | video | audio | document")
    alt_text: Optional[str] = Field(None, description="Alt text")
    duration: Optional[int] = Field(None, description="Duration for video/audio")

class EmbeddedComponentRequest(BaseModel):
    """Schema untuk embedded component request"""
    component_id: str = Field(..., description="Unique component ID")
    type: str = Field(..., description="quiz | assignment | interactive")
    position: int = Field(..., description="Position dalam content")
    title: str = Field(..., description="Component title")
    required: bool = Field(default=True)
    estimated_duration: int = Field(default=10, description="Minutes")
    data: Dict[str, Any] = Field(..., description="Component configuration")

class LessonPageRequest(BaseModel):
    """Schema untuk lesson page request"""
    title: str = Field(..., min_length=1, max_length=200)
    content_markdown: str = Field(..., description="Page content dalam markdown")
    media_references: List[MediaReferenceRequest] = Field(default_factory=list)
    embedded_components: List[EmbeddedComponentRequest] = Field(default_factory=list)
    estimated_duration: int = Field(default=10, description="Minutes")
    difficulty_level: str = Field(default="medium", description="easy | medium | hard")
    learning_objectives: List[str] = Field(default_factory=list)

class LessonCreateRequest(BaseModel):
    """Request untuk creating lesson"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    subject_id: PyObjectId = Field(..., description="Subject ID")
    grade_level: int = Field(..., ge=1, le=12)
    topic_tags: List[str] = Field(default_factory=list)
    
    # Content
    pages: List[LessonPageRequest] = Field(default_factory=list)
    
    # Settings
    difficulty_level: str = Field(default="medium")
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    visibility: str = Field(default="public", description="public | private | shared")

class LessonUpdateRequest(BaseModel):
    """Request untuk updating lesson"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    topic_tags: Optional[List[str]] = Field(None)
    pages: Optional[List[LessonPageRequest]] = Field(None)
    difficulty_level: Optional[str] = Field(None)
    learning_objectives: Optional[List[str]] = Field(None)
    prerequisites: Optional[List[str]] = Field(None)
    visibility: Optional[str] = Field(None)
    status: Optional[str] = Field(None, description="draft | published | archived")

class LessonPageAddRequest(BaseModel):
    """Request untuk adding single page to lesson"""
    page_number: Optional[int] = Field(None, description="Auto-assigned if not provided")
    title: str = Field(..., min_length=1, max_length=200)
    content_markdown: str = Field(..., description="Page content")
    estimated_duration: int = Field(default=10)
    difficulty_level: str = Field(default="medium")

class ComponentAddRequest(BaseModel):
    """Request untuk adding component to lesson page"""
    page_number: int = Field(..., ge=1, description="Target page number")
    component_id: str = Field(..., description="Unique component ID")
    type: str = Field(..., description="quiz | assignment | interactive")
    position: int = Field(..., description="Position dalam page content")
    title: str = Field(..., description="Component title")
    data: Dict[str, Any] = Field(..., description="Component configuration")

# ==================== RESPONSE SCHEMAS ====================

class MediaReferenceResponse(BaseModel):
    """Response untuk media reference"""
    media_key: str
    file_name: str
    file_type: str
    file_size: int
    url: str
    alt_text: Optional[str] = None
    duration: Optional[int] = None

class EmbeddedComponentResponse(BaseModel):
    """Response untuk embedded component"""
    component_id: str
    type: str
    position: int
    title: str
    required: bool
    estimated_duration: int
    data: Dict[str, Any]

class LessonPageResponse(BaseModel):
    """Response untuk lesson page"""
    page_number: int
    title: str
    content_markdown: str
    media_references: List[MediaReferenceResponse]
    embedded_components: List[EmbeddedComponentResponse]
    estimated_duration: int
    difficulty_level: str
    learning_objectives: List[str]
    is_published: bool
    created_at: datetime
    updated_at: datetime

class LessonMetadataResponse(BaseModel):
    """Response untuk lesson metadata"""
    total_pages: int
    total_duration: int
    total_components: int
    total_media: int
    component_breakdown: Dict[str, int]
    media_breakdown: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    usage_count: int
    completion_rate: float
    rating: float
    review_count: int
    calculated_at: datetime

class LessonSummaryResponse(BaseModel):
    """Summary response untuk lesson list"""
    id: str
    title: str
    description: str
    slug: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None  # Populated
    grade_level: int
    topic_tags: List[str]
    
    # Quick stats
    total_pages: int
    total_duration: int
    difficulty_level: str
    
    # Creator info
    created_by: str
    created_by_name: Optional[str] = None  # Populated
    
    # Status
    visibility: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    # User permissions
    can_edit: bool = False
    can_delete: bool = False
    is_favorited: bool = False

class LessonDetailResponse(BaseModel):
    """Detailed response untuk lesson"""
    id: str
    title: str
    description: str
    slug: Optional[str] = None
    
    # Academic info
    subject_id: str
    subject_name: Optional[str] = None
    grade_level: int
    topic_tags: List[str]
    
    # Content
    pages: List[LessonPageResponse]
    
    # Lesson settings
    difficulty_level: str
    learning_objectives: List[str]
    prerequisites: List[str]
    
    # Sharing
    visibility: str
    created_by: str
    created_by_name: Optional[str] = None
    collaborators: List[str]
    
    # Metadata
    metadata: LessonMetadataResponse
    
    # Status
    status: str
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # User context
    can_edit: bool = False
    can_delete: bool = False
    can_collaborate: bool = False
    usage_in_modules: Optional[List[Dict[str, Any]]] = None  # Where this lesson is used

class LessonOperationResponse(BaseModel):
    """Response untuk lesson operations"""
    success: bool
    message: str
    lesson_id: Optional[str] = None
    affected_modules: Optional[List[str]] = None

# ==================== FILTER & SORT SCHEMAS ====================

class LessonFilters(BaseModel):
    """Filters untuk lesson list"""
    subject_id: Optional[str] = None
    grade_level: Optional[int] = None
    created_by: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    difficulty_level: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    has_components: Optional[bool] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    search: Optional[str] = None

class LessonSortBy(BaseModel):
    """Sort options untuk lesson list"""
    field: str = Field(default="updated_at", description="Field to sort by")
    direction: str = Field(default="desc", pattern="^(asc|desc)$")

# ==================== ANALYTICS SCHEMAS ====================

class LessonAnalyticsResponse(BaseModel):
    """Analytics untuk lesson"""
    lesson_id: str
    
    # Usage statistics
    total_views: int = 0
    unique_students: int = 0
    times_used_in_modules: int = 0
    average_completion_time: float = 0.0
    completion_rate: float = 0.0
    
    # Performance metrics
    average_score: float = 0.0
    component_performance: Dict[str, float] = Field(default_factory=dict)
    difficulty_feedback: Dict[str, int] = Field(default_factory=dict)
    
    # Engagement metrics
    page_views: List[Dict[str, Any]] = Field(default_factory=list)
    drop_off_points: List[Dict[str, Any]] = Field(default_factory=list)
    most_popular_components: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Time analysis
    peak_usage_hours: List[int] = Field(default_factory=list)
    usage_by_day: Dict[str, int] = Field(default_factory=dict)
    
    # Quality metrics
    student_ratings: List[float] = Field(default_factory=list)
    teacher_reviews: List[Dict[str, Any]] = Field(default_factory=list)

# ==================== COLLABORATION SCHEMAS ====================

class LessonCollaboratorRequest(BaseModel):
    """Request untuk adding collaborator"""
    teacher_id: PyObjectId = Field(..., description="Teacher to add as collaborator")
    permissions: List[str] = Field(default=["edit"], description="edit | comment | view")

class LessonShareRequest(BaseModel):
    """Request untuk sharing lesson"""
    recipient_ids: List[PyObjectId] = Field(..., description="Teachers to share with")
    message: Optional[str] = Field(None, description="Optional message")
    allow_editing: bool = Field(default=False)

class LessonReviewRequest(BaseModel):
    """Request untuk reviewing lesson"""
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    review: Optional[str] = Field(None, max_length=1000, description="Optional review text")
    recommend: bool = Field(default=True, description="Would recommend to others")

# ==================== PAGINATED RESPONSES ====================

class PaginatedLessonResponse(PaginatedResponse[LessonSummaryResponse]):
    """Paginated lesson response dengan additional stats"""
    total_by_subject: Optional[Dict[str, int]] = None
    total_by_difficulty: Optional[Dict[str, int]] = None
    total_by_status: Optional[Dict[str, int]] = None
    average_rating: Optional[float] = None

class LessonLibraryResponse(BaseModel):
    """Response untuk lesson library/browse"""
    featured_lessons: List[LessonSummaryResponse] = Field(default_factory=list)
    recent_lessons: List[LessonSummaryResponse] = Field(default_factory=list)
    popular_lessons: List[LessonSummaryResponse] = Field(default_factory=list)
    my_lessons: List[LessonSummaryResponse] = Field(default_factory=list)
    
    # Browse categories
    subjects: List[Dict[str, Any]] = Field(default_factory=list)
    grade_levels: List[int] = Field(default_factory=list)
    topic_tags: List[str] = Field(default_factory=list)
    
    # Statistics
    total_lessons: int = 0
    total_creators: int = 0
