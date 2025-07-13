# ==============================================================================
# File: app/schemas/academic_period.py
# Deskripsi: Skema Pydantic untuk Periode Akademik.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .base import PyObjectId

class AcademicPeriodBase(BaseModel):
    year: str # Contoh: "2025/2026"
    semester: str # Contoh: "ganjil" atau "genap"
    status: str # Contoh: "active", "planning", "archived"
    start_date: datetime
    end_date: datetime

class AcademicPeriodCreate(AcademicPeriodBase):
    pass

class AcademicPeriodUpdate(BaseModel):
    year: Optional[str] = None
    semester: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class AcademicPeriodPublic(AcademicPeriodBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True