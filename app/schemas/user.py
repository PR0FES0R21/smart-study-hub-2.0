# ==============================================================================
# File: app/schemas/user.py
# Deskripsi: Skema Pydantic untuk User.
# --- DIUBAH ---
# ==============================================================================
from pydantic import BaseModel, EmailStr, Field, model_validator, validator
from typing import List, Optional, TYPE_CHECKING, Any
from .base import PyObjectId
from .expertise_program import ExpertiseProgramPublic
from .profile import ProfilePublic, ProfileCreate, ProfileUpdate, SelfProfileUpdate
from datetime import datetime
from .pagination import PaginatedResponse

if TYPE_CHECKING:
    from .classes import ClassWithDetails

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

    @model_validator(mode='before')
    @classmethod
    def clean_role_specific_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            roles = data.get('roles', [])
            profile = data.get('profile', {})
            
            if 'student' in roles:
                # Siswa tidak boleh punya department_id
                if 'department_id' in profile:
                    profile['department_id'] = None
            
            if 'teacher' in roles or 'admin' in roles:
                # Guru/Admin tidak boleh punya class_id di profil
                if 'class_id' in profile:
                    profile['class_id'] = None
        return data

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
    # Detail untuk siswa dan guru
    profile_details: Optional[ProfilePublic]
    class_details: Optional['ClassWithDetails'] = None  # Untuk siswa: berisi expertise_details
    department_details: Optional[ExpertiseProgramPublic] = None  # Untuk guru: berisi data departemen
    teaching_summary: Optional[List[TeachingSummaryItem]] = None

class UserWithProfile(UserPublic):
    profile_details: Optional[ProfilePublic]

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

class TeacherBasic(BaseModel):
    """Schema untuk daftar guru sederhana (hanya ID dan nama)"""
    id: PyObjectId = Field(alias="_id")
    full_name: str
    profile_picture_url: Optional[str] = None
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True