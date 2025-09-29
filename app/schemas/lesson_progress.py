# ==============================================================================
# File: app/schemas/lesson_progress.py
# Deskripsi: Pydantic schemas untuk Progress Tracking API
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.base import PyObjectId
from app.schemas.pagination import PaginatedResponse

# ==================== PROGRESS DATA SCHEMAS ====================

class OverallProgressSchema(BaseModel):
    """Schema untuk overall progress"""
    percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = Field(default="not_started", description="not_started | in_progress | completed | paused")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    
    total_time_spent: int = Field(default=0, description="Total time in seconds")
    estimated_remaining_time: int = Field(default=0, description="Estimated remaining time in minutes")
    
    milestones_completed: int = Field(default=0)
    total_milestones: int = Field(default=0)

class GranularityProgressSchema(BaseModel):
    """Schema untuk granularity progress"""
    granularity_id: PyObjectId
    granularity_title: Optional[str] = None
    status: str = Field(default="not_started")
    percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    time_spent: int = Field(default=0, description="Time spent in seconds")
    first_accessed: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    completion_requirements_met: Dict[str, bool] = Field(default_factory=dict)
    content_progress_summary: Dict[str, Any] = Field(default_factory=dict)

class ContentProgressSchema(BaseModel):
    """Schema untuk content progress"""
    content_id: PyObjectId
    content_title: Optional[str] = None
    content_type: Optional[str] = None
    viewed: bool = Field(default=False)
    view_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    time_spent: int = Field(default=0, description="Time spent in seconds")
    first_viewed: Optional[datetime] = None
    last_viewed: Optional[datetime] = None
    
    interactions_count: int = Field(default=0)
    bookmarked: bool = Field(default=False)
    rated: Optional[int] = Field(None, ge=1, le=5)
    
    completion_criteria_met: bool = Field(default=False)

class SessionDataSchema(BaseModel):
    """Schema untuk session data"""
    session_start: datetime
    session_end: Optional[datetime] = None
    duration: int = Field(default=0, description="Duration in seconds")
    
    device_type: Optional[str] = None
    location: Optional[str] = None
    
    contents_viewed: List[PyObjectId] = Field(default_factory=list)
    assignments_attempted: List[PyObjectId] = Field(default_factory=list)
    interactions_count: int = Field(default=0)
    
    focus_score: float = Field(default=0.0, ge=0.0, le=100.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=100.0)

class LearningStatisticsSchema(BaseModel):
    """Schema untuk learning statistics"""
    total_time_spent: int = Field(default=0)
    session_count: int = Field(default=0)
    avg_session_duration: int = Field(default=0)
    
    completion_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    content_completion_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    assignment_completion_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    
    avg_engagement_score: float = Field(default=0.0, ge=0.0, le=100.0)
    total_interactions: int = Field(default=0)
    bookmarks_count: int = Field(default=0)
    
    most_active_hour: Optional[int] = Field(None, ge=0, le=23)
    most_active_day: Optional[str] = None
    learning_streak: int = Field(default=0)
    
    quiz_average_score: float = Field(default=0.0, ge=0.0, le=100.0)
    assignment_average_score: float = Field(default=0.0, ge=0.0, le=100.0)
    improvement_trend: float = Field(default=0.0)

# ==================== REQUEST SCHEMAS ====================

class ProgressUpdateRequest(BaseModel):
    """Request schema untuk updating progress"""
    content_id: Optional[PyObjectId] = Field(None, description="Content that was accessed")
    granularity_id: Optional[PyObjectId] = Field(None, description="Granularity that was accessed")
    
    # Activity data
    time_spent: int = Field(default=0, description="Time spent in this session (seconds)")
    view_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="View completion percentage")
    interactions_count: int = Field(default=0)
    
    # Session context
    device_type: Optional[str] = None
    activity_type: str = Field(default="view", description="view | interaction | completion")
    
    # Completion indicators
    completed: bool = Field(default=False, description="User completed this content/granularity")
    milestone_reached: Optional[str] = Field(None, description="Milestone identifier if reached")

class SessionStartRequest(BaseModel):
    """Request schema untuk starting learning session"""
    lesson_id: PyObjectId
    device_type: Optional[str] = None
    planned_duration: Optional[int] = Field(None, description="Planned session duration in minutes")

class SessionEndRequest(BaseModel):
    """Request schema untuk ending learning session"""
    session_id: str
    final_activity: Optional[str] = Field(None, description="Last activity before ending session")

