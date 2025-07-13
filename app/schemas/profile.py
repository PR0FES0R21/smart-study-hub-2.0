# ==============================================================================
# File: app/schemas/profile.py
# --- DIUBAH --- (Menambahkan start_year dan end_year)
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .base import PyObjectId

class ProfileBase(BaseModel):
    user_id: Optional[PyObjectId] = None
    full_name: str
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    birth_place: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    class_id: Optional[PyObjectId] = None
    department_id: Optional[PyObjectId] = None
    start_year: Optional[int] = None #
    end_year: Optional[int] = None   #
    profile_picture_url: Optional[str] = None
    profile_picture_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProfileCreate(BaseModel):
    full_name: str
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    birth_place: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    class_id: Optional[PyObjectId] = None
    department_id: Optional[PyObjectId] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    birth_place: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    class_id: Optional[PyObjectId] = None
    department_id: Optional[PyObjectId] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class ProfilePublic(ProfileBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class SelfProfileUpdate(BaseModel):
    phone_number: Optional[str] = None
    address: Optional[str] = None
