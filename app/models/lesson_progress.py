# ==============================================================================
# File: app/models/lesson_progress.py
# Deskripsi: Progress tracking untuk lessons, modules, dan courses
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.schemas.base import PyObjectId

class ComponentProgress(BaseModel):
    """Progress tracking untuk individual components"""
    component_id: str = Field(..., description="Component identifier")
    component_type: str = Field(..., description="quiz | assignment | interactive")
    status: str = Field(default="not_started", description="not_started | in_progress | completed | failed")
    score: Optional[float] = Field(None, description="Score achieved (0-100)")
    max_score: Optional[float] = Field(None, description="Maximum possible score")
    attempts: int = Field(default=0, description="Number of attempts")
    time_spent: int = Field(default=0, description="Time spent in seconds")
    
    # Progress tracking
    started_at: Optional[datetime] = Field(None, description="When user started this component")
    completed_at: Optional[datetime] = Field(None, description="When user completed this component")
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Component-specific data
    responses: List[Dict[str, Any]] = Field(default_factory=list, description="User responses/submissions")
    feedback: Optional[str] = Field(None, description="Feedback from teacher/system")

class PageProgress(BaseModel):
    """Progress tracking untuk lesson pages"""
    page_number: int = Field(..., description="Page number")
    status: str = Field(default="not_started", description="not_started | reading | completed")
    time_spent: int = Field(default=0, description="Time spent reading (seconds)")
    completion_percentage: float = Field(default=0.0, description="Page completion percentage")
    
    # Component progress within this page
    component_progress: List[ComponentProgress] = Field(default_factory=list)
    
    # Progress tracking
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    def calculate_page_completion(self) -> float:
        """Calculate overall page completion percentage"""
        if not self.component_progress:
            return 100.0 if self.status == "completed" else 0.0
        
        completed_components = sum(1 for comp in self.component_progress if comp.status == "completed")
        total_components = len(self.component_progress)
        
        base_completion = 50.0 if self.status == "completed" else 0.0  # Reading completion
        component_completion = (completed_components / total_components) * 50.0  # Component completion
        
        return base_completion + component_completion

class LessonProgress(BaseModel):
    """Progress tracking untuk individual lessons"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Identifiers
    student_id: PyObjectId = Field(..., description="Student user ID")
    lesson_id: PyObjectId = Field(..., description="Lesson ID")
    course_id: Optional[PyObjectId] = Field(None, description="Course ID (if accessed via course)")
    module_id: Optional[PyObjectId] = Field(None, description="Module ID (if accessed via module)")
    
    # Overall lesson progress
    status: str = Field(default="not_started", description="not_started | in_progress | completed | failed")
    completion_percentage: float = Field(default=0.0, description="Overall lesson completion (0-100)")
    score: Optional[float] = Field(None, description="Overall lesson score")
    
    # Time tracking
    total_time_spent: int = Field(default=0, description="Total time spent in seconds")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time to completion")
    
    # Page progress
    current_page: int = Field(default=1, description="Current page being viewed")
    page_progress: List[PageProgress] = Field(default_factory=list, description="Progress per page")
    
    # Progress tracking
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    access_method: str = Field(default="direct", description="direct | via_module | via_course")
    device_type: Optional[str] = Field(None, description="mobile | tablet | desktop")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def calculate_completion_percentage(self) -> float:
        """Calculate overall lesson completion percentage"""
        if not self.page_progress:
            return 0.0
        
        total_page_completion = sum(page.calculate_page_completion() for page in self.page_progress)
        return total_page_completion / len(self.page_progress) if self.page_progress else 0.0
    
    def update_completion_status(self) -> None:
        """Update lesson completion status based on page progress"""
        completion = self.calculate_completion_percentage()
        self.completion_percentage = completion
        
        if completion >= 100.0:
            self.status = "completed"
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        elif completion > 0:
            self.status = "in_progress"
            if not self.started_at:
                self.started_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True

class ModuleProgress(BaseModel):
    """Progress tracking untuk modules"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Identifiers
    student_id: PyObjectId = Field(..., description="Student user ID")
    module_id: PyObjectId = Field(..., description="Module ID")
    course_id: Optional[PyObjectId] = Field(None, description="Course ID (if accessed via course)")
    
    # Overall module progress
    status: str = Field(default="not_started", description="not_started | in_progress | completed | failed")
    completion_percentage: float = Field(default=0.0, description="Overall module completion (0-100)")
    score: Optional[float] = Field(None, description="Overall module score")
    
    # Lesson progress summary
    total_lessons: int = Field(default=0, description="Total lessons in module")
    completed_lessons: int = Field(default=0, description="Completed lessons")
    in_progress_lessons: int = Field(default=0, description="Lessons in progress")
    
    # Current position
    current_lesson_id: Optional[PyObjectId] = Field(None, description="Currently active lesson")
    lesson_completion_order: List[PyObjectId] = Field(default_factory=list, description="Order lessons were completed")
    
    # Time tracking
    total_time_spent: int = Field(default=0, description="Total time spent in seconds")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time to completion")
    
    # Progress tracking
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def calculate_from_lesson_progress(self, lesson_progress_data: List[dict]) -> None:
        """Calculate module progress from lesson progress data"""
        if not lesson_progress_data:
            return
        
        self.total_lessons = len(lesson_progress_data)
        completed = sum(1 for lp in lesson_progress_data if lp.get('status') == 'completed')
        in_progress = sum(1 for lp in lesson_progress_data if lp.get('status') == 'in_progress')
        
        self.completed_lessons = completed
        self.in_progress_lessons = in_progress
        
        # Calculate completion percentage
        if self.total_lessons > 0:
            self.completion_percentage = (completed / self.total_lessons) * 100
        
        # Update overall status
        if self.completion_percentage >= 100.0:
            self.status = "completed"
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        elif self.completion_percentage > 0:
            self.status = "in_progress"
            if not self.started_at:
                self.started_at = datetime.utcnow()
        
        # Calculate total time spent
        self.total_time_spent = sum(lp.get('total_time_spent', 0) for lp in lesson_progress_data)
        
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True