class ProgressGoalsRequest(BaseModel):
    """Request schema untuk setting learning goals"""
    lesson_id: PyObjectId
    target_completion_date: Optional[datetime] = None
    daily_time_goal: Optional[int] = Field(None, description="Daily learning time goal in minutes")
    weekly_time_goal: Optional[int] = Field(None, description="Weekly learning time goal in minutes")
    completion_target: float = Field(default=100.0, ge=0.0, le=100.0, description="Target completion percentage")
    custom_goals: Optional[Dict[str, Any]] = Field(None, description="Custom learning goals")

class BookmarkRequest(BaseModel):
    """Request schema untuk bookmarking content"""
    content_id: PyObjectId
    bookmark_note: Optional[str] = Field(None, max_length=500, description="Optional note for bookmark")

class ContentRatingRequest(BaseModel):
    """Request schema untuk rating content"""
    content_id: PyObjectId
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    review_text: Optional[str] = Field(None, max_length=1000, description="Optional review text")

# ==================== RESPONSE SCHEMAS ====================

class ProgressSummaryResponse(BaseModel):
    """Response schema untuk progress summary"""
    user_id: str
    user_name: Optional[str] = None
    lesson_id: str
    lesson_title: str
    
    overall_percentage: float
    status: str
    last_accessed: Optional[datetime] = None
    total_time_spent: int
    
    # Quick stats
    completed_granularities: int = 0
    total_granularities: int = 0
    completed_content: int = 0
    total_content: int = 0
    
    # Current activity
    current_granularity: Optional[str] = None
    current_granularity_title: Optional[str] = None
    next_content: Optional[str] = None
    next_content_title: Optional[str] = None

class DetailedProgressResponse(BaseModel):
    """Response schema untuk detailed progress"""
    id: str
    user_id: str
    lesson_id: str
    lesson_title: str
    
    # Overall progress
    overall_progress: OverallProgressSchema
    
    # Granular progress
    granularity_progress: List[GranularityProgressSchema]
    content_progress: List[ContentProgressSchema]
    
    # Current session
    current_session: Optional[SessionDataSchema] = None
    recent_sessions: List[SessionDataSchema] = Field(default_factory=list)
    
    # Statistics
    statistics: LearningStatisticsSchema
    
    # Goals and milestones
    learning_goals: Optional[Dict[str, Any]] = None
    target_completion_date: Optional[datetime] = None
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Flags
    is_paused: bool = False
    pause_reason: Optional[str] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime

class ProgressAnalyticsResponse(BaseModel):
    """Response schema untuk progress analytics"""
    # Overall metrics
    total_users: int
    active_users: int
    completed_users: int
    average_completion_rate: float
    average_completion_time: int
    
    # Progress distribution
    progress_distribution: Dict[str, int]  # percentage ranges and counts
    completion_by_granularity: List[Dict[str, Any]]
    
    # Time analytics
    learning_time_trends: List[Dict[str, Any]]
    peak_learning_hours: Dict[int, int]
    learning_patterns: Dict[str, Any]
    
    # User engagement
    engagement_levels: Dict[str, int]
    most_engaged_users: List[Dict[str, Any]]
    content_engagement: List[Dict[str, Any]]
    
    # Goals and achievements
    goal_achievement_rate: float
    common_completion_paths: List[Dict[str, Any]]
    drop_off_points: List[Dict[str, Any]]

class SessionResponse(BaseModel):
    """Response schema untuk learning session"""
    id: str
    lesson_id: str
    session_start: datetime
    session_end: Optional[datetime] = None
    duration: int
    is_active: bool
    
    # Activity summary
    contents_viewed: List[str] = Field(default_factory=list)
    assignments_attempted: List[str] = Field(default_factory=list)
    interactions_count: int = 0
    
    # Quality metrics
    focus_score: float = 0.0
    engagement_score: float = 0.0
    
    # Context
    device_type: Optional[str] = None
    location: Optional[str] = None

class BookmarkResponse(BaseModel):
    """Response schema untuk bookmark"""
    id: str
    content_id: str
    content_title: Optional[str] = None
    content_type: Optional[str] = None
    lesson_id: str
    lesson_title: Optional[str] = None
    
    bookmark_note: Optional[str] = None
    created_at: datetime
    
    # Quick access
    content_url: Optional[str] = None
    progress_percentage: float = 0.0

