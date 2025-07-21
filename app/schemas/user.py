# ==============================================================================
# File: app/schemas/user.py
# Deskripsi: Skema Pydantic untuk User.
# --- DIUBAH ---
# ==============================================================================
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, TYPE_CHECKING, Any
from .base import PyObjectId
from .expertise_program import ExpertiseProgramPublic
from .profile import ProfilePublic, ProfileCreate, ProfileUpdate, SelfProfileUpdate
from datetime import datetime
from .pagination import PaginatedResponse

if TYPE_CHECKING:
    from .classes import ClassPublic

class TeachingSummaryItem(BaseModel):
    subject_name: str
    class_name: str

class UserBase(BaseModel):
    login_id: str
    email: EmailStr
    is_active: bool = True
    roles: List[str] = []
    profile_id: Optional[PyObjectId] = None
    class_id: Optional[PyObjectId] = None
    department_id: Optional[PyObjectId] = None 
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    onboarding_completed: bool = False
    password_last_changed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class UserCreate(BaseModel):
    login_id: str
    email: EmailStr
    roles: List[str] = []
    is_active: bool = True
    profile: ProfileCreate

class UserUpdate(BaseModel):
    login_id: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None
    profile: Optional[ProfileUpdate] = None

class UserInDB(UserBase):
    hashed_password: str

class UserPublic(UserBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

class UserWithDetails(UserPublic):
    # Detail untuk siswa
    profile_details: Optional[ProfilePublic]
    class_details: Optional['ClassPublic'] = None
    department_details: Optional[ExpertiseProgramPublic] = None
    teaching_summary: Optional[List[TeachingSummaryItem]] = None

class PaginatedUserResponse(PaginatedResponse[UserWithDetails]):
    pass

class DataTablesUserResponse(BaseModel):
    draw: int
    recordsTotal: int
    recordsFiltered: int
    data: List[UserWithDetails] = []

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('passwords do not match')
        return v
    
class SelfDataUpdate(BaseModel):
    email: Optional[EmailStr] = None
    profile: Optional[SelfProfileUpdate] = None