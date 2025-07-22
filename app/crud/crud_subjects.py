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

#  Mendefinisikan kunci cache
SUBJECTS_IDS_CACHE_KEY = "subjects:all:ids"
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
    
    # Invalidate "Katalog ID" dan statistik
    await invalidate_cache(SUBJECTS_IDS_CACHE_KEY)
    await invalidate_cache(DASHBOARD_STATS_CACHE_KEY)
    
    return created_subject

async def get_all_subject_ids(db: AsyncIOMotorDatabase) -> List[str]:
    """Mengambil daftar semua ID mata pelajaran, menggunakan cache."""
    cached_ids = await get_cache(SUBJECTS_IDS_CACHE_KEY)
    if cached_ids is not None:
        print("HIT: Mengambil ID mata pelajaran dari cache.")
        return cached_ids

    print("MISS: Mengambil ID mata pelajaran dari database.")
    cursor = db["subjects"].find({}, {"_id": 1})
    # Mengubah ObjectId menjadi string untuk disimpan di cache
    all_ids = [str(doc["_id"]) for doc in await cursor.to_list(None)]
    
    await set_cache(SUBJECTS_IDS_CACHE_KEY, all_ids)
    return all_ids

async def get_subjects_by_ids(db: AsyncIOMotorDatabase, ids: List[ObjectId]) -> List[dict]:
    """Mengambil dokumen lengkap mata pelajaran berdasarkan daftar ID."""
    if not ids:
        return []
    cursor = db["subjects"].find({"_id": {"$in": ids}})
    return await cursor.to_list(length=len(ids))

async def search_subjects(db: AsyncIOMotorDatabase, search: str, skip: int, limit: int) -> Dict[str, Any]:
    """Melakukan pencarian langsung ke database (bypass cache)."""
    query = {
        "$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"code": {"$regex": search, "$options": "i"}},
        ]
    }
    total_items = await db["subjects"].count_documents(query)
    cursor = db["subjects"].find(query).skip(skip).limit(limit)
    data = await cursor.to_list(length=limit)
    return {"data": data, "total_items": total_items}

async def update_subject(db: AsyncIOMotorDatabase, subject_id: str, subject_update: SubjectUpdate) -> dict | None:
    if not ObjectId.is_valid(subject_id): return None
    
    update_data = {k: v for k, v in subject_update.model_dump().items() if v is not None}
    if not update_data: return await get_subject_by_id(db, subject_id)
    
    update_data["updated_at"] = datetime.utcnow()
    await db["subjects"].update_one({"_id": ObjectId(subject_id)}, {"$set": update_data})
    
    await invalidate_cache(SUBJECTS_IDS_CACHE_KEY)
    
    return await get_subject_by_id(db, subject_id)

async def delete_subject(db: AsyncIOMotorDatabase, subject_id: str) -> bool:
    if not ObjectId.is_valid(subject_id): return False
    result = await db["subjects"].delete_one({"_id": ObjectId(subject_id)})
    
    if result.deleted_count > 0:
        await invalidate_cache(SUBJECTS_IDS_CACHE_KEY)
        await invalidate_cache(DASHBOARD_STATS_CACHE_KEY)
        
    return result.deleted_count > 0

async def get_subject_by_id(db: AsyncIOMotorDatabase, subject_id: str) -> dict | None:
    if not ObjectId.is_valid(subject_id): return None
    return await db["subjects"].find_one({"_id": ObjectId(subject_id)})