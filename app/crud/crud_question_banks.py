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