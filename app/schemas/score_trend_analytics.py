# ==============================================================================
# File: app/schemas/score_trend_analytics.py
# Deskripsi: Schema Pydantic untuk analytics trend nilai ujian
# ==============================================================================

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, date
from .base import PyObjectId

class ScoreDataPoint(BaseModel):
    """Representasi satu data point dalam trend chart"""
    date: datetime
    score: float
    exam_id: PyObjectId
    exam_title: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    
class ScoreTrendSeries(BaseModel):
    """Series data untuk chart dengan label"""
    label: str
    data: List[ScoreDataPoint]
    metadata: Optional[Dict[str, Any]] = None
    
class ScoreTrendAnalytics(BaseModel):
    """Response model untuk analytics trend nilai"""
    series: List[ScoreTrendSeries]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "series": [
                    {
                        "label": "Kelas 12-A",
                        "data": [
                            {
                                "date": "2025-08-01T00:00:00Z",
                                "score": 85.5,
                                "exam_id": "60d21b4667d0d8992e610c85",
                                "exam_title": "Ulangan Tengah Semester",
                                "subject_name": "Matematika",
                                "subject_code": "MTK"
                            }
                        ],
                        "metadata": {
                            "class_id": "60d21b4667d0d8992e610c86",
                            "total_students": 30
                        }
                    }
                ],
                "metadata": {
                    "date_range": {
                        "start": "2025-07-01T00:00:00Z",
                        "end": "2025-09-30T00:00:00Z"
                    },
                    "aggregation": "class"
                }
            }
        }

class ScoreTrendRequest(BaseModel):
    """Request model untuk analytics trend nilai"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    class_id: Optional[PyObjectId] = None
    grade_level: Optional[int] = None
    subject_id: Optional[PyObjectId] = None
    expertise_id: Optional[PyObjectId] = None
    teacher_id: Optional[PyObjectId] = None
    student_id: Optional[PyObjectId] = None
    academic_period_id: Optional[PyObjectId] = None
    group_by: str = "class"  # Opsi: "class", "subject", "grade", "teacher", "student"
    
    @validator('group_by')
    def validate_group_by(cls, v):
        allowed_values = ["class", "subject", "grade", "teacher", "student"]
        if v not in allowed_values:
            raise ValueError(f"group_by must be one of {allowed_values}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "start_date": "2025-07-01T00:00:00Z",
                "end_date": "2025-09-30T00:00:00Z",
                "class_id": "60d21b4667d0d8992e610c86",
                "grade_level": 12,
                "subject_id": "60d21b4667d0d8992e610c87",
                "expertise_id": "60d21b4667d0d8992e610c88",
                "teacher_id": "60d21b4667d0d8992e610c89",
                "academic_period_id": "60d21b4667d0d8992e610c90",
                "group_by": "class"
            }
        }
