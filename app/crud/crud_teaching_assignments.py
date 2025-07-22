# ==============================================================================
# File: app/crud/crud_teaching_assignments.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'teaching_assignments'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
from bson import ObjectId

from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentUpdate
from app.core.cache import get_cache, set_cache, invalidate_cache

ASSIGNMENTS_IDS_CACHE_PATTERN = "assignments:ids:*"

def generate_assignment_ids_cache_key(filters: Dict[str, Any]) -> str:
    """Membuat kunci cache yang unik untuk daftar ID penugasan berdasarkan filter."""
    if not filters:
        return "assignments:ids:all"
    
    sorted_filters = sorted(filters.items())
    filter_str = "_".join([f"{k}={v}" for k, v in sorted_filters])
    return f"assignments:ids:{filter_str}"

async def get_filtered_assignment_ids(db: AsyncIOMotorDatabase, filters: Dict[str, Any]) -> List[str]:
    """Mengambil daftar ID penugasan yang sudah difilter, menggunakan cache."""
    cache_key = generate_assignment_ids_cache_key(filters)
    cached_ids = await get_cache(cache_key)
    if cached_ids is not None:
        return cached_ids

    query = {}
    if filters.get("class_id"):
        query["class_id"] = ObjectId(filters["class_id"])
    if filters.get("teacher_id"):
        query["teacher_id"] = ObjectId(filters["teacher_id"])
    
    cursor = db["teaching_assignments"].find(query, {"_id": 1})
    all_ids = [str(doc["_id"]) for doc in await cursor.to_list(None)]
    
    if all_ids:
        await set_cache(cache_key, all_ids)
        
    return all_ids

async def get_assignments_details_by_ids(db: AsyncIOMotorDatabase, assignment_ids: List[ObjectId]) -> List[dict]:
    """Mengambil detail lengkap penugasan berdasarkan daftar ID."""
    if not assignment_ids:
        return []
        
    pipeline = [
        {"$match": {"_id": {"$in": assignment_ids}}},
        # --- PERBAIKAN: Menggunakan preserveNullAndEmptyArrays untuk semua lookup ---
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": {"path": "$class_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject_details"}},
        {"$unwind": {"path": "$subject_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "teacher_id", "foreignField": "_id", "as": "teacher_details"}},
        {"$unwind": {"path": "$teacher_details", "preserveNullAndEmptyArrays": True}},
        # --- DITAMBAHKAN: Lookup tambahan untuk profil guru ---
        {"$lookup": {"from": "profiles", "localField": "teacher_details.profile_id", "foreignField": "_id", "as": "teacher_details.profile_details"}},
        {"$unwind": {"path": "$teacher_details.profile_details", "preserveNullAndEmptyArrays": True}},
        {"$project": {"teacher_details.hashed_password": 0}}
    ]
    return await db["teaching_assignments"].aggregate(pipeline).to_list(None)


async def create_teaching_assignment(db: AsyncIOMotorDatabase, assignment: TeachingAssignmentCreate) -> dict:
    if await db["teaching_assignments"].find_one({"class_id": assignment.class_id, "subject_id": assignment.subject_id, "teacher_id": assignment.teacher_id}):
        raise HTTPException(status_code=400, detail="This exact teaching assignment already exists.")
    
    assignment_dict = assignment.model_dump(mode='python')
    result = await db["teaching_assignments"].insert_one(assignment_dict)
    created = await db["teaching_assignments"].find_one({"_id": result.inserted_id})
    await invalidate_cache(ASSIGNMENTS_IDS_CACHE_PATTERN)
    return created

async def delete_teaching_assignment(db: AsyncIOMotorDatabase, assignment_id: str) -> bool:
    if not ObjectId.is_valid(assignment_id): return False
    result = await db["teaching_assignments"].delete_one({"_id": ObjectId(assignment_id)})
    if result.deleted_count > 0:
        await invalidate_cache(ASSIGNMENTS_IDS_CACHE_PATTERN)
    return result.deleted_count > 0

async def find_assignments_by_criteria(
    db: AsyncIOMotorDatabase, 
    subject_id: ObjectId,
    grade_level: Optional[int] = None,
    expertise_id: Optional[ObjectId] = None,
    class_id: Optional[ObjectId] = None
) -> List[dict]:
    """Mencari penugasan mengajar berdasarkan kriteria untuk pembuatan ujian massal."""
    if class_id:
        return await db["teaching_assignments"].find({"class_id": class_id, "subject_id": subject_id}).to_list(1000)

    # Jika tidak menargetkan kelas spesifik, kita perlu join dengan collection 'classes'
    pipeline = []
    
    # Filter awal pada teaching_assignments untuk efisiensi
    pipeline.append({"$match": {"subject_id": subject_id}})
    
    # Join dengan collection 'classes'
    pipeline.extend([
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
    ])
    
    # Bangun filter berdasarkan data kelas
    class_match_criteria = {}
    if grade_level: class_match_criteria["class_info.grade_level"] = grade_level
    if expertise_id: class_match_criteria["class_info.expertise_id"] = expertise_id
    
    if class_match_criteria:
        pipeline.append({"$match": class_match_criteria})
    
    return await db["teaching_assignments"].aggregate(pipeline).to_list(1000)

async def update_teaching_assignment(db: AsyncIOMotorDatabase, assignment_id: ObjectId, assignment_update: TeachingAssignmentUpdate) -> dict | None:
    """Memperbarui penugasan mengajar (misalnya, mengganti guru)."""
    update_data = assignment_update.model_dump(mode='python', exclude_unset=True)
    if not update_data:
        return await db["teaching_assignments"].find_one({"_id": assignment_id})
        
    await db["teaching_assignments"].update_one(
        {"_id": assignment_id},
        {"$set": update_data}
    )
    return await db["teaching_assignments"].find_one({"_id": assignment_id})

