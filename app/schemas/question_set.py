# ==============================================================================
# File: app/schemas/question_set.py
# Deskripsi: Skema Pydantic untuk Paket Soal (Enhanced with Teaching Assignment Access).
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .base import PyObjectId

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

class QuestionSetSummary(BaseModel):
    """Simplified version for listing"""
    id: PyObjectId = Field(alias="_id")
    name: str
    subject_id: PyObjectId
    grade_level: int
    status: QuestionSetStatus
    is_public: bool
    total_questions: int
    created_by_coordinator_id: PyObjectId
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True