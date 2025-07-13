# ==============================================================================
# File: app/crud/crud_activity_logs.py
# Deskripsi: Fungsi CRUD untuk collection 'activity_logs'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, List
from datetime import datetime
import pymongo


async def create_log(db: AsyncIOMotorDatabase, log_data: Dict[str, Any]):
    """Menyimpan satu dokumen log ke database."""
    log_data["created_at"] = datetime.utcnow()
    await db["activity_logs"].insert_one(log_data)

async def get_latest_logs(db: AsyncIOMotorDatabase, limit: int = 5) -> List[dict]:
    """Mengambil N log aktivitas terbaru."""
    logs_cursor = db["activity_logs"].find().sort("created_at", pymongo.DESCENDING).limit(limit)
    return await logs_cursor.to_list(length=limit)