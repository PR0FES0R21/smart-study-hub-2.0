# ==============================================================================
# File: app/schemas/lesson_progress.py
# Deskripsi: Pydantic schemas untuk Progress Tracking API (Modular Architecture)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from app.schemas.base import PyObjectId
from app.schemas.pagination import PaginatedResponse

# ==================== COMPONENT PROGRESS SCHEMAS ====================

class ComponentProgressRequest(BaseModel):
    """Request untuk updating component progress"""
    component_id: str = Field(..., description="Component identifier")
    status: str = Field(..., description="not_started | in_progress | completed | failed")
    score: Optional[float] = Field(None, ge=0, le=100, description="Score achieved (0-100)")
    time_spent: int = Field(default=0, ge=0, description="Time spent in seconds")
    attempts: int = Field(default=1, ge=1, description="Number of attempts")
    responses: List[Dict[str, Any]] = Field(default_factory=list, description="User responses")

class ComponentProgressResponse(BaseModel):
    """Response untuk component progress"""
    component_id: str
    component_type: str
    status: str
    score: Optional[float] = None
    max_score: Optional[float] = None
    attempts: int
    time_spent: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: datetime
    feedback: Optional[str] = None

# ==================== PAGE PROGRESS SCHEMAS ====================

class PageProgressRequest(BaseModel):
    """Request untuk updating page progress"""
    status: str = Field(..., description="not_started | reading | completed")
    time_spent: int = Field(default=0, ge=0, description="Time spent reading (seconds)")
    completion_percentage: float = Field(default=0.0, ge=0, le=100, description="Page completion percentage")
    component_progress: List[ComponentProgressRequest] = Field(default_factory=list)

class PageProgressResponse(BaseModel):
    """Response untuk page progress"""
    page_number: int
    status: str
    time_spent: int
    completion_percentage: float
    component_progress: List[ComponentProgressResponse]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: datetime

# ==================== LESSON PROGRESS SCHEMAS ====================

class LessonProgressStartRequest(BaseModel):
    """Request untuk starting lesson progress"""
    course_id: Optional[str] = Field(None, description="Course ID if accessed via course")
    module_id: Optional[str] = Field(None, description="Module ID if accessed via module")
    access_method: str = Field(default="direct", description="direct | via_module | via_course")
    device_type: Optional[str] = Field(None, description="mobile | tablet | desktop")

class LessonProgressUpdateRequest(BaseModel):
    """Request untuk updating lesson progress"""
    status: Optional[str] = Field(None, description="not_started | in_progress | completed | failed")
    current_page: Optional[int] = Field(None, ge=1, description="Current page being viewed")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time to completion")
    device_type: Optional[str] = Field(None, description="mobile | tablet | desktop")

class LessonProgressResponse(BaseModel):
    """Response untuk lesson progress"""
    id: str
    student_id: str
    lesson_id: str
    lesson_title: Optional[str] = None
    lesson_description: Optional[str] = None
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    
    # Progress info
    status: str
    completion_percentage: float
    score: Optional[float] = None
    current_page: int
    total_pages: int
    page_progress: List[PageProgressResponse]
    
    # Time tracking
    total_time_spent: int
    estimated_time_remaining: Optional[int] = None
    
    # Metadata
    access_method: str
    device_type: Optional[str] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: datetime
    created_at: datetime

class LessonProgressSummaryResponse(BaseModel):
    """Summary response untuk lesson progress list"""
    id: str
    lesson_id: str
    lesson_title: str
    lesson_description: str
    status: str
    completion_percentage: float
    score: Optional[float] = None
    current_page: int
    total_pages: int
    total_time_spent: int
    access_method: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: datetime

# ==================== MODULE PROGRESS SCHEMAS ====================

class ModuleProgressResponse(BaseModel):
    """Response untuk module progress"""
    id: str
    student_id: str
    module_id: str
    module_title: Optional[str] = None
    module_description: Optional[str] = None
    course_id: Optional[str] = None
    
    # Progress info
    status: str
    completion_percentage: float
    score: Optional[float] = None
    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    
    # Current position
    current_lesson_id: Optional[str] = None
    lesson_completion_order: List[str] = Field(default_factory=list)
    
    # Time tracking
    total_time_spent: int
    estimated_time_remaining: Optional[int] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: datetime
    created_at: datetime

class ModuleProgressWithLessonsResponse(BaseModel):
    """Detailed module progress dengan lesson details"""
    module_progress: ModuleProgressResponse
    lesson_details: List[Dict[str, Any]]
    learning_path: List[Dict[str, Any]]
    next_lesson: Optional[Dict[str, Any]] = None
    completion_summary: Dict[str, Any]

# ==================== COURSE PROGRESS SCHEMAS ====================

