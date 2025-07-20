# ==============================================================================
# File: app/schemas/classes.py
# Deskripsi: Skema Pydantic untuk Kelas.
# --- DIPERBAIKI ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING
from .base import PyObjectId
from .expertise_program import ExpertiseProgramPublic

# Import hanya untuk type checking, tidak di runtime
if TYPE_CHECKING:
    from .user import UserPublic

class TeacherInfo(BaseModel):
    id: PyObjectId = Field(alias="_id")
    full_name: str
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None

class ClassBase(BaseModel):
    grade_level: int
    expertise_id: PyObjectId
    name: str # e.g., "1", "2", "A", "B"
    academic_year: str
    homeroom_teacher_id: Optional[PyObjectId] = None

class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    grade_level: Optional[int] = None
    expertise_id: Optional[PyObjectId] = None
    name: Optional[str] = None
    academic_year: Optional[str] = None
    homeroom_teacher_id: Optional[PyObjectId] = None

class ClassPublic(ClassBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# Skema untuk menampilkan data kelas yang sudah digabung
class ClassWithDetails(ClassPublic):
    homeroom_teacher_details: Optional[TeacherInfo] = None
    expertise_details: Optional[ExpertiseProgramPublic] = None

class TeacherInfo(BaseModel):
    id: PyObjectId = Field(alias="_id")
    full_name: str

class PaginatedClassResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    data: List[ClassWithDetails]
    # Statistik tambahan
    grade_10_total: int
    grade_11_total: int
    grade_12_total: int
