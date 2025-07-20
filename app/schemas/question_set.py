# ==============================================================================
# File: app/schemas/question_set.py
# Deskripsi: Skema Pydantic untuk Paket Soal.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional
from .base import PyObjectId

class QuestionSetBase(BaseModel):
    name: str
    subject_id: PyObjectId
    grade_level: int
    created_by_coordinator_id: PyObjectId
    question_ids: List[PyObjectId] = []

class QuestionSetCreate(QuestionSetBase):
    pass

class QuestionSetUpdate(BaseModel):
    name: Optional[str] = None
    question_ids: Optional[List[PyObjectId]] = None

class QuestionSetPublic(QuestionSetBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True