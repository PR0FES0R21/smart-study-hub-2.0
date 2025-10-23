# ==============================================================================
# File: app/schemas/course_class_settings.py
# Deskripsi: Schemas untuk CourseClassSettings API requests/responses
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class AssignCourseToClassRequest(BaseModel):
    """Request untuk assign course ke class"""
    course_id: str = Field(..., description="ID of the course to assign")
    class_id: str = Field(..., description="ID of the class")
    start_date: Optional[datetime] = Field(None, description="Custom start date")
    end_date: Optional[datetime] = Field(None, description="Custom end date")
    settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom settings"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "course_id": "507f1f77bcf86cd799439011",
                "class_id": "507f1f77bcf86cd799439012",
                "start_date": "2024-01-10T00:00:00Z",
                "end_date": "2024-06-30T00:00:00Z",
                "settings": {
                    "allow_skip": False
                }
            }
        }


class UpdateCourseClassSettingsRequest(BaseModel):
    """Request untuk update class settings"""
    start_date: Optional[datetime] = Field(None)
    end_date: Optional[datetime] = Field(None)
    settings: Optional[Dict[str, Any]] = Field(None)
    
    class Config:
        schema_extra = {
            "example": {
                "start_date": "2024-01-15T00:00:00Z",
                "end_date": "2024-07-01T00:00:00Z",
                "settings": {
                    "allow_skip": True
                }
            }
        }


class AddStudentOverrideRequest(BaseModel):
    """Request untuk add/update student override"""
    student_id: str = Field(..., description="Student user ID")
    unlocked_modules: Optional[List[str]] = Field(
        default_factory=list,
        description="Module IDs to unlock"
    )
    unlocked_lessons: Optional[List[str]] = Field(
        default_factory=list,
        description="Lesson IDs to unlock"
    )
    reason: Optional[str] = Field(None, description="Reason for override")
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "507f1f77bcf86cd799439013",
                "unlocked_modules": ["507f1f77bcf86cd799439014"],
                "unlocked_lessons": ["507f1f77bcf86cd799439015"],
                "reason": "Student request for exam preparation"
            }
        }


class RemoveStudentOverrideRequest(BaseModel):
    """Request untuk remove student override"""
    student_id: str = Field(..., description="Student user ID")
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "507f1f77bcf86cd799439013"
            }
        }


# ==================== RESPONSE SCHEMAS ====================

class StudentOverrideResponse(BaseModel):
    """Response untuk student override info"""
    student_id: str
    student_name: Optional[str] = None
    unlocked_modules: List[str]
    unlocked_lessons: List[str]
    reason: Optional[str]
    overridden_by: str
    overridden_by_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "507f1f77bcf86cd799439013",
                "student_name": "Ahmad Fauzi",
                "unlocked_modules": ["507f1f77bcf86cd799439014"],
                "unlocked_lessons": ["507f1f77bcf86cd799439015"],
                "reason": "Student request",
                "overridden_by": "507f1f77bcf86cd799439016",
                "overridden_by_name": "Pak Budi",
                "created_at": "2024-01-20T10:30:00Z"
            }
        }


class ClassOverridesResponse(BaseModel):
    """Response untuk class overrides"""
    unlocked_modules: List[str]
    student_overrides: List[StudentOverrideResponse]
    
    class Config:
        schema_extra = {
            "example": {
                "unlocked_modules": [],
                "student_overrides": [
                    {
                        "student_id": "507f1f77bcf86cd799439013",
                        "student_name": "Ahmad Fauzi",
                        "unlocked_modules": ["507f1f77bcf86cd799439014"],
                        "unlocked_lessons": [],
                        "reason": "Student request",
                        "overridden_by": "507f1f77bcf86cd799439016",
                        "overridden_by_name": "Pak Budi",
                        "created_at": "2024-01-20T10:30:00Z"
                    }
                ]
            }
        }


class CourseClassMetadataResponse(BaseModel):
    """Response untuk class metadata"""
    total_students: int
    started_students: int
    completed_students: int
    average_progress: float
    average_score: float
    last_calculated: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "total_students": 30,
                "started_students": 25,
                "completed_students": 5,
                "average_progress": 45.5,
                "average_score": 78.3,
                "last_calculated": "2024-01-20T15:00:00Z"
            }
        }


