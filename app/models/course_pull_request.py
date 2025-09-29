# ==============================================================================
# File: app/models/course_pull_request.py
# Deskripsi: Database models untuk Pull Request System
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class ChangeProposal(BaseModel):
    """Individual change proposal dalam PR"""
    change_id: PyObjectId = Field(default_factory=lambda: PyObjectId(ObjectId()))
    action: str = Field(..., description="add_module | remove_module | modify_module | add_lesson | remove_lesson | modify_lesson | reorder")
    target_type: str = Field(..., description="module | lesson | content | component")
    target_id: Optional[PyObjectId] = Field(None, description="ID of target element")
    
    # Change data
    old_data: Optional[Dict[str, Any]] = Field(None, description="Current data")
    new_data: Optional[Dict[str, Any]] = Field(None, description="Proposed data")
    
    # For additions
    insertion_data: Optional[Dict[str, Any]] = Field(None, description="New data untuk additions")
    insertion_position: Optional[int] = Field(None, description="Position untuk insertions")
    
    # Change description
    title: str = Field(..., min_length=1, max_length=200, description="Short change title")
    description: str = Field(..., max_length=1000, description="Detailed change description")
    rationale: str = Field(..., max_length=1000, description="Why this change is needed")
    
    # Impact assessment
    expected_impact: str = Field(default="low", description="low | medium | high")
    affected_students: int = Field(default=0, description="Number of students affected")
    implementation_effort: str = Field(default="low", description="low | medium | high")
    
    # Review status
    status: str = Field(default="pending", description="pending | approved | rejected | needs_revision")
    reviewer_comment: Optional[str] = Field(None, max_length=500)
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = [
            'add_module', 'remove_module', 'modify_module',
            'add_lesson', 'remove_lesson', 'modify_lesson', 
            'reorder', 'add_component', 'remove_component', 'modify_component'
        ]
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of {allowed_actions}')
        return v

class ApprovalWorkflowStep(BaseModel):
    """Step dalam approval workflow"""
    step_number: int = Field(..., ge=1)
    action: str = Field(..., description="submitted | reviewed | approved | rejected | merged")
    actor_id: PyObjectId = Field(..., description="User who performed this action")
    actor_name: Optional[str] = Field(None, description="User name for display")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    comment: Optional[str] = Field(None, max_length=1000)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['submitted', 'reviewed', 'approved', 'rejected', 'merged', 'revision_requested']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of {allowed_actions}')
        return v

class ImpactAssessment(BaseModel):
    """Assessment of PR impact"""
    affected_classes: List[PyObjectId] = Field(default_factory=list)
    affected_students: int = Field(default=0)
    student_impact: str = Field(default="low", description="low | medium | high")
    
    # Content impact
    content_complexity: str = Field(default="low", description="low | medium | high")
    learning_objective_changes: bool = Field(default=False)
    assessment_changes: bool = Field(default=False)
    
    # Implementation
    implementation_complexity: str = Field(default="low", description="low | medium | high")
    estimated_implementation_time: int = Field(default=60, description="Minutes to implement")
    
    # Risk assessment
    risk_level: str = Field(default="low", description="low | medium | high")
    potential_issues: List[str] = Field(default_factory=list)
    mitigation_strategies: List[str] = Field(default_factory=list)

class ReviewerFeedback(BaseModel):
    """Detailed reviewer feedback"""
    reviewer_id: PyObjectId = Field(..., description="Reviewer user ID")
    reviewer_name: Optional[str] = Field(None, description="Reviewer name")
    review_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Overall assessment
    overall_rating: str = Field(..., description="excellent | good | acceptable | needs_work | reject")
    recommendation: str = Field(..., description="approve | approve_with_changes | reject | request_revision")
    
    # Detailed feedback
    strengths: List[str] = Field(default_factory=list, description="What's good about this PR")
    concerns: List[str] = Field(default_factory=list, description="Issues or concerns")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    
    # Specific change feedback
    change_feedback: List[Dict[str, Any]] = Field(default_factory=list, description="Feedback per change")
    
    # Review summary
    summary_comment: str = Field(..., max_length=2000, description="Overall review summary")

