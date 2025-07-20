# ==============================================================================
# File: app/api/v1/routes/classes.py
# Deskripsi: Endpoint API untuk manajemen Kelas.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from app.api.v1 import deps
from app.crud import crud_classes
from app.schemas.classes import ClassCreate, ClassUpdate, ClassPublic, PaginatedClassResponse

router = APIRouter()

@router.post("/", response_model=ClassPublic, status_code=status.HTTP_201_CREATED)
async def create_new_class(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    class_in: ClassCreate,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Membuat kelas baru. Hanya bisa diakses oleh admin.
    """
    return await crud_classes.create_class(db=db, class_in=class_in)

@router.get("/", response_model=PaginatedClassResponse)
async def read_classes(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user),
    # --- DITAMBAHKAN: Parameter filter, paginasi, dan pencarian ---
    search: Optional[str] = Query(None),
    grade_level: Optional[int] = Query(None),
    expertise_id: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Mengambil daftar kelas dengan filter dinamis, paginasi, dan pencarian.
    """
    skip = (page - 1) * limit
    result = await crud_classes.get_paginated_classes_with_details(
        db=db, 
        skip=skip, 
        limit=limit, 
        search=search,
        grade_level=grade_level,
        expertise_id=expertise_id,
        academic_year=academic_year
    )
    
    total_items = result["total_items"]
    total_pages = (total_items + limit - 1) // limit

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": result["data"],
        "grade_10_total": result["grade_10_total"],
        "grade_11_total": result["grade_11_total"],
        "grade_12_total": result["grade_12_total"],
    }

@router.get("/{class_id}", response_model=ClassPublic)
async def read_class_by_id(
    class_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Mengambil detail satu kelas.
    """
    class_obj = await crud_classes.get_class_by_id(db=db, class_id=class_id)
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_obj

@router.put("/{class_id}", response_model=ClassPublic)
async def update_existing_class(
    class_id: str,
    class_in: ClassUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memperbarui kelas. Hanya bisa diakses oleh admin.
    """
    class_obj = await crud_classes.get_class_by_id(db, class_id=class_id)
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    updated_class = await crud_classes.update_class(db=db, class_id=class_id, class_update=class_in)
    return updated_class

@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_class(
    class_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghapus kelas. Hanya bisa diakses oleh admin.
    """
    deleted = await crud_classes.delete_class(db=db, class_id=class_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return