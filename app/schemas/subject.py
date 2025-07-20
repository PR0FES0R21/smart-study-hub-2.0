# ==============================================================================
# File: app/schemas/subject.py
# Deskripsi: Skema Pydantic untuk Mata Pelajaran (Subjects).
# ==============================================================================

from pydantic import BaseModel, Field
from typing import Optional, List
from .base import PyObjectId
from datetime import datetime

# Skema dasar: untuk validasi umum
class SubjectBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

# Skema saat create: input dari user
class SubjectCreate(SubjectBase):
    pass

# Skema saat update: input dari user, tapi opsional semua
class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

# Skema saat response: termasuk field internal
class SubjectPublic(SubjectBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

# Skema paginasi
class PaginatedSubjectResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    data: List[SubjectPublic]
