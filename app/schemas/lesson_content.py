# ==============================================================================
# File: app/schemas/lesson_content.py
# Deskripsi: Pydantic schemas untuk Content Management API
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from app.schemas.base import PyObjectId
from app.schemas.pagination import PaginatedResponse

# ==================== CONTENT DATA SCHEMAS ====================

class RichContentSchema(BaseModel):
    """Schema untuk rich text content"""
    html: str = Field(..., description="HTML content from rich editor")
    plain_text: Optional[str] = Field(None, description="Plain text version")
    word_count: Optional[int] = Field(None)
    reading_time: Optional[int] = Field(None, description="Estimated reading time in minutes")
    has_media: bool = Field(default=False)

class MediaContentSchema(BaseModel):
    """Schema untuk media content"""
    file_url: str = Field(..., description="File URL in storage")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="Size in bytes")
    file_name: str = Field(..., description="Original filename")
    
    # Optional media properties
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = Field(None, description="Duration in seconds for video/audio")
    dimensions: Optional[Dict[str, int]] = Field(None, description="Width/height for images/videos")
    
    # Processing
    processing_status: str = Field(default="completed", description="pending | processing | completed | failed")
    processed_content: Optional[str] = Field(None, description="Converted content for PDF/DOC")
    
    # Metadata
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    copyright_info: Optional[str] = None

class EmbedContentSchema(BaseModel):
    """Schema untuk embedded content"""
    embed_type: str = Field(..., description="youtube | vimeo | iframe | custom")
    embed_url: str = Field(..., description="Source URL")
    embed_code: str = Field(..., description="Embed HTML code")
    
    # Optional metadata
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    provider: Optional[str] = None
    
    # Settings
    autoplay: bool = Field(default=False)
    controls: bool = Field(default=True)
    responsive: bool = Field(default=True)
    
    @validator('embed_type')
    def validate_embed_type(cls, v):
        allowed_types = ['youtube', 'vimeo', 'iframe', 'custom']
        if v not in allowed_types:
            raise ValueError(f'embed_type must be one of {allowed_types}')
        return v

class InteractiveContentSchema(BaseModel):
    """Schema untuk interactive content"""
    interaction_type: str = Field(..., description="poll | quiz | survey | interactive_media")
    configuration: Dict[str, Any] = Field(..., description="Configuration for interactive element")
    
    # Poll/Survey specific
    questions: Optional[List[Dict[str, Any]]] = None
    allow_multiple_responses: bool = Field(default=False)
    show_results: bool = Field(default=True)
    
    # Statistics
    total_responses: int = Field(default=0)
    response_data: Optional[Dict[str, Any]] = None

# ==================== REQUEST SCHEMAS ====================

class ContentCreateRequest(BaseModel):
    """Request schema untuk creating content"""
    lesson_id: PyObjectId = Field(..., description="Parent lesson ID")
    granularity_id: Optional[PyObjectId] = Field(None, description="Parent granularity ID (optional)")
    
    title: str = Field(..., min_length=1, max_length=200, description="Content title")
    content_type: str = Field(..., description="text | image | video | audio | file | embed | interactive")
    content_order: int = Field(..., ge=0, description="Order within lesson/granularity")
    
    # Content data (one of these based on content_type)
    rich_content: Optional[RichContentSchema] = None
    media_content: Optional[MediaContentSchema] = None
    embed_content: Optional[EmbedContentSchema] = None
    interactive_content: Optional[InteractiveContentSchema] = None
    
    # Settings
    is_required: bool = Field(default=True)
    is_downloadable: bool = Field(default=False)
    view_tracking: bool = Field(default=True)
    visibility: str = Field(default="all", description="all | enrolled_only | premium")
    
    # SEO
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['text', 'image', 'video', 'audio', 'file', 'embed', 'interactive']
        if v not in allowed_types:
            raise ValueError(f'content_type must be one of {allowed_types}')
        return v

