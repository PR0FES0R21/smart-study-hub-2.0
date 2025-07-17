# ==============================================================================
# File: app/api/v1/routes/academic_periods.py
# Deskripsi: Endpoint API untuk manajemen Periode Akademik.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_academic_periods
from app.schemas.academic_period import AcademicPeriodCreate, AcademicPeriodUpdate, AcademicPeriodPublic

router = APIRouter()

@router.post("/", response_model=AcademicPeriodPublic, status_code=status.HTTP_201_CREATED)
async def create_new_academic_period(
    period_in: AcademicPeriodCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Membuat periode akademik baru. Hanya untuk admin."""
    return await crud_academic_periods.create_academic_period(db=db, period=period_in)

@router.get("/", response_model=List[AcademicPeriodPublic])
async def read_all_academic_periods(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """Mengambil semua periode akademik."""
    return await crud_academic_periods.get_all_periods(db=db)

@router.put("/{period_id}", response_model=AcademicPeriodPublic)
async def update_existing_academic_period(
    period_id: str,
    period_in: AcademicPeriodUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Memperbarui periode akademik. Hanya untuk admin."""
    updated_period = await crud_academic_periods.update_academic_period(db, period_id, period_in)
    if not updated_period:
        raise HTTPException(status_code=404, detail="Academic period not found")
    return updated_period

@router.get("/active", response_model=AcademicPeriodPublic)
async def get_current_active_period_route(
    active_period: dict = Depends(deps.get_current_academic_period)
):
    """Mengambil detail periode akademik yang sedang aktif dari cache."""
    return active_period

@router.post("/{period_id}/set-active", response_model=AcademicPeriodPublic)
async def set_period_as_active(
    period_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Mengatur sebuah periode akademik menjadi aktif."""
    new_active_period = await crud_academic_periods.set_active_period(db, period_id)
    if not new_active_period:
        raise HTTPException(status_code=404, detail="Academic period not found")
    return new_active_period