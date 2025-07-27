# ==============================================================================
# File: app/api/v1/routes/analytics.py
# Deskripsi: Endpoint API untuk data analitik.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.api.v1 import deps
from app.crud import crud_analytics
from app.schemas.analytics import (
    StudentCountByMajor, StudentGrowthDataPoint,
    BrowserUsageStat, DashboardStats, TopStudentResult,
    StudentPerformanceRosterItem, MajorDistributionByGradeResponse,
    MajorGrowthDataPoint, GenderDistributionStat, CompetencyProfileResponse,
    TeacherDashboardStats
)
from app.core.cache import get_cache
from app.tasks.analytics_tasks import recompute_competency_profile_task


router = APIRouter()

@router.get("/student-count-by-major", response_model=List[StudentCountByMajor])
async def get_student_counts(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil data jumlah siswa per jurusan, dikelompokkan per tingkat kelas.
    Untuk digunakan di diagram batang.
    """
    return await crud_analytics.get_student_count_by_major_and_grade(db=db)

@router.get("/student-growth", response_model=List[StudentGrowthDataPoint])
async def get_student_growth(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    years: int = Query(default=10, ge=1, le=50, description="Jumlah tahun terakhir yang akan ditampilkan (antara 1 dan 50).")
):
    """
    Mengambil data pertumbuhan jumlah siswa berdasarkan tahun masuk (10 tahun terakhir).
    Untuk digunakan di diagram garis.
    """
    return await crud_analytics.get_student_growth_over_years(db=db, years_to_check=years)

@router.get("/browser-usage", response_model=List[BrowserUsageStat])
async def get_browser_usage(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil data statistik penggunaan browser oleh pengguna.
    Untuk digunakan di diagram lingkaran (pie chart).
    """
    return await crud_analytics.get_browser_usage_stats(db=db)

@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_statistics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil data statistik utama untuk dasbor admin.
    Data ini di-cache untuk performa.
    """
    return await crud_analytics.get_dashboard_stats(db=db)

@router.get("/top-students", response_model=List[TopStudentResult])
async def get_top_students(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil daftar 5 siswa dengan nilai tertinggi dari ujian resmi terakhir.
    """
    return await crud_analytics.get_top_students_from_last_official_exam(db=db, limit=5)

@router.get("/student-performance-roster", response_model=List[StudentPerformanceRosterItem])
async def get_student_performance(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil laporan rangkuman performa untuk semua siswa.
    """
    return await crud_analytics.get_student_performance_roster(db=db)

@router.get("/major-distribution", response_model=MajorDistributionByGradeResponse)
async def get_major_distribution(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil data distribusi persentase siswa per jurusan untuk setiap tingkat kelas.
    """
    return await crud_analytics.get_major_distribution_by_grade(db=db)

@router.get("/major-growth", response_model=List[MajorGrowthDataPoint])
async def get_major_growth(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    years: int = Query(default=10, ge=1, le=50, description="Jumlah tahun terakhir yang akan ditampilkan.")
):
    """
    Mengambil data pertumbuhan jumlah siswa per jurusan dari tahun ke tahun.
    """
    return await crud_analytics.get_major_growth_over_years(db=db, years_to_check=years)

@router.get("/gender-distribution", response_model=List[GenderDistributionStat])
async def get_gender_stats(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil data distribusi jumlah dan persentase siswa aktif berdasarkan jenis kelamin.
    """
    return await crud_analytics.get_gender_distribution(db=db)

@router.get("/competency-profile", response_model=CompetencyProfileResponse)
async def get_competency_profile(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    grade_level: Optional[int] = None,
    expertise_id: Optional[str] = None,
    class_id: Optional[str] = None,
    student_id: Optional[str] = None
):
    """
    Mengambil data profil kompetensi siswa.
    Mendukung filter dinamis dan perhitungan di latar belakang.
    """
    filters = {
        "grade_level": grade_level,
        "expertise_id": expertise_id,
        "class_id": class_id,
        "student_id": student_id,
    }
    # Hapus filter yang tidak diisi
    active_filters = {k: v for k, v in filters.items() if v is not None}
    
    cache_key = crud_analytics.generate_cache_key(active_filters)
    cached_data = await get_cache(cache_key)
    
    if cached_data:
        return {"status": "ready", "data": cached_data}
    else:
        # Panggil task dengan filter yang aktif
        recompute_competency_profile_task.delay(active_filters)
        return {"status": "processing", "data": None}
    
@router.get("/teacher/dashboard-stats", response_model=TeacherDashboardStats)
async def get_teacher_dashboard_statistics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil statistik dashboard untuk guru yang sedang login.
    Menampilkan total kelas mengajar, total siswa, total ujian, dan total soal yang dibuat.
    """
    teacher_id = str(current_user["_id"])
    return await crud_analytics.get_teacher_dashboard_stats(db=db, teacher_id=teacher_id)