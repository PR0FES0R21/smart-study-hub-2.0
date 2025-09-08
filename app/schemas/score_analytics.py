# ==============================================================================
# File: app/schemas/score_analytics.py
# Deskripsi: Skema Pydantic khusus untuk Analitik Nilai (Admin/Teacher/Student)
# --- DITAMBAHKAN ---
# ==============================================================================
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from .base import PyObjectId

# Duplikasi dihapus - menggunakan versi yang lebih lengkap di bawah

# ==============================================================================
# File: app/schemas/score_analytics.py
# Deskripsi: Skema Pydantic untuk analitik nilai (Admin, Teacher, Student).
# --- MODUL BARU ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from .base import PyObjectId


# ============================================================================
# BASE MODELS
# ============================================================================
class ScoreDistribution(BaseModel):
    """Distribusi nilai berdasarkan rentang"""
    range: str              # "0-20", "21-40", "41-60", "61-80", "81-100"
    count: int
    percentage: float

class ExamStatistics(BaseModel):
    """Statistik lengkap untuk satu ujian"""
    exam_id: PyObjectId
    exam_title: str
    exam_type: str          # "official_uts", "official_uas", etc.
    subject_name: str
    class_name: str
    teacher_name: str
    total_participants: int
    average_score: float
    highest_score: float
    lowest_score: float
    score_distribution: List[ScoreDistribution]
    exam_date: datetime
    completion_rate: float  # Persentase siswa yang mengerjakan vs total siswa kelas

class QuestionAnalytics(BaseModel):
    """Analitik per soal dalam ujian"""
    question_id: PyObjectId
    question_text: str
    question_type: str
    difficulty: str
    total_answers: int
    correct_answers: int
    accuracy_rate: float
    average_time_spent: Optional[float] = None  # Jika ada data waktu


# ============================================================================
# ADMIN ANALYTICS MODELS
# ============================================================================
class AdminGlobalStats(BaseModel):
    """Statistik global untuk admin"""
    total_exams_conducted: int
    total_students_participated: int
    school_wide_average: float
    total_questions_answered: int
    active_teachers: int
    active_classes: int

class AdminGradePerformance(BaseModel):
    """Performa per tingkat kelas"""
    grade_level: int        # 10, 11, 12
    total_students: int
    average_score: float
    total_exams: int
    best_subject: str
    worst_subject: str
    improvement_trend: str  # "improving", "declining", "stable"

class AdminMajorPerformance(BaseModel):
    """Performa per jurusan"""
    major_id: PyObjectId
    major_name: str
    major_abbreviation: str
    total_students: int
    average_score: float
    grade_breakdown: Dict[str, float]  # {"10": 75.5, "11": 80.2, "12": 78.9}
    strongest_subject: str
    weakest_subject: str

class AdminSubjectRanking(BaseModel):
    """Ranking mata pelajaran berdasarkan performa"""
    subject_id: PyObjectId
    subject_name: str
    school_average: float
    total_exams: int
    total_participants: int
    difficulty_rating: str  # "Easy", "Medium", "Hard"
    rank: int              # 1 = terbaik

class AdminScoreTrend(BaseModel):
    """Trend nilai dari waktu ke waktu"""
    period: str            # "2024-01", "2024-02", etc.
    average_score: float
    total_exams: int
    total_participants: int

class AdminDashboard(BaseModel):
    """Dashboard lengkap untuk admin"""
    global_stats: AdminGlobalStats
    recent_exams: List[ExamStatistics]
    grade_performances: List[AdminGradePerformance]
    major_performances: List[AdminMajorPerformance]
    subject_rankings: List[AdminSubjectRanking]
    score_trends: List[AdminScoreTrend]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# TEACHER ANALYTICS MODELS
