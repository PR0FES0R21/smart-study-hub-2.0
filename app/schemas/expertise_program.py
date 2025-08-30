# ==============================================================================
# File: app/schemas/expertise_program.py
# Deskripsi: Skema Pydantic untuk Jurusan.
# --- DIUBAH --- (Sekarang menjadi file terpisah)
# ==============================================================================
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from typing import Optional
from .base import PyObjectId
from .pagination import PaginatedResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import UserWithProfile

class ExpertiseProgramBase(BaseModel):
    name: str
    abbreviation: str
    description: Optional[str] = None
    head_of_department_id: Optional[PyObjectId] = None

class ExpertiseProgramCreate(ExpertiseProgramBase):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpertiseProgramUpdate(BaseModel):
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    description: Optional[str] = None
    head_of_department_id: Optional[PyObjectId] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpertiseProgramPublic(ExpertiseProgramBase):
    head_of_department_details: Optional["UserWithProfile"] = None
    id: PyObjectId = Field(alias="_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config: from_attributes = True; arbitrary_types_allowed = True

class PaginatedExpertiseProgramResponse(PaginatedResponse[ExpertiseProgramPublic]):
    pass
