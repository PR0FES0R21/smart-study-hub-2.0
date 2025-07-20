# ==============================================================================
# File: app/schemas/coordination_assignment.py
# Deskripsi: Skema Pydantic untuk Penunjukan Koordinator.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional
from .base import PyObjectId

class CoordinationAssignmentBase(BaseModel):
    subject_id: PyObjectId
    grade_level: int
    coordinator_id: PyObjectId

class CoordinationAssignmentCreate(CoordinationAssignmentBase):
    pass

class CoordinationAssignmentPublic(CoordinationAssignmentBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True