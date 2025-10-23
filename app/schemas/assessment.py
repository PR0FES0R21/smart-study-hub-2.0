# ==============================================================================
# File: app/schemas/assessment.py
# Deskripsi: Schemas untuk Assessment API requests/responses
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class StartAssessmentRequest(BaseModel):
    """Request untuk start assessment"""
    assessment_id: str = Field(..., description="Assessment ID from course")
    
    class Config:
        schema_extra = {
            "example": {
                "assessment_id": "assessment_1"
            }
        }


class SubmitAssessmentAnswerRequest(BaseModel):
    """Individual answer dalam submission"""
    question_id: str = Field(..., description="Question ID")
    answer: Any = Field(..., description="Student's answer")
    
    class Config:
        schema_extra = {
            "example": {
                "question_id": "q1",
                "answer": "B"
            }
        }


class SubmitAssessmentRequest(BaseModel):
    """Request untuk submit assessment"""
    session_id: str = Field(..., description="Session ID from start assessment")
    answers: List[SubmitAssessmentAnswerRequest] = Field(
        default_factory=list,
        description="Quiz answers"
    )
    files: List[str] = Field(
        default_factory=list,
        description="File URLs (for assignment)"
    )
    text_answer: Optional[str] = Field(None, description="Text answer (for essay)")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "session_123",
                "answers": [
                    {"question_id": "q1", "answer": "B"},
                    {"question_id": "q2", "answer": "A"}
                ],
                "files": [],
                "text_answer": None
            }
        }


# ==================== RESPONSE SCHEMAS ====================

class QuestionResponse(BaseModel):
    """Response untuk question (tanpa correct answer)"""
    question_id: str
    type: str  # multiple_choice, essay, etc.
    question_text: str
    options: Optional[List[str]] = None  # For multiple choice
    points: float
    
    class Config:
        schema_extra = {
            "example": {
                "question_id": "q1",
                "type": "multiple_choice",
                "question_text": "Berapakah 2 + 2?",
                "options": ["2", "3", "4", "5"],
                "points": 10.0
            }
        }


class AssessmentSessionResponse(BaseModel):
    """Response saat start assessment"""
    session_id: str
    assessment: Dict[str, Any]
    questions: List[QuestionResponse]
    
    # Time constraints
    time_limit: int  # minutes
    started_at: datetime
    must_submit_before: datetime
    
    # Metadata
    total_questions: int
    total_points: float
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "session_123",
                "assessment": {
                    "assessment_id": "assessment_1",
                    "title": "Ujian Akhir Matematika",
                    "type": "quiz"
                },
                "questions": [
                    {
                        "question_id": "q1",
                        "type": "multiple_choice",
                        "question_text": "2 + 2 = ?",
                        "options": ["2", "3", "4", "5"],
                        "points": 10.0
                    }
                ],
                "time_limit": 120,
                "started_at": "2024-01-20T08:00:00Z",
                "must_submit_before": "2024-01-20T10:00:00Z",
                "total_questions": 10,
                "total_points": 100.0
            }
        }


class AnswerReviewResponse(BaseModel):
    """Response untuk review answer"""
    question_id: str
    question_text: str
    your_answer: Any
    correct_answer: Optional[Any] = None  # Only if show_correct_answers = True
    is_correct: bool
    points_earned: float
    explanation: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "question_id": "q1",
                "question_text": "2 + 2 = ?",
                "your_answer": "4",
                "correct_answer": "4",
                "is_correct": True,
                "points_earned": 10.0,
                "explanation": "2 + 2 = 4"
            }
        }


