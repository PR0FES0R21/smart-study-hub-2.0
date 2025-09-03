# ==============================================================================
# File: app/schemas/exam_analytics.py
# Deskripsi: Schema Pydantic untuk analytics hasil ujian yang komprehensif
# ==============================================================================

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from .base import PyObjectId

# ============================================================================
# BASE ANALYTICS MODELS
# ============================================================================

class QuestionAnalytics(BaseModel):
    """Analitik untuk satu soal"""
    question_id: PyObjectId
    original_position: int                    # Posisi asli di bank soal/exam
    displayed_position: int                   # Posisi yang ditampilkan ke siswa
    question_text: str
    question_type: str                        # "multiple_choice", "essay"
    difficulty: str                           # "easy", "medium", "hard"
    points: int
    student_answer: Optional[str] = None      # Jawaban siswa (option_id atau text)
    correct_answer: Optional[str] = None      # Jawaban yang benar
    student_answer_text: Optional[str] = None # Teks jawaban siswa untuk display
    correct_answer_text: Optional[str] = None # Teks jawaban benar untuk display
    is_correct: bool
    points_earned: int
    time_spent: Optional[float] = None        # Waktu yang dihabiskan (detik)
    answer_timestamp: Optional[datetime] = None
    change_count: int = 0                     # Berapa kali jawaban diubah
    options: List[Dict[str, Any]] = []        # Options untuk multiple choice

class TimelineEvent(BaseModel):
    """Event di timeline pengerjaan ujian"""
    timestamp: datetime
    event_type: str                           # "answer_submitted", "answer_changed", "violation"
    question_id: Optional[PyObjectId] = None
    displayed_position: Optional[int] = None
    original_position: Optional[int] = None
    old_answer: Optional[str] = None
    new_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    cumulative_score: int = 0                 # Score kumulatif sampai event ini
    details: Dict[str, Any] = {}

class ScoreTimeline(BaseModel):
    """Timeline skor progresif"""
    timestamp: datetime
    question_position: int                    # Posisi soal yang dijawab
    question_id: PyObjectId
    is_correct: bool
    cumulative_correct: int                   # Jumlah benar sampai sekarang
    cumulative_wrong: int                     # Jumlah salah sampai sekarang
    cumulative_score: float                   # Skor kumulatif
    score_change: int                         # +1 benar, -1 salah, 0 tidak berubah

class ViolationAnalytics(BaseModel):
    """Analitik pelanggaran ujian"""
    total_violations: int
    violations_by_severity: Dict[str, int]    # {"low": 5, "medium": 2, "high": 0}
    violations_by_type: Dict[str, int]        # {"text_selection": 3, "tab_switch": 2}
    violation_timeline: List[Dict[str, Any]]  # Timeline violations
    fraud_score: float
    is_flagged: bool
    risk_level: str                           # "low", "medium", "high", "critical"

class PerformanceMetrics(BaseModel):
    """Metrik performa siswa"""
    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int
    accuracy_percentage: float
    completion_percentage: float
    total_time_taken: float                   # Total waktu (detik)
    average_time_per_question: float
    fastest_answer: float
    slowest_answer: float
    score: float
    max_possible_score: float

class ClassComparison(BaseModel):
    """Perbandingan dengan kelas untuk ujian ini"""
    class_average_score: float
    class_highest_score: float
    class_lowest_score: float
    student_rank: int                         # Ranking di kelas (1 = tertinggi)
    total_participants: int
    percentile: float                         # Persentil dalam kelas
    above_average: bool
    score_distribution: List[Dict[str, Any]]  # Distribusi nilai kelas

class QuestionDifficultyAnalysis(BaseModel):
    """Analisis tingkat kesulitan soal berdasarkan performa kelas"""
    question_id: PyObjectId
    intended_difficulty: str                  # Difficulty yang ditetapkan
    actual_difficulty: str                    # Difficulty berdasarkan data
    class_accuracy: float                     # Akurasi kelas untuk soal ini
    time_difficulty_score: float             # Skor kesulitan berdasarkan waktu
    is_problematic: bool                      # Apakah soal bermasalah

