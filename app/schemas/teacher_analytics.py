# ==============================================================================
# File: app/schemas/teacher_analytics.py
# Deskripsi: Schema Pydantic untuk Teacher Analytics (Exam-level Analytics)
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import PyObjectId


class ExamMetadata(BaseModel):
    """Metadata basic ujian"""
    exam_id: PyObjectId
    exam_title: str
    exam_type: str
    subject_name: str
    class_name: str
    teacher_name: str
    total_questions: int
    max_score: int
    duration_minutes: int
    availability_start_time: datetime
    availability_end_time: datetime
    academic_period: str


class ClassStatistics(BaseModel):
    """Statistik keseluruhan kelas"""
    total_students: int
    students_completed: int
    students_in_progress: int
    students_not_started: int
    completion_rate: float
    
    # Score statistics
    class_average: float
    median_score: float
    highest_score: float
    lowest_score: float
    standard_deviation: float
    passing_rate: float  # Persentase siswa yang lulus (>= 60)
    
    # Grade distribution
    grade_distribution: Dict[str, int] = Field(default_factory=dict)  # A, B, C, D, E
    score_ranges: Dict[str, int] = Field(default_factory=dict)  # 0-20, 21-40, etc.


class QuestionAnalysis(BaseModel):
    """Analisis per pertanyaan"""
    question_id: PyObjectId
    question_number: int
    question_text: str
    question_type: str  # multiple_choice, essay
    difficulty: str
    points: int
    
    # Performance metrics
    class_accuracy: float  # 0.0 - 1.0
    correct_count: int
    wrong_count: int
    unanswered_count: int
    
    # Time metrics
    average_time: float  # seconds
    median_time: float
    fastest_time: float
    slowest_time: float
    
    # Quality indicators
    is_problematic: bool  # jika accuracy < 0.5
    discrimination_index: float  # -1.0 to 1.0 (seberapa baik soal membedakan siswa)
    
    # Multiple choice specific
    answer_distribution: Optional[Dict[str, int]] = None  # untuk MC questions
    correct_option: Optional[str] = None


class StudentPerformance(BaseModel):
    """Performa individual siswa"""
    student_id: PyObjectId
    student_name: str
    exam_session_id: PyObjectId
    status: str  # completed, ongoing, not_started
    
    # Score metrics
    score: float
    percentage: float
    rank: int  # 1 = tertinggi
    percentile: float
    grade: str  # A, B, C, D, E
    
    # Time metrics  
    duration_taken: float  # minutes
    time_efficiency: float  # score per minute
    
    # Performance breakdown
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int
    accuracy_rate: float
    
    # Behavioral metrics
    violations_count: int
    integrity_score: float  # 0.0 - 1.0
    
    # Timestamps
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None


class TimeAnalysis(BaseModel):
    """Analisis waktu pengerjaan"""
    average_completion_time: float  # minutes
    median_completion_time: float
    fastest_completion: float
    slowest_completion: float
    standard_deviation: float
    
    # Distribution
    time_distribution: Dict[str, int] = Field(default_factory=dict)  # time ranges
    overtime_count: int
    early_submission_count: int  # submitted < 50% of time limit
    
    # Efficiency metrics
    average_time_per_question: float
    questions_with_long_response: List[PyObjectId] = Field(default_factory=list)


class ViolationAnalysis(BaseModel):
    """Analisis pelanggaran dan integritas"""
    total_violations: int
    students_with_violations: int
    violation_percentage: float
    
    # Violation breakdown
    violation_types: Dict[str, int] = Field(default_factory=dict)
    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # High-risk students
    flagged_students: List[PyObjectId] = Field(default_factory=list)
    high_risk_count: int
    
    # Overall integrity
    class_integrity_score: float  # 0.0 - 1.0
    integrity_rating: str  # excellent, good, fair, poor


class ComparisonAnalysis(BaseModel):
    """Perbandingan dengan ujian serupa"""
    has_comparison: bool = False
    comparison_exams: List[PyObjectId] = Field(default_factory=list)
    
    # Comparative metrics (jika ada data pembanding)
    score_improvement: Optional[float] = None  # vs previous exam
    difficulty_comparison: Optional[str] = None  # harder, easier, similar
    performance_trend: Optional[str] = None  # improving, declining, stable


class AnalyticsTask(BaseModel):
    """Status background task untuk analytics"""
    task_id: str
    exam_id: PyObjectId
    teacher_id: PyObjectId
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 - 1.0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class ExamAnalytics(BaseModel):
    """Schema utama untuk exam analytics"""
    # Task info
    task_id: Optional[str] = None
    status: str  # completed, processing, failed
    
    # Core analytics
    exam_metadata: ExamMetadata
    class_statistics: ClassStatistics
    questions_analysis: List[QuestionAnalysis]
    student_performances: List[StudentPerformance]
    time_analysis: TimeAnalysis
    violation_analysis: ViolationAnalysis
    comparison_analysis: Optional[ComparisonAnalysis] = None
    
    # Metadata
    generated_at: datetime
    generation_time: float  # seconds taken to generate
    cache_expires_at: datetime
    data_version: str = "1.0"
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class AnalyticsRequest(BaseModel):
    """Request untuk generate analytics"""
    force_regenerate: bool = False
    include_comparison: bool = True
    
    
class AnalyticsListItem(BaseModel):
    """Item dalam list analytics (untuk endpoint list)"""
    exam_id: PyObjectId
    exam_title: str
    class_name: str
    total_students: int
    completion_rate: float
    class_average: float
    status: str
    generated_at: Optional[datetime] = None
    has_analytics: bool


class PaginatedAnalyticsResponse(BaseModel):
    """Paginated response untuk list analytics"""
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    data: List[AnalyticsListItem]
