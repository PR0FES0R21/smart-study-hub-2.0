# ==============================================================================
# File: app/models/course_change_history.py
# Deskripsi: Database models untuk Course Change History & Audit Trail
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class ChangeContext(BaseModel):
    """Context information untuk change event"""
    pr_id: Optional[PyObjectId] = Field(None, description="Pull request yang triggered change")
    old_version: Optional[str] = Field(None, description="Previous version")
    new_version: Optional[str] = Field(None, description="New version")
    
    # Affected elements
    affected_modules: List[PyObjectId] = Field(default_factory=list)
    affected_lessons: List[PyObjectId] = Field(default_factory=list)
    affected_components: List[str] = Field(default_factory=list)
    
    # Change metrics
    lines_added: int = Field(default=0, description="Lines added dalam content")
    lines_removed: int = Field(default=0, description="Lines removed dalam content")
    
    # Impact data
    student_count_affected: int = Field(default=0)
    class_count_affected: int = Field(default=0)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NotificationRecord(BaseModel):
    """Record of notifications sent for this change"""
    recipient_id: PyObjectId = Field(..., description="Notification recipient")
    recipient_type: str = Field(..., description="teacher | student | coordinator | admin")
    recipient_name: Optional[str] = Field(None, description="Recipient name")
    
    # Notification content
    notification_type: str = Field(..., description="course_updated | pr_submitted | pr_approved | version_archived")
    message: str = Field(..., max_length=500)
    
    # Delivery info
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_method: str = Field(default="system", description="system | email | push | sms")
    delivery_status: str = Field(default="sent", description="sent | delivered | failed | read")
    
    # Read/interaction tracking
    read_at: Optional[datetime] = Field(None)
    clicked_at: Optional[datetime] = Field(None)
    
    @validator('recipient_type')
    def validate_recipient_type(cls, v):
        allowed_types = ['teacher', 'student', 'coordinator', 'admin', 'system']
        if v not in allowed_types:
            raise ValueError(f'Recipient type must be one of {allowed_types}')
        return v

class ChangeDetail(BaseModel):
    """Detailed information about specific change"""
    change_id: PyObjectId = Field(default_factory=lambda: PyObjectId(ObjectId()))
    action: str = Field(..., description="Specific action taken")
    target_type: str = Field(..., description="What was changed")
    target_id: Optional[PyObjectId] = Field(None, description="ID of changed element")
    target_name: Optional[str] = Field(None, description="Name of changed element")
    
    # Change data
    before_snapshot: Optional[Dict[str, Any]] = Field(None, description="Data before change")
    after_snapshot: Optional[Dict[str, Any]] = Field(None, description="Data after change")
    
    # Change description
    summary: str = Field(..., max_length=200, description="Brief change summary")
    details: Optional[str] = Field(None, max_length=1000, description="Detailed change description")
    
    # Technical details
    field_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Specific field changes")
    dependencies_affected: List[str] = Field(default_factory=list)