class CoursePullRequest(BaseModel):
    """Main Pull Request model"""
    id: Optional[str] = Field(None, alias="_id")
    pr_number: int = Field(..., description="Auto-increment PR number")
    course_family_id: PyObjectId = Field(..., description="Course family this PR targets")
    
    # PR identification
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=3000, description="Detailed PR description")
    
    # Source and target
    source_version_id: PyObjectId = Field(..., description="Teacher's fork version")
    target_version_id: PyObjectId = Field(..., description="Master version to merge into")
    requested_by: PyObjectId = Field(..., description="Teacher who submitted PR")
    
    # Proposed changes
    changes: List[ChangeProposal] = Field(..., min_items=1, description="List of proposed changes")
    
    # Review process
    status: str = Field(default="pending", description="pending | under_review | approved | rejected | merged | cancelled")
    priority: str = Field(default="normal", description="low | normal | high | urgent")
    
    # Assignment and review
    assigned_reviewer: Optional[PyObjectId] = Field(None, description="Assigned coordinator/reviewer")
    reviewer_feedback: Optional[ReviewerFeedback] = Field(None)
    
    # Impact assessment
    impact_assessment: ImpactAssessment = Field(default_factory=ImpactAssessment)
    
    # Workflow tracking
    approval_workflow: List[ApprovalWorkflowStep] = Field(default_factory=list)
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(None)
    merged_at: Optional[datetime] = Field(None)
    closed_at: Optional[datetime] = Field(None)
    
    # Merge information
    merged_version_id: Optional[PyObjectId] = Field(None, description="New version created from this PR")
    merge_commit_message: Optional[str] = Field(None, max_length=1000)
    
    # Communication
    comments: List[Dict[str, Any]] = Field(default_factory=list)
    notifications_sent: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Labels and categorization
    labels: List[str] = Field(default_factory=list, description="bug | enhancement | feature | refactor")
    category: Optional[str] = Field(None, description="content | structure | assessment | media")
    
    def add_workflow_step(self, action: str, actor_id: PyObjectId, comment: Optional[str] = None):
        """Add step to approval workflow"""
        step = ApprovalWorkflowStep(
            step_number=len(self.approval_workflow) + 1,
            action=action,
            actor_id=actor_id,
            comment=comment
        )
        self.approval_workflow.append(step)
        self.updated_at = datetime.utcnow()
    
    def get_current_status_step(self) -> Optional[ApprovalWorkflowStep]:
        """Get current workflow step"""
        return self.approval_workflow[-1] if self.approval_workflow else None
    
    def is_ready_for_merge(self) -> bool:
        """Check if PR is ready for merge"""
        return (
            self.status == "approved" and
            self.reviewer_feedback and
            self.reviewer_feedback.recommendation == "approve"
        )
    
    def get_changes_summary(self) -> Dict[str, int]:
        """Get summary of changes by type"""
        summary = {}
        for change in self.changes:
            action_type = change.action.split('_')[0]  # add, remove, modify
            if action_type in summary:
                summary[action_type] += 1
            else:
                summary[action_type] = 1
        return summary
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'under_review', 'approved', 'rejected', 'merged', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
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

class PRComment(BaseModel):
    """Comment pada pull request"""
    id: Optional[str] = Field(None, alias="_id")
    pr_id: PyObjectId = Field(..., description="Pull request ID")
    
    # Comment data
    author_id: PyObjectId = Field(..., description="Comment author")
    author_name: Optional[str] = Field(None, description="Author name for display")
    content: str = Field(..., min_length=1, max_length=2000)
    
    # Comment type
    comment_type: str = Field(default="general", description="general | suggestion | concern | approval")
    
    # References
    references_change_id: Optional[PyObjectId] = Field(None, description="Specific change this comment refers to")
    reply_to_comment_id: Optional[PyObjectId] = Field(None, description="Parent comment if this is a reply")
    
    # Status
    is_resolved: bool = Field(default=False, description="Whether concern/suggestion is resolved")
    resolved_by: Optional[PyObjectId] = Field(None)
    resolved_at: Optional[datetime] = Field(None)
    
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

class PRTemplate(BaseModel):
    """Template untuk PR submissions"""
    id: Optional[str] = Field(None, alias="_id")
    template_name: str = Field(..., min_length=1, max_length=100)
    subject_id: PyObjectId = Field(..., description="Subject this template is for")
    
    # Template content
    title_template: str = Field(..., description="Title template dengan placeholders")
    description_template: str = Field(..., description="Description template")
    
    # Required fields
    required_fields: List[str] = Field(default_factory=list)
    suggested_labels: List[str] = Field(default_factory=list)
    
    # Usage
    usage_count: int = Field(default=0)
    created_by: PyObjectId = Field(..., description="Template creator")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
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
