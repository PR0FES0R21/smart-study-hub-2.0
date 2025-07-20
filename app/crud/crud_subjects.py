# ==============================================================================
# File: app/crud/crud_subjects.py
# --- DIUBAH --- (Logika caching diperbaiki)
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.schemas.subject import SubjectCreate, SubjectUpdate
from datetime import datetime
from app.core.cache import get_cache, set_cache, invalidate_cache

# Mendefinisikan kunci cache
SUBJECTS_ALL_CACHE_KEY = "subjects:all"
DASHBOARD_STATS_CACHE_KEY = "analytics:dashboard_stats"

async def create_subject(db: AsyncIOMotorDatabase, subject: SubjectCreate) -> dict:
    if await db["subjects"].find_one({"code": subject.code}):
        raise HTTPException(status_code=400, detail=f"Subject with code '{subject.code}' already exists.")
    
    now = datetime.utcnow()
    subject_dict = subject.model_dump(mode='python')
    subject_dict["created_at"] = now
    subject_dict["updated_at"] = now
    
    result = await db["subjects"].insert_one(subject_dict)
    created_subject = await db["subjects"].find_one({"_id": result.inserted_id})
    
    await invalidate_cache(f"{SUBJECTS_ALL_CACHE_KEY}:*")
    await invalidate_cache(DASHBOARD_STATS_CACHE_KEY)
    
    return created_subject

async def get_all_subjects(
    db: AsyncIOMotorDatabase, 
    skip: int, 
    limit: int, 
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Mengambil semua mata pelajaran dengan paginasi dan pencarian."""
    # --- PERBAIKAN: Caching hanya berlaku jika tidak ada pencarian DAN di halaman pertama ---
    # Ini untuk menghindari caching data yang tidak lengkap
    cache_key = f"{SUBJECTS_ALL_CACHE_KEY}:{skip}:{limit}"
    if not search:
        cached_data = await get_cache(cache_key)
        if cached_data is not None:
            print("HIT: Mengambil daftar mata pelajaran dari cache.")
            return cached_data
        print("MISS: Mengambil daftar mata pelajaran dari database.")

    query = {}
    if search:
        query = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"code": {"$regex": search, "$options": "i"}},
            ]
        }

    total_items = await db["subjects"].count_documents(query)
    subjects_cursor = db["subjects"].find(query).skip(skip).limit(limit)
    subjects = await subjects_cursor.to_list(length=limit)
    
    response_data = {"data": subjects, "total_items": total_items}
    
    if not search:
        await set_cache(cache_key, response_data)
        
    return response_data

async def get_subject_by_id(db: AsyncIOMotorDatabase, subject_id: str) -> dict | None:
    if not ObjectId.is_valid(subject_id): return None
    return await db["subjects"].find_one({"_id": ObjectId(subject_id)})

async def update_subject(db: AsyncIOMotorDatabase, subject_id: str, subject_update: SubjectUpdate) -> dict | None:
    if not ObjectId.is_valid(subject_id): return None
    
    update_data = {}
    for field in subject_update.model_fields_set:
        update_data[field] = getattr(subject_update, field)

    if not update_data: 
        return await get_subject_by_id(db, subject_id)
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db["subjects"].update_one({"_id": ObjectId(subject_id)}, {"$set": update_data})
    
    await invalidate_cache(f"{SUBJECTS_ALL_CACHE_KEY}:*")
    
    return await get_subject_by_id(db, subject_id)

async def delete_subject(db: AsyncIOMotorDatabase, subject_id: str) -> bool:
    if not ObjectId.is_valid(subject_id): return False
    result = await db["subjects"].delete_one({"_id": ObjectId(subject_id)})
    
    if result.deleted_count > 0:
        await invalidate_cache(f"{SUBJECTS_ALL_CACHE_KEY}:*")
        await invalidate_cache(DASHBOARD_STATS_CACHE_KEY)
        
    return result.deleted_count > 0