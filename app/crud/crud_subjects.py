# ==============================================================================
# File: app/crud/crud_subjects.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'subjects'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List
from bson import ObjectId

from app.schemas.subject import SubjectCreate, SubjectUpdate
from app.core.cache import invalidate_cache

async def create_subject(db: AsyncIOMotorDatabase, subject: SubjectCreate) -> dict:
    """Membuat mata pelajaran baru."""
    # Cek duplikasi berdasarkan kode mata pelajaran
    existing_subject = await db["subjects"].find_one({"code": subject.code})
    if existing_subject:
        raise HTTPException(status_code=400, detail=f"Subject with code '{subject.code}' already exists.")
    
    subject_dict = subject.dict()
    result = await db["subjects"].insert_one(subject_dict)
    created_subject = await db["subjects"].find_one({"_id": result.inserted_id})
    await invalidate_cache("analytics:dashboard_stats")
    return created_subject

async def get_all_subjects(db: AsyncIOMotorDatabase) -> List[dict]:
    """Mengambil semua mata pelajaran."""
    subjects = await db["subjects"].find().to_list(1000) # Batasi 1000 untuk awal
    return subjects

async def get_subject_by_id(db: AsyncIOMotorDatabase, subject_id: str) -> dict | None:
    """Mengambil satu mata pelajaran berdasarkan ID."""
    if not ObjectId.is_valid(subject_id):
        return None
    subject = await db["subjects"].find_one({"_id": ObjectId(subject_id)})
    return subject

async def update_subject(db: AsyncIOMotorDatabase, subject_id: str, subject_update: SubjectUpdate) -> dict | None:
    """Memperbarui mata pelajaran."""
    if not ObjectId.is_valid(subject_id):
        return None
    
    update_data = subject_update.dict(exclude_unset=True)
    if not update_data:
        return await get_subject_by_id(db, subject_id)

    await db["subjects"].update_one({"_id": ObjectId(subject_id)}, {"$set": update_data})
    updated_subject = await get_subject_by_id(db, subject_id)
    return updated_subject

async def delete_subject(db: AsyncIOMotorDatabase, subject_id: str) -> bool:
    """Menghapus mata pelajaran."""
    if not ObjectId.is_valid(subject_id):
        return False
    result = await db["subjects"].delete_one({"_id": ObjectId(subject_id)})
    if result.deleted_count > 0:
        await invalidate_cache("analytics:dashboard_stats")
    return result.deleted_count > 0