class CourseEnrollmentRequest(BaseModel):
    """Request untuk enrolling in course"""
    enrollment_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CourseProgressResponse(BaseModel):
    """Response untuk course progress"""
    id: str
    student_id: str
    course_id: str
    course_title: Optional[str] = None
    course_description: Optional[str] = None
    enrollment_id: Optional[str] = None
    
    # Progress info
    status: str
    completion_percentage: float
    score: Optional[float] = None
    grade: Optional[str] = None
    
    # Module/Lesson summary
    total_modules: int
    completed_modules: int
    in_progress_modules: int
    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    
    # Current position
    current_module_id: Optional[str] = None
    current_lesson_id: Optional[str] = None
    learning_path: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Time tracking
    total_time_spent: int
    estimated_time_remaining: Optional[int] = None
    
    # Performance metrics
    average_quiz_score: float
    average_assignment_score: float
    quiz_scores: List[float] = Field(default_factory=list)
    assignment_scores: List[float] = Field(default_factory=list)
    
    # Engagement metrics
    login_count: int
    active_days: int
    streak_days: int
    longest_streak: int
    
    # Timestamps
    enrolled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    last_activity: datetime
    created_at: datetime

class CourseProgressDashboardResponse(BaseModel):
    """Comprehensive dashboard response"""
    course_progress: CourseProgressResponse
    course_info: Dict[str, Any]
    module_progress: List[Dict[str, Any]]
    learning_path: List[Dict[str, Any]]
    next_steps: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    statistics: Dict[str, Any]

# ==================== ANALYTICS SCHEMAS ====================

class LessonAnalyticsResponse(BaseModel):
    """Analytics untuk lesson progress"""
    lesson_id: str
    total_students: int
    completion_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]
    time_stats: Dict[str, Any]
    page_analytics: Dict[str, Any]
    engagement_stats: Dict[str, Any]

class ModuleAnalyticsResponse(BaseModel):
    """Analytics untuk module progress"""
    module_id: str
    total_students: int
    completion_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]
    lesson_analytics: Dict[str, Any]
    engagement_stats: Dict[str, Any]

class CourseAnalyticsResponse(BaseModel):
    """Analytics untuk course progress"""
    course_id: str
    enrollment_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]
    module_analytics: Dict[str, Any]
    engagement_analytics: Dict[str, Any]
    trends: Dict[str, Any]

# ==================== ACTIVITY SCHEMAS ====================

class ActivityRecordRequest(BaseModel):
    """Request untuk recording activity"""
    activity_type: str = Field(..., description="page_view | component_interaction | session_start | session_end")
    time_spent: int = Field(default=0, ge=0, description="Time spent in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional activity data")

class ActivityResponse(BaseModel):
    """Response untuk activity record"""
    success: bool
    message: str
    updated_progress: Optional[Dict[str, Any]] = None

# ==================== FILTER & SORT SCHEMAS ====================

class ProgressFilters(BaseModel):
    """Filters untuk progress queries"""
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    status: Optional[str] = None
    access_method: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_completion: Optional[float] = Field(None, ge=0, le=100)
    max_completion: Optional[float] = Field(None, ge=0, le=100)

# ==================== BATCH OPERATION SCHEMAS ====================

class BatchProgressUpdateRequest(BaseModel):
    """Request untuk batch progress updates"""
    updates: List[Dict[str, Any]] = Field(..., description="List of progress updates")
    update_type: str = Field(..., description="activity_timestamp | completion_status | scores")

class BatchProgressUpdateResponse(BaseModel):
    """Response untuk batch updates"""
    success: bool
    updated_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)

# ==================== STATISTICS SCHEMAS ====================

class ProgressStatsRequest(BaseModel):
    """Request untuk progress statistics"""
    student_ids: Optional[List[str]] = None
    course_ids: Optional[List[str]] = None
    module_ids: Optional[List[str]] = None
    lesson_ids: Optional[List[str]] = None
    date_range: Optional[Dict[str, datetime]] = None
    group_by: str = Field(default="student", description="student | course | module | lesson | date")

class ProgressStatsResponse(BaseModel):
    """Response untuk progress statistics"""
    total_records: int
    completion_rates: Dict[str, float]
    performance_metrics: Dict[str, Any]
    time_analytics: Dict[str, Any]
    engagement_metrics: Dict[str, Any]
    trends: Dict[str, Any]

# ==================== PAGINATED RESPONSES ====================

class PaginatedLessonProgressResponse(PaginatedResponse[LessonProgressSummaryResponse]):
    """Paginated lesson progress response"""
    summary_stats: Optional[Dict[str, Any]] = None

class PaginatedModuleProgressResponse(PaginatedResponse[ModuleProgressResponse]):
    """Paginated module progress response"""
    summary_stats: Optional[Dict[str, Any]] = None

class PaginatedCourseProgressResponse(PaginatedResponse[CourseProgressResponse]):
    """Paginated course progress response"""
    summary_stats: Optional[Dict[str, Any]] = None

# ==================== OPERATION RESPONSES ====================

class ProgressOperationResponse(BaseModel):
    """Generic progress operation response"""
    success: bool
    message: str
    progress_id: Optional[str] = None
    updated_fields: Optional[List[str]] = None
    next_steps: Optional[List[Dict[str, Any]]] = None
