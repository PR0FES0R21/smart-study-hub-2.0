# ==============================================================================
# File: app/models/lesson_assignment.py
# Deskripsi: Module model dengan lesson references (Modular Architecture)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class LessonReference(BaseModel):
    """Reference ke lesson dalam module"""
    lesson_id: PyObjectId = Field(..., description="ID of the referenced lesson")
    order: int = Field(..., ge=1, description="Order of lesson dalam module")
    required: bool = Field(default=True, description="Whether lesson is required for completion")
    custom_title: Optional[str] = Field(None, description="Override lesson title for this module")
    custom_description: Optional[str] = Field(None, description="Additional context for this module")
    
    # Module-specific settings for this lesson
    weight: float = Field(default=1.0, description="Weight untuk progress calculation")
    unlock_condition: str = Field(default="sequential", description="sequential | immediate | conditional")
    unlock_requirements: List[str] = Field(default_factory=list, description="Requirements to unlock this lesson")

class ModuleAssessment(BaseModel):
    """Module-level assessment (quiz/assignment yang mencakup seluruh module)"""
    assessment_id: str = Field(..., description="Unique assessment identifier")
    type: str = Field(..., description="quiz | assignment | project | exam")
    title: str = Field(..., description="Assessment title")
    description: str = Field(..., description="Assessment description")
    required: bool = Field(default=True, description="Required for module completion")
    weight: float = Field(default=1.0, description="Weight dalam module scoring")
    estimated_duration: int = Field(default=60, description="Estimated completion time (minutes)")
    
    @validator('type')
    def validate_assessment_type(cls, v):
        allowed_types = ['quiz', 'assignment', 'project', 'exam', 'presentation']
        if v not in allowed_types:
            raise ValueError(f'Assessment type must be one of {allowed_types}')
        return v

