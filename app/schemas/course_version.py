# ==============================================================================
# File: app/schemas/course_version.py
# Deskripsi: Pydantic schemas untuk Course Version System API
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.base import PyObjectId
from app.schemas.pagination import PaginatedResponse

# ==================== REQUEST SCHEMAS ====================

class MediaReferenceSchema(BaseModel):
    """Schema untuk media reference"""
    media_key: str = Field(..., description="Key untuk reference dalam markdown")
    url: Optional[str] = Field(None, description="URL (auto-filled by system)")
    type: str = Field(..., description="image | video | audio | document")
    filename: str = Field(..., description="Original filename")
    alt_text: Optional[str] = Field(None, description="Alt text untuk accessibility")
    duration: Optional[int] = Field(None, description="Duration for video/audio")

class EmbeddedComponentSchema(BaseModel):
    """Schema untuk embedded component"""
    component_id: str = Field(..., description="Unique component ID")
    type: str = Field(..., description="quiz | assignment | interactive")
    position: int = Field(..., description="Position dalam markdown")
    data: Dict[str, Any] = Field(..., description="Component configuration")
    required: bool = Field(default=True)
    estimated_duration: int = Field(default=10, description="Estimated duration (minutes)")

class LessonContentSchema(BaseModel):
    """Schema untuk lesson content"""
    lesson_id: Optional[PyObjectId] = Field(None, description="Auto-generated if not provided")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    order: int = Field(..., ge=0)
    content_markdown: str = Field(..., description="Main content dalam markdown")
    media_references: List[MediaReferenceSchema] = Field(default_factory=list)
    embedded_components: List[EmbeddedComponentSchema] = Field(default_factory=list)
    estimated_duration: int = Field(default=30, description="Minutes")
    difficulty_level: str = Field(default="medium", description="easy | medium | hard")
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)

class CourseModuleSchema(BaseModel):
    """Schema untuk course module"""
    module_id: Optional[PyObjectId] = Field(None, description="Auto-generated if not provided")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    order: int = Field(..., ge=0)
    lessons: List[LessonContentSchema] = Field(default_factory=list)
    estimated_duration: int = Field(default=0, description="Auto-calculated from lessons")
    difficulty_level: str = Field(default="medium")
    completion_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "all_lessons",
            "required_percentage": 100
        }
    )

class CourseFamilyCreateRequest(BaseModel):
    """Request untuk creating course family"""
    base_title: str = Field(..., min_length=1, max_length=200, description="Course title")
    subject_id: PyObjectId = Field(..., description="Subject ID")
    grade_level: int = Field(..., ge=1, le=12, description="Grade level")
    description: str = Field(..., max_length=2000, description="Course description")
    modules: List[CourseModuleSchema] = Field(default_factory=list, description="Initial modules")

class TeacherForkCreateRequest(BaseModel):
    """Request untuk creating teacher fork"""
    master_version_id: PyObjectId = Field(..., description="Master version to fork from")
    class_ids: List[PyObjectId] = Field(..., min_items=1, description="Classes yang akan use fork ini")
    fork_title_suffix: Optional[str] = Field(None, max_length=100, description="Optional suffix for fork title")

class CourseContentUpdateRequest(BaseModel):
    """Request untuk updating course content"""
    modules: Optional[List[CourseModuleSchema]] = Field(None, description="Updated modules")
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Settings updates
    settings: Optional[Dict[str, Any]] = Field(None, description="Course settings")
    
class ChangeProposalSchema(BaseModel):
    """Schema untuk change proposal dalam PR"""
    action: str = Field(..., description="add_module | remove_module | modify_module | add_lesson | etc.")
    target_type: str = Field(..., description="module | lesson | content | component")
    target_id: Optional[PyObjectId] = Field(None, description="Target element ID")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=1000)
    rationale: str = Field(..., max_length=1000, description="Why this change is needed")
    
    # Change data
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    insertion_data: Optional[Dict[str, Any]] = None
    insertion_position: Optional[int] = None
    
    # Impact
    expected_impact: str = Field(default="low", description="low | medium | high")

