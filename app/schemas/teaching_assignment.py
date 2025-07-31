# ==============================================================================
# File: app/schemas/teaching_assignment.py
# Deskripsi: Skema Pydantic untuk Penugasan Mengajar (Updated with academic_period_id).
# --- DIPERBARUI ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from .base import PyObjectId
from .classes import ClassWithDetails
from .subject import SubjectBase, SubjectPublic
from .user import UserPublic
from .pagination import PaginatedResponse
from .expertise_program import ExpertiseProgramPublic
from .classes import ClassPublic

class TeachingAssignmentBase(BaseModel):
    academic_period_id: PyObjectId
    class_id: PyObjectId
    subject_id: PyObjectId
    teacher_id: PyObjectId

class TeachingAssignmentCreate(BaseModel):
    # academic_period_id akan diisi otomatis dari current academic period
    class_id: PyObjectId
    subject_id: PyObjectId
    teacher_id: PyObjectId

class TeachingAssignmentUpdate(BaseModel):
    class_id: Optional[PyObjectId] = None
    subject_id: Optional[PyObjectId] = None
    teacher_id: Optional[PyObjectId] = None
    # academic_period_id tidak bisa diubah setelah dibuat

class TeachingAssignmentPublic(TeachingAssignmentBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class TeachingAssignmentWithDetails(TeachingAssignmentPublic):
    class_details: Optional[ClassWithDetails] = None
    subject_details: Optional[SubjectPublic] = None
    teacher_details: Optional[UserPublic] = None

class BulkUpdateAction(BaseModel):
    type: Literal["create", "update", "delete"]
    assignment_id: Optional[PyObjectId] = None # Diperlukan untuk update & delete
    data: Optional[Dict[str, Any]] = None # Diperlukan untuk create & update

class BulkUpdateRequest(BaseModel):
    actions: List[BulkUpdateAction]

class PaginatedTeachingAssignmentResponse(PaginatedResponse[TeachingAssignmentWithDetails]):
    pass

class assignments(SubjectBase):
    teaching_assignment_id: PyObjectId
    subject_id: PyObjectId
    class Config: from_attributes = True; arbitrary_types_allowed = True
    
class TeachingClassSummary(BaseModel):
    total_students: int
    assignments: List[assignments]
    class_details: ClassPublic
    expertise_details: ExpertiseProgramPublic

class TeacherTeachingSummary(BaseModel):
    classes: List[TeachingClassSummary]