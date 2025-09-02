# ==============================================================================
# File: app/schemas/question_set.py
# Deskripsi: Skema Pydantic untuk Paket Soal (Enhanced with Teaching Assignment Access).
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .base import PyObjectId
from .user import TeacherBasic
from .subject import SubjectBase
from .question_bank import QuestionBankPublic

class QuestionSetStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class DifficultyDistribution(BaseModel):
    easy: int = 0
    medium: int = 0
    hard: int = 0

class QuestionSetMetadata(BaseModel):
    total_questions: int = 0
    difficulty_distribution: DifficultyDistribution = DifficultyDistribution()
    total_points: int = 0
    tags: List[str] = []

class AccessPermissions(BaseModel):
    can_view: List[PyObjectId] = []
    can_edit: List[PyObjectId] = []
    can_manage_questions: List[PyObjectId] = []  # Add/remove questions
    can_publish: List[PyObjectId] = []  # Publish/archive rights

class QuestionSetBase(BaseModel):
    name: str
    subject_id: PyObjectId
    grade_level: int
    created_by_coordinator_id: PyObjectId
    question_ids: List[PyObjectId] = []
    status: QuestionSetStatus = QuestionSetStatus.DRAFT
    is_public: bool = False  # NEW: Public/Private flag
    access_permissions: AccessPermissions = AccessPermissions()
    metadata: QuestionSetMetadata = QuestionSetMetadata()
    description: Optional[str] = None
    version: int = 1

class QuestionSetCreate(BaseModel):
    name: str
    subject_id: PyObjectId
    grade_level: int
    description: Optional[str] = None
    is_public: bool = False
    tags: List[str] = []

class QuestionSetUpdate(BaseModel):
    name: Optional[str] = None
    question_ids: Optional[List[PyObjectId]] = None
    status: Optional[QuestionSetStatus] = None
    is_public: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    access_permissions: Optional[AccessPermissions] = None

class QuestionSetAddQuestions(BaseModel):
    question_ids: List[PyObjectId]

class QuestionSetRemoveQuestions(BaseModel):
    question_ids: List[PyObjectId]

class PermissionManagement(BaseModel):
    user_id: PyObjectId
    permissions: List[str]  # ["edit", "manage_questions", "publish"]
    action: str  # "grant" or "revoke"

class QuestionSetPublic(QuestionSetBase):
    id: PyObjectId = Field(alias="_id")
    published_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class PermissionHolders(BaseModel):
    """Users who have various permissions on question set"""
    can_view: List[TeacherBasic] = []
    can_edit: List[TeacherBasic] = []
    can_manage_questions: List[TeacherBasic] = []
    can_publish: List[TeacherBasic] = []

class CurrentUserPermissions(BaseModel):
    """Enhanced current user permissions dengan grup info"""
    can_view: bool = False
    can_edit: bool = False
    can_manage_questions: bool = False
    can_publish: bool = False
    can_delete: bool = False  # NEW
    is_creator: bool = False
    
    # Usage validation
    is_used_in_exams: bool = False  # NEW
    total_exams_using: int = 0      # NEW
    
    # Group information
    coordinator_id: Optional[str] = None     # NEW
    coordinator_name: Optional[str] = None   # NEW
    is_same_coordinator: bool = False        # NEW
    group_access_reason: Optional[str] = None # NEW: "creator", "same_coordinator", "explicit_permission", "public"

class QuestionSetDetailedPublic(BaseModel):
    """Detailed question set with all permission info"""
    id: PyObjectId = Field(alias="_id")
    name: str
    description: Optional[str]
    grade_level: int
    status: str
    is_public: bool
    metadata: QuestionSetMetadata
    version: int
    published_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    question_ids: List[PyObjectId] = []
    
    # Lookup results
    subject: Optional[SubjectBase]
    created_by: Optional[TeacherBasic]
    
    # Permission details
    permission_holders: PermissionHolders
    current_user_permissions: CurrentUserPermissions
    
    class Config:
        from_attributes = True
        validate_by_name = True

class QuestionSetSummaryEnhanced(BaseModel):
    """Enhanced summary with creator info and permissions"""
    id: PyObjectId = Field(alias="_id")
    name: str
    description: Optional[str]
    grade_level: int
    status: str
    is_public: bool
    metadata: QuestionSetMetadata
    created_at: datetime
    updated_at: datetime
    
    # Lookup results
    subject: Optional[SubjectBase]
    created_by: Optional[TeacherBasic]
    
    # Enhanced permissions
    can_edit: bool = False
    can_manage_questions: bool = False
    can_delete: bool = False  # NEW
    can_duplicate: bool = False  # NEW
    is_creator: bool = False
    
    # Usage info
    is_used_in_exams: bool = False  # NEW
    total_exams_using: int = 0      # NEW
    
    # Group info
    group_info: Optional[Dict[str, Any]] = None  # NEW
    access_reason: str = "unknown"               # NEW
    
    # Permission holders - NEW: Siapa saja yang punya akses
    permission_holders: PermissionHolders = PermissionHolders()
    
    class Config:
        from_attributes = True
        validate_by_name = True

# New schemas for enhanced functionality
class BulkGroupPermissionManagement(BaseModel):
    """Bulk permission management untuk seluruh grup koordinator"""
    question_set_ids: List[PyObjectId]
    coordinator_id: PyObjectId  # Target coordinator group
    permissions: List[str]      # ["edit", "manage_questions", "publish"]
    action: str                 # "grant" or "revoke"
    apply_to_all_teachers: bool = True  # Apply to all teachers under coordinator

class QuestionSetDeleteRequest(BaseModel):
    """Request schema untuk delete question set"""
    force: bool = False  # Force delete even if used in exams
    reason: Optional[str] = None  # Reason for deletion

class GroupInfo(BaseModel):
    """Group information untuk question set access"""
    coordinator_id: str
    coordinator_name: str
    subject_id: str
    subject_name: str
    grade_level: int
    total_teachers: int = 0
    is_user_in_group: bool = False

class UsageInfo(BaseModel):
    """Usage information untuk question set"""
    total_exams: int = 0
    active_exams: int = 0
    completed_exams: int = 0
    scheduled_exams: int = 0
    can_delete: bool = True

class QuestionSetSummary(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    description: Optional[str]
    grade_level: int
    status: str
    is_public: bool
    metadata: QuestionSetMetadata = QuestionSetMetadata()
    created_at: datetime
    updated_at: datetime
    
    # Lookup results
    subject: Optional[SubjectBase]
    created_by: Optional[TeacherBasic]
    
    # Computed permissions
    can_edit: bool = False
    can_manage_questions: bool = False
    
    class Config:
        from_attributes = True

class QuestionSetQuestions(BaseModel):
    """Schema for returning question IDs within a question set"""
    question_set_id: PyObjectId
    question_set_name: str
    total_questions: int
    question_ids: List[PyObjectId]
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True