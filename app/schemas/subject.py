# ==============================================================================
# File: app/schemas/subject.py
# Deskripsi: Skema Pydantic untuk Mata Pelajaran (Subjects).
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional
from .base import PyObjectId

class SubjectBase(BaseModel):
    name: str
    code: str

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class SubjectPublic(SubjectBase):
    id: PyObjectId = Field(alias="_id")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
