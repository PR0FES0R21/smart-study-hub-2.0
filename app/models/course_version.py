# ==============================================================================
# File: app/models/course_version.py
# Deskripsi: Database models untuk Course Versioning System (New Architecture)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class MediaReference(BaseModel):
    """Reference ke media file di Cloudflare R2"""
    media_key: str = Field(..., description="Key untuk reference dalam markdown")
    url: str = Field(..., description="Full URL di Cloudflare R2")
    type: str = Field(..., description="image | video | audio | document")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    alt_text: Optional[str] = Field(None, description="Alt text untuk accessibility")
    duration: Optional[int] = Field(None, description="Duration untuk video/audio (seconds)")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    
    @validator('type')
    def validate_media_type(cls, v):
        allowed_types = ['image', 'video', 'audio', 'document']
        if v not in allowed_types:
            raise ValueError(f'Media type must be one of {allowed_types}')
        return v

class EmbeddedComponent(BaseModel):
    """Component yang di-embed dalam lesson content"""
    component_id: str = Field(..., description="Unique component ID")
    type: str = Field(..., description="quiz | assignment | interactive")
    position: int = Field(..., description="Position dalam markdown content")
    data: Dict[str, Any] = Field(..., description="Component configuration data")
    
    # Component-specific settings
    required: bool = Field(default=True, description="Required untuk completion")
    estimated_duration: int = Field(default=10, description="Estimated duration (minutes)")
    
    @validator('type')
    def validate_component_type(cls, v):
        allowed_types = ['quiz', 'assignment', 'interactive', 'survey', 'reflection']
        if v not in allowed_types:
            raise ValueError(f'Component type must be one of {allowed_types}')
        return v

class LessonContent(BaseModel):
    """Individual lesson dalam module"""
    lesson_id: PyObjectId = Field(default_factory=lambda: PyObjectId(ObjectId()))
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    order: int = Field(..., ge=0, description="Order dalam module")
    
    # Rich content dengan markdown
    content_markdown: str = Field(..., description="Main lesson content dalam markdown")
    
    # Media dan embedded components
    media_references: List[MediaReference] = Field(default_factory=list)
    embedded_components: List[EmbeddedComponent] = Field(default_factory=list)
    
    # Learning metadata
    estimated_duration: int = Field(default=30, description="Estimated duration (minutes)")
    difficulty_level: str = Field(default="medium", description="easy | medium | hard")
    learning_objectives: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[PyObjectId] = Field(None, description="Teacher who created this lesson")

class CourseModule(BaseModel):
    """Module dalam course (collection of lessons)"""
    module_id: PyObjectId = Field(default_factory=lambda: PyObjectId(ObjectId()))
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    order: int = Field(..., ge=0, description="Order dalam course")
    
    # Module content
    lessons: List[LessonContent] = Field(default_factory=list)
    
    # Module metadata
    estimated_duration: int = Field(default=0, description="Total estimated duration (minutes)")
    difficulty_level: str = Field(default="medium", description="easy | medium | hard")
    
    # Completion requirements
    completion_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "all_lessons",  # all_lessons | percentage | time_based | custom
            "required_percentage": 100,
            "required_lessons": [],
            "minimum_time": 0
        }
    )
    
    # Module-level assignments
    module_assignments: List[EmbeddedComponent] = Field(default_factory=list)

class CourseChangeRecord(BaseModel):
    """Record individual change applied to course"""
    action: str = Field(..., description="add_module | remove_module | modify_module | add_lesson | remove_lesson | modify_lesson | reorder")
    target_type: str = Field(..., description="module | lesson | content")
    target_id: Optional[PyObjectId] = Field(None, description="ID of modified element")
    
    # Change data
    old_data: Optional[Dict[str, Any]] = Field(None, description="Data before change")
    new_data: Optional[Dict[str, Any]] = Field(None, description="Data after change")
    
    # Change metadata
    description: str = Field(..., description="Human-readable description of change")
    rationale: Optional[str] = Field(None, description="Why this change was made")
    
    # Position/ordering changes
    old_position: Optional[int] = None
    new_position: Optional[int] = None

class UsageStatistics(BaseModel):
    """Usage statistics untuk course version"""
    enrolled_students: int = Field(default=0)
    active_students: int = Field(default=0)  # Students dengan progress dalam 30 hari
    completed_students: int = Field(default=0)
    
    # Engagement metrics
    average_completion_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    total_time_spent: int = Field(default=0, description="Total time spent by all students (minutes)")
    
    # Content metrics
    most_viewed_lessons: List[Dict[str, Any]] = Field(default_factory=list)
    completion_drop_points: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Update tracking
    last_calculated: datetime = Field(default_factory=datetime.utcnow)