class CourseClassSettingsResponse(BaseModel):
    """Response untuk course class settings (full info)"""
    id: str
    course_id: str
    course_title: Optional[str] = None
    class_id: str
    class_name: Optional[str] = None
    teacher_id: str
    teacher_name: Optional[str] = None
    
    metadata: CourseClassMetadataResponse
    class_overrides: ClassOverridesResponse
    settings: Dict[str, Any]
    
    assigned_at: datetime
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: str
    
    created_at: datetime
    updated_at: datetime
    
    # Permissions
    can_edit: bool = False
    can_delete: bool = False
    can_override: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439017",
                "course_id": "507f1f77bcf86cd799439011",
                "course_title": "Matematika Kelas 10",
                "class_id": "507f1f77bcf86cd799439012",
                "class_name": "Kelas 10A",
                "teacher_id": "507f1f77bcf86cd799439016",
                "teacher_name": "Pak Budi",
                "metadata": {
                    "total_students": 30,
                    "started_students": 25,
                    "completed_students": 5,
                    "average_progress": 45.5,
                    "average_score": 78.3,
                    "last_calculated": "2024-01-20T15:00:00Z"
                },
                "class_overrides": {
                    "unlocked_modules": [],
                    "student_overrides": []
                },
                "settings": {},
                "assigned_at": "2024-01-10T08:00:00Z",
                "start_date": "2024-01-10T00:00:00Z",
                "end_date": "2024-06-30T00:00:00Z",
                "status": "active",
                "created_at": "2024-01-10T08:00:00Z",
                "updated_at": "2024-01-20T15:00:00Z",
                "can_edit": True,
                "can_delete": True,
                "can_override": True
            }
        }


class CourseClassSettingsSummaryResponse(BaseModel):
    """Response untuk course class settings (summary/list)"""
    id: str
    course_id: str
    course_title: Optional[str] = None
    class_id: str
    class_name: Optional[str] = None
    teacher_name: Optional[str] = None
    
    total_students: int
    started_students: int
    completed_students: int
    average_progress: float
    
    assigned_at: datetime
    status: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439017",
                "course_id": "507f1f77bcf86cd799439011",
                "course_title": "Matematika Kelas 10",
                "class_id": "507f1f77bcf86cd799439012",
                "class_name": "Kelas 10A",
                "teacher_name": "Pak Budi",
                "total_students": 30,
                "started_students": 25,
                "completed_students": 5,
                "average_progress": 45.5,
                "assigned_at": "2024-01-10T08:00:00Z",
                "status": "active"
            }
        }


class CourseClassAnalyticsResponse(BaseModel):
    """Response untuk class analytics"""
    class_info: CourseClassSettingsSummaryResponse
    
    # Progress distribution
    progress_distribution: Dict[str, int] = Field(
        description="Distribution: not_started, in_progress, completed"
    )
    
    # Module completion
    module_completion: List[Dict[str, Any]] = Field(
        description="Completion rate per module"
    )
    
    # Top performers
    top_students: List[Dict[str, Any]] = Field(
        description="Top 5 students by progress/score"
    )
    
    # Students needing help
    struggling_students: List[Dict[str, Any]] = Field(
        description="Students with low progress"
    )
    
    # Time analytics
    average_time_per_module: float
    total_time_spent: int
    
    class Config:
        schema_extra = {
            "example": {
                "class_info": {
                    "id": "507f1f77bcf86cd799439017",
                    "course_title": "Matematika Kelas 10",
                    "class_name": "Kelas 10A",
                    "total_students": 30,
                    "average_progress": 45.5
                },
                "progress_distribution": {
                    "not_started": 5,
                    "in_progress": 20,
                    "completed": 5
                },
                "module_completion": [
                    {
                        "module_id": "507f1f77bcf86cd799439014",
                        "module_title": "Aljabar",
                        "completion_rate": 80.0,
                        "average_score": 82.5
                    }
                ],
                "top_students": [
                    {
                        "student_id": "507f1f77bcf86cd799439018",
                        "student_name": "Ahmad Fauzi",
                        "progress": 95.0,
                        "score": 92.0
                    }
                ],
                "struggling_students": [
                    {
                        "student_id": "507f1f77bcf86cd799439019",
                        "student_name": "Budi Santoso",
                        "progress": 15.0,
                        "last_activity": "2024-01-15T10:00:00Z"
                    }
                ],
                "average_time_per_module": 120.5,
                "total_time_spent": 36150
            }
        }
