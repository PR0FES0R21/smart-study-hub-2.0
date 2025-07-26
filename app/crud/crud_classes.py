# ==============================================================================
# File: app/crud/crud_classes.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'classes'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.schemas.classes import ClassCreate, ClassUpdate
from app.core.cache import invalidate_cache
from app.core.cache import get_cache, set_cache
from app.crud.crud_teaching_assignments import delete_assignment_by_class_id

CLASSES_IDS_CACHE_PATTERN = "classes:ids:*"

async def create_class(db: AsyncIOMotorDatabase, class_in: ClassCreate) -> dict:
    """Membuat kelas baru."""
    # Cek duplikasi: kelas dengan nama, jurusan, dan tahun ajaran yang sama tidak boleh ada
    existing_class = await db["classes"].find_one({
        "grade_level": class_in.grade_level,
        "expertise_id": class_in.expertise_id,
        "name": class_in.name,
        "academic_year": class_in.academic_year
    })
    if existing_class:
        raise HTTPException(status_code=400, detail="Class with the same details already exists.")
    
    class_dict = class_in.dict(exclude_unset=True)
    result = await db["classes"].insert_one(class_dict)
    created_class = await db["classes"].find_one({"_id": result.inserted_id})
    await invalidate_cache(CLASSES_IDS_CACHE_PATTERN)
    await invalidate_cache("analytics:dashboard_stats")
    return created_class

def generate_class_ids_cache_key(filters: Dict[str, Any]) -> str:
    """Membuat kunci cache yang unik untuk daftar ID kelas berdasarkan filter."""
    if not filters:
        return "classes:ids:all"
    
    sorted_filters = sorted(filters.items())
    filter_str = "_".join([f"{k}={v}" for k, v in sorted_filters])
    return f"classes:ids:{filter_str}"

async def get_filtered_class_ids(db: AsyncIOMotorDatabase, filters: Dict[str, Any]) -> List[str]:
    """Mengambil daftar ID kelas yang sudah difilter, menggunakan cache."""
    cache_key = generate_class_ids_cache_key(filters)
    cached_ids = await get_cache(cache_key)
    if cached_ids is not None:
        print(f"HIT: Mengambil ID kelas dari cache untuk filter: {filters}")
        return cached_ids

    print(f"MISS: Mengambil ID kelas dari database untuk filter: {filters}")
    
    query = {}
    if filters.get("grade_level"):
        query["grade_level"] = filters["grade_level"]
    if filters.get("expertise_id"):
        query["expertise_id"] = ObjectId(filters["expertise_id"])
    if filters.get("academic_year"):
        query["academic_year"] = filters["academic_year"]

    cursor = db["classes"].find(query, {"_id": 1})
    all_ids = [str(doc["_id"]) for doc in await cursor.to_list(None)]
    
    if all_ids:
        await set_cache(cache_key, all_ids)
        
    return all_ids

async def get_classes_details_by_ids(db: AsyncIOMotorDatabase, class_ids: List[ObjectId]) -> List[dict]:
    """Mengambil detail lengkap kelas berdasarkan daftar ID."""
    if not class_ids:
        return []
        
    pipeline = [
        {"$match": {"_id": {"$in": class_ids}}},
        {"$lookup": {"from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
        {"$unwind": {"path": "$expertise_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "homeroom_teacher_id", "foreignField": "_id", "as": "teacher_user_info"}},
        {"$unwind": {"path": "$teacher_user_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "profiles", "localField": "teacher_user_info.profile_id", "foreignField": "_id", "as": "teacher_profile_info"}},
        {"$unwind": {"path": "$teacher_profile_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "grade_level": 1, "expertise_id": 1, "name": 1, "academic_year": 1, "homeroom_teacher_id": 1,
            "expertise_details": 1,
            "homeroom_teacher_details": {
                "$cond": {
                    "if": "$teacher_profile_info",
                    "then": {"_id": "$teacher_user_info._id", "full_name": "$teacher_profile_info.full_name", "gender": "$teacher_profile_info.gender", "profile_picture_url": "$teacher_profile_info.profile_picture_url"},
                    "else": None
                }
            }
        }}
    ]
    return await db["classes"].aggregate(pipeline).to_list(None)

async def search_classes_with_details(db: AsyncIOMotorDatabase, search: str, skip: int, limit: int) -> Dict[str, Any]:
    """Melakukan pencarian langsung ke DB (bypass cache) dan mengembalikan data lengkap."""
    # Pipeline lookup dasar
    lookup_pipeline = [
        {"$lookup": {"from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
        {"$unwind": "$expertise_details"},
        # (Tambahkan lookup lain jika pencarian perlu mencakup nama wali kelas)
    ]
    
    # Query pencarian
    match_query = {"$match": {
        "$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"academic_year": {"$regex": search, "$options": "i"}},
            {"expertise_details.name": {"$regex": search, "$options": "i"}},
        ]
    }}
    
    full_pipeline = lookup_pipeline + [match_query]
    
    # Hitung total item yang cocok
    count_pipeline = full_pipeline + [{"$count": "count"}]
    total_items_result = await db["classes"].aggregate(count_pipeline).to_list(1)
    total_items = total_items_result[0]['count'] if total_items_result else 0
    
    # Ambil data dengan paginasi
    data_pipeline = full_pipeline + [{"$skip": skip}, {"$limit": limit}]
    data = await db["classes"].aggregate(data_pipeline).to_list(limit)
    
    return {"data": data, "total_items": total_items}

async def get_class_by_id(db: AsyncIOMotorDatabase, class_id: str) -> dict | None:
    """Mengambil satu kelas berdasarkan ID."""
    if not ObjectId.is_valid(class_id): return None
    return await db["classes"].find_one({"_id": ObjectId(class_id)})

async def update_class(db: AsyncIOMotorDatabase, class_id: str, class_update: ClassUpdate) -> dict | None:
    """Memperbarui kelas."""
    if not ObjectId.is_valid(class_id): return None
    
    update_data = class_update.dict(exclude_unset=True)
    if not update_data:
        return await get_class_by_id(db, class_id)

    await db["classes"].update_one({"_id": ObjectId(class_id)}, {"$set": update_data})
    return await get_class_by_id(db, class_id)

async def delete_class(db: AsyncIOMotorDatabase, class_id: str) -> bool:
    """Menghapus kelas."""
    if not ObjectId.is_valid(class_id): return False
    
    result = await db["classes"].delete_one({"_id": ObjectId(class_id)})
    if result.deleted_count > 0:
        await delete_assignment_by_class_id(db=db, class_id=class_id)
        await invalidate_cache(CLASSES_IDS_CACHE_PATTERN)
        await invalidate_cache("analytics:dashboard_stats")
    return result.deleted_count > 0

async def create_classes_for_next_year(db: AsyncIOMotorDatabase, current_year: str, next_year: str) -> int:
    """Menduplikasi struktur kelas dari tahun saat ini ke tahun berikutnya."""
    current_year_classes = await db["classes"].find({"academic_year": current_year}).to_list(None)
    if not current_year_classes:
        raise HTTPException(status_code=404, detail=f"No classes found for academic year {current_year}")

    new_classes_to_create = []
    for old_class in current_year_classes:
        new_class_doc = {
            "grade_level": old_class["grade_level"],
            "expertise_id": old_class["expertise_id"],
            "name": old_class["name"],
            "academic_year": next_year,
            "homeroom_teacher_id": None # Dikosongkan untuk diisi kembali
        }
        new_classes_to_create.append(new_class_doc)

    if not new_classes_to_create:
        return 0

    result = await db["classes"].insert_many(new_classes_to_create)
    return len(result.inserted_ids)
