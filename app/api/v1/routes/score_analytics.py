# ==============================================================================
# File: app/api/v1/routes/score_analytics.py
# Deskripsi: Endpoint API untuk Analitik Nilai (Admin/Teacher/Student)
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any
import logging

from app.api.v1 import deps
from app.crud.crud_score_analytics import (
    get_admin_dashboard,
    get_teacher_dashboard,
    get_student_dashboard
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/admin/dashboard")
async def admin_dashboard(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
) -> Dict[str, Any]:
    return await get_admin_dashboard(db, academic_period_id=str(current_period["_id"]))

@router.get("/student/dashboard")
async def student_dashboard(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period)
) -> Dict[str, Any]:
    return await get_student_dashboard(db, student_id=str(current_user["_id"]), academic_period_id=str(current_period["_id"]))

# ==============================================================================
# File: app/api/v1/routes/score_analytics.py
# Deskripsi: API endpoints untuk analitik nilai (Admin, Teacher, Student).
# --- MODUL BARU ---
# ==============================================================================
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Optional, Any
from datetime import datetime
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_score_analytics
from app.schemas.score_analytics import (
    # Admin schemas
    AdminDashboard, AdminGlobalStats, AdminGradePerformance, 
    AdminMajorPerformance, AdminSubjectRanking, AdminScoreTrend,
    
    # Teacher schemas  
    TeacherDashboard, TeacherClassStats, TeacherStudentPerformance,
    TeacherExamAnalysis, TeacherSubjectSummary,
    
    # Student schemas
    StudentPersonalDashboard, StudentSubjectPerformance, 
    StudentExamHistory, StudentClassComparison, StudentStrengthWeakness,
    StudentClassExamAnalytics, StudentIndividualStatistics,
    StudentClassStatistics, CombinedStudentStatistics,
    
    # Common schemas
    ExamStatistics, ScoreDistribution, AnalyticsFilters,
    PaginatedAnalyticsResponse, ExportRequest
)


