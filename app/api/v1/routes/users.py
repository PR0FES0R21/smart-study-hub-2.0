# ==============================================================================
# File: app/api/v1/routes/users.py
# --- DIUBAH --- (Menambahkan parameter 'role')
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from app.api.v1 import deps
from app.crud import crud_users
from app.schemas.user import (
    UserCreate, UserPublic, UserUpdate, 
    DataTablesUserResponse, PasswordChange, 
    SelfDataUpdate, UserWithDetails
)
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
    """
    if "student" in user_in.roles and not user_in.profile.class_id:
        raise HTTPException(status_code=400, detail="Siswa harus memiliki ID kelas.")
    if ("teacher" in user_in.roles) and not user_in.profile.department_id:
        raise HTTPException(status_code=400, detail="Guru harus memiliki ID departemen.")
    
    created_user = await crud_users.create_user_and_profile(db=db, user_in=user_in)
    return created_user

@router.get("/", response_model=DataTablesUserResponse)
async def read_all_users_for_datatables(
    request: Request,
    role: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil daftar semua user dengan data profil tergabung.
    """
    dt_params = dict(request.query_params)
    response_data = await crud_users.get_users_with_profiles_for_datatables(
        db=db, dt_params=dt_params, role=role
    )
    return response_data

@router.get("/{user_id}", response_model=UserPublic)
async def read_user_by_id(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Mengambil detail satu user. Hanya bisa diakses oleh admin.
    """
    user = await crud_users.get_user_by_id(db=db, user_id=user_id)
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
    
    updated_user = await crud_users.update_user(db=db, user_id=user_id, user_update=user_in)
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
    user = await crud_users.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    deleted = await crud_users.delete_user(db=db, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found during deletion")
    return

@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_user_password(
    password_in: PasswordChange,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """
    Endpoint untuk pengguna yang sedang login mengubah password mereka sendiri.
    """
    # 1. Verifikasi password saat ini
    if not security.verify_password(password_in.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # 2. Verifikasi password baru sudah dilakukan oleh Pydantic validator
    
    # 3. Update password di database
    await crud_users.update_user_password(db, user_id=current_user["_id"], new_password=password_in.new_password)
    
    # 4. Buat log aktivitas
    background_tasks.add_task(
        create_activity_log,
        db=db,
        request=request,
        user_data=current_user,
        activity="PASSWORD_CHANGE",
        description=f"User '{current_user['login_id']}' successfully changed their password."
    )

@router.get("/me", response_model=UserWithDetails)
async def read_own_data(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Endpoint untuk pengguna mengambil data lengkap mereka sendiri.
    """
    # Kita menggunakan fungsi CRUD baru untuk mengambil data user beserta profilnya
    user_details = await crud_users.get_user_with_details_by_id(db, user_id=current_user["_id"])
    if not user_details:
        raise HTTPException(status_code=404, detail="User not found")
    return user_details

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