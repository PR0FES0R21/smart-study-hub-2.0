# ==============================================================================
# File: app/schemas/question_submission.py
# Deskripsi: Skema Pydantic untuk Pengajuan Soal.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .base import PyObjectId
from .question_bank import QuestionBankPublic

class QuestionSubmissionBase(BaseModel):
    question_id: PyObjectId
    submitted_by_teacher_id: PyObjectId
    coordination_assignment_id: PyObjectId
    academic_period_id: PyObjectId
    purpose: str # Contoh: "UTS Ganjil 2025"
    status: str = "submitted" # submitted, approved, rejected
    reviewer_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuestionSubmissionCreate(BaseModel):
    question_ids: List[PyObjectId]
    coordination_assignment_id: PyObjectId
    purpose: str

class SubmissionStatusUpdate(BaseModel):
    status: str # "approved" atau "rejected"
    reviewer_comment: Optional[str] = None

class QuestionSubmissionPublic(QuestionSubmissionBase):
    id: PyObjectId = Field(alias="_id")
    question_details: QuestionBankPublic
    class Config: from_attributes = True; arbitrary_types_allowed = True