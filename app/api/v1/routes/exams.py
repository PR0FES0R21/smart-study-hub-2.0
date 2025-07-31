# ==============================================================================
# File: app/api/v1/routes/exams.py
# Deskripsi: Endpoint API untuk manajemen Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_exams, crud_teaching_assignments, crud_academic_periods
from app.schemas.exam import (
    ExamCreate, ExamPublic, BulkExamCreate, 
    ExamQuestionUpdate, ExamWithDetails,
    PaginatedExamResponse, ExamUpdate
)
from app.schemas.exam_session import ExamSessionPublic
from app.core.websocket import manager

router = APIRouter()

@router.post("/bulk-create", status_code=status.HTTP_201_CREATED)
async def create_bulk_exams(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    bulk_exam_in: BulkExamCreate,
    current_user: dict = Depends(deps.get_current_active_admin),
    active_period: dict = Depends(deps.get_current_academic_period)
):
    
    """
    Membuat ujian resmi secara massal untuk target tertentu.
    Hanya bisa diakses oleh admin.
    """
    criteria = bulk_exam_in.target_criteria
    target_assignments = await crud_teaching_assignments.find_assignments_by_criteria(
        db,
        academic_period_id=active_period["_id"],
        subject_id=criteria.subject_id,
        grade_level=criteria.grade_level,
        expertise_id=criteria.expertise_id,
        class_id=criteria.class_id
        
    )

    if not target_assignments:
        raise HTTPException(status_code=404, detail="No matching classes or teachers found for the given criteria.")
    
    if not active_period:
        raise HTTPException(status_code=400, detail="Gagal membuat ujian karena belum ada semester aktif. Harap atur semester aktif terlebih dahulu.")
    
    created_exams_count = 0
    for assignment in target_assignments:
        exam_data = ExamCreate(
            title=bulk_exam_in.title,
            exam_type=bulk_exam_in.exam_type,
            duration_minutes=bulk_exam_in.duration_minutes,
            availability_start_time=bulk_exam_in.availability_start_time,
            availability_end_time=bulk_exam_in.availability_end_time,
            settings=bulk_exam_in.settings,
            teaching_assignment_id=assignment["_id"],
            proctor_ids=bulk_exam_in.proctor_ids,
            academic_period_id=active_period["_id"]
        )
        await crud_exams.create_exam(db=db, exam=exam_data)
        created_exams_count += 1
    
    return {"message": f"Successfully created {created_exams_count} exam(s)."}


@router.post("/", response_model=ExamPublic, status_code=status.HTTP_201_CREATED)
async def create_quiz_or_daily_test(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    exam_in: ExamCreate,
    current_user: dict = Depends(deps.get_current_active_teacher),
    active_period: dict = Depends(deps.get_current_academic_period)
):
    
    """
    Membuat ujian lokal (kuis/ulangan harian). Hanya bisa diakses oleh guru.
    """
    # Validasi: Guru hanya bisa membuat ujian untuk penugasan miliknya
    assignment = await db["teaching_assignments"].find_one({"_id": exam_in.teaching_assignment_id})
    if not assignment or assignment["teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You can only create exams for your own assignments.")

    exam_data_with_period = exam_in.model_copy(update={"academic_period_id": ObjectId(active_period["_id"])})
    return await crud_exams.create_exam(db=db, exam=exam_data_with_period)

@router.get("/", response_model=PaginatedExamResponse)
async def read_all_exams(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user),
    active_period: dict = Depends(deps.get_current_academic_period),
    academic_period_id: Optional[str] = Query(None),
    exam_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Mengambil daftar ujian dengan filter dinamis, paginasi, dan pencarian.
    """
    filters = {}
    skip = (page - 1) * limit

    # 1. Tentukan periode akademik
    # Jika tidak ada filter, gunakan periode aktif sebagai default
    target_period_id = academic_period_id or str(active_period["_id"])
    if target_period_id != 'all':
        filters["academic_period_id"] = ObjectId(target_period_id)

    # 2. Terapkan filter berdasarkan peran pengguna
    if "admin" in current_user["roles"]:
        default_exam_type = 'official'
        if exam_type and exam_type != 'all':
            filters["exam_type"] = {"$in": ["official_uts", "official_uas"]} if exam_type == 'official' else exam_type
        elif not exam_type:
            filters["exam_type"] = {"$in": ["official_uts", "official_uas"]}
        
    elif "teacher" in current_user["roles"]:
        filters["$or"] = [
            {"teaching_assignment_details.teacher_id": current_user["_id"]},
            {"proctor_ids": current_user["_id"]}
        ]
        if exam_type and exam_type != 'all':
            filters["exam_type"] = {"$in": ["official_uts", "official_uas"]} if exam_type == 'official' else exam_type
    
    result = await crud_exams.get_all_exams_with_details(
        db=db, filters=filters, skip=skip, limit=limit, search=search
    )
    
    total_items = result["total_items"]
    total_pages = (total_items + limit - 1) // limit

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": result["data"]
    }


@router.put("/{exam_id}/questions", response_model=ExamPublic)
async def add_questions_to_exam_route(
    exam_id: str,
    questions_in: ExamQuestionUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menambahkan soal ke dalam ujian yang sudah ada.
    Hanya bisa dilakukan oleh guru yang ditugaskan untuk ujian tersebut.
    """
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Validasi kepemilikan
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    if not assignment or assignment["teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You are not authorized to modify this exam.")

    # (Opsional: validasi apakah semua question_id yang dikirim benar-benar milik guru ini)

    updated_exam = await crud_exams.add_questions_to_exam(db, exam_id=exam["_id"], questions_update=questions_in)
    return updated_exam


