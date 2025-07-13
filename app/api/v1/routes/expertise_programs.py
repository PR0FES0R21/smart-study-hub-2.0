# ==============================================================================
# File: app/api/v1/routes/expertise_programs.py
# Deskripsi: Endpoint API untuk manajemen Jurusan.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_expertise_programs
from app.schemas.expertise_program import ExpertiseProgramCreate, ExpertiseProgramUpdate, ExpertiseProgramPublic

router = APIRouter()

@router.post("/", response_model=ExpertiseProgramPublic, status_code=status.HTTP_201_CREATED)
async def create_new_expertise_program(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    program_in: ExpertiseProgramCreate,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Membuat jurusan baru. Hanya bisa diakses oleh admin.
    """
    return await crud_expertise_programs.create_expertise_program(db=db, program=program_in)

@router.get("/", response_model=List[ExpertiseProgramPublic])
async def read_expertise_programs(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Mengambil daftar semua jurusan.
    """
    return await crud_expertise_programs.get_all_expertise_programs(db=db)

@router.get("/{program_id}", response_model=ExpertiseProgramPublic)
async def read_expertise_program_by_id(
    program_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Mengambil detail satu jurusan.
    """
    program = await crud_expertise_programs.get_expertise_program_by_id(db=db, program_id=program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Expertise Program not found")
    return program

@router.put("/{program_id}", response_model=ExpertiseProgramPublic)
async def update_existing_expertise_program(
    program_id: str,
    program_in: ExpertiseProgramUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memperbarui jurusan. Hanya bisa diakses oleh admin.
    """
    program = await crud_expertise_programs.get_expertise_program_by_id(db, program_id=program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Expertise Program not found")
    
    updated_program = await crud_expertise_programs.update_expertise_program(db=db, program_id=program_id, program_update=program_in)
    return updated_program

@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_expertise_program(
    program_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghapus jurusan. Hanya bisa diakses oleh admin.
    """
    deleted = await crud_expertise_programs.delete_expertise_program(db=db, program_id=program_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expertise Program not found")
    return