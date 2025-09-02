# ==============================================================================
# File: app/crud/crud_question_banks.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'question_banks'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.schemas.question_bank import QuestionBankCreate, QuestionBankUpdate
from app.core.cache import invalidate_cache, get_cache, set_cache
import logging

logger = logging.getLogger(__name__)

QUESTION_BANKS_IDS_CACHE_PATTERN = "question_banks:ids:*"

async def create_question(db: AsyncIOMotorDatabase, question: QuestionBankCreate) -> dict:
    question_dict = question.model_dump(mode='python')
    result = await db["question_banks"].insert_one(question_dict)
    created_question = await db["question_banks"].find_one({"_id": result.inserted_id})
    
    # Invalidate cache setelah create
    await invalidate_cache(QUESTION_BANKS_IDS_CACHE_PATTERN)
    
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
    
    # Invalidate cache setelah update
    await invalidate_cache(QUESTION_BANKS_IDS_CACHE_PATTERN)
    
    return await get_question_by_id(db, question_id)

async def delete_question(db: AsyncIOMotorDatabase, question_id: str) -> bool:
    if not ObjectId.is_valid(question_id): return False
    result = await db["question_banks"].delete_one({"_id": ObjectId(question_id)})
    
    # Invalidate cache setelah delete jika berhasil
    if result.deleted_count > 0:
        await invalidate_cache(QUESTION_BANKS_IDS_CACHE_PATTERN)
    
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

def generate_question_ids_cache_key(filters: Dict[str, Any]) -> str:
    """Membuat kunci cache yang unik untuk daftar ID question berdasarkan filter."""
    if not filters:
        return "question_banks:ids:all"
    
    sorted_filters = sorted(filters.items())
    filter_str = "_".join([f"{k}={v}" for k, v in sorted_filters])
    return f"question_banks:ids:{filter_str}"

async def get_filtered_question_ids(db: AsyncIOMotorDatabase, filters: Dict[str, Any]) -> List[str]:
    """Mengambil daftar ID question yang sudah difilter, menggunakan cache."""
    cache_key = generate_question_ids_cache_key(filters)
    cached_ids = await get_cache(cache_key)
    if cached_ids is not None:
        logger.info(f"HIT: Mengambil ID question dari cache untuk filter: {filters}")
        return cached_ids

    logger.info(f"MISS: Mengambil ID question dari database untuk filter: {filters}")
    
    pipeline = []
    # Bangun pipeline filter
    match_query = {}
    
    # Filter berdasarkan teacher
    if filters.get("teacher_id"):
        match_query["created_by_teacher_id"] = ObjectId(filters["teacher_id"])
    
    # Filter berdasarkan subject
    if filters.get("subject_id"):
        match_query["subject_id"] = ObjectId(filters["subject_id"])
    
    # Filter berdasarkan question_type
    if filters.get("question_type"):
        match_query["question_type"] = filters["question_type"]
    
    # Filter berdasarkan difficulty
    if filters.get("difficulty"):
        match_query["difficulty"] = filters["difficulty"]
    
    # Filter berdasarkan status
    if filters.get("status"):
        match_query["status"] = filters["status"]
    
    if match_query:
        pipeline.append({"$match": match_query})

    pipeline.append({"$project": {"_id": 1}})
    cursor = db["question_banks"].aggregate(pipeline)
    all_ids = [str(doc["_id"]) for doc in await cursor.to_list(None)]
    
    if all_ids:
        await set_cache(cache_key, all_ids)
        
    return all_ids

