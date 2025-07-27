# ==============================================================================
# File: app/schemas/analytics.py
# Deskripsi: Skema Pydantic untuk data analitik.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from .base import PyObjectId


class StudentCountByMajor(BaseModel):
    major_name: str
    major_abbreviation: str
    grade_10_count: int = 0
    grade_11_count: int = 0
    grade_12_count: int = 0

class StudentGrowthDataPoint(BaseModel):
    year: int
    student_count: int

class BrowserUsageStat(BaseModel):
    browser_name: str
    count: int
    percentage: float

class DashboardStats(BaseModel):
    total_students: int
    total_teachers: int
    total_classes: int
    total_subjects: int

class TopStudentResult(BaseModel):
    student_name: str
    class_name: str
    major_abbreviation: str
    score: float
    exam_title: str

class StudentPerformanceRosterItem(BaseModel):
    student_id: PyObjectId
    full_name: str
    class_name: str
    major_name: str
    scores: List[float]
    average_score: float

class MajorDistributionItem(BaseModel):
    major_name: str
    major_abbreviation: str
    student_count: int
    percentage: float

class MajorDistributionByGradeResponse(BaseModel):
    grade_10: List[MajorDistributionItem]
    grade_11: List[MajorDistributionItem]
    grade_12: List[MajorDistributionItem]

class MajorGrowthDataPoint(BaseModel):
    year: int
    # Menggunakan Dict untuk menyimpan jumlah siswa per jurusan secara dinamis
    # Contoh: { "TKJ": 50, "TKR": 60, "TBSM": 55 }
    counts: Dict[str, int]

class GenderDistributionStat(BaseModel):
    gender: str
    count: int
    percentage: float

class CompetencyItem(BaseModel):
    subject: str
    average_score: float

class CompetencyProfileGlobal(BaseModel):
    grade_10: List[CompetencyItem]
    grade_11: List[CompetencyItem]
    grade_12: List[CompetencyItem]

class CompetencyProfileFiltered(BaseModel):
    filter_name: str
    filter_value: str
    result: List[CompetencyItem]

class CompetencyProfileResponse(BaseModel):
    status: str # "ready" atau "processing"
    # Data bisa berupa salah satu dari dua skema di atas, atau null
    data: Optional[Dict[str, Any]] = None

class CompetencyProfile(BaseModel):
    grade_10: List[CompetencyItem]
    grade_11: List[CompetencyItem]
    grade_12: List[CompetencyItem]

class TeacherDashboardStats(BaseModel):
    total_classes: int
    total_students: int  
    total_exams: int
    total_questions: int