class AssessmentResultsResponse(BaseModel):
    """Response untuk assessment results"""
    submission_id: str
    
    # Results
    score: float
    max_score: float
    percentage: float
    passed: bool
    
    # Breakdown
    correct_answers: int
    wrong_answers: int
    
    # Review (if allowed)
    answers_review: Optional[List[AnswerReviewResponse]] = None
    
    # Retake info
    can_retake: bool = False  # Always False for final assessment
    attempts_used: int = 1
    attempts_allowed: int = 1
    
    # Course completion
    course_completed: bool = False
    
    # Timestamps
    submitted_at: datetime
    graded_at: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "submission_id": "507f1f77bcf86cd799439011",
                "score": 85.0,
                "max_score": 100.0,
                "percentage": 85.0,
                "passed": True,
                "correct_answers": 8,
                "wrong_answers": 2,
                "answers_review": [
                    {
                        "question_id": "q1",
                        "question_text": "2 + 2 = ?",
                        "your_answer": "4",
                        "correct_answer": "4",
                        "is_correct": True,
                        "points_earned": 10.0
                    }
                ],
                "can_retake": False,
                "attempts_used": 1,
                "attempts_allowed": 1,
                "course_completed": True,
                "submitted_at": "2024-01-20T10:30:00Z",
                "graded_at": "2024-01-20T10:30:00Z"
            }
        }


class AssessmentAvailabilityResponse(BaseModel):
    """Response untuk check assessment availability"""
    available: bool
    reason: Optional[str] = None
    
    # Requirements
    all_modules_completed: bool
    already_attempted: bool
    
    # Assessment info
    assessment: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "reason": None,
                "all_modules_completed": True,
                "already_attempted": False,
                "assessment": {
                    "assessment_id": "assessment_1",
                    "title": "Ujian Akhir Matematika",
                    "type": "quiz",
                    "time_limit": 120,
                    "max_score": 100.0,
                    "passing_score": 70.0
                }
            }
        }


# ==================== TEACHER RESPONSE SCHEMAS ====================

class StudentSubmissionSummaryResponse(BaseModel):
    """Response untuk teacher view submission summary"""
    student_id: str
    student_name: str
    
    score: float
    max_score: float
    percentage: float
    passed: bool
    
    submitted_at: datetime
    time_spent: int  # seconds
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "507f1f77bcf86cd799439012",
                "student_name": "Ahmad Fauzi",
                "score": 85.0,
                "max_score": 100.0,
                "percentage": 85.0,
                "passed": True,
                "submitted_at": "2024-01-20T10:30:00Z",
                "time_spent": 7200
            }
        }


class QuestionAnalysisResponse(BaseModel):
    """Response untuk question analysis"""
    question_id: str
    question_text: str
    
    correct_count: int
    wrong_count: int
    success_rate: float  # percentage
    
    class Config:
        schema_extra = {
            "example": {
                "question_id": "q1",
                "question_text": "2 + 2 = ?",
                "correct_count": 28,
                "wrong_count": 2,
                "success_rate": 93.3
            }
        }


class AssessmentResultsSummaryResponse(BaseModel):
    """Response untuk teacher view all results"""
    assessment: Dict[str, Any]
    
    # Statistics
    statistics: Dict[str, Any] = Field(
        description="total_students, submitted, passed, failed, average_score, etc."
    )
    
    # Submissions
    submissions: List[StudentSubmissionSummaryResponse]
    
    # Question analysis
    question_analysis: List[QuestionAnalysisResponse]
    
    class Config:
        schema_extra = {
            "example": {
                "assessment": {
                    "assessment_id": "assessment_1",
                    "title": "Ujian Akhir Matematika",
                    "total_students": 30
                },
                "statistics": {
                    "submitted": 25,
                    "not_submitted": 5,
                    "passed": 20,
                    "failed": 5,
                    "average_score": 78.5,
                    "highest_score": 95.0,
                    "lowest_score": 45.0
                },
                "submissions": [
                    {
                        "student_id": "507f1f77bcf86cd799439012",
                        "student_name": "Ahmad Fauzi",
                        "score": 85.0,
                        "max_score": 100.0,
                        "percentage": 85.0,
                        "passed": True,
                        "submitted_at": "2024-01-20T10:30:00Z",
                        "time_spent": 7200
                    }
                ],
                "question_analysis": [
                    {
                        "question_id": "q1",
                        "question_text": "2 + 2 = ?",
                        "correct_count": 28,
                        "wrong_count": 2,
                        "success_rate": 93.3
                    }
                ]
            }
        }