async def get_questions_details_by_ids(db: AsyncIOMotorDatabase, question_ids: List[ObjectId]) -> List[dict]:
    """Mengambil detail lengkap question berdasarkan daftar ID."""
    if not question_ids:
        return []
    
    # Pipeline agregasi untuk menggabungkan data dari collection lain
    pipeline = [
        {"$match": {"_id": {"$in": question_ids}}},
        
        # Lookup untuk detail subject
        {"$lookup": {
            "from": "subjects",
            "localField": "subject_id",
            "foreignField": "_id",
            "as": "subject_details"
        }},
        {"$unwind": {"path": "$subject_details", "preserveNullAndEmptyArrays": True}},
        
        # Lookup untuk detail teacher
        {"$lookup": {
            "from": "users",
            "localField": "created_by_teacher_id",
            "foreignField": "_id",
            "as": "teacher_details"
        }},
        {"$unwind": {"path": "$teacher_details", "preserveNullAndEmptyArrays": True}},
        
        # Lookup untuk profile teacher
        {"$lookup": {
            "from": "profiles",
            "localField": "teacher_details.profile_id",
            "foreignField": "_id",
            "as": "teacher_profile"
        }},
        {"$unwind": {"path": "$teacher_profile", "preserveNullAndEmptyArrays": True}},
        
        # Tambahkan field computed untuk teacher name
        {"$addFields": {
            "teacher_name": "$teacher_profile.full_name"
        }},
        
        # Sorting berdasarkan creation date (newest first)
        {"$sort": {"created_at": -1}}
    ]
    
    return await db["question_banks"].aggregate(pipeline).to_list(None)

async def search_questions_with_details(
    db: AsyncIOMotorDatabase,
    search: str,
    skip: int,
    limit: int,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Melakukan pencarian langsung ke DB (bypass cache) dan mengembalikan data lengkap
    dengan dukungan filter tambahan.
    """
    base_pipeline = [
        # Lookup untuk detail subject
        {"$lookup": {
            "from": "subjects",
            "localField": "subject_id",
            "foreignField": "_id",
            "as": "subject_details"
        }},
        {"$unwind": {"path": "$subject_details", "preserveNullAndEmptyArrays": True}},
        
        # Lookup untuk detail teacher
        {"$lookup": {
            "from": "users",
            "localField": "created_by_teacher_id",
            "foreignField": "_id",
            "as": "teacher_details"
        }},
        {"$unwind": {"path": "$teacher_details", "preserveNullAndEmptyArrays": True}},
        
        # Lookup untuk profile teacher
        {"$lookup": {
            "from": "profiles",
            "localField": "teacher_details.profile_id",
            "foreignField": "_id",
            "as": "teacher_profile"
        }},
        {"$unwind": {"path": "$teacher_profile", "preserveNullAndEmptyArrays": True}},
        
        # Tambahkan field computed
        {"$addFields": {
            "teacher_name": "$teacher_profile.full_name"
        }}
    ]
    
    # Build match conditions untuk search dan filters
    match_conditions = {
        "$and": [
            {
                "$or": [
                    {"question_text": {"$regex": search, "$options": "i"}},
                    {"subject_details.name": {"$regex": search, "$options": "i"}},
                    {"teacher_name": {"$regex": search, "$options": "i"}},
                    {"tags": {"$regex": search, "$options": "i"}},
                ]
            }
        ]
    }
    
    # Apply additional filters if provided
    if filters:
        for key, value in filters.items():
            if value is not None:
                if key == "teacher_id":
                    match_conditions["$and"].append({"created_by_teacher_id": ObjectId(value)})
                elif key == "subject_id":
                    match_conditions["$and"].append({"subject_id": ObjectId(value)})
                elif key == "question_type":
                    match_conditions["$and"].append({"question_type": value})
                elif key == "difficulty":
                    match_conditions["$and"].append({"difficulty": value})
                elif key == "status":
                    match_conditions["$and"].append({"status": value})
    
    match_stage = {"$match": match_conditions}
    full_pipeline = base_pipeline + [match_stage]
    
    # Count pipeline
    count_pipeline = full_pipeline + [{"$count": "count"}]
    total_items_result = await db["question_banks"].aggregate(count_pipeline).to_list(1)
    total_items = total_items_result[0]['count'] if total_items_result else 0
    
    # Data pipeline dengan sorting dan pagination
    data_pipeline = full_pipeline + [
        {"$sort": {"created_at": -1}},
        {"$skip": skip}, 
        {"$limit": limit}
    ]
    data = await db["question_banks"].aggregate(data_pipeline).to_list(limit)
    
    return {"data": data, "total_items": total_items}