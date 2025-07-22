# ==============================================================================
# File: app/schemas/expertise_program.py
# Deskripsi: Skema Pydantic untuk Jurusan.
# --- DIUBAH --- (Sekarang menjadi file terpisah)
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional
from .base import PyObjectId
from .pagination import PaginatedResponse


class ExpertiseProgramBase(BaseModel):
    name: str
    abbreviation: str
    description: Optional[str] = None
    head_of_department_id: Optional[PyObjectId] = None

class ExpertiseProgramCreate(ExpertiseProgramBase):
    pass

class ExpertiseProgramUpdate(BaseModel):
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    description: Optional[str] = None
    head_of_department_id: Optional[PyObjectId] = None

class ExpertiseProgramPublic(ExpertiseProgramBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class PaginatedExpertiseProgramResponse(PaginatedResponse[ExpertiseProgramPublic]):
    pass
