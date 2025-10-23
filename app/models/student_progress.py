# ==============================================================================
# File: app/models/student_progress.py
# Deskripsi: Simplified student progress tracking (New Course System)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId


class SubmissionData(BaseModel):
    """Data untuk submission (quiz/assignment)"""
    files: List[str] = Field(default_factory=list, description="Uploaded file URLs")
    text_answer: Optional[str] = Field(None, description="Text/essay answer")
    answers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Quiz answers: [{question_id, answer, is_correct}]"
    )
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    graded_at: Optional[datetime] = Field(None)
    graded_by: Optional[PyObjectId] = Field(None)
    feedback: Optional[str] = Field(None, description="Teacher feedback")
    
    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class StudentProgress(BaseModel):
    """
    Simplified progress tracking per content item.
    
    Tracks student completion of modules, lessons, and pages.
    Independent dari course - linked via course_class_setting_id.
    """
    id: Optional[str] = Field(None, alias="_id")
    
    # Identifiers
    student_id: PyObjectId = Field(..., description="Student user ID")
    course_class_setting_id: PyObjectId = Field(
        ...,
        description="Reference to course_class_settings (NOT course_id directly!)"
    )
    
    # Content identifiers (track by ID, not position)
    module_id: Optional[PyObjectId] = Field(None, description="Module ID (if module-level)")
    lesson_id: Optional[PyObjectId] = Field(None, description="Lesson ID (if lesson-level)")
    page_number: Optional[int] = Field(None, description="Page number (if page-level)")
    
    # Content type
    content_type: str = Field(
        ...,
        description="module | lesson | page | assessment"
    )
    
    # Status
    status: str = Field(
        default="not_started",
        description="not_started | in_progress | completed"
    )
    
    # Completion info
    completed_at: Optional[datetime] = Field(None, description="When completed")
    time_spent: int = Field(default=0, description="Time spent in seconds")
    
    # Score (for quizzes/assignments)
    score: Optional[float] = Field(None, description="Score achieved")
    max_score: Optional[float] = Field(None, description="Maximum possible score")
    
    # Submission (for assignments/quizzes)
    submission: Optional[SubmissionData] = Field(
        None,
        description="Submission data if this is assignment/quiz"
    )
    
    # Metadata
    attempts: int = Field(default=0, description="Number of attempts")
    started_at: Optional[datetime] = Field(None, description="When started")
    last_activity: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last activity timestamp"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['module', 'lesson', 'page', 'assessment']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of {allowed_types}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['not_started', 'in_progress', 'completed']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        data = self.dict(by_alias=True, exclude_none=True)
        
        # Remove id if None
        if data.get('_id') is None:
            data.pop('_id', None)
        
        # Convert PyObjectId to ObjectId
        for field in ['student_id', 'course_class_setting_id', 'module_id', 'lesson_id']:
            if field in data and data[field] is not None:
                if not isinstance(data[field], ObjectId):
                    data[field] = ObjectId(data[field])
        
        # Convert submission graded_by
        if 'submission' in data and data['submission']:
            if 'graded_by' in data['submission'] and data['submission']['graded_by']:
                data['submission']['graded_by'] = ObjectId(data['submission']['graded_by'])
        
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "StudentProgress":
        """Create from MongoDB document"""
        if not data:
            return None
        
        # Convert ObjectId to string
        if '_id' in data:
            data['_id'] = str(data['_id'])
        
        for field in ['student_id', 'course_class_setting_id', 'module_id', 'lesson_id']:
            if field in data and data[field] is not None:
                data[field] = str(data[field])
        
        # Convert submission graded_by
        if 'submission' in data and data['submission']:
            if 'graded_by' in data['submission'] and data['submission']['graded_by']:
                data['submission']['graded_by'] = str(data['submission']['graded_by'])
        
        return cls(**data)
    
    # ==================== HELPER METHODS ====================
    
    def mark_completed(self, score: float = None, max_score: float = None) -> None:
        """Mark content as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if score is not None:
            self.score = score
        if max_score is not None:
            self.max_score = max_score
    
    def mark_in_progress(self) -> None:
        """Mark content as in progress"""
        if self.status == "not_started":
            self.started_at = datetime.utcnow()
        
        self.status = "in_progress"
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_time_spent(self, seconds: int) -> None:
        """Add time spent"""
        self.time_spent += seconds
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def calculate_percentage(self) -> float:
        """Calculate score percentage"""
        if self.score is not None and self.max_score is not None and self.max_score > 0:
            return (self.score / self.max_score) * 100
        return 0.0
    
    def is_passed(self, passing_score: float = 70.0) -> bool:
        """Check if passed"""
        percentage = self.calculate_percentage()
        return percentage >= passing_score
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True


# ==================== AGGREGATE PROGRESS MODELS ====================

class CourseProgressSummary(BaseModel):
    """
    Aggregate summary of student progress dalam course.
    
    Calculated on-the-fly from student_progress collection.
    NOT stored in database - computed when needed.
    """
    student_id: str
    course_class_setting_id: str
    course_id: str
    
    # Module summary
    total_modules: int = 0
    completed_modules: int = 0
    in_progress_modules: int = 0
    
    # Lesson summary
    total_lessons: int = 0
    completed_lessons: int = 0
    in_progress_lessons: int = 0
    
    # Overall
    completion_percentage: float = 0.0
    average_score: float = 0.0
    total_time_spent: int = 0
    
    # Status
    status: str = "not_started"  # not_started | in_progress | completed
    
    # Dates
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def calculate_completion_percentage(self) -> float:
        """Calculate overall completion"""
        if self.total_lessons == 0:
            return 0.0
        return (self.completed_lessons / self.total_lessons) * 100
    
    def determine_status(self) -> str:
        """Determine overall status"""
        if self.completed_lessons == 0:
            return "not_started"
        elif self.completed_lessons == self.total_lessons:
            return "completed"
        else:
            return "in_progress"
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModuleProgressSummary(BaseModel):
    """
    Aggregate summary of student progress dalam module.
    
    Calculated on-the-fly from student_progress collection.
    """
    student_id: str
    course_class_setting_id: str
    module_id: str
    
    # Lesson summary
    total_lessons: int = 0
    completed_lessons: int = 0
    in_progress_lessons: int = 0
    
    # Overall
    completion_percentage: float = 0.0
    average_score: float = 0.0
    total_time_spent: int = 0
    
    # Status
    status: str = "not_started"
    
    # Dates
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
