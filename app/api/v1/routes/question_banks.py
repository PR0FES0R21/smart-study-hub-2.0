# ==============================================================================
# File: app/api/v1/routes/question_banks.py
# Deskripsi: Endpoint API untuk manajemen Bank Soal.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from datetime import datetime

from app.api.v1 import deps
from app.crud import crud_question_banks, crud_coordination_assignments, crud_question_submissions
from app.schemas.question_bank import (
    QuestionBankCreate, QuestionBankUpdate, QuestionBankPublic, 
    QuestionIdsList
)
from app.schemas.question_submission import QuestionSubmissionCreate


router = APIRouter()

@router.post("/", response_model=QuestionBankPublic, status_code=status.HTTP_201_CREATED)
async def create_new_question(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    question_in: QuestionBankCreate,
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Membuat soal baru di bank soal. Hanya bisa diakses oleh guru.
    """
    # Pastikan guru hanya membuat soal atas namanya sendiri
    if question_in.created_by_teacher_id != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Cannot create question for another teacher")
    
    return await crud_question_banks.create_question(db=db, question=question_in)

@router.get("/", response_model=List[QuestionBankPublic])
async def read_my_questions(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil daftar semua soal yang dibuat oleh guru yang sedang login.
    """
    teacher_id = current_user["_id"]
    return await crud_question_banks.get_questions_by_teacher(db=db, teacher_id=teacher_id)

@router.put("/{question_id}", response_model=QuestionBankPublic)
async def update_existing_question(
    question_id: str,
    question_in: QuestionBankUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Memperbarui soal. Guru hanya bisa memperbarui soal miliknya sendiri.
    """
    question = await crud_question_banks.get_question_by_id(db, question_id=question_id)
    if not question or question["created_by_teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Question not found or not owned by user")
    
    return await crud_question_banks.update_question(db=db, question_id=question_id, question_update=question_in)

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_question(
    question_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menghapus soal. Guru hanya bisa menghapus soal miliknya sendiri.
    """
    question = await crud_question_banks.get_question_by_id(db, question_id=question_id)
    if not question or question["created_by_teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Question not found or not owned by user")
        
    await crud_question_banks.delete_question(db=db, question_id=question_id)
    return

@router.post("/by-ids", response_model=List[QuestionBankPublic])
async def read_questions_by_ids(
    ids_in: QuestionIdsList,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user) # Bisa diakses admin atau guru
):
    """
    Mengambil detail beberapa soal berdasarkan daftar ID yang diberikan.
    """
    questions = await crud_question_banks.get_questions_by_ids(db, question_ids=ids_in.ids)
    return questions

@router.get("/", response_model=List[QuestionBankPublic])
async def read_questions(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil daftar soal.
    - Jika user adalah koordinator, ia bisa melihat semua soal yang relevan.
    - Jika tidak, ia hanya melihat soal miliknya sendiri.
    """
    teacher_id = current_user["_id"]
    
    # Cek apakah user adalah koordinator
    coordinations = await crud_coordination_assignments.get_coordinations_by_user(db, teacher_id)
    
    # Kumpulkan semua soal yang bisa diakses
    accessible_questions = {} # Gunakan dict untuk menghindari duplikasi
    
    # 1. Ambil soal milik sendiri
    my_questions = await crud_question_banks.get_questions_by_teacher(db, teacher_id)
    for q in my_questions:
        accessible_questions[q["_id"]] = q

    # 2. Jika dia koordinator, ambil soal lain yang relevan
    for coord in coordinations:
        coord_questions = await crud_question_banks.get_questions_for_coordinator(db, coord["subject_id"], coord["grade_level"])
        for q in coord_questions:
            accessible_questions[q["_id"]] = q
            
    return list(accessible_questions.values())

@router.post("/submit-for-review", status_code=status.HTTP_201_CREATED)
async def submit_questions_for_review(
    submission_in: QuestionSubmissionCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    active_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Guru mengajukan soal-soal dari bank soalnya untuk direview oleh koordinator.
    """
    # Validasi: Pastikan koordinator yang dituju benar-benar ada
    coord_assignment = await db["coordination_assignments"].find_one({"_id": submission_in.coordination_assignment_id})
    if not coord_assignment:
        raise HTTPException(status_code=404, detail="Coordination assignment not found.")

    # Buat dokumen submission untuk setiap soal
    submissions_to_create = []
    for q_id in submission_in.question_ids:
        submissions_to_create.append({
            "question_id": q_id,
            "submitted_by_teacher_id": current_user["_id"],
            "coordination_assignment_id": submission_in.coordination_assignment_id,
            "academic_period_id": active_period["_id"],
            "purpose": submission_in.purpose,
            "status": "submitted",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    await crud_question_submissions.create_submissions(db, submissions_to_create)
    return {"message": f"{len(submissions_to_create)} question(s) submitted for review."}
