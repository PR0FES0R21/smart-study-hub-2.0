# ==============================================================================
# File: app/schemas/student_progress.py
# Deskripsi: Schemas untuk StudentProgress API requests/responses
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class MarkContentCompletedRequest(BaseModel):
    """Request untuk mark content as completed"""
    content_type: str = Field(..., description="module | lesson | page")
    module_id: Optional[str] = Field(None)
    lesson_id: Optional[str] = Field(None)
    page_number: Optional[int] = Field(None)
    score: Optional[float] = Field(None, description="Score if applicable")
    max_score: Optional[float] = Field(None)
    time_spent: Optional[int] = Field(None, description="Time spent in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "content_type": "lesson",
                "lesson_id": "507f1f77bcf86cd799439011",
                "score": 85.0,
                "max_score": 100.0,
                "time_spent": 1800
            }
        }


class UpdateProgressRequest(BaseModel):
    """Request untuk update progress (time spent, activity)"""
    time_spent: Optional[int] = Field(None, description="Additional time spent")
    
    class Config:
        schema_extra = {
            "example": {
                "time_spent": 300
            }
        }


# ==================== RESPONSE SCHEMAS ====================

class SubmissionDataResponse(BaseModel):
    """Response untuk submission data"""
    files: List[str]
    text_answer: Optional[str]
    answers: List[Dict[str, Any]]
    submitted_at: datetime
    graded_at: Optional[datetime]
    graded_by: Optional[str]
    graded_by_name: Optional[str]
    feedback: Optional[str]
    
    class Config:
        schema_extra = {
            "example": {
                "files": ["https://storage.../file1.pdf"],
                "text_answer": None,
                "answers": [
                    {"question_id": "q1", "answer": "B", "is_correct": True}
                ],
                "submitted_at": "2024-01-20T10:30:00Z",
                "graded_at": "2024-01-21T09:00:00Z",
                "graded_by": "507f1f77bcf86cd799439012",
                "graded_by_name": "Pak Budi",
                "feedback": "Good work!"
            }
        }


class StudentProgressResponse(BaseModel):
    """Response untuk individual progress item"""
    id: str
    student_id: str
    course_class_setting_id: str
    
    # Content
    module_id: Optional[str]
    lesson_id: Optional[str]
    page_number: Optional[int]
    content_type: str
    
    # Status
    status: str
    completed_at: Optional[datetime]
    time_spent: int
    
    # Score
    score: Optional[float]
    max_score: Optional[float]
    percentage: Optional[float]
    
    # Submission
    submission: Optional[SubmissionDataResponse]
    
    # Metadata
    attempts: int
    started_at: Optional[datetime]
    last_activity: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "student_id": "507f1f77bcf86cd799439014",
                "course_class_setting_id": "507f1f77bcf86cd799439015",
                "module_id": "507f1f77bcf86cd799439016",
                "lesson_id": "507f1f77bcf86cd799439017",
                "page_number": None,
                "content_type": "lesson",
                "status": "completed",
                "completed_at": "2024-01-20T10:30:00Z",
                "time_spent": 1800,
                "score": 85.0,
                "max_score": 100.0,
                "percentage": 85.0,
                "submission": None,
                "attempts": 1,
                "started_at": "2024-01-20T08:30:00Z",
                "last_activity": "2024-01-20T10:30:00Z"
            }
        }


class CourseProgressSummaryResponse(BaseModel):
    """Response untuk course progress summary"""
    student_id: str
    course_class_setting_id: str
    course_id: str
    course_title: Optional[str]
    
    # Module summary
    total_modules: int
    completed_modules: int
    in_progress_modules: int
    
    # Lesson summary
    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    
    # Overall
    completion_percentage: float
    average_score: float
    total_time_spent: int
    
    # Status
    status: str
    
    # Dates
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_activity: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "507f1f77bcf86cd799439014",
                "course_class_setting_id": "507f1f77bcf86cd799439015",
                "course_id": "507f1f77bcf86cd799439016",
                "course_title": "Matematika Kelas 10",
                "total_modules": 3,
                "completed_modules": 1,
                "in_progress_modules": 1,
                "total_lessons": 10,
                "completed_lessons": 4,
                "in_progress_lessons": 2,
                "completion_percentage": 40.0,
                "average_score": 82.5,
                "total_time_spent": 7200,
                "status": "in_progress",
                "started_at": "2024-01-10T08:00:00Z",
                "completed_at": None,
                "last_activity": "2024-01-20T15:30:00Z"
            }
        }


class ModuleProgressSummaryResponse(BaseModel):
    """Response untuk module progress summary"""
    student_id: str
    module_id: str
    module_title: Optional[str]
    
    # Lesson summary
    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    
    # Overall
    completion_percentage: float
    average_score: float
    total_time_spent: int
    
    # Status
    status: str
    
    # Lock status (calculated on-the-fly)
    locked: bool
    accessible: bool
    
    # Dates
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_activity: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "507f1f77bcf86cd799439014",
                "module_id": "507f1f77bcf86cd799439016",
                "module_title": "Aljabar",
                "total_lessons": 4,
                "completed_lessons": 4,
                "in_progress_lessons": 0,
                "completion_percentage": 100.0,
                "average_score": 85.0,
                "total_time_spent": 3600,
                "status": "completed",
                "locked": False,
                "accessible": True,
                "started_at": "2024-01-10T08:00:00Z",
                "completed_at": "2024-01-15T16:30:00Z",
                "last_activity": "2024-01-15T16:30:00Z"
            }
        }


class LessonProgressDetailResponse(BaseModel):
    """Response untuk lesson progress detail (with pages)"""
    lesson_id: str
    lesson_title: Optional[str]
    
    # Overall lesson progress
    status: str
    completion_percentage: float
    
    # Page progress
    total_pages: int
    completed_pages: int
    current_page: int
    
    # Lock status
    locked: bool
    accessible: bool
    
    # Score
    score: Optional[float]
    max_score: Optional[float]
    
    # Time
    time_spent: int
    
    # Dates
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "lesson_id": "507f1f77bcf86cd799439017",
                "lesson_title": "Persamaan Linear",
                "status": "in_progress",
                "completion_percentage": 60.0,
                "total_pages": 5,
                "completed_pages": 3,
                "current_page": 4,
                "locked": False,
                "accessible": True,
                "score": None,
                "max_score": None,
                "time_spent": 1200,
                "started_at": "2024-01-20T08:00:00Z",
                "completed_at": None
            }
        }


class NextButtonResponse(BaseModel):
    """Response untuk next button action"""
    success: bool
    message: str
    
    # Current content marked as completed
    completed_content: Dict[str, Any]
    
    # Next content to navigate to
    next_content: Optional[Dict[str, Any]]
    
    # Has next?
    has_next: bool
    
    # Course completion status
    course_completed: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Lesson completed! Moving to next lesson.",
                "completed_content": {
                    "content_type": "lesson",
                    "lesson_id": "507f1f77bcf86cd799439017",
                    "title": "Persamaan Linear"
                },
                "next_content": {
                    "content_type": "lesson",
                    "lesson_id": "507f1f77bcf86cd799439018",
                    "title": "Pertidaksamaan",
                    "url": "/courses/xxx/lessons/xxx"
                },
                "has_next": True,
                "course_completed": False
            }
        }