# ============================================================================
# MAIN ANALYTICS RESPONSE MODEL
# ============================================================================

class ExamSessionAnalytics(BaseModel):
    """Model lengkap untuk analytics exam session"""
    # Metadata
    exam_session_id: PyObjectId
    exam_id: PyObjectId
    student_id: PyObjectId
    exam_title: str
    exam_type: str
    subject_name: str
    teacher_name: str
    class_name: str
    academic_period: str
    
    # Timing Information
    started_at: datetime
    submitted_at: datetime
    duration_allowed: int                     # Durasi yang diizinkan (menit)
    duration_taken: float                     # Durasi actual (menit)
    is_overtime: bool
    
    # Core Analytics
    performance_metrics: PerformanceMetrics
    questions_analytics: List[QuestionAnalytics]
    timeline_events: List[TimelineEvent]
    score_timeline: List[ScoreTimeline]
    violation_analytics: ViolationAnalytics
    class_comparison: ClassComparison
    
    # Advanced Analytics
    question_difficulty_analysis: List[QuestionDifficultyAnalysis]
    answer_pattern_analysis: Dict[str, Any]   # Pola jawaban (streak, clustering, etc.)
    time_allocation_analysis: Dict[str, Any]  # Analisis alokasi waktu
    behavioral_insights: List[str]            # Insight perilaku siswa
    recommendations: List[str]                # Rekomendasi untuk siswa
    
    # Technical Metadata
    client_info: Dict[str, Any]               # Info device, browser, dll
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cache_expires_at: Optional[datetime] = None

# ============================================================================
# REQUEST MODELS
# ============================================================================

class ExamAnalyticsRequest(BaseModel):
    """Request untuk generate analytics"""
    exam_session_id: PyObjectId
    force_regenerate: bool = False            # Force regenerate meskipun sudah ada cache
    include_class_comparison: bool = True
    include_question_analysis: bool = True
    include_behavioral_insights: bool = True

# ============================================================================
# SUMMARY MODELS FOR QUICK ACCESS
# ============================================================================

class ExamAnalyticsSummary(BaseModel):
    """Summary analytics untuk quick access"""
    exam_session_id: PyObjectId
    student_name: str
    exam_title: str
    score: float
    accuracy: float
    completion: float
    rank_in_class: int
    total_violations: int
    risk_level: str
    duration_taken: float
    is_flagged: bool
    generated_at: datetime

class BatchAnalyticsResponse(BaseModel):
    """Response untuk batch analytics (untuk teacher/admin)"""
    exam_id: PyObjectId
    exam_title: str
    total_sessions: int
    analytics_summaries: List[ExamAnalyticsSummary]
    class_statistics: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# SPECIALIZED ANALYTICS MODELS
# ============================================================================

class CheatDetectionReport(BaseModel):
    """Report khusus untuk deteksi kecurangan"""
    exam_session_id: PyObjectId
    student_id: PyObjectId
    overall_fraud_score: float
    risk_assessment: str
    violation_summary: ViolationAnalytics
    suspicious_patterns: List[Dict[str, Any]]
    recommended_actions: List[str]
    requires_manual_review: bool
    confidence_level: float

class LearningInsights(BaseModel):
    """Insights pembelajaran untuk siswa"""
    strengths: List[str]                      # Area yang dikuasai dengan baik
    weaknesses: List[str]                     # Area yang perlu diperbaiki
    study_recommendations: List[str]          # Rekomendasi belajar
    time_management_tips: List[str]           # Tips manajemen waktu
    difficulty_progression: Dict[str, float]  # Performa berdasarkan tingkat kesulitan
    question_type_mastery: Dict[str, float]   # Penguasaan berdasarkan tipe soal
