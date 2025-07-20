# ==============================================================================
# File: app/api/v1/routes/question_sets.py
# Deskripsi: Endpoint API untuk manajemen Paket Soal.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_sets
from app.schemas.question_set import QuestionSetCreate, QuestionSetPublic

router = APIRouter()

@router.post("/", response_model=QuestionSetPublic, status_code=status.HTTP_201_CREATED)
async def create_new_question_set(
    qset_in: QuestionSetCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher) # Koordinator adalah guru
):
    """Membuat paket soal baru. Hanya untuk guru (diasumsikan koordinator)."""
    # (Di sini kita bisa menambahkan validasi apakah `created_by_coordinator_id` adalah koordinator sungguhan)
    return await crud_question_sets.create_question_set(db, qset_in)

@router.get("/", response_model=List[QuestionSetPublic])
async def read_question_sets(
    subject_id: str,
    grade_level: int,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """Mengambil paket soal yang tersedia untuk mata pelajaran dan jenjang tertentu."""
    return await crud_question_sets.get_question_sets(db, ObjectId(subject_id), grade_level)
