# ==============================================================================
# File: app/api/v1/routes/subjects.py
# Deskripsi: Endpoint API untuk manajemen Mata Pelajaran.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_subjects
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectPublic, PaginatedSubjectResponse


router = APIRouter()

@router.post("/", response_model=SubjectPublic, status_code=status.HTTP_201_CREATED)
async def create_new_subject(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    subject_in: SubjectCreate,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Membuat mata pelajaran baru. Hanya bisa diakses oleh admin.
    """
    return await crud_subjects.create_subject(db=db, subject=subject_in)

@router.get("/", response_model=PaginatedSubjectResponse)
async def read_subjects(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000)
):
    """
    Mengambil daftar mata pelajaran dengan paginasi dan pencarian
    menggunakan strategi caching "Katalog ID".
    """
    skip = (page - 1) * limit
    
    if search:
        # Jika ada pencarian, bypass cache dan query langsung ke DB
        result = await crud_subjects.search_subjects(db, search=search, skip=skip, limit=limit)
        data = result["data"]
        total_items = result["total_items"]
    else:
        # Jika tidak ada pencarian, gunakan strategi cache
        all_ids_str = await crud_subjects.get_all_subject_ids(db)
        total_items = len(all_ids_str)
        
        # Lakukan slicing pada daftar ID
        ids_for_page_str = all_ids_str[skip : skip + limit]
        ids_for_page_obj = [ObjectId(id_str) for id_str in ids_for_page_str]
        
        # Ambil data lengkap untuk ID di halaman ini
        data = await crud_subjects.get_subjects_by_ids(db, ids=ids_for_page_obj)

    total_pages = (total_items + limit - 1) // limit

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": data
    }

@router.get("/{subject_id}", response_model=SubjectPublic)
async def read_subject_by_id(
    subject_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Mengambil detail satu mata pelajaran.
    """
    subject = await crud_subjects.get_subject_by_id(db=db, subject_id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.put("/{subject_id}", response_model=SubjectPublic)
async def update_existing_subject(
    subject_id: str,
    subject_in: SubjectUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memperbarui mata pelajaran. Hanya bisa diakses oleh admin.
    """
    subject = await crud_subjects.get_subject_by_id(db, subject_id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    updated_subject = await crud_subjects.update_subject(db=db, subject_id=subject_id, subject_update=subject_in)
    return updated_subject

@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_subject(
    subject_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghapus mata pelajaran. Hanya bisa diakses oleh admin.
    """
    deleted = await crud_subjects.delete_subject(db=db, subject_id=subject_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subject not found")
    return