class ContentUpdateRequest(BaseModel):
    """Request schema untuk updating content"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content_order: Optional[int] = Field(None, ge=0)
    
    # Content data updates
    rich_content: Optional[RichContentSchema] = None
    media_content: Optional[MediaContentSchema] = None
    embed_content: Optional[EmbedContentSchema] = None
    interactive_content: Optional[InteractiveContentSchema] = None
    
    # Settings updates
    is_required: Optional[bool] = None
    is_downloadable: Optional[bool] = None
    view_tracking: Optional[bool] = None
    visibility: Optional[str] = None
    
    # SEO updates
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None

class ContentReorderRequest(BaseModel):
    """Request schema untuk reordering content"""
    content_orders: List[Dict[str, Union[str, int]]] = Field(
        ...,
        description="List of {content_id: str, new_order: int}"
    )

class ContentPublishRequest(BaseModel):
    """Request schema untuk publishing content"""
    publish: bool = Field(..., description="True to publish, False to unpublish")
    publish_message: Optional[str] = None

# ==================== RESPONSE SCHEMAS ====================

class ContentSummaryResponse(BaseModel):
    """Response schema untuk content summary (in lists)"""
    id: str
    title: str
    content_type: str
    content_order: int
    is_published: bool
    is_required: bool
    view_count: int
    created_at: datetime
    updated_at: datetime
    
    # Preview data based on content type
    preview_text: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    
    # User-specific data
    user_has_viewed: bool = False
    user_view_progress: float = 0.0
    user_can_edit: bool = False

class ContentDetailResponse(BaseModel):
    """Response schema untuk detailed content"""
    id: str
    lesson_id: str
    granularity_id: Optional[str] = None
    title: str
    content_type: str
    content_order: int
    
    # Content data
    rich_content: Optional[RichContentSchema] = None
    media_content: Optional[MediaContentSchema] = None
    embed_content: Optional[EmbedContentSchema] = None
    interactive_content: Optional[InteractiveContentSchema] = None
    
    # Settings
    is_required: bool
    is_downloadable: bool
    view_tracking: bool
    visibility: str
    access_restrictions: Optional[Dict[str, Any]] = None
    
    # SEO
    tags: List[str]
    keywords: List[str]
    
    # Status
    status: str
    is_published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    view_count: int = 0
    unique_viewers: int = 0
    average_view_time: int = 0
    engagement_score: float = 0.0
    
    # Related data
    lesson_title: Optional[str] = None
    granularity_title: Optional[str] = None
    comments_count: int = 0
    
    # User-specific data
    user_has_viewed: bool = False
    user_view_progress: float = 0.0
    user_can_edit: bool = False
    user_can_delete: bool = False
    user_bookmark_id: Optional[str] = None

# ==================== COMMENT SCHEMAS ====================

class CommentCreateRequest(BaseModel):
    """Request schema untuk creating comment"""
    comment_text: str = Field(..., min_length=1, max_length=1000)
    comment_type: str = Field(default="general", description="general | question | suggestion | issue")
    parent_comment_id: Optional[PyObjectId] = Field(None, description="Parent comment for replies")

class CommentUpdateRequest(BaseModel):
    """Request schema untuk updating comment"""
    comment_text: str = Field(..., min_length=1, max_length=1000)

class CommentResponse(BaseModel):
    """Response schema untuk comment"""
    id: str
    content_id: str
    user_id: str
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    
    comment_text: str
    comment_type: str
    parent_comment_id: Optional[str] = None
    
    is_approved: bool
    is_pinned: bool
    is_edited: bool
    
    created_at: datetime
    updated_at: datetime
    
    likes_count: int = 0
    replies_count: int = 0
    
    # User-specific data
    user_has_liked: bool = False
    user_can_edit: bool = False
    user_can_delete: bool = False
    
    # Replies (if requested)
    replies: Optional[List['CommentResponse']] = None

# ==================== FILE UPLOAD SCHEMAS ====================

class FileUploadRequest(BaseModel):
    """Request schema untuk file upload"""
    content_type: str = Field(..., description="Content type that will use this file")
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    copyright_info: Optional[str] = None

class FileUploadResponse(BaseModel):
    """Response schema untuk file upload"""
    file_id: str
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    processing_status: str
    thumbnail_url: Optional[str] = None
    upload_complete: bool = True

class FileProcessingStatusResponse(BaseModel):
    """Response schema untuk file processing status"""
    file_id: str
    processing_status: str
    progress_percentage: int = 0
    error_message: Optional[str] = None
    processed_content: Optional[str] = None
    thumbnail_url: Optional[str] = None

# ==================== ANALYTICS SCHEMAS ====================

class ContentViewCreateRequest(BaseModel):
    """Request schema untuk recording content view"""
    view_duration: int = Field(default=0, description="View duration in seconds")
    scroll_percentage: int = Field(default=0, description="Scroll percentage (0-100)")
    interactions: int = Field(default=0, description="Number of interactions")
    completed: bool = Field(default=False, description="Content fully viewed")
    
    # Optional context
    device_type: Optional[str] = None
    browser: Optional[str] = None

class ContentAnalyticsRequest(BaseModel):
    """Request schema untuk content analytics"""
    content_ids: Optional[List[PyObjectId]] = None
    lesson_id: Optional[PyObjectId] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    group_by: str = Field(default="content", description="content | lesson | content_type")

class ContentAnalyticsResponse(BaseModel):
    """Response schema untuk content analytics"""
    total_views: int
    unique_viewers: int
    average_view_duration: int
    total_engagement_time: int
    
    # Content performance
    most_viewed_content: List[Dict[str, Any]]
    least_viewed_content: List[Dict[str, Any]]
    highest_engagement: List[Dict[str, Any]]
    
    # User behavior
    view_patterns: Dict[str, Any]
    engagement_trends: List[Dict[str, Any]]
    device_breakdown: Dict[str, int]
    
    # Time-based analytics
    views_by_hour: Dict[int, int]
    views_by_day: Dict[str, int]

# ==================== FILTER & QUERY SCHEMAS ====================

class ContentFilters(BaseModel):
    """Schema untuk content filtering"""
    lesson_id: Optional[PyObjectId] = None
    granularity_id: Optional[PyObjectId] = None
    content_type: Optional[str] = None
    is_published: Optional[bool] = None
    is_required: Optional[bool] = None
    visibility: Optional[str] = None
    tags: Optional[List[str]] = None
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None

class ContentSortBy(BaseModel):
    """Schema untuk content sorting"""
    field: str = Field(default="content_order", description="Field to sort by")
    direction: str = Field(default="asc", description="asc | desc")
    
    @validator('field')
    def validate_sort_field(cls, v):
        allowed_fields = [
            'title', 'content_order', 'created_at', 'updated_at', 
            'view_count', 'engagement_score'
        ]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of {allowed_fields}')
        return v

# ==================== PAGINATED RESPONSES ====================

class PaginatedContentResponse(PaginatedResponse[ContentSummaryResponse]):
    """Paginated response untuk content lists"""
    total_by_type: Optional[Dict[str, int]] = None
    total_published: Optional[int] = None
    total_draft: Optional[int] = None

class PaginatedCommentResponse(PaginatedResponse[CommentResponse]):
    """Paginated response untuk comment lists"""
    total_approved: Optional[int] = None
    total_pending: Optional[int] = None

# ==================== BULK OPERATIONS ====================

class BulkContentOperationRequest(BaseModel):
    """Request schema untuk bulk content operations"""
    content_ids: List[PyObjectId] = Field(..., description="Content IDs to operate on")
    operation: str = Field(..., description="publish | unpublish | delete | move")
    operation_data: Optional[Dict[str, Any]] = Field(None, description="Additional operation data")

class BulkContentOperationResponse(BaseModel):
    """Response schema untuk bulk content operations"""
    success: bool
    total_processed: int
    successful_count: int
    failed_count: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    successful_items: List[str] = Field(default_factory=list)

# Update forward reference for recursive CommentResponse
CommentResponse.model_rebuild()
