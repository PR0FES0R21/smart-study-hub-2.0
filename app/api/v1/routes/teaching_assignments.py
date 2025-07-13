# ==============================================================================
# File: app/api/v1/routes/teaching_assignments.py
# Deskripsi: Endpoint API untuk manajemen Penugasan Mengajar.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_teaching_assignments
from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentPublic, TeachingAssignmentWithDetails

router = APIRouter()

@router.post("/", response_model=TeachingAssignmentPublic, status_code=status.HTTP_201_CREATED)
async def create_new_assignment(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    assignment_in: TeachingAssignmentCreate,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Membuat penugasan mengajar baru. Hanya bisa diakses oleh admin.
    """
    return await crud_teaching_assignments.create_teaching_assignment(db=db, assignment=assignment_in)

@router.get("/", response_model=List[TeachingAssignmentWithDetails])
async def read_assignments(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Mengambil daftar semua penugasan mengajar dengan detailnya.
    """
    return await crud_teaching_assignments.get_all_assignments_with_details(db=db)

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_assignment(
    assignment_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghapus penugasan mengajar. Hanya bisa diakses oleh admin.
    """
    deleted = await crud_teaching_assignments.delete_teaching_assignment(db=db, assignment_id=assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Teaching assignment not found")
    return