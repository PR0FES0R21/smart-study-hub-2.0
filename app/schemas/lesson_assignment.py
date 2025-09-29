# ==============================================================================
# File: app/schemas/lesson_assignment.py
# Deskripsi: Pydantic schemas untuk Assignment System API
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from app.schemas.base import PyObjectId
from app.schemas.pagination import PaginatedResponse

# ==================== ASSIGNMENT DATA SCHEMAS ====================

class AssignmentSettingsSchema(BaseModel):
    """Schema untuk assignment settings"""
    due_date: Optional[datetime] = None
    max_attempts: int = Field(default=0, ge=0, description="0 = unlimited")
    time_limit: int = Field(default=0, ge=0, description="Time limit in seconds, 0 = no limit")
    
    # Submission settings
    late_submission: bool = Field(default=False)
    late_penalty: float = Field(default=0.0, ge=0.0, le=100.0, description="Late penalty percentage")
    
    # Grading settings
    auto_grade: bool = Field(default=False)
    show_correct_answers: bool = Field(default=True)
    show_grade_immediately: bool = Field(default=True)
    
    # Availability
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    
    # Security
    require_lockdown_browser: bool = Field(default=False)
    randomize_questions: bool = Field(default=False)
    randomize_options: bool = Field(default=False)

class FileRequirementsSchema(BaseModel):
    """Schema untuk file upload requirements"""
    max_file_size: int = Field(default=50 * 1024 * 1024, description="Max file size in bytes")
    allowed_types: List[str] = Field(
        default=["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "jpg", "jpeg", "png"],
        description="Allowed file extensions"
    )
    max_files: int = Field(default=5, ge=1)
    required_files: int = Field(default=1, ge=1)
    total_size_limit: int = Field(default=100 * 1024 * 1024)
    
    # File naming
    file_naming_pattern: Optional[str] = None
    require_specific_names: bool = Field(default=False)
    required_file_names: List[str] = Field(default_factory=list)

class MCQQuestionSchema(BaseModel):
    """Schema untuk MCQ question"""
    question_id: str = Field(..., description="Unique question ID")
    question_text: str = Field(..., min_length=1, description="Question text")
    question_type: str = Field(default="single", description="single | multiple | true_false")
    
    options: List[str] = Field(..., min_items=2, description="Answer options")
    correct_answers: List[int] = Field(..., min_items=1, description="Correct answer indices")
    
    points: float = Field(default=1.0, ge=0.0)
    explanation: Optional[str] = Field(None, description="Explanation for correct answer")
    
    # Media support
    question_image: Optional[str] = None
    option_images: List[Optional[str]] = Field(default_factory=list)
    
    # Metadata
    difficulty: str = Field(default="medium", description="easy | medium | hard")
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @validator('correct_answers')
    def validate_correct_answers(cls, v, values):
        if 'options' in values and v:
            max_index = len(values['options']) - 1
            for answer in v:
                if answer < 0 or answer > max_index:
                    raise ValueError(f"Correct answer index {answer} is out of range")
        return v
    
    @validator('question_type')
    def validate_question_type(cls, v):
        allowed_types = ['single', 'multiple', 'true_false']
        if v not in allowed_types:
            raise ValueError(f'question_type must be one of {allowed_types}')
        return v

class EssaySettingsSchema(BaseModel):
    """Schema untuk essay assignment settings"""
    min_words: int = Field(default=0, ge=0)
    max_words: int = Field(default=0, ge=0, description="0 = no limit")
    
    # Grading rubric
    rubric: Optional[str] = None
    rubric_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Format requirements
    required_format: Optional[str] = None
    allow_rich_text: bool = Field(default=True)
    require_citations: bool = Field(default=False)
    
    # AI assistance
    allow_ai_assistance: bool = Field(default=True)
    plagiarism_check: bool = Field(default=True)

# ==================== REQUEST SCHEMAS ====================

class AssignmentCreateRequest(BaseModel):
    """Request schema untuk creating assignment"""
    lesson_id: Optional[PyObjectId] = Field(None, description="Parent lesson (optional)")
    granularity_id: Optional[PyObjectId] = Field(None, description="Parent granularity (optional)")
    
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    instructions: Optional[str] = Field(None, max_length=10000)
    
    assignment_type: str = Field(..., description="file_upload | essay | mcq | mixed")
    settings: AssignmentSettingsSchema = Field(default_factory=AssignmentSettingsSchema)
    
    # Type-specific data
    file_requirements: Optional[FileRequirementsSchema] = None
    questions: Optional[List[MCQQuestionSchema]] = None
    essay_settings: Optional[EssaySettingsSchema] = None
    assignment_parts: Optional[List[Dict[str, Any]]] = None
    
    # Grading
    total_points: float = Field(default=100.0, gt=0.0)
    passing_score: float = Field(default=60.0, ge=0.0, le=100.0)
    weight: float = Field(default=1.0, ge=0.0)
    
    # Integration
    is_required: bool = Field(default=True)
    unlock_next_content: bool = Field(default=False)
    
    @validator('assignment_type')
    def validate_assignment_type(cls, v):
        allowed_types = ['file_upload', 'essay', 'mcq', 'mixed']
        if v not in allowed_types:
            raise ValueError(f'assignment_type must be one of {allowed_types}')
        return v
    
    @validator('lesson_id', 'granularity_id')
    def validate_parent_required(cls, v, values, field):
        # At least one parent must be specified
        if field.name == 'granularity_id' and not v and not values.get('lesson_id'):
            raise ValueError('Either lesson_id or granularity_id must be specified')
        return v

class AssignmentUpdateRequest(BaseModel):
    """Request schema untuk updating assignment"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    instructions: Optional[str] = Field(None, max_length=10000)
    
    settings: Optional[AssignmentSettingsSchema] = None
    file_requirements: Optional[FileRequirementsSchema] = None
    questions: Optional[List[MCQQuestionSchema]] = None
    essay_settings: Optional[EssaySettingsSchema] = None
    
    total_points: Optional[float] = Field(None, gt=0.0)
    passing_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    weight: Optional[float] = Field(None, ge=0.0)
    
    is_required: Optional[bool] = None
    unlock_next_content: Optional[bool] = None

class AssignmentPublishRequest(BaseModel):
    """Request schema untuk publishing assignment"""
    publish: bool = Field(..., description="True to publish, False to unpublish")
    notify_students: bool = Field(default=True, description="Send notification to students")
    publish_message: Optional[str] = Field(None, max_length=500)

# ==================== SUBMISSION SCHEMAS ====================

class SubmissionFileSchema(BaseModel):
    """Schema untuk submitted file"""
    filename: str
    file_url: str
    file_size: int
    file_type: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    virus_scan_status: str = Field(default="pending", description="pending | clean | infected")
    processing_status: str = Field(default="pending", description="pending | processed | failed")
    
    checksum: Optional[str] = None
    thumbnail_url: Optional[str] = None

class SubmissionDataSchema(BaseModel):
    """Schema untuk submission data"""
    # File upload data
    files: List[SubmissionFileSchema] = Field(default_factory=list)
    
    # Essay data
    essay_content: Optional[str] = None
    word_count: Optional[int] = None
    
    # MCQ data
    mcq_answers: Dict[str, Union[int, List[int]]] = Field(default_factory=dict)
    
    # Mixed assignment data
    mixed_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional
    submission_notes: Optional[str] = Field(None, max_length=1000)
    draft_saved_at: Optional[datetime] = None

class SubmissionCreateRequest(BaseModel):
    """Request schema untuk creating submission"""
    assignment_id: PyObjectId
    submission_data: SubmissionDataSchema
    
    # Submission metadata
    is_final: bool = Field(default=False, description="True for final submission, False for draft")
    student_comments: Optional[str] = Field(None, max_length=1000)
    
    # Technical metadata (auto-populated by system)
    time_spent: Optional[int] = Field(None, description="Time spent in seconds")

class SubmissionUpdateRequest(BaseModel):
    """Request schema untuk updating submission (draft only)"""
    submission_data: SubmissionDataSchema
    student_comments: Optional[str] = Field(None, max_length=1000)
    
    # Only allow updates to drafts
    @validator('submission_data')
    def validate_draft_only(cls, v, values):
        # This validation would be enhanced in the actual implementation
        # to check if the submission is still in draft status
        return v

class SubmissionSubmitRequest(BaseModel):
    """Request schema untuk submitting final submission"""
    final_comments: Optional[str] = Field(None, max_length=1000)
    acknowledge_late: bool = Field(default=False, description="Acknowledge late submission if applicable")

# ==================== GRADING SCHEMAS ====================

class GradingRubricSchema(BaseModel):
    """Schema untuk grading rubric"""
    criterion_name: str = Field(..., min_length=1, max_length=200)
    max_points: float = Field(..., gt=0.0)
    earned_points: float = Field(default=0.0, ge=0.0)
    feedback: Optional[str] = Field(None, max_length=1000)

class GradingSchema(BaseModel):
    """Schema untuk grading"""
    score: float = Field(default=0.0, ge=0.0)
    max_score: float = Field(..., gt=0.0)
    percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    feedback: Optional[str] = Field(None, max_length=2000)
    rubric_scores: List[GradingRubricSchema] = Field(default_factory=list)
    
    graded_by: Optional[PyObjectId] = None
    graded_at: Optional[datetime] = None
    grading_method: str = Field(default="manual", description="manual | auto | ai_assisted")
    
    late_penalty_applied: float = Field(default=0.0, ge=0.0)
    bonus_points: float = Field(default=0.0, ge=0.0)

class GradeSubmissionRequest(BaseModel):
    """Request schema untuk grading submission"""
    grading: GradingSchema
    return_to_student: bool = Field(default=True, description="Return graded submission to student")
    send_notification: bool = Field(default=True, description="Send grade notification")

class BulkGradingRequest(BaseModel):
    """Request schema untuk bulk grading"""
    submission_ids: List[PyObjectId] = Field(..., min_items=1)
    grading_template: GradingSchema
    individual_feedback: Optional[Dict[str, str]] = Field(None, description="Individual feedback per submission")

# ==================== RESPONSE SCHEMAS ====================

class AssignmentSummaryResponse(BaseModel):
    """Response schema untuk assignment summary"""
    id: str
    title: str
    assignment_type: str
    total_points: float
    due_date: Optional[datetime] = None
    status: str
    is_published: bool
    
    # Context
    lesson_title: Optional[str] = None
    granularity_title: Optional[str] = None
    teacher_name: Optional[str] = None
    
    # Statistics
    total_submissions: int = 0
    avg_score: float = 0.0
    completion_rate: float = 0.0
    
    # User-specific data
    user_submission_count: int = 0
    user_best_score: Optional[float] = None
    user_can_submit: bool = True
    remaining_attempts: Optional[int] = None
    is_overdue: bool = False

class AssignmentDetailResponse(BaseModel):
    """Response schema untuk detailed assignment"""
    id: str
    lesson_id: Optional[str] = None
    granularity_id: Optional[str] = None  
    teacher_id: str
    
    title: str
    description: str
    instructions: Optional[str] = None
    assignment_type: str
    
    settings: AssignmentSettingsSchema
    file_requirements: Optional[FileRequirementsSchema] = None
    questions: Optional[List[MCQQuestionSchema]] = None
    essay_settings: Optional[EssaySettingsSchema] = None
    assignment_parts: Optional[List[Dict[str, Any]]] = None
    
    total_points: float
    passing_score: float
    weight: float
    
    is_required: bool
    unlock_next_content: bool
    
    status: str
    is_published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    total_submissions: int = 0
    avg_score: float = 0.0
    completion_rate: float = 0.0
    
    # Context
    lesson_title: Optional[str] = None
    granularity_title: Optional[str] = None
    teacher_name: Optional[str] = None
    
    # User-specific data
    user_submission: Optional['SubmissionSummaryResponse'] = None
    user_can_edit: bool = False
    user_can_delete: bool = False
    user_can_grade: bool = False

class SubmissionSummaryResponse(BaseModel):
    """Response schema untuk submission summary"""
    id: str
    assignment_id: str
    assignment_title: Optional[str] = None
    student_id: str
    student_name: Optional[str] = None
    
    submission_number: int
    status: str
    is_late: bool
    
    submitted_at: Optional[datetime] = None
    time_spent: int = 0
    
    # Grading
    score: Optional[float] = None
    percentage: Optional[float] = None
    graded_at: Optional[datetime] = None
    
    # Quick stats
    file_count: int = 0
    word_count: Optional[int] = None
    has_feedback: bool = False

class SubmissionDetailResponse(BaseModel):
    """Response schema untuk detailed submission"""
    id: str
    assignment_id: str
    student_id: str
    submission_number: int
    
    submission_data: SubmissionDataSchema
    status: str
    is_late: bool
    
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    time_spent: int = 0
    
    grading: Optional[GradingSchema] = None
    
    # Academic integrity
    plagiarism_score: Optional[float] = None
    ai_detection_score: Optional[float] = None
    similarity_report: Optional[str] = None
    
    # Communication
    student_comments: Optional[str] = None
    teacher_feedback: Optional[str] = None
    feedback_viewed: bool = False
    
    # Technical metadata  
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    
    # Context
    assignment_title: Optional[str] = None
    student_name: Optional[str] = None
    
    # Permissions
    user_can_edit: bool = False
    user_can_grade: bool = False
    user_can_resubmit: bool = False

# ==================== ANALYTICS SCHEMAS ====================

class AssignmentAnalyticsRequest(BaseModel):
    """Request schema untuk assignment analytics"""
    assignment_ids: Optional[List[PyObjectId]] = None
    lesson_ids: Optional[List[PyObjectId]] = None
    class_ids: Optional[List[PyObjectId]] = None
    
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    include_question_analysis: bool = Field(default=True, description="Include per-question analysis for MCQ")
    include_time_analysis: bool = Field(default=True)
    include_grade_distribution: bool = Field(default=True)

class AssignmentAnalyticsResponse(BaseModel):
    """Response schema untuk assignment analytics"""
    assignment_id: str
    assignment_title: str
    assignment_type: str
    
    # Performance metrics
    total_attempts: int = 0
    completed_submissions: int = 0
    average_score: float = 0.0
    median_score: float = 0.0
    
    # Time analytics
    average_completion_time: int = 0
    median_completion_time: int = 0
    
    # Question analytics (for MCQ)
    question_analytics: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Difficulty analysis
    difficulty_score: float = 0.0
    discrimination_index: float = 0.0
    
    # Grade distribution
    grade_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Trends
    submission_trends: List[Dict[str, Any]] = Field(default_factory=list)
    performance_trends: List[Dict[str, Any]] = Field(default_factory=list)
    
    last_calculated: datetime = Field(default_factory=datetime.utcnow)

# ==================== FILTER & QUERY SCHEMAS ====================

class AssignmentFilters(BaseModel):
    """Schema untuk assignment filtering"""
    lesson_id: Optional[PyObjectId] = None
    granularity_id: Optional[PyObjectId] = None
    teacher_id: Optional[PyObjectId] = None
    assignment_type: Optional[str] = None
    status: Optional[str] = None
    is_published: Optional[bool] = None
    
    # Date filters
    due_after: Optional[datetime] = None
    due_before: Optional[datetime] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

class SubmissionFilters(BaseModel):
    """Schema untuk submission filtering"""
    assignment_id: Optional[PyObjectId] = None
    student_id: Optional[PyObjectId] = None
    status: Optional[str] = None
    is_late: Optional[bool] = None
    is_graded: Optional[bool] = None
    
    # Score filters
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    
    # Date filters
    submitted_after: Optional[datetime] = None
    submitted_before: Optional[datetime] = None

# ==================== PAGINATED RESPONSES ====================

class PaginatedAssignmentResponse(PaginatedResponse[AssignmentSummaryResponse]):
    """Paginated response untuk assignment lists"""
    total_published: Optional[int] = None
    total_draft: Optional[int] = None
    total_by_type: Optional[Dict[str, int]] = None
    upcoming_due_dates: Optional[List[Dict[str, Any]]] = None

class PaginatedSubmissionResponse(PaginatedResponse[SubmissionSummaryResponse]):
    """Paginated response untuk submission lists"""
    total_graded: Optional[int] = None
    total_pending: Optional[int] = None
    total_late: Optional[int] = None
    average_score: Optional[float] = None

# Forward reference resolution
AssignmentDetailResponse.model_rebuild()
