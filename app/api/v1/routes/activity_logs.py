# ==============================================================================
# File: app/api/v1/routes/activity_logs.py
# Deskripsi: Endpoint API untuk mengambil log aktivitas.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_activity_logs
from app.schemas.activity_log import ActivityLogPublic

router = APIRouter()

@router.get("/", response_model=List[ActivityLogPublic])
async def read_latest_activity_logs(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    limit: int = Query(default=5, ge=1, le=50, description="Jumlah log terbaru yang akan diambil."),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil N log aktivitas terbaru. Hanya bisa diakses oleh admin.
    """
    return await crud_activity_logs.get_latest_logs(db=db, limit=limit)