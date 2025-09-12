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
    PaginatedExamResponse, ExamUpdate, ExamCompleteRequest
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
    Guru hanya bisa membuat ujian non-official melalui endpoint ini.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # VALIDASI: Guru hanya bisa membuat quiz atau daily_test melalui endpoint ini
    if exam_in.exam_type in ["official_uts", "official_uas"]:
        logger.error(f"SECURITY_VIOLATION: Teacher {current_user['_id']} attempted to create official exam type '{exam_in.exam_type}' via teacher endpoint")
        raise HTTPException(status_code=403, detail="Guru hanya dapat membuat ujian dengan tipe 'quiz' atau 'daily_test' melalui endpoint ini. Ujian official dibuat oleh admin.")
    
    # Validasi: Guru hanya bisa membuat ujian untuk penugasan miliknya
    assignment = await db["teaching_assignments"].find_one({"_id": exam_in.teaching_assignment_id})
    if not assignment or assignment["teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You can only create exams for your own assignments.")

    # LOGGING: Track exam creation
    logger.info(f"EXAM_CREATE: Teacher {current_user['_id']} creating exam type '{exam_in.exam_type}' for assignment {exam_in.teaching_assignment_id}")

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
    Guru bisa mengubah quiz↔daily_test tapi tidak bisa mengubah ke/dari official.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Otorisasi: Cek apakah user adalah admin atau guru yang bersangkutan
    is_admin = "admin" in current_user.get("roles", [])
    
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    is_assigned_teacher = assignment and assignment["teacher_id"] == current_user["_id"]

    if not is_admin and not is_assigned_teacher:
        raise HTTPException(status_code=403, detail="Not authorized to modify this exam")

    # VALIDASI UNTUK GURU: Cek perubahan exam_type
    if not is_admin and exam_in.exam_type and exam_in.exam_type != exam["exam_type"]:
        current_exam_type = exam["exam_type"]
        new_exam_type = exam_in.exam_type
        
        # Definisikan tipe official dan non-official
        official_types = ["official_uts", "official_uas"]
        non_official_types = ["quiz", "daily_test"]
        
        # Cek apakah guru mencoba mengubah dari/ke official
        current_is_official = current_exam_type in official_types
        new_is_official = new_exam_type in official_types
        
        if current_is_official or new_is_official:
            # Guru tidak boleh mengubah ujian official ke tipe lain atau sebaliknya
            logger.error(f"SECURITY_VIOLATION: Teacher {current_user['_id']} attempted to change exam_type from '{current_exam_type}' to '{new_exam_type}' for exam {exam_id}")
            raise HTTPException(
                status_code=403,
                detail="Guru tidak dapat mengubah tipe ujian official atau mengubah ujian menjadi official. Hanya admin yang dapat melakukan perubahan tersebut."
            )
        
        # Jika sampai sini, berarti guru mengubah antar non-official (quiz ↔ daily_test)
        logger.info(f"EXAM_TYPE_CHANGE: Teacher {current_user['_id']} changing exam {exam_id} from '{current_exam_type}' to '{new_exam_type}' (both non-official)")

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