class CourseChangeHistory(BaseModel):
    """Main change history record"""
    id: Optional[str] = Field(None, alias="_id")
    course_family_id: PyObjectId = Field(..., description="Course family this change belongs to")
    version_id: Optional[PyObjectId] = Field(None, description="Specific version affected")
    
    # Change identification
    change_type: str = Field(..., description="Type of change event")
    title: str = Field(..., min_length=1, max_length=200, description="Change title")
    description: str = Field(..., max_length=2000, description="Detailed change description")
    
    # Who and when
    actor_id: PyObjectId = Field(..., description="User who initiated change")
    actor_type: str = Field(..., description="coordinator | teacher | admin | system")
    actor_name: Optional[str] = Field(None, description="Actor name for display")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Change context
    context: ChangeContext = Field(default_factory=ChangeContext)
    
    # Detailed changes
    changes_applied: List[ChangeDetail] = Field(default_factory=list)
    
    # Review and approval info
    approved_by: Optional[PyObjectId] = Field(None, description="Who approved this change")
    approval_timestamp: Optional[datetime] = Field(None)
    approval_comment: Optional[str] = Field(None, max_length=500)
    
    # Impact tracking
    impact_level: str = Field(default="low", description="low | medium | high")
    rollback_possible: bool = Field(default=True, description="Can this change be rolled back")
    rollback_instructions: Optional[str] = Field(None, max_length=1000)
    
    # Notifications sent
    notifications_sent: List[NotificationRecord] = Field(default_factory=list)
    
    # Status
    status: str = Field(default="completed", description="completed | failed | partially_applied | rolled_back")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Tags and categorization
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = Field(None, description="content | structure | permissions | settings")
    
    # Performance tracking
    processing_time_ms: Optional[int] = Field(None, description="Time taken to process change")
    
    def add_change_detail(self, action: str, target_type: str, summary: str, **kwargs):
        """Add detailed change record"""
        detail = ChangeDetail(
            action=action,
            target_type=target_type,
            summary=summary,
            **kwargs
        )
        self.changes_applied.append(detail)
    
    def add_notification(self, recipient_id: PyObjectId, recipient_type: str, 
                        notification_type: str, message: str, **kwargs):
        """Add notification record"""
        notification = NotificationRecord(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            notification_type=notification_type,
            message=message,
            **kwargs
        )
        self.notifications_sent.append(notification)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for this change"""
        return {
            "total_changes": len(self.changes_applied),
            "notifications_sent": len(self.notifications_sent),
            "students_affected": self.context.student_count_affected,
            "classes_affected": self.context.class_count_affected,
            "impact_level": self.impact_level,
            "processing_time": self.processing_time_ms
        }
    
    @validator('change_type')
    def validate_change_type(cls, v):
        allowed_types = [
            'version_update', 'fork_created', 'pr_submitted', 'pr_approved', 
            'pr_rejected', 'pr_merged', 'course_archived', 'course_restored',
            'permission_changed', 'sync_completed', 'rollback_executed'
        ]
        if v not in allowed_types:
            raise ValueError(f'Change type must be one of {allowed_types}')
        return v
    
    @validator('actor_type')
    def validate_actor_type(cls, v):
        allowed_types = ['coordinator', 'teacher', 'admin', 'system']
        if v not in allowed_types:
            raise ValueError(f'Actor type must be one of {allowed_types}')
        return v
    
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
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class ChangeStatistics(BaseModel):
    """Aggregated change statistics untuk course family"""
    id: Optional[str] = Field(None, alias="_id")
    course_family_id: PyObjectId = Field(..., description="Course family")
    
    # Time period
    period_start: datetime = Field(..., description="Statistics period start")
    period_end: datetime = Field(..., description="Statistics period end")
    
    # Change metrics
    total_changes: int = Field(default=0)
    changes_by_type: Dict[str, int] = Field(default_factory=dict)
    changes_by_actor_type: Dict[str, int] = Field(default_factory=dict)
    
    # PR statistics
    total_prs: int = Field(default=0)
    approved_prs: int = Field(default=0)
    rejected_prs: int = Field(default=0)
    avg_review_time_hours: float = Field(default=0.0)
    
    # Impact metrics
    students_affected: int = Field(default=0)
    classes_affected: int = Field(default=0)
    teachers_involved: int = Field(default=0)
    
    # Quality metrics
    rollback_count: int = Field(default=0)
    error_rate: float = Field(default=0.0, description="Percentage of failed changes")
    avg_processing_time_ms: float = Field(default=0.0)
    
    # Activity patterns
    most_active_day: Optional[str] = Field(None)
    most_active_hour: Optional[int] = Field(None)
    peak_activity_periods: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Top contributors
    top_contributors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Calculated timestamp
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class SystemEvent(BaseModel):
    """System-level events (automated processes, etc.)"""
    id: Optional[str] = Field(None, alias="_id")
    event_type: str = Field(..., description="Type of system event")
    event_name: str = Field(..., description="Human readable event name")
    
    # Event data
    description: str = Field(..., max_length=1000)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Scope
    course_family_id: Optional[PyObjectId] = Field(None)
    affected_versions: List[PyObjectId] = Field(default_factory=list)
    
    # Execution info
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    status: str = Field(default="running", description="running | completed | failed | cancelled")
    
    # Results
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = Field(None)
    
    # Performance
    execution_time_ms: Optional[int] = Field(None)
    resources_used: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = [
            'stats_calculation', 'cleanup_old_versions', 'sync_forks',
            'notification_batch', 'backup_creation', 'data_migration',
            'index_rebuild', 'cache_refresh'
        ]
        if v not in allowed_types:
            raise ValueError(f'Event type must be one of {allowed_types}')
        return v
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
