# ==============================================================================
# File: app/api/v1/routes/coordination_assignments.py
# Deskripsi: Endpoint API untuk manajemen Koordinator.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_coordination_assignments
from app.schemas.coordination_assignment import CoordinationAssignmentCreate, CoordinationAssignmentPublic

router = APIRouter()

@router.post("/", response_model=CoordinationAssignmentPublic, status_code=status.HTTP_201_CREATED)
async def create_new_coordination(
    coord_in: CoordinationAssignmentCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Membuat penunjukan koordinator baru. Hanya untuk admin."""
    return await crud_coordination_assignments.create_coordination(db, coord_in)
