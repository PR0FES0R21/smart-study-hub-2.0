# ==============================================================================
# File: app/crud/crud_academic_periods.py
# Deskripsi: Fungsi CRUD untuk collection 'academic_periods'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List
from bson import ObjectId
from datetime import datetime

from app.schemas.academic_period import AcademicPeriodCreate, AcademicPeriodUpdate
from app.core.cache import invalidate_cache

ACADEMIC_PERIOD_ACTIVE_CACHE_KEY = "academic_periods:active"

async def create_academic_period(db: AsyncIOMotorDatabase, period: AcademicPeriodCreate) -> dict:
    """Membuat periode akademik baru."""
    now = datetime.utcnow()
    
    # Jika periode baru ini aktif, nonaktifkan yang lain
    if period.status == "active":
        await db["academic_periods"].update_many(
            {"status": "active"},
            {"$set": {"status": "archived", "updated_at": now}}
        )
        await invalidate_cache(ACADEMIC_PERIOD_ACTIVE_CACHE_KEY)

    period_dict = period.model_dump(mode='python')
    period_dict["created_at"] = now
    period_dict["updated_at"] = now
    
    result = await db["academic_periods"].insert_one(period_dict)
    created_period = await db["academic_periods"].find_one({"_id": result.inserted_id})
    return created_period

async def get_active_period(db: AsyncIOMotorDatabase) -> dict | None:
    """Mengambil periode akademik yang sedang aktif."""
    return await db["academic_periods"].find_one({"status": "active"})

async def get_all_periods(db: AsyncIOMotorDatabase) -> List[dict]:
    """Mengambil semua periode akademik."""
    return await db["academic_periods"].find().sort("start_date", -1).to_list(100)

async def update_academic_period(db: AsyncIOMotorDatabase, period_id: str, period_update: AcademicPeriodUpdate) -> dict | None:
    """Memperbarui periode akademik."""
    if not ObjectId.is_valid(period_id): return None
    
    now = datetime.utcnow()
    update_data = period_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = now

    # Jika status diubah menjadi 'active', nonaktifkan yang lain dulu
    if update_data.get("status") == "active":
        await db["academic_periods"].update_many(
            {"status": "active", "_id": {"$ne": ObjectId(period_id)}},
            {"$set": {"status": "archived", "updated_at": now}}
        )
    
    await db["academic_periods"].update_one({"_id": ObjectId(period_id)}, {"$set": update_data})
    
    # Invalidate cache setiap kali ada update, untuk memastikan data tetap segar
    await invalidate_cache(ACADEMIC_PERIOD_ACTIVE_CACHE_KEY)
    
    return await db["academic_periods"].find_one({"_id": ObjectId(period_id)})
