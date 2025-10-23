# ==============================================================================
# File: app/models/assessment_submission.py
# Deskripsi: Model untuk final assessment submissions
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId


class AssessmentAnswer(BaseModel):
    """Individual answer dalam submission"""
    question_id: str = Field(..., description="Question ID from question_set")
    answer: Any = Field(..., description="Student's answer")
    is_correct: Optional[bool] = Field(None, description="Whether answer is correct")
    points_earned: float = Field(default=0.0, description="Points earned for this question")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssessmentSubmissionData(BaseModel):
    """Submission data"""
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # For quiz (auto-graded)
    answers: List[AssessmentAnswer] = Field(
        default_factory=list,
        description="Quiz answers"
    )
    
    # For assignment (file upload)
    files: List[str] = Field(
        default_factory=list,
        description="Uploaded file URLs"
    )
    
    # For essay/text submission
    text_answer: Optional[str] = Field(None, description="Text/essay answer")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssessmentGrading(BaseModel):
    """Grading information"""
    status: str = Field(
        default="pending",
        description="pending | graded | needs_revision"
    )
    score: float = Field(default=0.0, description="Score achieved")
    max_score: float = Field(..., description="Maximum possible score")
    passed: bool = Field(default=False, description="Whether student passed")
    
    graded_at: Optional[datetime] = Field(None, description="When graded")
    graded_by: Optional[PyObjectId] = Field(None, description="Teacher who graded")
    feedback: Optional[str] = Field(None, description="Teacher feedback")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'graded', 'needs_revision']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v
    
    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class AssessmentSubmission(BaseModel):
    """
    Assessment submission tracking.
    
    Tracks student submissions for course-level final assessments.
    No retake allowed (max_attempts = 1).
    """
    id: Optional[str] = Field(None, alias="_id")
    
    # Identifiers
    student_id: PyObjectId = Field(..., description="Student user ID")
    course_class_setting_id: PyObjectId = Field(
        ...,
        description="Reference to course_class_settings"
    )
    assessment_id: str = Field(..., description="Assessment ID from course.assessments")
    question_set_id: Optional[PyObjectId] = Field(
        None,
        description="Reference to question_sets (if quiz)"
    )
    
    # Submission
    submission: AssessmentSubmissionData = Field(
        ...,
        description="Submission data"
    )
    
    # Grading
    grading: AssessmentGrading = Field(
        ...,
        description="Grading information"
    )
    
    # Metadata
    attempt_number: int = Field(default=1, description="Attempt number (always 1, no retake)")
    time_spent: int = Field(default=0, description="Time spent in seconds")
    started_at: datetime = Field(..., description="When assessment started")
    completed_at: Optional[datetime] = Field(None, description="When completed/submitted")
    
    # Session tracking
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('attempt_number')
    def validate_attempt_number(cls, v):
        if v != 1:
            raise ValueError('Only 1 attempt allowed (no retake)')
        return v
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        data = self.dict(by_alias=True, exclude_none=True)
        
        # Remove id if None
        if data.get('_id') is None:
            data.pop('_id', None)
        
        # Convert PyObjectId to ObjectId
        for field in ['student_id', 'course_class_setting_id', 'question_set_id']:
            if field in data and data[field] is not None:
                if not isinstance(data[field], ObjectId):
                    data[field] = ObjectId(data[field])
        
        # Convert graded_by
        if 'grading' in data and 'graded_by' in data['grading'] and data['grading']['graded_by']:
            data['grading']['graded_by'] = ObjectId(data['grading']['graded_by'])
        
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "AssessmentSubmission":
        """Create from MongoDB document"""
        if not data:
            return None
        
        # Convert ObjectId to string
        if '_id' in data:
            data['_id'] = str(data['_id'])
        
        for field in ['student_id', 'course_class_setting_id', 'question_set_id']:
            if field in data and data[field] is not None:
                data[field] = str(data[field])
        
        # Convert graded_by
        if 'grading' in data and 'graded_by' in data['grading'] and data['grading']['graded_by']:
            data['grading']['graded_by'] = str(data['grading']['graded_by'])
        
        return cls(**data)
    
    # ==================== HELPER METHODS ====================
    
    def auto_grade(self, correct_answers: Dict[str, Any]) -> None:
        """
        Auto-grade quiz submission.
        
        Args:
            correct_answers: Dict mapping question_id to correct answer
        """
        total_points = 0.0
        max_points = self.grading.max_score
        
        for answer in self.submission.answers:
            question_id = answer.question_id
            
            # Check if correct
            if question_id in correct_answers:
                is_correct = str(answer.answer).strip().lower() == str(correct_answers[question_id]).strip().lower()
                answer.is_correct = is_correct
                
                # Award points
                if is_correct:
                    # Assume equal points per question
                    points_per_question = max_points / len(self.submission.answers)
                    answer.points_earned = points_per_question
                    total_points += points_per_question
        
        # Update grading
        self.grading.score = total_points
        self.grading.passed = total_points >= (max_points * 0.7)  # 70% passing
        self.grading.status = "graded"
        self.grading.graded_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        """Mark submission as completed"""
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def calculate_percentage(self) -> float:
        """Calculate score percentage"""
        if self.grading.max_score > 0:
            return (self.grading.score / self.grading.max_score) * 100
        return 0.0
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True
