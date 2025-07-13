# ==============================================================================
# File: app/api/v1/routes/question_banks.py
# Deskripsi: Endpoint API untuk manajemen Bank Soal.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_banks
from app.schemas.question_bank import QuestionBankCreate, QuestionBankUpdate, QuestionBankPublic

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