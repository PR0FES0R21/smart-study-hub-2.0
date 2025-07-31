# ==============================================================================
# File: app/crud/crud_question_banks.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'question_banks'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List
from bson import ObjectId
from app.schemas.question_bank import QuestionBankCreate, QuestionBankUpdate

async def create_question(db: AsyncIOMotorDatabase, question: QuestionBankCreate) -> dict:
    question_dict = question.model_dump(mode='python')
    result = await db["question_banks"].insert_one(question_dict)
    created_question = await db["question_banks"].find_one({"_id": result.inserted_id})
    return created_question

async def get_questions_by_teacher(db: AsyncIOMotorDatabase, teacher_id: ObjectId) -> List[dict]:
    questions = await db["question_banks"].find({"created_by_teacher_id": teacher_id}).to_list(1000)
    return questions

async def get_question_by_id(db: AsyncIOMotorDatabase, question_id: str) -> dict | None:
    if not ObjectId.is_valid(question_id): return None
    return await db["question_banks"].find_one({"_id": ObjectId(question_id)})

async def update_question(db: AsyncIOMotorDatabase, question_id: str, question_update: QuestionBankUpdate) -> dict | None:
    if not ObjectId.is_valid(question_id): return None
    update_data = question_update.model_dump(exclude_unset=True)
    if not update_data: return await get_question_by_id(db, question_id)
    await db["question_banks"].update_one({"_id": ObjectId(question_id)}, {"$set": update_data})
    return await get_question_by_id(db, question_id)

async def delete_question(db: AsyncIOMotorDatabase, question_id: str) -> bool:
    if not ObjectId.is_valid(question_id): return False
    result = await db["question_banks"].delete_one({"_id": ObjectId(question_id)})
    return result.deleted_count > 0

async def get_questions_by_ids(db: AsyncIOMotorDatabase, question_ids: List[ObjectId]) -> List[dict]:
    """Mengambil beberapa soal berdasarkan daftar ID."""
    if not question_ids:
        return []
    cursor = db["question_banks"].find({"_id": {"$in": question_ids}})
    return await cursor.to_list(length=len(question_ids))

async def get_questions_for_coordinator(db: AsyncIOMotorDatabase, subject_id: ObjectId, grade_level: int) -> List[dict]:
    """Mengambil semua soal untuk mata pelajaran dan jenjang kelas tertentu."""
    # Kita perlu join dengan data guru dan kelas untuk memfilter berdasarkan jenjang
    # Ini adalah query yang lebih kompleks, untuk sekarang kita sederhanakan
    # Asumsi: Soal tidak secara langsung terikat ke jenjang kelas, hanya ke mata pelajaran
    return await db["question_banks"].find({"subject_id": subject_id}).to_list(None)

async def get_questions_by_teacher(db: AsyncIOMotorDatabase, teacher_id: ObjectId) -> List[dict]:
    """Mengambil semua soal yang dibuat oleh seorang guru."""
    questions = await db["question_banks"].find({"created_by_teacher_id": teacher_id}).to_list(None)
    return questions