class CourseProgress(BaseModel):
    """Progress tracking untuk courses"""
    id: Optional[str] = Field(None, alias="_id")
    
    # Identifiers
    student_id: PyObjectId = Field(..., description="Student user ID")
    course_id: PyObjectId = Field(..., description="Course ID")
    enrollment_id: Optional[PyObjectId] = Field(None, description="Enrollment record ID")
    
    # Overall course progress
    status: str = Field(default="not_started", description="not_started | in_progress | completed | failed | withdrawn")
    completion_percentage: float = Field(default=0.0, description="Overall course completion (0-100)")
    score: Optional[float] = Field(None, description="Overall course score")
    grade: Optional[str] = Field(None, description="Final grade (A, B, C, D, F)")
    
    # Module progress summary
    total_modules: int = Field(default=0, description="Total modules in course")
    completed_modules: int = Field(default=0, description="Completed modules")
    in_progress_modules: int = Field(default=0, description="Modules in progress")
    
    # Lesson progress summary
    total_lessons: int = Field(default=0, description="Total lessons across all modules")
    completed_lessons: int = Field(default=0, description="Completed lessons")
    in_progress_lessons: int = Field(default=0, description="Lessons in progress")
    
    # Current position
    current_module_id: Optional[PyObjectId] = Field(None, description="Currently active module")
    current_lesson_id: Optional[PyObjectId] = Field(None, description="Currently active lesson")
    learning_path: List[Dict[str, Any]] = Field(default_factory=list, description="Student's learning path")
    
    # Time tracking
    total_time_spent: int = Field(default=0, description="Total time spent in seconds")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time to completion")
    
    # Performance metrics
    quiz_scores: List[float] = Field(default_factory=list, description="All quiz scores")
    assignment_scores: List[float] = Field(default_factory=list, description="All assignment scores")
    average_quiz_score: float = Field(default=0.0, description="Average quiz performance")
    average_assignment_score: float = Field(default=0.0, description="Average assignment performance")
    
    # Engagement metrics
    login_count: int = Field(default=0, description="Number of times logged in for this course")
    active_days: int = Field(default=0, description="Number of days active")
    streak_days: int = Field(default=0, description="Current consecutive days streak")
    longest_streak: int = Field(default=0, description="Longest consecutive days streak")
    
    # Progress tracking
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    withdrawn_at: Optional[datetime] = Field(None)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    async def calculate_from_module_progress(self, module_progress_data: List[dict], lesson_progress_data: List[dict]) -> None:
        """Calculate course progress from module and lesson progress data"""
        # Module progress
        if module_progress_data:
            self.total_modules = len(module_progress_data)
            self.completed_modules = sum(1 for mp in module_progress_data if mp.get('status') == 'completed')
            self.in_progress_modules = sum(1 for mp in module_progress_data if mp.get('status') == 'in_progress')
        
        # Lesson progress
        if lesson_progress_data:
            self.total_lessons = len(lesson_progress_data)
            self.completed_lessons = sum(1 for lp in lesson_progress_data if lp.get('status') == 'completed')
            self.in_progress_lessons = sum(1 for lp in lesson_progress_data if lp.get('status') == 'in_progress')
        
        # Calculate completion percentage (weighted: 70% lessons, 30% modules)
        lesson_completion = (self.completed_lessons / self.total_lessons * 100) if self.total_lessons > 0 else 0
        module_completion = (self.completed_modules / self.total_modules * 100) if self.total_modules > 0 else 0
        
        self.completion_percentage = (lesson_completion * 0.7) + (module_completion * 0.3)
        
        # Update overall status
        if self.completion_percentage >= 100.0:
            self.status = "completed"
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        elif self.completion_percentage > 0:
            self.status = "in_progress"
            if not self.started_at:
                self.started_at = datetime.utcnow()
        
        # Calculate total time spent
        self.total_time_spent = sum(mp.get('total_time_spent', 0) for mp in module_progress_data)
        
        # Calculate performance metrics
        all_scores = []
        quiz_scores = []
        assignment_scores = []
        
        for lp in lesson_progress_data:
            for page in lp.get('page_progress', []):
                for comp in page.get('component_progress', []):
                    if comp.get('score') is not None:
                        all_scores.append(comp['score'])
                        if comp.get('component_type') == 'quiz':
                            quiz_scores.append(comp['score'])
                        elif comp.get('component_type') == 'assignment':
                            assignment_scores.append(comp['score'])
        
        self.quiz_scores = quiz_scores
        self.assignment_scores = assignment_scores
        self.average_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0.0
        self.average_assignment_score = sum(assignment_scores) / len(assignment_scores) if assignment_scores else 0.0
        self.score = sum(all_scores) / len(all_scores) if all_scores else None
        
        self.updated_at = datetime.utcnow()
    
    def calculate_grade(self) -> str:
        """Calculate letter grade based on score"""
        if not self.score:
            return "I"  # Incomplete
        
        if self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"  
        elif self.score >= 70:
            return "C"
        elif self.score >= 60:
            return "D"
        else:
            return "F"
    
    @classmethod
    def from_mongo(cls, data: dict):
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True