# ============================================================================
class TeacherClassStats(BaseModel):
    """Statistik kelas yang diajar guru"""
    class_id: PyObjectId
    class_name: str         # "12 TKRO 2"
    subject_name: str
    total_students: int
    average_score: float
    highest_score: float
    lowest_score: float
    completion_rate: Optional[float] = 0.0  # Persentase siswa yang sudah ujian
    needs_attention_count: int  # Jumlah siswa yang perlu perhatian

class TeacherStudentPerformance(BaseModel):
    """Performa individual siswa untuk guru"""
    student_id: PyObjectId
    student_name: str
    class_name: str
    total_exams_taken: int
    average_score: float
    last_exam_score: Optional[float]
    trend: str              # "improving", "declining", "stable"
    needs_attention: bool   # True jika performa di bawah threshold
    subject_specific_average: float  # Rata-rata untuk mata pelajaran guru ini

class TeacherExamAnalysis(BaseModel):
    """Analisis mendalam untuk satu ujian"""
    exam_id: PyObjectId
    exam_title: str
    class_name: str
    participants: int
    average_score: float
    question_analytics: List[QuestionAnalytics]
    difficult_questions: List[str]  # Daftar soal yang banyak salah
    top_performers: List[str]       # 3 siswa terbaik
    low_performers: List[str]       # Siswa yang perlu bantuan

class TeacherSubjectSummary(BaseModel):
    """Ringkasan per mata pelajaran untuk guru"""
    subject_id: PyObjectId
    subject_name: str
    total_classes: int
    total_students: int
    overall_average: float
    best_class: str
    challenging_class: str

class TeacherDashboard(BaseModel):
    """Dashboard lengkap untuk guru"""
    teacher_id: PyObjectId
    teacher_name: str
    subject_summaries: List[TeacherSubjectSummary]
    class_statistics: List[TeacherClassStats]
    recent_exam_analyses: List[TeacherExamAnalysis]
    students_need_attention: List[TeacherStudentPerformance]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# STUDENT ANALYTICS MODELS
# ============================================================================
class StudentSubjectPerformance(BaseModel):
    """Performa siswa per mata pelajaran"""
    subject_id: PyObjectId
    subject_name: str
    teacher_name: str
    exams_taken: int
    average_score: float
    highest_score: float
    lowest_score: float
    last_exam_score: Optional[float]
    class_average: float    # Rata-rata kelas untuk perbandingan
    improvement_trend: str  # "improving", "declining", "stable"

class StudentExamHistory(BaseModel):
    """Riwayat ujian siswa"""
    exam_id: PyObjectId
    exam_title: str
    subject_name: str
    teacher_name: str
    score: float
    exam_date: datetime
    exam_type: str
    class_average: float
    ranking_in_class: int
    total_classmates: int
    time_spent: Optional[int] = None  # Durasi dalam menit

class StudentClassComparison(BaseModel):
    """Perbandingan siswa dengan teman sekelas"""
    student_average: float
    class_average: float
    student_ranking: int
    total_classmates: int
    percentile: float       # Persentil dalam kelas
    subjects_above_average: List[str]
    subjects_below_average: List[str]

class StudentStrengthWeakness(BaseModel):
    """Analisis kekuatan dan kelemahan siswa"""
    strongest_subjects: List[str]
    weakest_subjects: List[str]
    most_improved_subject: Optional[str]
    needs_focus_subjects: List[str]
    consistency_rating: str  # "Very Consistent", "Consistent", "Inconsistent"

class StudentGoalTracking(BaseModel):
    """Tracking target siswa"""
    target_average: Optional[float]
    current_average: float
    progress_percentage: float
    subjects_on_track: List[str]
    subjects_behind: List[str]
    estimated_completion: Optional[str]

