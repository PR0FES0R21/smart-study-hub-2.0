# ==============================================================================
# File: app/crud/crud_system_state.py
# Deskripsi: Fungsi CRUD untuk collection 'system_state'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any
from datetime import datetime

async def get_task_state(db: AsyncIOMotorDatabase, task_name: str) -> dict | None:
    """Mengambil status tugas dari database."""
    return await db["system_state"].find_one({"task_name": task_name})

async def update_task_state(db: AsyncIOMotorDatabase, task_name: str, updates: Dict[str, Any]):
    """Memperbarui status tugas di database."""
    updates["updated_at"] = datetime.utcnow()
    await db["system_state"].update_one(
        {"task_name": task_name},
        {"$set": updates},
        upsert=True # Buat jika belum ada
    )