class PullRequestCreateRequest(BaseModel):
    """Request untuk creating pull request"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=3000)
    target_version_id: PyObjectId = Field(..., description="Master version to merge into")
    changes: List[ChangeProposalSchema] = Field(..., min_items=1, description="Proposed changes")

class PullRequestReviewRequest(BaseModel):
    """Request untuk reviewing pull request"""
    decision: str = Field(..., description="approve | reject | request_revision")
    comment: str = Field(..., max_length=2000, description="Review comment")
    detailed_feedback: Optional[Dict[str, Any]] = Field(None, description="Detailed per-change feedback")

# ==================== RESPONSE SCHEMAS ====================

class UsageStatsResponse(BaseModel):
    """Response untuk usage statistics"""
    enrolled_students: int = 0
    active_students: int = 0
    completed_students: int = 0
    average_completion_rate: float = 0.0
    average_progress_percentage: float = 0.0
    total_time_spent: int = 0
    last_calculated: datetime

class CourseVersionSummaryResponse(BaseModel):
    """Summary response untuk course version"""
    id: str
    course_family_id: str
    version: str
    title: str
    subject_id: str
    subject_name: Optional[str] = None
    grade_level: int
    coordinator_id: str
    coordinator_name: Optional[str] = None
    
    # Version info
    is_master: bool
    is_active: bool
    fork_type: str
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    
    # Counts
    modules_count: int = 0
    lessons_count: int = 0
    total_duration: int = 0
    
    # Status
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Usage
    usage_stats: UsageStatsResponse

class CourseVersionDetailResponse(BaseModel):
    """Detailed response untuk course version"""
    id: str
    course_family_id: str
    version: str
    version_number: float
    title: str
    description: str
    
    # Course info
    subject_id: str
    subject_name: Optional[str] = None
    grade_level: int
    coordinator_id: str
    coordinator_name: Optional[str] = None
    academic_period_id: Optional[str] = None
    
    # Version control
    is_master: bool
    is_active: bool
    parent_version_id: Optional[str] = None
    created_from_pr_id: Optional[str] = None
    
    # Fork info
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    class_ids: List[str] = Field(default_factory=list)
    class_names: List[str] = Field(default_factory=list)
    fork_type: str
    
    # Content
    modules: List[CourseModuleSchema]
    
    # Changes tracking
    changes_from_parent: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Status
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    created_by: str
    
    # Usage statistics
    usage_stats: UsageStatsResponse
    
    # Settings
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    # User permissions
    user_can_edit: bool = False
    user_can_delete: bool = False
    user_can_fork: bool = False
    user_can_create_pr: bool = False

class CourseFamilyResponse(BaseModel):
    """Response untuk course family"""
    id: str
    course_family_id: str
    base_title: str
    subject_id: str
    subject_name: Optional[str] = None
    grade_level: int
    coordinator_id: str
    coordinator_name: Optional[str] = None
    
    # Current status
    current_master_version_id: str
    current_version: str
    
    # Statistics
    total_versions: int
    total_forks: int
    total_pull_requests: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

class WorkflowStepResponse(BaseModel):
    """Response untuk workflow step"""
    step_number: int
    action: str
    actor_id: str
    actor_name: Optional[str] = None
    timestamp: datetime
    comment: Optional[str] = None

class PullRequestSummaryResponse(BaseModel):
    """Summary response untuk pull request"""
    id: str
    pr_number: int
    title: str
    course_family_id: str
    source_version_id: str
    target_version_id: str
    requested_by: str
    requested_by_name: Optional[str] = None
    
    # Status
    status: str
    priority: str
    created_at: datetime
    
    # Review info
    assigned_reviewer: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    # Changes summary
    changes_count: int = 0
    changes_summary: Dict[str, int] = Field(default_factory=dict)
    
    # Impact
    impact_level: str = "low"

class PullRequestDetailResponse(BaseModel):
    """Detailed response untuk pull request"""
    id: str
    pr_number: int
    course_family_id: str
    title: str
    description: str
    
    # Source & target
    source_version_id: str
    target_version_id: str
    source_version_name: Optional[str] = None
    target_version_name: Optional[str] = None
    
    # Requestor
    requested_by: str
    requested_by_name: Optional[str] = None
    
    # Changes
    changes: List[ChangeProposalSchema]
    
    # Status
    status: str
    priority: str
    
    # Review
    assigned_reviewer: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_feedback: Optional[Dict[str, Any]] = None
    
    # Impact assessment
    impact_assessment: Dict[str, Any] = Field(default_factory=dict)
    
    # Workflow
    approval_workflow: List[WorkflowStepResponse] = Field(default_factory=list)
    
    # Timeline
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None
    
    # Merge info
    merged_version_id: Optional[str] = None
    merge_commit_message: Optional[str] = None
    
    # Communication
    comments_count: int = 0
    labels: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    
    # User permissions
    user_can_edit: bool = False
    user_can_review: bool = False
    user_can_merge: bool = False
    user_can_close: bool = False

class ChangeHistoryResponse(BaseModel):
    """Response untuk change history"""
    id: str
    course_family_id: str
    version_id: Optional[str] = None
    change_type: str
    title: str
    description: str
    
    # Actor
    actor_id: str
    actor_type: str
    actor_name: Optional[str] = None
    timestamp: datetime
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    changes_applied: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Impact
    impact_level: str
    notifications_sent: int = 0

# ==================== FILTER & SORT SCHEMAS ====================

class CourseVersionFilters(BaseModel):
    """Filters untuk course version lists"""
    course_family_id: Optional[PyObjectId] = None
    subject_id: Optional[PyObjectId] = None
    grade_level: Optional[int] = None
    coordinator_id: Optional[PyObjectId] = None
    teacher_id: Optional[PyObjectId] = None
    is_master: Optional[bool] = None
    is_active: Optional[bool] = None
    fork_type: Optional[str] = None
    status: Optional[str] = None
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

class PullRequestFilters(BaseModel):
    """Filters untuk pull request lists"""
    course_family_id: Optional[PyObjectId] = None
    requested_by: Optional[PyObjectId] = None
    assigned_reviewer: Optional[PyObjectId] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

# ==================== PAGINATED RESPONSES ====================

class PaginatedCourseVersionResponse(PaginatedResponse[CourseVersionSummaryResponse]):
    """Paginated course versions"""
    total_master_versions: Optional[int] = None
    total_teacher_forks: Optional[int] = None
    total_by_status: Optional[Dict[str, int]] = None

class PaginatedPullRequestResponse(PaginatedResponse[PullRequestSummaryResponse]):
    """Paginated pull requests"""
    total_pending: Optional[int] = None
    total_approved: Optional[int] = None
    total_merged: Optional[int] = None

class PaginatedChangeHistoryResponse(PaginatedResponse[ChangeHistoryResponse]):
    """Paginated change history"""
    total_by_type: Optional[Dict[str, int]] = None
    most_active_period: Optional[str] = None

# ==================== ANALYTICS SCHEMAS ====================

class CourseAnalyticsResponse(BaseModel):
    """Analytics untuk course family"""
    course_family_id: str
    
    # Version statistics
    total_versions: int
    total_forks: int
    active_forks: int
    
    # Pull request statistics
    total_prs: int
    approved_prs: int
    avg_review_time_hours: float
    
    # Usage statistics
    total_enrolled_students: int
    average_completion_rate: float
    total_learning_time: int
    
    # Activity statistics
    changes_last_30_days: int
    most_active_teachers: List[Dict[str, Any]]
    content_growth_trend: List[Dict[str, Any]]

class SystemHealthResponse(BaseModel):
    """System health untuk course management"""
    total_course_families: int
    total_versions: int
    total_active_forks: int
    pending_prs: int
    
    # Performance metrics
    avg_pr_review_time: float
    avg_fork_creation_time: float
    storage_usage_mb: float
    
    # Quality metrics
    rollback_rate: float
    error_rate: float
    user_satisfaction: float
