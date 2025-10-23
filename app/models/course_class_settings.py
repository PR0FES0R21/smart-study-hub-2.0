# ==============================================================================
# File: app/models/course_class_settings.py
# Deskripsi: Model untuk course assignment ke class dengan per-class settings
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId


class StudentOverride(BaseModel):
    """Override unlock untuk student tertentu"""
    student_id: PyObjectId = Field(..., description="Student user ID")
    unlocked_modules: List[str] = Field(
        default_factory=list,
        description="Module IDs yang di-override unlock"
    )
    unlocked_lessons: List[str] = Field(
        default_factory=list,
        description="Lesson IDs yang di-override unlock"
    )
    reason: Optional[str] = Field(None, description="Alasan override")
    overridden_by: PyObjectId = Field(..., description="Teacher yang override")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class ClassOverrides(BaseModel):
    """Override settings untuk seluruh class"""
    unlocked_modules: List[str] = Field(
        default_factory=list,
        description="Module IDs yang di-unlock untuk semua siswa di class ini"
    )
    student_overrides: List[StudentOverride] = Field(
        default_factory=list,
        description="Per-student overrides"
    )
    
    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class CourseClassMetadata(BaseModel):
    """Auto-calculated metadata untuk class ini"""
    total_students: int = Field(default=0, description="Total siswa di class")
    started_students: int = Field(default=0, description="Siswa yang sudah mulai")
    completed_students: int = Field(default=0, description="Siswa yang sudah selesai")
    average_progress: float = Field(default=0.0, description="Rata-rata progress (%)")
    average_score: float = Field(default=0.0, description="Rata-rata score")
    last_calculated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Terakhir dihitung"
    )
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CourseClassSettings(BaseModel):
    """
    Course assignment ke class dengan per-class settings dan overrides.
    
    Model ini menjembatani course (master/template) dengan class (kumpulan siswa).
    Setiap assignment adalah independent, sehingga course yang sama bisa dipakai
    di multiple classes dengan settings berbeda.
    """
    id: Optional[str] = Field(None, alias="_id")
    
    # References
    course_id: PyObjectId = Field(..., description="Reference ke courses collection")
    class_id: PyObjectId = Field(..., description="Reference ke classes collection")
    teacher_id: PyObjectId = Field(..., description="Teacher yang assign course ini")
    
    # Metadata (auto-calculated)
    metadata: CourseClassMetadata = Field(
        default_factory=CourseClassMetadata,
        description="Statistik untuk class ini"
    )
    
    # Override unlocks (teacher bisa unlock module/lesson tertentu)
    class_overrides: ClassOverrides = Field(
        default_factory=ClassOverrides,
        description="Override settings untuk class ini"
    )
    
    # Settings (optional overrides dari course default)
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom settings untuk class ini"
    )
    
    # Dates
    assigned_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Kapan course di-assign"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Custom start date untuk class ini"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Custom end date untuk class ini"
    )
    
    # Status
    status: str = Field(
        default="active",
        description="active | archived"
    )
    archived_at: Optional[datetime] = Field(None, description="Kapan di-archive")
    archived_by: Optional[PyObjectId] = Field(None, description="Siapa yang archive")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'archived']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        data = self.dict(by_alias=True, exclude_none=True)
        
        # Remove id if None
        if data.get('_id') is None:
            data.pop('_id', None)
        
        # Convert PyObjectId to ObjectId
        for field in ['course_id', 'class_id', 'teacher_id', 'archived_by']:
            if field in data and data[field] is not None:
                if not isinstance(data[field], ObjectId):
                    data[field] = ObjectId(data[field])
        
        # Convert student_overrides ObjectIds
        if 'class_overrides' in data and 'student_overrides' in data['class_overrides']:
            for override in data['class_overrides']['student_overrides']:
                if 'student_id' in override:
                    override['student_id'] = ObjectId(override['student_id'])
                if 'overridden_by' in override:
                    override['overridden_by'] = ObjectId(override['overridden_by'])
        
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "CourseClassSettings":
        """Create from MongoDB document"""
        if not data:
            return None
        
        # Convert ObjectId to string
        if '_id' in data:
            data['_id'] = str(data['_id'])
        
        for field in ['course_id', 'class_id', 'teacher_id', 'archived_by']:
            if field in data and data[field] is not None:
                data[field] = str(data[field])
        
        # Convert student_overrides ObjectIds
        if 'class_overrides' in data and 'student_overrides' in data['class_overrides']:
            for override in data['class_overrides']['student_overrides']:
                if 'student_id' in override:
                    override['student_id'] = str(override['student_id'])
                if 'overridden_by' in override:
                    override['overridden_by'] = str(override['overridden_by'])
        
        return cls(**data)
    
    # ==================== HELPER METHODS ====================
    
    def add_student_override(
        self,
        student_id: str,
        teacher_id: str,
        unlocked_modules: List[str] = None,
        unlocked_lessons: List[str] = None,
        reason: str = None
    ) -> None:
        """Add atau update student override"""
        # Check if override already exists
        existing_override = None
        for override in self.class_overrides.student_overrides:
            if str(override.student_id) == str(student_id):
                existing_override = override
                break
        
        if existing_override:
            # Update existing
            if unlocked_modules:
                existing_override.unlocked_modules.extend(unlocked_modules)
                # Remove duplicates
                existing_override.unlocked_modules = list(set(existing_override.unlocked_modules))
            if unlocked_lessons:
                existing_override.unlocked_lessons.extend(unlocked_lessons)
                existing_override.unlocked_lessons = list(set(existing_override.unlocked_lessons))
            if reason:
                existing_override.reason = reason
        else:
            # Create new override
            new_override = StudentOverride(
                student_id=PyObjectId(student_id),
                unlocked_modules=unlocked_modules or [],
                unlocked_lessons=unlocked_lessons or [],
                reason=reason,
                overridden_by=PyObjectId(teacher_id)
            )
            self.class_overrides.student_overrides.append(new_override)
        
        self.updated_at = datetime.utcnow()
    
    def remove_student_override(self, student_id: str) -> bool:
        """Remove student override"""
        original_count = len(self.class_overrides.student_overrides)
        self.class_overrides.student_overrides = [
            override for override in self.class_overrides.student_overrides
            if str(override.student_id) != str(student_id)
        ]
        
        if len(self.class_overrides.student_overrides) < original_count:
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def get_student_override(self, student_id: str) -> Optional[StudentOverride]:
        """Get student override"""
        for override in self.class_overrides.student_overrides:
            if str(override.student_id) == str(student_id):
                return override
        return None
    
    def archive(self, archived_by: str) -> None:
        """Archive assignment (soft delete)"""
        self.status = "archived"
        self.archived_at = datetime.utcnow()
        self.archived_by = PyObjectId(archived_by)
        self.updated_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore archived assignment"""
        self.status = "active"
        self.archived_at = None
        self.archived_by = None
        self.updated_at = datetime.utcnow()
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True