# --- DITAMBAHKAN ---
@router.post("/{exam_id}/start", response_model=ExamSessionPublic)
async def start_exam(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user) # Siswa yang login
):
    """
    Memulai sesi ujian untuk siswa yang sedang login.
    Membuat dokumen exam_session baru dengan peta acak.
    """
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # (Di sini kita akan menambahkan validasi apakah siswa ini berhak mengerjakan ujian ini)
    
    student_id = current_user["_id"]
    session = await crud_exams.start_exam_session(db=db, exam=exam, student_id=student_id)
    return session

@router.put("/{exam_id}", response_model=ExamPublic)
async def update_existing_exam(
    exam_id: str,
    exam_in: ExamUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Memperbarui detail ujian.
    Hanya bisa dilakukan oleh admin atau guru yang ditugaskan.
    """
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Otorisasi: Cek apakah user adalah admin atau guru yang bersangkutan
    is_admin = "admin" in current_user.get("roles", [])
    
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    is_assigned_teacher = assignment and assignment["teacher_id"] == current_user["_id"]

    if not is_admin and not is_assigned_teacher:
        raise HTTPException(status_code=403, detail="Not authorized to modify this exam")

    # Validasi tambahan: Cek apakah guru mencoba mengubah tipe ujian official_uts atau official_uas menjadi tipe lain
    if not is_admin and exam["type"] in ["official_uts", "official_uas"] and exam_in.type != exam["type"]:
        raise HTTPException(status_code=403, detail="Tidak dapat mengubah tipe ujian official_uts atau official_uas menjadi tipe lain")

    updated_exam = await crud_exams.update_exam(db, exam_id=exam_id, exam_update=exam_in)
    return updated_exam

@router.post("/{exam_id}/start-manually", response_model=ExamPublic)
async def start_exam_manually(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user) # Pengawas bisa guru atau admin
):
    """
    Memulai ujian secara manual. Hanya bisa dilakukan oleh pengawas yang ditugaskan.
    Akan mengirim trigger WebSocket ke semua siswa di ruangan ujian.
    """
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Otorisasi: Cek apakah pengguna adalah pengawas untuk ujian ini
    proctor_ids_as_str = [str(p_id) for p_id in exam.get("proctor_ids", [])]
    if str(current_user["_id"]) not in proctor_ids_as_str:
        raise HTTPException(status_code=403, detail="You are not an authorized proctor for this exam.")

    # Ubah status ujian
    updated_exam = await crud_exams.set_exam_status(db, exam_id=exam_id, status="ongoing")
    
    # Kirim trigger WebSocket ke siswa di ruangan ini
    # await manager.broadcast_to_students(exam_id, {"type": "EXAM_STARTED", "exam_id": exam_id})
    
    return updated_exam

@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_exam(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Menghapus ujian. Hanya bisa dilakukan oleh admin atau guru yang ditugaskan.
    """
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    is_admin = "admin" in current_user.get("roles", [])
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    is_assigned_teacher = assignment and assignment["teacher_id"] == current_user["_id"]

    if not is_admin and not is_assigned_teacher:
        raise HTTPException(status_code=403, detail="Not authorized to delete this exam")

    deleted = await crud_exams.delete_exam_and_sessions(db, exam_id=exam_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Exam not found during deletion")
    return

@router.get("/{exam_id}/details", response_model=ExamWithDetails)
async def read_exam_details(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil detail lengkap sebuah ujian, TANPA daftar soalnya.
    Hanya untuk admin.
    """
    exam_details = await crud_exams.get_exam_details_by_id(db, exam_id=exam_id)
    if not exam_details:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam_details


# --- TAMBAHKAN DI ROUTES EXAMS ---
@router.get("/teacher", response_model=PaginatedExamResponse)
async def get_teacher_exams(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period),
    academic_period_id: Optional[str] = Query(None),
    class_id: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(20, le=100)
):
    """Endpoint khusus guru untuk melihat ujian yang terkait dengan dia."""
    current_period_id = academic_period_id if academic_period_id else current_period["_id"]

    result = await crud_exams.get_exams_by_teacher(
        db=db,
        teacher_id=str(current_user["_id"]),
        academic_period_id=current_period_id,
        class_id=class_id,
        skip=skip,
        limit=limit
    )
    
    total_items = result["total_items"]
    total_pages = (total_items + limit - 1) // limit
    
    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": (skip // limit) + 1,
        "limit": limit,
        "data": result["data"]
    }

@router.get("/student", response_model=PaginatedExamResponse)
async def get_student_exams(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    academic_period_id: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(20, le=100)
):
    """Endpoint khusus siswa untuk melihat ujian yang terkait dengan kelasnya."""
    student_profile = await db["profiles"].find_one({"user_id": current_user["_id"]})
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    result = await crud_exams.get_exams_by_student(
        db=db,
        student_profile=student_profile,
        academic_period_id=academic_period_id,
        skip=skip,
        limit=limit
    )
    
    total_items = result["total_items"]
    total_pages = (total_items + limit - 1) // limit
    
    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": (skip // limit) + 1,
        "limit": limit,
        "data": result["data"]
    }