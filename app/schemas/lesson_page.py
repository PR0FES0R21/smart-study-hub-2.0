# ==============================================================================
# File: app/schemas/lesson_page.py
# Deskripsi: Schemas for lesson page API requests/responses
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# ==================== REQUEST SCHEMAS ====================

class MediaReferenceSchema(BaseModel):
    """Media reference schema"""
    media_key: str
    file_name: str
    file_type: str
    file_size: int
    url: str
    alt_text: Optional[str] = None
    duration: Optional[int] = None

class EmbeddedComponentSchema(BaseModel):
    """Embedded component schema"""
    component_id: str
    type: str
    position: int
    title: str
    required: bool = True
    estimated_duration: int = 10
    data: Dict[str, Any]

class CreatePageRequest(BaseModel):
    """Request untuk create new page"""
    page_number: int = Field(..., ge=1, description="Page number (must be unique)")
    title: str = Field(..., min_length=1, max_length=200)
    content_markdown: str = Field(default="", description="Markdown content")
    media_references: List[MediaReferenceSchema] = Field(default_factory=list)
    embedded_components: List[EmbeddedComponentSchema] = Field(default_factory=list)
    estimated_duration: int = Field(default=10, ge=1, le=180)
    difficulty_level: str = Field(default="medium")
    learning_objectives: List[str] = Field(default_factory=list)
    status: str = Field(default="published")
    
    @validator('difficulty_level')
    def validate_difficulty(cls, v):
        allowed = ['easy', 'medium', 'hard']
        if v not in allowed:
            raise ValueError(f'Difficulty must be one of {allowed}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed = ['draft', 'published', 'archived']
        if v not in allowed:
            raise ValueError(f'Status must be one of {allowed}')
        return v

class UpdatePageRequest(BaseModel):
    """Request untuk update page"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content_markdown: Optional[str] = None
    media_references: Optional[List[MediaReferenceSchema]] = None
    embedded_components: Optional[List[EmbeddedComponentSchema]] = None
    estimated_duration: Optional[int] = Field(None, ge=1, le=180)
    difficulty_level: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    status: Optional[str] = None
    
    @validator('difficulty_level')
    def validate_difficulty(cls, v):
        if v is not None:
            allowed = ['easy', 'medium', 'hard']
            if v not in allowed:
                raise ValueError(f'Difficulty must be one of {allowed}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed = ['draft', 'published', 'archived']
            if v not in allowed:
                raise ValueError(f'Status must be one of {allowed}')
        return v

class ReorderPagesRequest(BaseModel):
    """Request untuk reorder pages"""
    page_numbers: List[int] = Field(..., description="New order of page numbers")
    
    @validator('page_numbers')
    def validate_order(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Page numbers must be unique')
        if min(v) < 1:
            raise ValueError('Page numbers must be >= 1')
        return v

# ==================== RESPONSE SCHEMAS ====================

class PageResponse(BaseModel):
    """Response untuk single page"""
    id: str
    lesson_id: str
    page_number: int
    title: str
    content_markdown: str
    media_references: List[MediaReferenceSchema]
    embedded_components: List[EmbeddedComponentSchema]
    estimated_duration: int
    difficulty_level: str
    learning_objectives: List[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class PageSummaryResponse(BaseModel):
    """Response untuk page summary (tanpa content)"""
    page_number: int
    title: str
    estimated_duration: int
    difficulty_level: str
    status: str
    has_media: bool
    has_components: bool
    media_count: int
    component_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PagesListResponse(BaseModel):
    """Response untuk list pages"""
    lesson_id: str
    lesson_title: str
    total_pages: int
    pages: List[PageSummaryResponse]

class PageWithNavigationResponse(BaseModel):
    """Response untuk single page dengan navigation info"""
    lesson_id: str
    lesson_title: str
    total_pages: int
    current_page: int
    has_previous: bool
    has_next: bool
    previous_page: Optional[int] = None
    next_page: Optional[int] = None
    page: PageResponse

class BatchPagesResponse(BaseModel):
    """Response untuk batch pages (prefetch)"""
    lesson_id: str
    pages: List[PageResponse]
    page_numbers: List[int]