class LeaderboardResponse(BaseModel):
    """Response schema untuk leaderboard"""
    rank: int
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    
    # Metrics
    completion_percentage: float
    total_time_spent: int
    lessons_completed: int
    assignments_completed: int
    
    # Achievements
    badges: List[str] = Field(default_factory=list)
    streak_days: int = 0
    engagement_score: float = 0.0

# ==================== ANALYTICS REQUEST SCHEMAS ====================

class ProgressAnalyticsRequest(BaseModel):
    """Request schema untuk progress analytics"""
    lesson_ids: Optional[List[PyObjectId]] = None
    user_ids: Optional[List[PyObjectId]] = None
    class_ids: Optional[List[PyObjectId]] = None
    
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    group_by: str = Field(default="lesson", description="lesson | user | class | granularity")
    include_details: bool = Field(default=False)
    time_zone: str = Field(default="UTC")

class LearningPathAnalyticsRequest(BaseModel):
    """Request schema untuk learning path analytics"""
    lesson_id: PyObjectId
    min_users: int = Field(default=5, description="Minimum users to consider a path significant")
    path_depth: int = Field(default=10, description="Maximum path depth to analyze")

class EngagementAnalyticsRequest(BaseModel):
    """Request schema untuk engagement analytics"""
    lesson_ids: Optional[List[PyObjectId]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    metrics: List[str] = Field(
        default=["view_time", "interactions", "completion_rate", "return_rate"],
        description="Metrics to include in analysis"
    )

# ==================== FILTER & QUERY SCHEMAS ====================

class ProgressFilters(BaseModel):
    """Schema untuk progress filtering"""
    lesson_id: Optional[PyObjectId] = None
    user_id: Optional[PyObjectId] = None
    status: Optional[str] = None
    completion_percentage_min: Optional[float] = Field(None, ge=0.0, le=100.0)
    completion_percentage_max: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    # Time filters
    last_accessed_after: Optional[datetime] = None
    last_accessed_before: Optional[datetime] = None
    completed_after: Optional[datetime] = None
    completed_before: Optional[datetime] = None
    
    # Activity filters
    min_time_spent: Optional[int] = None
    max_time_spent: Optional[int] = None
    has_bookmarks: Optional[bool] = None
    is_paused: Optional[bool] = None

class ProgressSortBy(BaseModel):
    """Schema untuk progress sorting"""
    field: str = Field(default="last_accessed", description="Field to sort by")
    direction: str = Field(default="desc", description="asc | desc")
    
    @validator('field')
    def validate_sort_field(cls, v):
        allowed_fields = [
            'overall_percentage', 'last_accessed', 'total_time_spent', 
            'completed_at', 'created_at', 'updated_at'
        ]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of {allowed_fields}')
        return v

# ==================== PAGINATED RESPONSES ====================

class PaginatedProgressResponse(PaginatedResponse[ProgressSummaryResponse]):
    """Paginated response untuk progress lists"""
    total_completed: Optional[int] = None
    total_in_progress: Optional[int] = None
    total_not_started: Optional[int] = None
    average_completion_rate: Optional[float] = None

class PaginatedBookmarkResponse(PaginatedResponse[BookmarkResponse]):
    """Paginated response untuk bookmark lists"""
    total_by_content_type: Optional[Dict[str, int]] = None

class PaginatedLeaderboardResponse(PaginatedResponse[LeaderboardResponse]):
    """Paginated response untuk leaderboard"""
    current_user_rank: Optional[int] = None
    total_participants: Optional[int] = None

# ==================== BULK OPERATIONS ====================

class BulkProgressUpdateRequest(BaseModel):
    """Request schema untuk bulk progress updates"""
    updates: List[Dict[str, Any]] = Field(..., description="List of progress updates")
    batch_id: Optional[str] = Field(None, description="Batch identifier for tracking")

class ProgressResetRequest(BaseModel):
    """Request schema untuk resetting progress"""
    user_ids: List[PyObjectId] = Field(..., description="Users to reset progress for")
    lesson_ids: List[PyObjectId] = Field(..., description="Lessons to reset progress for")
    reset_type: str = Field(default="soft", description="soft | hard")
    reason: Optional[str] = Field(None, description="Reason for reset")

class ProgressExportRequest(BaseModel):
    """Request schema untuk exporting progress data"""
    lesson_ids: Optional[List[PyObjectId]] = None
    user_ids: Optional[List[PyObjectId]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    format: str = Field(default="csv", description="csv | xlsx | json")
    include_details: bool = Field(default=True)
    include_sessions: bool = Field(default=False)
