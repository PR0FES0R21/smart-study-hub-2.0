# ==============================================================================
# File: app/schemas/exam.py
# Deskripsi: Skema Pydantic untuk Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .base import PyObjectId

class ExamSettings(BaseModel):
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_results_after_submission: bool = False

class ExamBase(BaseModel):
    title: str
    exam_type: str = Field(..., pattern="^(official_uts|official_uas|quiz|daily_test)$")
    duration_minutes: int
    availability_start_time: datetime
    availability_end_time: datetime
    status: str = "pending_questions" # Default status
    settings: ExamSettings = Field(default_factory=ExamSettings)

class ExamCreate(ExamBase):
    teaching_assignment_id: PyObjectId
    question_ids: List[PyObjectId] = []
    proctor_ids: List[PyObjectId] = []

class ExamPublic(ExamBase):
    id: PyObjectId = Field(alias="_id")
    teaching_assignment_id: PyObjectId
    proctor_ids: List[PyObjectId] = []
    class Config: from_attributes = True; arbitrary_types_allowed = True

# Skema untuk Admin membuat ujian secara massal
class TargetCriteria(BaseModel):
    subject_id: PyObjectId
    grade_level: Optional[int] = None
    expertise_id: Optional[PyObjectId] = None
    class_id: Optional[PyObjectId] = None # Untuk target satu kelas spesifik

class BulkExamCreate(BaseModel):
    title: str
    exam_type: str = Field(..., pattern="^(official_uts|official_uas)$")
    duration_minutes: int
    availability_start_time: datetime
    availability_end_time: datetime
    settings: ExamSettings = Field(default_factory=ExamSettings)
    target_criteria: TargetCriteria
    proctor_ids: List[PyObjectId] = []

class ExamQuestionUpdate(BaseModel):
    question_ids: List[PyObjectId]