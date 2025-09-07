# ==============================================================================
# File: app/schemas/subject_mastery_analytics.py
# Deskripsi: Optimized schema untuk Subject Mastery Analytics (Radar Chart)
# Performance-focused dengan minimal data transfer
# ==============================================================================

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from .base import PyObjectId

class SubjectMasteryData(BaseModel):
    """Lean data structure untuk radar chart - minimal transfer"""
    subject_scores: Dict[str, float] = Field(
        ..., 
        description="Subject name to mastery score (0-100 scale)"
    )
    overall_average: float = Field(
        ..., 
        ge=0, 
        le=100, 
        description="Overall GPA/average across all subjects"
    )
    total_exams: int = Field(
        ..., 
        ge=0, 
        description="Total number of exams included in calculation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "subject_scores": {
                    "Matematika": 78.5,
                    "Bahasa Indonesia": 85.2,
                    "Pemrograman Dasar": 92.1,
                    "Jaringan Dasar": 74.8,
                    "Sistem Operasi": 81.3
                },
                "overall_average": 82.4,
                "total_exams": 15
            }
        }

class SubjectMasteryAnalytics(BaseModel):
    """Main response model untuk Subject Mastery Analytics"""
    entity_id: str = Field(..., description="ID of student/class/school being analyzed")
    entity_type: str = Field(..., description="Type: student, class, grade, school")
    entity_name: str = Field(..., description="Display name (Student Name, Class Name, etc)")
    
    mastery_data: SubjectMasteryData
    
    # Compact metadata
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "generated_at": datetime.utcnow(),
            "cache_duration": "15min"
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "entity_id": "688477a78a56906f19d02551",
                "entity_type": "student",
                "entity_name": "Ahmad Rizki",
                "mastery_data": {
                    "subject_scores": {
                        "Matematika": 78.5,
                        "Bahasa Indonesia": 85.2,
                        "Pemrograman Dasar": 92.1,
                        "Jaringan Dasar": 74.8,
                        "Sistem Operasi": 81.3
                    },
                    "overall_average": 82.4,
                    "total_exams": 15
                },
                "metadata": {
                    "generated_at": "2025-09-07T14:25:00Z",
                    "cache_duration": "15min",
                    "user_role": ["student"]
                }
            }
        }

class MultiEntityMasteryAnalytics(BaseModel):
    """Response untuk multiple entities (teacher/admin comparing multiple students/classes)"""
    entities: List[SubjectMasteryAnalytics]
    comparison_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata untuk comparison (class averages, rankings, etc)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "entities": [
                    {
                        "entity_id": "class_12_tkj_1",
                        "entity_type": "class",
                        "entity_name": "Kelas 12 TKJ 1",
                        "mastery_data": {
                            "subject_scores": {
                                "Matematika": 78.5,
                                "Pemrograman Dasar": 85.2
                            },
                            "overall_average": 81.9,
                            "total_exams": 8
                        }
                    }
                ],
                "comparison_metadata": {
                    "total_entities": 7,
                    "school_average": 79.3,
                    "best_subject": "Pemrograman Dasar",
                    "weakest_subject": "Matematika"
                }
            }
        }

class SubjectMasteryRequest(BaseModel):
    """Request model dengan performance optimization options"""
    # Entity selection (role-based filtering applied automatically)
    student_id: Optional[PyObjectId] = None
    class_id: Optional[PyObjectId] = None  
    grade_level: Optional[int] = None
    expertise_id: Optional[PyObjectId] = None
    
    # Time filtering for performance
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    academic_period_id: Optional[PyObjectId] = None
    
    # Performance options
    include_zero_scores: bool = Field(
        default=False, 
        description="Include subjects with 0 exams (for complete radar)"
    )
    min_exams_per_subject: int = Field(
        default=1,
        ge=1,
        description="Minimum exams per subject to include in analysis"
    )
    use_cache: bool = Field(
        default=True,
        description="Use cached results if available (15min TTL)"
    )
    
    @validator('min_exams_per_subject')
    def validate_min_exams(cls, v):
        if v < 1:
            raise ValueError('min_exams_per_subject must be at least 1')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "student_id": "688477a78a56906f19d02551",
                "start_date": "2025-08-01T00:00:00Z",
                "end_date": "2025-12-31T23:59:59Z",
                "include_zero_scores": False,
                "min_exams_per_subject": 2,
                "use_cache": True
            }
        }

# Specialized responses untuk different use cases
class StudentMasteryResponse(SubjectMasteryAnalytics):
    """Optimized response for individual students"""
    pass

class ClassMasteryResponse(MultiEntityMasteryAnalytics):
    """Optimized response for class-level analysis"""
    pass

class SchoolMasteryResponse(MultiEntityMasteryAnalytics):
    """Optimized response for school-wide analysis"""
    pass
