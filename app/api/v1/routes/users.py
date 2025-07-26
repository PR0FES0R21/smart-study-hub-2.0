# ==============================================================================
# File: app/api/v1/routes/users.py
# --- DIUBAH --- (Menambahkan parameter 'role')
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_users
from app.schemas.user import (
    UserCreate, UserPublic, UserUpdate, 
    DataTablesUserResponse, PasswordChange, 
    SelfDataUpdate, UserWithDetails
)
from app.schemas.user import PaginatedUserResponse
from app.core.logging import create_activity_log
from app.core import security

router = APIRouter()

@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    user_in: UserCreate,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Membuat user baru beserta profilnya. Hanya bisa diakses oleh admin.
    Validasi data spesifik peran (class_id vs department_id) ditangani di level skema.
    """
    # Validasi bisnis yang masih relevan di sini
    if "student" in user_in.roles and not user_in.profile.class_id:
        raise HTTPException(status_code=400, detail="Siswa harus memiliki ID kelas.")
    if ("teacher" in user_in.roles or "admin" in user_in.roles) and not user_in.profile.department_id:
        raise HTTPException(status_code=400, detail="Guru atau admin harus memiliki ID departemen.")
    
    created_user = await crud_users.create_user_and_profile(db=db, user_in=user_in)
    return created_user

@router.get("/", response_model=PaginatedUserResponse)
async def read_all_users(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    role: Optional[str] = None,
    grade_level: Optional[int] = None,
    expertise_id: Optional[str] = None,
    class_id: Optional[str] = None,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000)
):
    """
    Mengambil daftar user dengan filter, paginasi, dan pencarian
    menggunakan strategi caching "Katalog ID".
    """
    skip = (page - 1) * limit
    
    # Build filters dict
    filters = {
        "role": role, 
        "grade_level": grade_level, 
        "expertise_id": expertise_id, 
        "class_id": class_id
    }
    active_filters = {k: v for k, v in filters.items() if v is not None}
    
    if search:
        # Jika ada pencarian, bypass cache dan query langsung ke DB dengan filter
        result = await crud_users.search_users_with_details(
            db, 
            search=search, 
            skip=skip, 
            limit=limit,
            filters=active_filters
        )
        data = result["data"]
        total_items = result["total_items"]
    else:
        # Jika tidak ada pencarian, gunakan strategi cache
        all_filtered_ids_str = await crud_users.get_filtered_user_ids(db, active_filters)
        total_items = len(all_filtered_ids_str)
        
        ids_for_page_str = all_filtered_ids_str[skip : skip + limit]
        ids_for_page_obj = [ObjectId(id_str) for id_str in ids_for_page_str]
        
        data = await crud_users.get_users_details_by_ids(db, user_ids=ids_for_page_obj)
    
    total_pages = (total_items + limit - 1) // limit
    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": data
    }

@router.get("/me", response_model=UserWithDetails)
async def debug_read_own_data(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Endpoint tes sementara untuk mengisolasi masalah.
    Ini memanggil fungsi CRUD secara langsung dan mengembalikan hasilnya.
    """
    print(f"DEBUG: Memulai get_user_with_details_by_id untuk user_id: {current_user['_id']}")
    user_details = await crud_users.get_user_with_details_by_id(db, user_id=current_user["_id"])
    
    if not user_details:
        print("DEBUG: get_user_with_details_by_id mengembalikan None.")
        raise HTTPException(status_code=404, detail="DEBUG: User details not found in aggregation.")
    
    print("DEBUG: Data berhasil diambil dari agregasi.")
    return user_details

@router.put("/me", response_model=UserPublic)
async def update_own_data(
    data_in: SelfDataUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """
    Endpoint untuk pengguna memperbarui data mereka sendiri yang diizinkan
    (email, nomor telepon, alamat).
    """
    updated_user = await crud_users.update_self_data(db, current_user=current_user, data_in=data_in)
    
    background_tasks.add_task(
        create_activity_log,
        db=db, request=request, user_data=current_user,
        activity="SELF_UPDATE_PROFILE",
        description=f"User '{current_user['login_id']}' updated their profile information."
    )
    
    return updated_user

@router.get("/{user_id}", response_model=UserWithDetails)
async def read_user_by_id(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil detail satu user. Hanya bisa diakses oleh admin.
    """
    user = await crud_users.get_user_with_details_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserPublic)
async def update_existing_user(
    user_id: str,
    user_in: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memperbarui data user. Hanya bisa diakses oleh admin.
    """
    user = await crud_users.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await crud_users.update_user_and_profile(db=db, user_id=user_id, user_in=user_in)
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghapus user. Hanya bisa diakses oleh admin.
    """
    deleted = await crud_users.delete_user_and_profile(db=db, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found or could not be deleted")
    return

@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_user_password(
    password_in: PasswordChange,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    if not security.verify_password(password_in.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    await crud_users.update_user_password(db, user_id=current_user["_id"], new_password=password_in.new_password)
    
    background_tasks.add_task(
        create_activity_log,
        db=db, request=request, user_data=current_user,
        activity="PASSWORD_CHANGE",
        description=f"User '{current_user['login_id']}' successfully changed their password."
    )

@router.put("/{user_id}/deactivate", response_model=UserPublic)
async def deactivate_user_account(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """
    Menonaktifkan akun pengguna. Hanya untuk admin.
    """
    user_to_deactivate = await crud_users.get_user_by_id(db, user_id)
    if not user_to_deactivate:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_to_deactivate["_id"] == current_user["_id"]:
        raise HTTPException(status_code=400, detail="Admin cannot deactivate their own account.")

    deactivated_user = await crud_users.set_user_active_status(db, user_id=user_id, is_active=False)
    
    background_tasks.add_task(
        create_activity_log,
        db=db, request=request, user_data=current_user,
        activity="USER_DEACTIVATED",
        description=f"Admin '{current_user['login_id']}' deactivated user '{deactivated_user['login_id']}'."
    )
    
    return deactivated_user

@router.put("/{user_id}/reactivate", response_model=UserPublic)
async def reactivate_user_account(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """
    Mengaktifkan kembali akun pengguna. Hanya untuk admin.
    """
    user_to_reactivate = await crud_users.get_user_by_id(db, user_id)
    if not user_to_reactivate:
        raise HTTPException(status_code=404, detail="User not found")

    reactivated_user = await crud_users.set_user_active_status(db, user_id=user_id, is_active=True)
    
    background_tasks.add_task(
        create_activity_log,
        db=db, request=request, user_data=current_user,
        activity="USER_REACTIVATED",
        description=f"Admin '{current_user['login_id']}' reactivated user '{reactivated_user['login_id']}'."
    )
    
    return reactivated_user