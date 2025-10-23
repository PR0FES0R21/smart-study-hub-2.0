# ==============================================================================
# File: app/models/course.py  
# Deskripsi: Course model dengan module references (Modular Architecture)
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class ModuleReference(BaseModel):
    """Reference ke module dalam course"""
    module_id: PyObjectId = Field(..., description="ID of the referenced module")
    order: int = Field(..., ge=1, description="Order of module dalam course")
    required: bool = Field(default=True, description="Whether module is required for course completion")
    custom_title: Optional[str] = Field(None, description="Override module title for this course")
    custom_description: Optional[str] = Field(None, description="Additional context for this course")
    
    # Course-specific settings for this module
    weight: float = Field(default=1.0, description="Weight untuk course progress calculation")
    unlock_condition: str = Field(default="sequential", description="sequential | immediate | conditional")
    unlock_requirements: List[str] = Field(default_factory=list, description="Requirements to unlock this module")
    
    # Snapshot of module data untuk stability (optional)
    module_snapshot: Optional[Dict[str, Any]] = Field(None, description="Cached module metadata")

class AssessmentConfig(BaseModel):
    """Configuration untuk assessment"""
    time_limit: int = Field(default=120, description="Time limit in minutes")
    max_score: float = Field(default=100.0, description="Maximum score")
    passing_score: float = Field(default=70.0, description="Minimum score to pass")
    allow_retake: bool = Field(default=False, description="Allow retake (always False for final)")
    max_attempts: int = Field(default=1, description="Maximum attempts (always 1 for final)")
    shuffle_questions: bool = Field(default=True, description="Shuffle question order")
    show_correct_answers: bool = Field(default=False, description="Show correct answers after submit")

class CourseAssessment(BaseModel):
    """
    Course-level assessment (final exam, project, etc.)
    
    Linked to question_sets collection for quiz questions.
    Position: after all modules completed (displayed at course end).
    """
    assessment_id: str = Field(..., description="Unique assessment identifier")
    question_set_id: Optional[PyObjectId] = Field(
        None,
        description="Reference to question_sets collection (for quiz/exam)"
    )
    type: str = Field(default="quiz", description="quiz | assignment")
    title: str = Field(..., description="Assessment title")
    description: Optional[str] = Field(None, description="Assessment description")
    required: bool = Field(default=True, description="Required for course completion")
    
    # Configuration
    config: AssessmentConfig = Field(
        default_factory=AssessmentConfig,
        description="Assessment configuration"
    )
    
    # Position (always after modules for MVP)
    position: str = Field(
        default="after_modules",
        description="after_modules (displayed when all modules completed)"
    )
    
    @validator('type')
    def validate_assessment_type(cls, v):
        allowed_types = ['quiz', 'assignment']
        if v not in allowed_types:
            raise ValueError(f'Assessment type must be one of {allowed_types}')
        return v
    
    @validator('position')
    def validate_position(cls, v):
        # For MVP, only after_modules allowed
        if v != "after_modules":
            raise ValueError('Position must be "after_modules" for final assessment')
        return v