router = APIRouter()


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================
@router.get("/admin/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan dashboard lengkap analitik nilai untuk admin.
    Menampilkan statistik global, performa per grade/jurusan, ranking mata pelajaran, dan trend.
    """
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_admin_dashboard(db, academic_period_id)

@router.get("/admin/global-stats", response_model=AdminGlobalStats)
async def get_admin_global_statistics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan statistik global sekolah untuk admin.
    """
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_admin_global_statistics(db, academic_period_id)

@router.get("/admin/grade-performances", response_model=List[AdminGradePerformance])
async def get_admin_grade_performances(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan analisis performa per tingkat kelas (10, 11, 12).
    """
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_admin_grade_performances(db, academic_period_id)

@router.get("/admin/major-performances", response_model=List[AdminMajorPerformance])
async def get_admin_major_performances(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan analisis performa per jurusan/program keahlian.
    """
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_admin_major_performances(db, academic_period_id)

@router.get("/admin/subject-rankings", response_model=List[AdminSubjectRanking])
async def get_admin_subject_rankings(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan ranking mata pelajaran berdasarkan rata-rata nilai.
    """
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_admin_subject_rankings(db, academic_period_id)

@router.get("/admin/score-trends", response_model=List[AdminScoreTrend])
async def get_admin_score_trends(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period),
    months: int = Query(6, ge=1, le=24, description="Jumlah bulan untuk analisis trend")
):
    """
    Mendapatkan trend nilai dari waktu ke waktu.
    """
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_admin_score_trends(db, academic_period_id, months)

@router.get("/admin/exam-statistics/{exam_id}", response_model=ExamStatistics)
async def get_exam_statistics(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mendapatkan statistik detail untuk satu ujian spesifik.
    """
    # TODO: Implement get_exam_statistics function
    raise HTTPException(status_code=501, detail="Endpoint ini akan segera tersedia")

@router.post("/admin/export-report")
async def export_admin_report(
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Export laporan analitik admin ke Excel atau PDF.
    """
    # TODO: Implement export functionality
    raise HTTPException(status_code=501, detail="Fitur export akan segera tersedia")


# ============================================================================
# TEACHER ENDPOINTS
# ============================================================================
@router.get("/teacher/dashboard", response_model=TeacherDashboard)
async def get_teacher_dashboard(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan dashboard lengkap analitik nilai untuk guru.
    Menampilkan statistik kelas yang diajar, performa siswa, dan analisis ujian.
    """
    
    teacher_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    data = await crud_score_analytics.get_teacher_dashboard(db, teacher_id, academic_period_id)
    return TeacherDashboard.model_validate(data)

@router.get("/teacher/class-statistics", response_model=List[TeacherClassStats])
async def get_teacher_class_statistics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period),
    class_id: Optional[str] = Query(None, description="Filter berdasarkan kelas tertentu"),
    subject_id: Optional[str] = Query(None, description="Filter berdasarkan mata pelajaran")
):
    """
    Mendapatkan statistik kelas yang diajar oleh guru.
    """
    teacher_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    class_stats = await crud_score_analytics.get_teacher_class_statistics(db, teacher_id, academic_period_id)
    
    # Apply filters if provided
    if class_id:
        class_stats = [stat for stat in class_stats if str(stat.get("class_id")) == class_id]
    
    # TODO: Add subject_id filter support
    
    return class_stats

@router.get("/teacher/student-performances", response_model=List[TeacherStudentPerformance])
async def get_teacher_student_performances(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period),
    class_id: Optional[str] = Query(None, description="Filter berdasarkan kelas"),
    needs_attention_only: bool = Query(False, description="Hanya siswa yang perlu perhatian"),
    page: int = Query(1, ge=1, description="Halaman"),
    limit: int = Query(50, ge=1, le=200, description="Jumlah data per halaman")
):
    """
    Mendapatkan daftar performa individual siswa untuk guru.
    """
    teacher_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    student_performances = await crud_score_analytics.get_teacher_student_performances(db, teacher_id, academic_period_id)
    
    # Apply filters
    if class_id:
        # TODO: Add class_id filter support in the CRUD function
        pass
    
    if needs_attention_only:
        student_performances = [sp for sp in student_performances if sp.get("needs_attention", False)]
    
    # Apply pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_data = student_performances[start_idx:end_idx]
    
    return paginated_data

@router.get("/teacher/exam-analysis/{exam_id}", response_model=TeacherExamAnalysis)
async def get_teacher_exam_analysis(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mendapatkan analisis mendalam untuk satu ujian yang dibuat guru.
    """
    # Verify that the exam belongs to this teacher
    exam = await db["exams"].find_one({"_id": exam_id})
    if not exam:
        raise HTTPException(status_code=404, detail="Ujian tidak ditemukan")
    
    # Check teaching assignment
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    if not assignment or str(assignment["teacher_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke ujian ini")
    
    return await crud_score_analytics.get_teacher_exam_analysis(db, exam_id)

@router.get("/teacher/students-attention", response_model=List[TeacherStudentPerformance])
async def get_students_needing_attention(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period),
    threshold: float = Query(60.0, ge=0, le=100, description="Batas nilai untuk perhatian khusus")
):
    """
    Mendapatkan daftar siswa yang perlu perhatian khusus berdasarkan performa.
    """
    teacher_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    all_students = await crud_score_analytics.get_teacher_student_performances(db, teacher_id, academic_period_id)
    students_need_attention = [s for s in all_students if s.get("average_score", 100) < threshold]
    
    return students_need_attention

@router.post("/teacher/export-class-report/{class_id}")
async def export_teacher_class_report(
    class_id: str,
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Export laporan kelas untuk guru ke Excel atau PDF.
    """
    # TODO: Implement export functionality
    raise HTTPException(status_code=501, detail="Fitur export akan segera tersedia")


# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================
@router.get("/student/dashboard", response_model=StudentPersonalDashboard)
async def get_student_dashboard(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan dashboard personal analitik nilai untuk siswa.
    """
    # Verify user is a student
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_student_dashboard(db, student_id, academic_period_id)

@router.get("/student/subject-performances", response_model=List[StudentSubjectPerformance])
async def get_student_subject_performances(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period),
    subject_id: Optional[str] = Query(None, description="Filter berdasarkan mata pelajaran tertentu")
):
    """
    Mendapatkan performa siswa per mata pelajaran.
    """
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    subject_performances = await crud_score_analytics.get_student_subject_performances(db, student_id, academic_period_id)
    
    if subject_id:
        subject_performances = [sp for sp in subject_performances if str(sp.get("subject_id")) == subject_id]
    
    return subject_performances

@router.get("/student/exam-history", response_model=List[StudentExamHistory])
async def get_student_exam_history(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period),
    subject_id: Optional[str] = Query(None, description="Filter berdasarkan mata pelajaran"),
    exam_type: Optional[str] = Query(None, description="Filter berdasarkan jenis ujian"),
    page: int = Query(1, ge=1, description="Halaman"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah data per halaman")
):
    """
    Mendapatkan riwayat ujian siswa dengan pagination.
    """
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    exam_history = await crud_score_analytics.get_student_exam_history(db, student_id, academic_period_id)
    
    # Apply filters
    if subject_id:
        # TODO: Add subject filtering support
        pass
    
    if exam_type:
        exam_history = [eh for eh in exam_history if eh.get("exam_type") == exam_type]
    
    # Apply pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_data = exam_history[start_idx:end_idx]
    
    return paginated_data

@router.get("/student/class-comparison", response_model=StudentClassComparison)
async def get_student_class_comparison(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan perbandingan performa siswa dengan teman sekelas.
    """
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    return await crud_score_analytics.get_student_class_comparison(db, student_id, academic_period_id)

@router.get("/student/improvement-suggestions", response_model=List[str])
async def get_student_improvement_suggestions(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Mendapatkan saran perbaikan personal untuk siswa.
    """
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    return await crud_score_analytics.generate_improvement_suggestions(db, student_id)

@router.get("/student/strength-weakness", response_model=StudentStrengthWeakness)
async def get_student_strength_weakness(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan analisis kekuatan dan kelemahan siswa.
    """
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    # Get subject performances and analyze
    subject_performances = await crud_score_analytics.get_student_subject_performances(db, student_id, academic_period_id)
    
    if not subject_performances:
        return {
            "strongest_subjects": [],
            "weakest_subjects": [],
            "most_improved_subject": None,
            "needs_focus_subjects": [],
            "consistency_rating": "No Data"
        }
    
    sorted_subjects = sorted(subject_performances, key=lambda x: x["average_score"], reverse=True)
    
    return {
        "strongest_subjects": [s["subject_name"] for s in sorted_subjects[:3]],
        "weakest_subjects": [s["subject_name"] for s in sorted_subjects[-3:]],
        "most_improved_subject": None,  # TODO: Calculate based on trend
        "needs_focus_subjects": [s["subject_name"] for s in subject_performances if s["average_score"] < 60],
        "consistency_rating": "Consistent"  # TODO: Calculate actual consistency
    }

@router.get("/student/class-exam-analytics", response_model=StudentClassExamAnalytics)
async def get_student_class_exam_analytics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan analitik ujian global kelas untuk siswa (untuk grafik).
    Menampilkan distribusi nilai, trend performa, dan posisi siswa dalam kelas.
    """
    if "student" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Akses hanya untuk siswa")
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    return await crud_score_analytics.get_student_class_exam_analytics(db, student_id, academic_period_id)

@router.get("/student/my-statistics", response_model=CombinedStudentStatistics)
async def get_my_student_statistics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan statistik lengkap siswa yang sedang login (individu + komparatif kelas).
    Hanya bisa diakses oleh siswa itu sendiri.
    
    Statistik siswa (individual):
    - overall_average_student: rata-rata nilai dari semua ujian yang sudah dikerjakan siswa
    - best_score_student: nilai tertinggi siswa
    - latest_score_student: nilai ujian terakhir siswa
    - participant_rate: (jumlah ujian yang sudah dikerjakan siswa / total ujian kelas) * 100
    - trend_scores_student: 10 nilai ujian terakhir siswa, format array [{exam_date, score}]
    - score_distribution_student: distribusi nilai siswa (range 0–20, 21–40, dst.)
    
    Statistik kelas (comparative):
    - overall_average_class: rata-rata nilai semua siswa dalam kelas
    - class_highest: nilai tertinggi dalam kelas
    - class_lowest: nilai terendah dalam kelas
    - trend_scores_class: 10 data nilai ujian terakhir kelas (rata-rata per ujian), format array [{exam_date, average_score}]
    - score_distribution_class: distribusi nilai seluruh siswa dalam kelas (range 0–20, 21–40, dst.)
    """
    
    # Verify user is a student
    if "student" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=403, 
            detail="Endpoint ini hanya dapat diakses oleh siswa"
        )
    
    student_id = str(current_user["_id"])
    academic_period_id = str(current_period["_id"])
    
    try:
        # Get combined statistics for the current user
        combined_stats = await crud_score_analytics.get_combined_student_statistics(
            db, student_id, academic_period_id
        )
        
        logger.info(f"Student statistics retrieved successfully for user {student_id}")
        return combined_stats
        
    except Exception as e:
        logger.error(f"Error getting student statistics for user {student_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Terjadi kesalahan saat mengambil statistik siswa"
        )


# ============================================================================
# COMMON/SHARED ENDPOINTS
# ============================================================================
@router.get("/score-distribution", response_model=List[ScoreDistribution])
async def get_score_distribution(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    current_period: dict = Depends(deps.get_current_academic_period),
    exam_id: Optional[str] = Query(None, description="Distribusi untuk ujian tertentu"),
    class_id: Optional[str] = Query(None, description="Distribusi untuk kelas tertentu"),
    subject_id: Optional[str] = Query(None, description="Distribusi untuk mata pelajaran tertentu")
):
    """
    Mendapatkan distribusi nilai berdasarkan filter.
    Accessible for admin, teacher (with scope), and student (own data only).
    """
    academic_period_id = str(current_period["_id"])
    
    # Build filter based on user role and parameters
    filters = {"academic_period_id": academic_period_id}
    
    if exam_id:
        filters["exam_id"] = exam_id
    if class_id:
        filters["class_id"] = class_id  
    if subject_id:
        filters["subject_id"] = subject_id
    
    # Apply role-based restrictions
    if "student" in current_user.get("roles", []):
        # Students can only see their own data
        filters["student_id"] = str(current_user["_id"])
    elif "teacher" in current_user.get("roles", []) and "admin" not in current_user.get("roles", []):
        # Teachers can only see data from their teaching assignments
        # TODO: Implement teacher scope filtering
        pass
    
    # TODO: Implement actual score distribution calculation with filters
    return []

@router.get("/compare-periods")
async def compare_academic_periods(
    period1_id: str = Query(..., description="ID periode akademik pertama"),
    period2_id: str = Query(..., description="ID periode akademik kedua"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Membandingkan performa antara dua periode akademik.
    Hanya untuk admin.
    """
    # TODO: Implement period comparison
    raise HTTPException(status_code=501, detail="Fitur perbandingan periode akan segera tersedia")

@router.post("/refresh-cache")
async def refresh_analytics_cache(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_period: dict = Depends(deps.get_current_academic_period),
    scope: str = Query("all", regex="^(all|admin|teacher|student)$", description="Scope cache yang akan di-refresh")
):
    """
    Refresh cache analytics. Hanya untuk admin.
    """
    academic_period_id = str(current_period["_id"])
    
    # TODO: Implement cache refresh logic
    # background_tasks.add_task(refresh_cache_task, scope, academic_period_id)
    
    return {"message": f"Cache refresh untuk scope '{scope}' telah dijadwalkan"}


# ============================================================================
# HEALTH CHECK & METADATA
# ============================================================================
@router.get("/health")
async def analytics_health_check():
    """
    Health check untuk modul score analytics.
    """
    return {
        "status": "healthy",
        "module": "score_analytics",
        "version": "1.0.0",
        "timestamp": datetime.utcnow(),
        "features": {
            "admin_dashboard": True,
            "teacher_dashboard": True, 
            "student_dashboard": True,
            "export_reports": False,  # TODO: Implement
            "real_time_updates": False  # TODO: Implement
        }
    }

@router.get("/metadata")
async def get_analytics_metadata(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Mendapatkan metadata untuk analytics (daftar filter yang tersedia, dll).
    """
    # Get available academic periods
    periods = await db["academic_periods"].find({}).sort("start_date", -1).to_list(10)
    
    # Get available grades, majors, subjects based on user role
    if "admin" in current_user.get("roles", []):
        grades = await db["classes"].distinct("grade_level")
        majors = await db["expertise_programs"].find({}, {"name": 1, "abbreviation": 1}).to_list(100)
        subjects = await db["subjects"].find({}, {"name": 1}).to_list(100)
    elif "teacher" in current_user.get("roles", []):
        # TODO: Get only grades/majors/subjects that teacher teaches
        grades = []
        majors = []
        subjects = []
    else:
        # Students don't need this metadata
        grades = []
        majors = []
        subjects = []
    
    return {
        "academic_periods": [{"id": str(p["_id"]), "name": f"{p['year']} {p['semester']}"} for p in periods],
        "grade_levels": sorted(grades),
        "majors": [{"id": str(m["_id"]), "name": m["name"], "abbreviation": m["abbreviation"]} for m in majors],
        "subjects": [{"id": str(s["_id"]), "name": s["name"]} for s in subjects],
        "exam_types": ["official_uts", "official_uas", "quiz", "daily_test"],
        "score_ranges": ["0-20", "21-40", "41-60", "61-80", "81-100"]
    }
