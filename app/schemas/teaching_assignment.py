# ==============================================================================
# File: app/schemas/teaching_assignment.py
# Deskripsi: Skema Pydantic untuk Penugasan Mengajar.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List
from .base import PyObjectId
from .classes import ClassPublic
from .subject import SubjectPublic
from .user import UserPublic

class TeachingAssignmentBase(BaseModel):
    # academic_period_id: PyObjectId # Akan kita tambahkan nanti
    class_id: PyObjectId
    subject_id: PyObjectId
    teacher_id: PyObjectId

class TeachingAssignmentCreate(TeachingAssignmentBase):
    pass

class TeachingAssignmentUpdate(BaseModel):
    class_id: Optional[PyObjectId] = None
    subject_id: Optional[PyObjectId] = None
    teacher_id: Optional[PyObjectId] = None

class TeachingAssignmentPublic(TeachingAssignmentBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class TeachingAssignmentWithDetails(TeachingAssignmentPublic):
    class_details: Optional[ClassPublic] = None
    subject_details: Optional[SubjectPublic] = None
    teacher_details: Optional[UserPublic] = None