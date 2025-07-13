# ==============================================================================
# File: app/crud/crud_exams.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'exams'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId
from app.schemas.exam import ExamCreate
import random

from app.schemas.exam import ExamCreate, ExamQuestionUpdate
from app.schemas.exam_session import ExamSessionBase, QuestionMapItem
from app.schemas.exam_session import ExamSessionBase, QuestionMapItem

async def get_exam_by_id(db: AsyncIOMotorDatabase, exam_id: str) -> dict | None:
    """Mengambil satu dokumen ujian berdasarkan ID."""
    if not ObjectId.is_valid(exam_id): return None
    return await db["exams"].find_one({"_id": ObjectId(exam_id)})

async def create_exam(db: AsyncIOMotorDatabase, exam: ExamCreate) -> dict:
    exam_dict = exam.model_dump(mode='python')
    result = await db["exams"].insert_one(exam_dict)
    created_exam = await db["exams"].find_one({"_id": result.inserted_id})
    return created_exam

async def start_exam_session(db: AsyncIOMotorDatabase, exam: dict, student_id: ObjectId) -> dict:
    """Membuat sesi ujian baru untuk siswa, lengkap dengan peta acak."""
    
    # Cek jika siswa sudah punya sesi aktif untuk ujian ini
    existing_session = await db["exam_sessions"].find_one({
        "exam_id": exam["_id"],
        "student_id": student_id,
        "status": "ongoing"
    })
    if existing_session:
        return existing_session # Kembalikan sesi yang sudah ada jika belum disubmit

    # --- Membuat Peta Acak ---
    question_ids = exam.get("question_ids", [])
    if exam.get("settings", {}).get("shuffle_questions", False):
        random.shuffle(question_ids)

    question_map = []
    for i, q_id in enumerate(question_ids):
        question_map.append(QuestionMapItem(position=i + 1, question_id=q_id))

    # (Opsional: Di sini kita bisa menambahkan logika untuk mengacak opsi jawaban)

    session_data = ExamSessionBase(
        exam_id=exam["_id"],
        student_id=student_id,
        question_map=question_map
    )
    
    session_dict = session_data.model_dump(mode='python')
    result = await db["exam_sessions"].insert_one(session_dict)
    created_session = await db["exam_sessions"].find_one({"_id": result.inserted_id})
    return created_session


async def add_questions_to_exam(db: AsyncIOMotorDatabase, exam_id: ObjectId, questions_update: ExamQuestionUpdate) -> dict | None:
    """Menambahkan atau memperbarui daftar soal dalam sebuah ujian."""
    update_data = {
        "question_ids": questions_update.question_ids,
        "status": "ready" # Ubah status menjadi siap dikerjakan
    }
    await db["exams"].update_one({"_id": exam_id}, {"$set": update_data})
    return await db["exams"].find_one({"_id": exam_id})