class ModuleMetadata(BaseModel):
    """Auto-calculated metadata untuk module"""
    total_lessons: int = Field(default=0, description="Total lessons dalam module")
    total_duration: int = Field(default=0, description="Total estimated duration (minutes)")
    total_pages: int = Field(default=0, description="Total pages across all lessons")
    total_components: int = Field(default=0, description="Total embedded components")
    
    # Content analysis
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict, description="Lessons by difficulty")
    component_summary: Dict[str, int] = Field(default_factory=dict, description="Components by type")
    
    # Learning path
    sequential_lessons: int = Field(default=0, description="Lessons yang harus diambil sequential")
    optional_lessons: int = Field(default=0, description="Optional lessons")
    
    # Usage statistics
    usage_count: int = Field(default=0, description="Times used in courses")
    average_completion_time: Optional[float] = Field(None, description="Actual completion time")
    completion_rate: float = Field(default=0.0, description="Student completion rate (0-100)")
    
    # Quality metrics
    rating: float = Field(default=0.0, description="Average rating")
    review_count: int = Field(default=0, description="Number of reviews")
    
    # Last calculated
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class Module(BaseModel):
    """Main module model - contains lesson references and metadata"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Basic module info
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    slug: Optional[str] = Field(None, description="URL-friendly slug")
    
    # Academic classification
    subject_id: PyObjectId = Field(..., description="Subject this module belongs to")
    grade_level: int = Field(..., ge=1, le=12, description="Target grade level")
    topic_tags: List[str] = Field(default_factory=list, description="Topic tags")
    
    # Lesson references (NOT embedded)
    lesson_refs: List[LessonReference] = Field(default_factory=list, description="References to lessons")
    
    # Module structure
    difficulty_level: str = Field(default="medium", description="Overall module difficulty")
    learning_objectives: List[str] = Field(default_factory=list, description="Module learning objectives")
    prerequisites: List[str] = Field(default_factory=list, description="Required prior knowledge")
    
    # Completion criteria
    completion_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "all_required",  # all_required | percentage | points | custom
            "required_percentage": 100,  # If type is percentage
            "minimum_score": 0,  # If type is points
            "custom_rules": []  # If type is custom
        }
    )
    
    # Module assessments
    assessments: List[ModuleAssessment] = Field(default_factory=list, description="Module-level assessments")
    
    # Sharing dan visibility
    visibility: str = Field(default="public", description="public | private | shared")
    created_by: PyObjectId = Field(..., description="Teacher who created this module")
    collaborators: List[PyObjectId] = Field(default_factory=list, description="Teachers who can edit")
    
    # Auto-calculated metadata
    metadata: ModuleMetadata = Field(default_factory=ModuleMetadata)
    
    # Status dan lifecycle
    status: str = Field(default="draft", description="draft | published | archived")
    published_at: Optional[datetime] = Field(None)
    archived_at: Optional[datetime] = Field(None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def calculate_metadata(self, lesson_data: List[dict]) -> ModuleMetadata:
        """Calculate module metadata berdasarkan lesson data"""
        metadata = ModuleMetadata()
        
        # Basic counts
        metadata.total_lessons = len(self.lesson_refs)
        
        # Analyze lesson data
        total_duration = 0
        total_pages = 0
        total_components = 0
        difficulty_count = {"easy": 0, "medium": 0, "hard": 0}
        component_summary = {}
        sequential_count = 0
        optional_count = 0
        
        for lesson_ref in self.lesson_refs:
            # Find corresponding lesson data
            lesson = next((l for l in lesson_data if str(l['_id']) == str(lesson_ref.lesson_id)), None)
            if not lesson:
                continue
            
            # Accumulate data
            if 'metadata' in lesson:
                lesson_meta = lesson['metadata']
                total_duration += lesson_meta.get('total_duration', 0)
                total_pages += lesson_meta.get('total_pages', 0)
                total_components += lesson_meta.get('total_components', 0)
                
                # Component breakdown
                for comp_type, count in lesson_meta.get('component_breakdown', {}).items():
                    component_summary[comp_type] = component_summary.get(comp_type, 0) + count
            
            # Difficulty distribution
            difficulty_count[lesson.get('difficulty_level', 'medium')] += 1
            
            # Learning path analysis
            if lesson_ref.required:
                if lesson_ref.unlock_condition == "sequential":
                    sequential_count += 1
                else:
                    optional_count += 1
            else:
                optional_count += 1
        
        # Update metadata
        metadata.total_duration = total_duration
        metadata.total_pages = total_pages
        metadata.total_components = total_components
        metadata.difficulty_distribution = difficulty_count
        metadata.component_summary = component_summary
        metadata.sequential_lessons = sequential_count
        metadata.optional_lessons = optional_count
        metadata.calculated_at = datetime.utcnow()
        
        self.metadata = metadata
        return metadata
    
    def add_lesson_reference(self, lesson_id: PyObjectId, order: Optional[int] = None, **kwargs) -> None:
        """Add lesson reference to module"""
        if order is None:
            order = len(self.lesson_refs) + 1
        
        lesson_ref = LessonReference(
            lesson_id=lesson_id,
            order=order,
            **kwargs
        )
        
        self.lesson_refs.append(lesson_ref)
        self.updated_at = datetime.utcnow()
        self._reorder_lessons()
    
    def remove_lesson_reference(self, lesson_id: PyObjectId) -> bool:
        """Remove lesson reference from module"""
        original_count = len(self.lesson_refs)
        self.lesson_refs = [ref for ref in self.lesson_refs if ref.lesson_id != lesson_id]
        
        if len(self.lesson_refs) < original_count:
            self.updated_at = datetime.utcnow()
            self._reorder_lessons()
            return True
        return False
    
    def reorder_lessons(self, new_order: List[str]) -> None:
        """Reorder lessons berdasarkan lesson IDs"""
        if len(new_order) != len(self.lesson_refs):
            raise ValueError("New order must include all lessons")
        
        # Create mapping dari lesson_id ke reference
        lesson_map = {str(ref.lesson_id): ref for ref in self.lesson_refs}
        
        # Reorder
        reordered_refs = []
        for i, lesson_id in enumerate(new_order):
            if lesson_id not in lesson_map:
                raise ValueError(f"Lesson ID {lesson_id} not found in module")
            
            lesson_ref = lesson_map[lesson_id]
            lesson_ref.order = i + 1
            reordered_refs.append(lesson_ref)
        
        self.lesson_refs = reordered_refs
        self.updated_at = datetime.utcnow()
    
    def _reorder_lessons(self) -> None:
        """Internal method to reorder lessons by order field"""
        self.lesson_refs.sort(key=lambda x: x.order)
        
        # Fix order numbers to be sequential
        for i, ref in enumerate(self.lesson_refs):
            ref.order = i + 1
    
    def get_lesson_reference(self, lesson_id: PyObjectId) -> Optional[LessonReference]:
        """Get lesson reference by lesson ID"""
        for ref in self.lesson_refs:
            if ref.lesson_id == lesson_id:
                return ref
        return None
    
    def is_editable_by(self, user_id: PyObjectId) -> bool:
        """Check if user can edit this module"""
        return (
            self.created_by == user_id or 
            user_id in self.collaborators
        )
    
    @validator('visibility')
    def validate_visibility(cls, v):
        allowed_values = ['public', 'private', 'shared']
        if v not in allowed_values:
            raise ValueError(f'Visibility must be one of {allowed_values}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_values = ['draft', 'published', 'archived']
        if v not in allowed_values:
            raise ValueError(f'Status must be one of {allowed_values}')
        return v
    
    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB document to Pydantic model"""
        if '_id' in data:
            data['id'] = str(data['_id'])
            del data['_id']  # Remove _id after converting to id
        
        # Convert all ObjectId fields to strings
        if 'subject_id' in data and data['subject_id']:
            data['subject_id'] = str(data['subject_id'])
        if 'created_by' in data and data['created_by']:
            data['created_by'] = str(data['created_by'])
        if 'collaborators' in data:
            data['collaborators'] = [str(c) for c in data['collaborators']]
        
        # Convert lesson_refs ObjectIds
        if 'lesson_refs' in data:
            for ref in data['lesson_refs']:
                if 'lesson_id' in ref and ref['lesson_id']:
                    ref['lesson_id'] = str(ref['lesson_id'])
        
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