class CourseMetadata(BaseModel):
    """Auto-calculated metadata untuk course"""
    total_modules: int = Field(default=0, description="Total modules dalam course")
    total_lessons: int = Field(default=0, description="Total lessons across all modules")
    total_duration: int = Field(default=0, description="Total estimated duration (minutes)")
    total_pages: int = Field(default=0, description="Total pages across all lessons")
    total_components: int = Field(default=0, description="Total embedded components")
    
    # Content analysis
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict, description="Modules by difficulty")
    component_summary: Dict[str, int] = Field(default_factory=dict, description="Components by type")
    subject_coverage: List[str] = Field(default_factory=list, description="Topics covered")
    
    # Learning path
    sequential_modules: int = Field(default=0, description="Modules yang harus diambil sequential")
    optional_modules: int = Field(default=0, description="Optional modules")
    estimated_weeks: int = Field(default=0, description="Estimated completion time in weeks")
    
    # Enrollment statistics
    enrolled_students: int = Field(default=0, description="Currently enrolled students")
    completed_students: int = Field(default=0, description="Students who completed course")
    active_students: int = Field(default=0, description="Students active in last 30 days")
    
    # Performance metrics
    average_completion_rate: float = Field(default=0.0, description="Average student completion rate")
    average_completion_time: Optional[float] = Field(None, description="Actual completion time (hours)")
    average_score: Optional[float] = Field(None, description="Average student score")
    
    # Quality metrics
    rating: float = Field(default=0.0, description="Average course rating")
    review_count: int = Field(default=0, description="Number of reviews")
    dropout_rate: float = Field(default=0.0, description="Student dropout rate")
    
    # Last calculated
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class Course(BaseModel):
    """Main course model - contains module references and metadata"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Basic course info
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=3000)
    slug: Optional[str] = Field(None, description="URL-friendly slug")
    course_code: Optional[str] = Field(None, description="Official course code")
    
    # Academic classification
    subject_id: PyObjectId = Field(..., description="Subject this course belongs to")
    grade_level: int = Field(..., ge=1, le=12, description="Target grade level")
    academic_period_id: Optional[PyObjectId] = Field(None, description="Academic period")
    
    # Course management
    coordinator_id: PyObjectId = Field(..., description="Course coordinator")
    instructor_ids: List[PyObjectId] = Field(default_factory=list, description="Additional instructors")
    
    # Module references (NOT embedded)
    module_refs: List[ModuleReference] = Field(default_factory=list, description="References to modules")
    
    # Course structure
    difficulty_level: str = Field(default="medium", description="Overall course difficulty")
    learning_objectives: List[str] = Field(default_factory=list, description="Course learning objectives")
    prerequisites: List[str] = Field(default_factory=list, description="Required prior knowledge/courses")
    
    # Completion criteria
    completion_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "weighted_average",  # all_required | weighted_average | points | custom
            "minimum_score": 70,  # Minimum score for completion
            "required_modules": [],  # Specific modules that must be completed
            "optional_module_count": 0,  # Number of optional modules required
            "final_assessment_required": True
        }
    )
    
    # Course assessments
    assessments: List[CourseAssessment] = Field(default_factory=list, description="Course-level assessments")
    
    # Course settings
    auto_enroll_students: bool = Field(default=False, description="Auto-enroll students from assigned classes")
    allow_late_enrollment: bool = Field(default=True, description="Allow enrollment after course starts")
    self_paced: bool = Field(default=False, description="Self-paced vs instructor-paced")
    
    # Enrollment management
    max_enrollments: Optional[int] = Field(None, description="Maximum student enrollments")
    enrollment_start: Optional[datetime] = Field(None, description="Enrollment start date")
    enrollment_end: Optional[datetime] = Field(None, description="Enrollment end date")
    course_start: Optional[datetime] = Field(None, description="Course start date")
    course_end: Optional[datetime] = Field(None, description="Course end date")
    
    # Sharing dan visibility
    visibility: str = Field(default="institutional", description="public | institutional | private")
    featured: bool = Field(default=False, description="Featured course")
    
    # Auto-calculated metadata
    metadata: CourseMetadata = Field(default_factory=CourseMetadata)
    
    # Status dan lifecycle
    status: str = Field(default="draft", description="draft | published | active | completed | archived")
    published_at: Optional[datetime] = Field(None)
    archived_at: Optional[datetime] = Field(None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def calculate_metadata(self, module_data: List[dict], lesson_data: List[dict]) -> CourseMetadata:
        """Calculate course metadata berdasarkan module dan lesson data"""
        metadata = CourseMetadata()
        
        # Basic counts
        metadata.total_modules = len(self.module_refs)
        
        # Analyze module and lesson data
        total_duration = 0
        total_lessons = 0
        total_pages = 0
        total_components = 0
        difficulty_count = {"easy": 0, "medium": 0, "hard": 0}
        component_summary = {}
        sequential_count = 0
        optional_count = 0
        subject_tags = set()
        
        for module_ref in self.module_refs:
            # Find corresponding module data
            module = next((m for m in module_data if str(m['_id']) == str(module_ref.module_id)), None)
            if not module:
                continue
            
            # Accumulate module data
            if 'metadata' in module:
                module_meta = module['metadata']
                total_duration += module_meta.get('total_duration', 0)
                total_lessons += module_meta.get('total_lessons', 0)
                total_pages += module_meta.get('total_pages', 0)
                total_components += module_meta.get('total_components', 0)
                
                # Component breakdown
                for comp_type, count in module_meta.get('component_summary', {}).items():
                    component_summary[comp_type] = component_summary.get(comp_type, 0) + count
            
            # Difficulty distribution
            difficulty_count[module.get('difficulty_level', 'medium')] += 1
            
            # Learning path analysis
            if module_ref.required:
                if module_ref.unlock_condition == "sequential":
                    sequential_count += 1
                else:
                    optional_count += 1
            else:
                optional_count += 1
            
            # Subject coverage
            if 'topic_tags' in module:
                subject_tags.update(module['topic_tags'])
        
        # Calculate derived metrics
        metadata.total_duration = total_duration
        metadata.total_lessons = total_lessons
        metadata.total_pages = total_pages
        metadata.total_components = total_components
        metadata.difficulty_distribution = difficulty_count
        metadata.component_summary = component_summary
        metadata.sequential_modules = sequential_count
        metadata.optional_modules = optional_count
        metadata.subject_coverage = list(subject_tags)
        
        # Estimate weeks (assuming 3 hours study per week)
        if total_duration > 0:
            metadata.estimated_weeks = max(1, round(total_duration / 180))  # 180 minutes = 3 hours
        
        metadata.calculated_at = datetime.utcnow()
        
        self.metadata = metadata
        return metadata
    
    def add_module_reference(self, module_id: PyObjectId, order: Optional[int] = None, **kwargs) -> None:
        """Add module reference to course"""
        if order is None:
            order = len(self.module_refs) + 1
        
        module_ref = ModuleReference(
            module_id=module_id,
            order=order,
            **kwargs
        )
        
        self.module_refs.append(module_ref)
        self.updated_at = datetime.utcnow()
        self._reorder_modules()
    
    def remove_module_reference(self, module_id: PyObjectId) -> bool:
        """Remove module reference from course"""
        original_count = len(self.module_refs)
        self.module_refs = [ref for ref in self.module_refs if ref.module_id != module_id]
        
        if len(self.module_refs) < original_count:
            self.updated_at = datetime.utcnow()
            self._reorder_modules()
            return True
        return False
    
    def reorder_modules(self, new_order: List[str]) -> None:
        """Reorder modules berdasarkan module IDs"""
        if len(new_order) != len(self.module_refs):
            raise ValueError("New order must include all modules")
        
        # Create mapping dari module_id ke reference
        module_map = {str(ref.module_id): ref for ref in self.module_refs}
        
        # Reorder
        reordered_refs = []
        for i, module_id in enumerate(new_order):
            if module_id not in module_map:
                raise ValueError(f"Module ID {module_id} not found in course")
            
            module_ref = module_map[module_id]
            module_ref.order = i + 1
            reordered_refs.append(module_ref)
        
        self.module_refs = reordered_refs
        self.updated_at = datetime.utcnow()
    
    def _reorder_modules(self) -> None:
        """Internal method to reorder modules by order field"""
        self.module_refs.sort(key=lambda x: x.order)
        
        # Fix order numbers to be sequential
        for i, ref in enumerate(self.module_refs):
            ref.order = i + 1
    
    def get_module_reference(self, module_id: PyObjectId) -> Optional[ModuleReference]:
        """Get module reference by module ID"""
        for ref in self.module_refs:
            if ref.module_id == module_id:
                return ref
        return None
    
    def is_manageable_by(self, user_id: PyObjectId) -> bool:
        """Check if user can manage this course"""
        return (
            self.coordinator_id == user_id or 
            user_id in self.instructor_ids
        )
    
    def is_active(self) -> bool:
        """Check if course is currently active"""
        now = datetime.utcnow()
        
        if self.status != "active":
            return False
        
        if self.course_start and now < self.course_start:
            return False
        
        if self.course_end and now > self.course_end:
            return False
        
        return True
    
    def can_enroll(self) -> bool:
        """Check if course is accepting enrollments"""
        now = datetime.utcnow()
        
        if not self.is_active():
            return False
        
        if self.enrollment_start and now < self.enrollment_start:
            return False
        
        if self.enrollment_end and now > self.enrollment_end:
            return self.allow_late_enrollment
        
        if self.max_enrollments and self.metadata.enrolled_students >= self.max_enrollments:
            return False
        
        return True
    
    @validator('visibility')
    def validate_visibility(cls, v):
        allowed_values = ['public', 'institutional', 'private']
        if v not in allowed_values:
            raise ValueError(f'Visibility must be one of {allowed_values}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_values = ['draft', 'published', 'active', 'completed', 'archived']
        if v not in allowed_values:
            raise ValueError(f'Status must be one of {allowed_values}')
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