@router.post("/{exam_id}/complete", response_model=ExamPublic)
async def complete_exam_manually(
    exam_id: str,
    request: ExamCompleteRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Menyelesaikan ujian secara manual dengan mengubah status menjadi 'completed'.
    
    Hanya bisa dilakukan oleh:
    - Admin (bisa menyelesaikan ujian apapun)
    - Guru yang ditugaskan untuk ujian tersebut
    - Pengawas yang ditugaskan untuk ujian tersebut
    
    Parameter:
    - confirmation: Boolean yang harus true sebagai konfirmasi
    - reason: Alasan opsional mengapa ujian diselesaikan manual
    """
    # Validasi konfirmasi
    if not request.confirmation:
        raise HTTPException(
            status_code=400, 
            detail="Confirmation is required to complete the exam manually"
        )
    
    # Cek apakah ujian ada
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Cek apakah ujian sudah completed
    if exam.get("status") == "completed":
        raise HTTPException(
            status_code=400, 
            detail="Exam is already completed"
        )
    
    # Otorisasi: Cek apakah user memiliki akses
    is_admin = "admin" in current_user.get("roles", [])
    
    # Cek apakah user adalah guru yang ditugaskan
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    is_assigned_teacher = assignment and assignment["teacher_id"] == current_user["_id"]
    
    # Cek apakah user adalah pengawas
    proctor_ids_as_str = [str(p_id) for p_id in exam.get("proctor_ids", [])]
    is_proctor = str(current_user["_id"]) in proctor_ids_as_str
    
    # Jika bukan admin, guru, atau pengawas, maka tidak diizinkan
    if not (is_admin or is_assigned_teacher or is_proctor):
        raise HTTPException(
            status_code=403, 
            detail="You are not authorized to complete this exam. Only admin, assigned teacher, or proctors can complete exams manually."
        )
    
    # Validasi status ujian
    current_status = exam.get("status")
    if current_status in ["pending_questions", "ready"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete exam with status '{current_status}'. Exam must be started (ongoing) first."
        )
    
    # Log aktivitas untuk audit
    import logging
    logger = logging.getLogger(__name__)
    
    user_role = "admin" if is_admin else ("teacher" if is_assigned_teacher else "proctor")
    logger.info(
        f"EXAM_COMPLETE_MANUAL: {user_role.upper()} {current_user['_id']} manually completing exam {exam_id}. "
        f"Previous status: {current_status}. Reason: {request.reason or 'No reason provided'}"
    )
    
    # Menyelesaikan ujian
    completed_exam = await crud_exams.complete_exam_manually(
        db=db,
        exam_id=exam_id,
        completed_by=current_user["_id"],
        reason=request.reason
    )
    
    if not completed_exam:
        raise HTTPException(status_code=500, detail="Failed to complete exam")
    
    # Optional: Kirim notifikasi WebSocket ke siswa yang terkait
    # await manager.broadcast_to_students(exam_id, {
    #     "type": "EXAM_COMPLETED", 
    #     "exam_id": exam_id,
    #     "message": "Ujian telah diselesaikan oleh pengawas"
    # })
    
    return completed_exam

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
    exam_type: Optional[str] = Query(None, description="Filter berdasarkan tipe ujian (quiz, uts, uas, practice, official_uts, official_uas)"),
    search: Optional[str] = Query(None, description="Pencarian berdasarkan judul ujian atau nama mata pelajaran"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Endpoint khusus guru untuk melihat ujian yang terkait dengan dia dengan filter type dan search."""
    current_period_id = academic_period_id if academic_period_id else current_period["_id"]
    skip = (page - 1) * limit

    result = await crud_exams.get_exams_by_teacher(
        db=db,
        teacher_id=str(current_user["_id"]),
        academic_period_id=current_period_id,
        class_id=class_id,
        exam_type=exam_type,
        search=search,
        skip=skip,
        limit=limit
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

@router.get("/student", response_model=PaginatedExamResponse)
async def get_student_exams(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    academic_period_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter by computed status (pending_questions, ready, ongoing, submitted, completed, etc.)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Endpoint khusus siswa untuk melihat ujian yang terkait dengan kelasnya.
    
    PERBAIKAN: Status sekarang mempertimbangkan exam session siswa:
    - Jika siswa sudah memiliki exam session, status akan berdasarkan session tersebut
    - Jika exam session status = "graded", maka status = "completed"
    - Jika exam session status = "ongoing" atau "submitted", gunakan status tersebut
    - Jika tidak ada exam session, gunakan status exam asli
    
    Parameter status: all, pending_questions, ready, ongoing, submitted, completed
    Response akan include field has_session dan session_score untuk frontend
    """
    student_profile = await db["profiles"].find_one({"user_id": current_user["_id"]})
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    skip = (page - 1) * limit
    
    result = await crud_exams.get_exams_by_student(
        db=db,
        student_profile=student_profile,
        academic_period_id=academic_period_id,
        status=status,
        skip=skip,
        limit=limit
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