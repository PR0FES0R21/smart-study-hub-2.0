# ==============================================================================
# File: app/schemas/exam.py
# Deskripsi: Skema Pydantic untuk Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from .base import PyObjectId

from .teaching_assignment import TeachingAssignmentWithDetails
from .academic_period import AcademicPeriodPublic

if TYPE_CHECKING:
    from .question_bank import QuestionBankPublic

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
    academic_period_id: PyObjectId


class ExamCreate(ExamBase):
    teaching_assignment_id: PyObjectId
    question_ids: List[PyObjectId] = []
    proctor_ids: List[PyObjectId] = []

class ExamUpdate(BaseModel):
    title: Optional[str] = None
    exam_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    availability_start_time: Optional[datetime] = None
    availability_end_time: Optional[datetime] = None
    status: Optional[str] = None
    proctor_ids: Optional[List[PyObjectId]] = None
    settings: Optional[ExamSettings] = None

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

class ExamCompleteRequest(BaseModel):
    """Request untuk menyelesaikan ujian secara manual"""
    confirmation: bool = Field(..., description="Konfirmasi untuk menyelesaikan ujian")
    reason: Optional[str] = Field(None, description="Alasan menyelesaikan ujian secara manual")

class ExamWithDetails(ExamPublic):
    teaching_assignment_details: Optional[TeachingAssignmentWithDetails] = None
    academic_period_details: Optional[AcademicPeriodPublic] = None
    question_ids: List[PyObjectId]
    # Field tambahan untuk student endpoint
    has_session: Optional[bool] = None  # Apakah siswa sudah pernah mengerjakan
    session_score: Optional[float] = None  # Skor dari exam session jika ada
    exam_session_id: Optional[PyObjectId] = None  # ID dari exam session jika ada (hanya untuk student)
    # Field tambahan untuk teacher analytics
    analytics_status: Optional[str] = None  # Status analytics: not_generated, pending, processing, completed, failed
    analytics_generated_at: Optional[datetime] = None  # Kapan analytics di-generate (jika sudah completed)
    analytics_task_id: Optional[str] = None  # Task ID jika sedang processing/pending
    analytics_progress: Optional[float] = None  # Progress percentage jika sedang processing

class PaginatedExamResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    data: List[ExamWithDetails]