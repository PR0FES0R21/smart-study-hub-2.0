# ==============================================================================
# File: app/crud/crud_exams.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'exams'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.schemas.exam import ExamCreate
import random
from datetime import datetime

from app.schemas.exam import ExamCreate, ExamQuestionUpdate, ExamUpdate
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

async def get_all_exams_with_details(
    db: AsyncIOMotorDatabase, 
    filters: Dict[str, Any],
    skip: int,
    limit: int,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mengambil semua ujian dengan detail lengkap, mendukung filter, paginasi, dan pencarian.
    """
    pipeline = []
    
    initial_match = {}
    if "academic_period_id" in filters:
        initial_match["academic_period_id"] = filters["academic_period_id"]
    if "exam_type" in filters:
        initial_match["exam_type"] = filters["exam_type"]
    
    if initial_match:
        pipeline.append({"$match": initial_match})

    # Pipeline lookup yang sudah ada
    lookup_pipeline = [
        {"$lookup": {"from": "academic_periods", "localField": "academic_period_id", "foreignField": "_id", "as": "academic_period_details"}},
        {"$unwind": {"path": "$academic_period_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "teaching_assignments", "localField": "teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment_details"}},
        {"$unwind": {"path": "$teaching_assignment_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "subjects", "localField": "teaching_assignment_details.subject_id", "foreignField": "_id", "as": "teaching_assignment_details.subject_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.subject_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "classes", "localField": "teaching_assignment_details.class_id", "foreignField": "_id", "as": "teaching_assignment_details.class_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.class_details", "preserveNullAndEmptyArrays": True}},
        # Tambahkan lookup untuk expertise_programs
        {"$lookup": {"from": "expertise_programs", "localField": "teaching_assignment_details.class_details.expertise_id", "foreignField": "_id", "as": "teaching_assignment_details.class_details.expertise_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.class_details.expertise_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "teaching_assignment_details.teacher_id", "foreignField": "_id", "as": "teaching_assignment_details.teacher_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.teacher_details", "preserveNullAndEmptyArrays": True}},
        {"$project": {"teaching_assignment_details.teacher_details.hashed_password": 0}},
    ]
    pipeline.extend(lookup_pipeline)
    
    # Filter kedua berdasarkan data yang sudah di-join
    if "teacher_id" in filters:
        pipeline.append({"$match": {"teaching_assignment_details.teacher_id": filters["teacher_id"]}})
        
    # Filter pencarian
    if search:
        pipeline.append({"$match": {
            "$or": [
                {"title": {"$regex": search, "$options": "i"}},
                {"teaching_assignment_details.subject_details.name": {"$regex": search, "$options": "i"}},
                {"teaching_assignment_details.teacher_details.full_name": {"$regex": search, "$options": "i"}},
            ]
        }})

    # Menggunakan $facet untuk mendapatkan data dan total count dalam satu query
    facet_stage = {
        "$facet": {
            "data": [
                {"$sort": {"availability_start_time": -1}},
                {"$skip": skip},
                {"$limit": limit}
            ],
            "total_count": [
                {"$count": "count"}
            ]
        }
    }
    pipeline.append(facet_stage)
    
    result = await db["exams"].aggregate(pipeline).to_list(1)
    
    data = result[0]['data'] if result and result[0]['data'] else []
    total_items = result[0]['total_count'][0]['count'] if result and result[0]['total_count'] else 0
    
    return {"data": data, "total_items": total_items}

async def update_exam(db: AsyncIOMotorDatabase, exam_id: str, exam_update: ExamUpdate) -> dict | None:
    """Memperbarui detail ujian."""
    if not ObjectId.is_valid(exam_id): return None
    
    update_data = exam_update.model_dump(mode='python', exclude_unset=True)
    if not update_data:
        return await get_exam_by_id(db, exam_id)

    update_data["updated_at"] = datetime.utcnow()
    
    await db["exams"].update_one(
        {"_id": ObjectId(exam_id)},
        {"$set": update_data}
    )
    return await get_exam_by_id(db, exam_id)

async def set_exam_status(db: AsyncIOMotorDatabase, exam_id: str, status: str) -> dict | None:
    """Mengubah status ujian (misal: menjadi 'ongoing')."""
    if not ObjectId.is_valid(exam_id): return None
    await db["exams"].update_one(
        {"_id": ObjectId(exam_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    return await get_exam_by_id(db, exam_id)

async def delete_exam_and_sessions(db: AsyncIOMotorDatabase, exam_id: str) -> bool:
    """Menghapus dokumen ujian dan semua sesi ujian terkait."""
    if not ObjectId.is_valid(exam_id): return False
    
    # Hapus semua sesi ujian yang terkait terlebih dahulu
    await db["exam_sessions"].delete_many({"exam_id": ObjectId(exam_id)})
    
    # Hapus dokumen ujian utama
    result = await db["exams"].delete_one({"_id": ObjectId(exam_id)})
    return result.deleted_count > 0

async def get_exam_details_by_id(db: AsyncIOMotorDatabase, exam_id: str) -> dict | None:
    """Mengambil detail ujian lengkap, TAPI tanpa isi soalnya."""
    if not ObjectId.is_valid(exam_id): return None
    
    # Kita gunakan pipeline yang sama dengan get_all_exams, tapi dengan $match di awal
    pipeline = [
        {"$match": {"_id": ObjectId(exam_id)}},
        {"$lookup": {"from": "academic_periods", "localField": "academic_period_id", "foreignField": "_id", "as": "academic_period_details"}},
        {"$unwind": {"path": "$academic_period_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "teaching_assignments", "localField": "teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment_details"}},
        {"$unwind": {"path": "$teaching_assignment_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "subjects", "localField": "teaching_assignment_details.subject_id", "foreignField": "_id", "as": "teaching_assignment_details.subject_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.subject_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "classes", "localField": "teaching_assignment_details.class_id", "foreignField": "_id", "as": "teaching_assignment_details.class_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.class_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "teaching_assignment_details.teacher_id", "foreignField": "_id", "as": "teaching_assignment_details.teacher_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.teacher_details", "preserveNullAndEmptyArrays": True}},
        {"$project": {"teaching_assignment_details.teacher_details.hashed_password": 0}},
    ]
    
    result = await db["exams"].aggregate(pipeline).to_list(1)
    return result[0] if result else None