class StudentPersonalDashboard(BaseModel):
    """Dashboard personal untuk siswa"""
    student_id: PyObjectId
    student_name: str
    class_name: str
    academic_period: str
    overall_statistics: Dict[str, Any]
    subject_performances: List[StudentSubjectPerformance]
    exam_history: List[StudentExamHistory]
    class_comparison: StudentClassComparison
    strength_weakness: StudentStrengthWeakness
    goal_tracking: Optional[StudentGoalTracking]
    improvement_suggestions: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class StudentExamAnalytics(BaseModel):
    """Analitik ujian per exam untuk siswa (dengan data kelas)"""
    exam_id: PyObjectId
    exam_title: str
    subject_name: str
    exam_type: str
    exam_date: datetime
    class_average: float
    class_highest: float
    class_lowest: float
    student_score: Optional[float] = None  # Bisa null jika siswa tidak ikut ujian
    student_percentile: Optional[float] = None  # Posisi siswa dalam persentil kelas
    total_participants: int
    score_distribution: List[ScoreDistribution]

class StudentClassTrendData(BaseModel):
    """Data trend performa siswa vs kelas"""
    exam_title: str
    class_average: float
    student_score: Optional[float] = None  # Bisa None jika siswa tidak ikut ujian
    exam_date: datetime

class StudentClassExamAnalytics(BaseModel):
    """Analitik ujian global kelas untuk siswa (untuk grafik)"""
    exam_analytics: List[StudentExamAnalytics]
    trend_data: List[StudentClassTrendData]
    overall_stats: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# EXPORT & REPORTING MODELS
# ============================================================================
class ExportRequest(BaseModel):
    """Request untuk export data"""
    export_type: str        # "excel", "pdf"
    data_scope: str         # "admin_global", "teacher_class", "student_personal"
    filters: Dict[str, Any] = {}
    include_charts: bool = True

class ReportMetadata(BaseModel):
    """Metadata untuk laporan yang di-generate"""
    report_id: str
    report_type: str
    generated_by: PyObjectId
    generated_at: datetime
    file_path: str
    file_size: int
    expiry_date: datetime


# ============================================================================
# FILTER & SEARCH MODELS
# ============================================================================
class AnalyticsFilters(BaseModel):
    """Filter untuk query analytics"""
    academic_period_id: Optional[str] = None
    grade_level: Optional[int] = None
    major_id: Optional[str] = None
    class_id: Optional[str] = None
    subject_id: Optional[str] = None
    teacher_id: Optional[str] = None
    student_id: Optional[str] = None
    exam_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None

class PaginatedAnalyticsResponse(BaseModel):
    """Response dengan pagination"""
    data: List[Any]
    total_count: int
    page: int
    limit: int
    has_next: bool
    has_previous: bool


# ============================================================================
# COMPARISON & BENCHMARK MODELS
# ============================================================================
class PeriodComparison(BaseModel):
    """Perbandingan antar periode akademik"""
    current_period: str
    previous_period: str
    current_average: float
    previous_average: float
    improvement_percentage: float
    trend: str  # "improved", "declined", "stable"

class BenchmarkData(BaseModel):
    """Data benchmark untuk perbandingan"""
    category: str           # "grade", "major", "school"
    current_value: float
    benchmark_value: float
    performance_level: str  # "above", "at", "below"
    percentile_rank: float


# ============================================================================
# NEW STUDENT INDIVIDUAL STATISTICS MODELS
# ============================================================================
class StudentIndividualStatistics(BaseModel):
    """Statistik individu siswa"""
    overall_average_student: float
    best_score_student: float
    latest_score_student: float
    participant_rate: float
    trend_scores_student: List[Dict[str, Any]]  # [{"exam_date": datetime, "score": float}]
    score_distribution_student: List[ScoreDistribution]

class StudentClassStatistics(BaseModel):
    """Statistik komparatif kelas"""
    overall_average_class: float
    class_highest: float
    class_lowest: float
    trend_scores_class: List[Dict[str, Any]]  # [{"exam_date": datetime, "average_score": float}]
    score_distribution_class: List[ScoreDistribution]

class CombinedStudentStatistics(BaseModel):
    """Gabungan statistik individu dan kelas untuk endpoint baru"""
    student_statistics: StudentIndividualStatistics
    class_statistics: StudentClassStatistics

