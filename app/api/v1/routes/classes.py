# ==============================================================================
# File: app/api/v1/routes/classes.py
# Deskripsi: Endpoint API untuk manajemen Kelas.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from bson import ObjectId

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
    search: Optional[str] = Query(None),
    grade_level: Optional[int] = Query(None),
    expertise_id: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000)
):
    """
    Mengambil daftar kelas dengan filter, paginasi, dan pencarian
    menggunakan strategi caching "Katalog ID".
    """
    skip = (page - 1) * limit
    
    if search:
        # Jika ada pencarian, bypass cache
        result = await crud_classes.search_classes_with_details(db, search=search, skip=skip, limit=limit)
        data = result["data"]
        total_items = result["total_items"]
    else:
        # Jika tidak ada pencarian, gunakan strategi cache
        filters = {
            "grade_level": grade_level,
            "expertise_id": expertise_id,
            "academic_year": academic_year
        }
        active_filters = {k: v for k, v in filters.items() if v is not None}
        
        all_filtered_ids_str = await crud_classes.get_filtered_class_ids(db, active_filters)
        total_items = len(all_filtered_ids_str)
        
        ids_for_page_str = all_filtered_ids_str[skip : skip + limit]
        ids_for_page_obj = [ObjectId(id_str) for id_str in ids_for_page_str]
        
        data = await crud_classes.get_classes_details_by_ids(db, class_ids=ids_for_page_obj)

    total_pages = (total_items + limit - 1) // limit

    # Statistik total per angkatan (contoh sederhana, bisa dioptimalkan)
    grade_10_total = await db["classes"].count_documents({"grade_level": 10})
    grade_11_total = await db["classes"].count_documents({"grade_level": 11})
    grade_12_total = await db["classes"].count_documents({"grade_level": 12})

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": data,
        "grade_10_total": grade_10_total,
        "grade_11_total": grade_11_total,
        "grade_12_total": grade_12_total,
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