# ==============================================================================
# File: app/schemas/student_stats.py
# Deskripsi: Schema Pydantic untuk statistik ujian siswa
# ==============================================================================

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from .base import PyObjectId

class StudentStatsResponse(BaseModel):
    student_id: PyObjectId = Field(..., description="ID siswa")
    total_exams: int = Field(..., ge=0)
    average_score: float = Field(..., ge=0, le=100)
    highest_score: float = Field(..., ge=0, le=100)
    lowest_score: float = Field(..., ge=0, le=100)

    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filter metadata applied")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

