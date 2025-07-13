# ==============================================================================
# File: app/api/v1/routes/exams.py
# Deskripsi: Endpoint API untuk manajemen Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_exams, crud_teaching_assignments
from app.schemas.exam import ExamCreate, ExamPublic, BulkExamCreate, ExamQuestionUpdate
from app.schemas.exam_session import ExamSessionPublic

router = APIRouter()

@router.post("/bulk-create", status_code=status.HTTP_201_CREATED)
async def create_bulk_exams(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    bulk_exam_in: BulkExamCreate,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    
    print(bulk_exam_in)
    """
    Membuat ujian resmi secara massal untuk target tertentu.
    Hanya bisa diakses oleh admin.
    """
    criteria = bulk_exam_in.target_criteria
    target_assignments = await crud_teaching_assignments.find_assignments_by_criteria(
        db,
        subject_id=criteria.subject_id,
        grade_level=criteria.grade_level,
        expertise_id=criteria.expertise_id,
        class_id=criteria.class_id
    )

    if not target_assignments:
        raise HTTPException(status_code=404, detail="No matching classes or teachers found for the given criteria.")

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
            proctor_ids=bulk_exam_in.proctor_ids
        )
        await crud_exams.create_exam(db=db, exam=exam_data)
        created_exams_count += 1
    
    return {"message": f"Successfully created {created_exams_count} exam(s)."}


@router.post("/", response_model=ExamPublic, status_code=status.HTTP_201_CREATED)
async def create_quiz_or_daily_test(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    exam_in: ExamCreate,
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Membuat ujian lokal (kuis/ulangan harian). Hanya bisa diakses oleh guru.
    """
    # Validasi: Guru hanya bisa membuat ujian untuk penugasan miliknya
    assignment = await db["teaching_assignments"].find_one({"_id": exam_in.teaching_assignment_id})
    if not assignment or assignment["teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You can only create exams for your own assignments.")

    return await crud_exams.create_exam(db=db, exam=exam_in)


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