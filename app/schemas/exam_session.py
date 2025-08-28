# ==============================================================================
# File: app/schemas/exam_session.py
# Deskripsi: Skema Pydantic untuk Sesi Pengerjaan Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import PyObjectId

# Peta untuk soal dan opsi yang diacak
class QuestionMapItem(BaseModel):
    position: int
    question_id: PyObjectId
    # Menyimpan urutan ID opsi yang sudah diacak
    shuffled_option_ids: Optional[List[PyObjectId]] = None 

# Log interaksi siswa
class InteractionLogItem(BaseModel):
    timestamp: Optional[datetime] = None
    question_id: Optional[PyObjectId] = None
    displayed_position: Optional[int] = None
    action: str # e.g., "answer_selected", "answer_changed"
    student_answer: Any

class ViolationLogItem(BaseModel):
    violation_id: str
    type: str  # "tab_switch", "paste_detected", "time_anomaly", "right_click", "dev_tools", etc
    timestamp: datetime
    context: Optional[Dict[str, Any]] = {}  # Additional context data
    auto_detected: bool = True
    severity: str = "medium"  # "low", "medium", "high", "critical"
    details: Optional[str] = None

class SubmitAllPayload(BaseModel):
    answers: Dict[str, Any]  # {"question_id": "answer_id" atau null}
    interaction_logs: List[InteractionLogItem]
    violations: List[ViolationLogItem] = []  # Dedicated violations field
    client_metadata: Optional[Dict[str, Any]] = {}

class ExamSessionBase(BaseModel):
    exam_id: PyObjectId
    student_id: PyObjectId
    status: str = "ongoing" # ongoing, submitted, graded
    started_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    score: Optional[float] = None
    # Menyimpan jawaban siswa: { "question_id": "jawaban" }
    answers: Dict[str, Any] = {} 
    # Peta acak yang unik untuk sesi ini
    question_map: List[QuestionMapItem] = []
    # Log untuk analitik
    interaction_logs: List[InteractionLogItem] = []

class ExamSessionPublic(ExamSessionBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class AnswerUpdate(BaseModel):
    question_id: PyObjectId
    student_answer: Any

class OptionForStudent(BaseModel):
    id: PyObjectId
    text: str

class QuestionForStudent(BaseModel):
    id: PyObjectId
    position: int
    question_text: str
    question_type: str
    points: int
    options: Optional[List[OptionForStudent]] = None