class CourseVersion(BaseModel):
    """Main course version model - supports master courses and teacher forks"""
    id: Optional[str] = Field(None, alias="_id")
    course_family_id: PyObjectId = Field(..., description="Groups all versions of same course")
    
    # Version identification
    version: str = Field(..., description="Semantic version like 1.2.0")
    version_number: float = Field(..., description="Numeric version for easy sorting")
    
    # Course metadata
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    subject_id: PyObjectId = Field(..., description="Reference to subjects collection")
    grade_level: int = Field(..., ge=1, le=12, description="Grade level 1-12")
    coordinator_id: PyObjectId = Field(..., description="Coordinator responsible for this course")
    academic_period_id: Optional[PyObjectId] = Field(None, description="Academic period")
    
    # Version control
    is_master: bool = Field(default=True, description="True for master course, False for forks")
    is_active: bool = Field(default=True, description="Currently active version")
    parent_version_id: Optional[PyObjectId] = Field(None, description="Parent version (for versioning chain)")
    created_from_pr_id: Optional[PyObjectId] = Field(None, description="PR that created this version")
    
    # Fork information (for teacher forks)
    teacher_id: Optional[PyObjectId] = Field(None, description="Teacher who owns this fork")
    class_ids: List[PyObjectId] = Field(default_factory=list, description="Classes using this fork")
    fork_type: str = Field(default="master", description="master | teacher_fork")
    
    # Course structure
    modules: List[CourseModule] = Field(default_factory=list)
    
    # Changes tracking
    changes_from_parent: List[CourseChangeRecord] = Field(default_factory=list)
    
    # Status and lifecycle
    status: str = Field(default="active", description="active | archived | draft | pending_approval")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = Field(None)
    created_by: PyObjectId = Field(..., description="User who created this version")
    
    # Usage statistics
    usage_stats: UsageStatistics = Field(default_factory=UsageStatistics)
    
    # Settings
    settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "allow_teacher_customization": True,
            "require_approval_for_changes": True,
            "auto_sync_forks": False,
            "notification_settings": {
                "notify_on_updates": True,
                "notify_teachers": True,
                "notify_students": False
            }
        }
    )
    
    def get_total_estimated_duration(self) -> int:
        """Calculate total estimated duration untuk seluruh course"""
        return sum(module.estimated_duration for module in self.modules)
    
    def get_total_lessons_count(self) -> int:
        """Calculate total number of lessons dalam course"""
        return sum(len(module.lessons) for module in self.modules)
    
    def get_module_by_id(self, module_id: str) -> Optional[CourseModule]:
        """Get module by ID"""
        for module in self.modules:
            if str(module.module_id) == module_id:
                return module
        return None
    
    def get_lesson_by_id(self, lesson_id: str) -> Optional[LessonContent]:
        """Get lesson by ID from any module"""
        for module in self.modules:
            for lesson in module.lessons:
                if str(lesson.lesson_id) == lesson_id:
                    return lesson
        return None
    
    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB document to Pydantic model"""
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        data = self.dict(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = ObjectId(self.id)
        return data
    
    @validator('fork_type')
    def validate_fork_type(cls, v, values):
        allowed_types = ['master', 'teacher_fork']
        if v not in allowed_types:
            raise ValueError(f'Fork type must be one of {allowed_types}')
        
        # Validation logic
        is_master = values.get('is_master', True)
        if is_master and v != 'master':
            raise ValueError('Master courses must have fork_type "master"')
        if not is_master and v == 'master':
            raise ValueError('Non-master courses cannot have fork_type "master"')
        
        return v
    
    @validator('teacher_id')
    def validate_teacher_id(cls, v, values):
        fork_type = values.get('fork_type', 'master')
        if fork_type == 'teacher_fork' and not v:
            raise ValueError('Teacher forks must have teacher_id')
        if fork_type == 'master' and v:
            raise ValueError('Master courses should not have teacher_id')
        return v
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class CourseFamilyMetadata(BaseModel):
    """Metadata untuk course family (groups all versions)"""
    id: Optional[str] = Field(None, alias="_id")
    course_family_id: PyObjectId = Field(default_factory=lambda: PyObjectId(ObjectId()))
    
    # Basic info
    base_title: str = Field(..., description="Base title tanpa version info")
    subject_id: PyObjectId = Field(..., description="Subject")
    grade_level: int = Field(..., ge=1, le=12)
    coordinator_id: PyObjectId = Field(..., description="Current coordinator")
    
    # Current status
    current_master_version_id: PyObjectId = Field(..., description="Current active master version")
    current_version: str = Field(..., description="Current version number")
    
    # Statistics
    total_versions: int = Field(default=1)
    total_forks: int = Field(default=0)
    total_pull_requests: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    def to_mongo(self) -> dict:
        data = self.dict(by_alias=True, exclude={'id'})
        if self.id:
            data['_id'] = ObjectId(self.id)
        return data
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
