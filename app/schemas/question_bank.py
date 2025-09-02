# ==============================================================================
# File: app/schemas/question_bank.py
# Deskripsi: Skema Pydantic untuk Bank Soal.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List
from .base import PyObjectId
from .pagination import PaginatedResponse

class QuestionOption(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId)
    text: str
    is_correct: bool

class QuestionBankBase(BaseModel):
    subject_id: PyObjectId
    created_by_teacher_id: PyObjectId
    question_type: str = Field(..., pattern="^(multiple_choice|essay)$")
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    question_text: str
    options: Optional[List[QuestionOption]] = None
    points: int = 10
    tags: Optional[List[str]] = []
    status: str = "private"

class QuestionBankCreate(QuestionBankBase):
    pass

class QuestionBankUpdate(BaseModel):
    subject_id: Optional[PyObjectId] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[QuestionOption]] = None
    points: Optional[int] = None
    tags: Optional[List[str]] = None

class QuestionBankPublic(QuestionBankBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class QuestionIdsList(BaseModel):
    ids: List[PyObjectId]

class PaginatedQuestionBankResponse(PaginatedResponse[QuestionBankPublic]):
    pass