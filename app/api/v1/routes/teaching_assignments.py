# ==============================================================================
# File: app/api/v1/routes/teaching_assignments.py
# Deskripsi: Endpoint API untuk manajemen Penugasan Mengajar (Updated with academic_period_id).
# --- DIPERBARUI ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_teaching_assignments
from app.schemas.teaching_assignment import (
    TeachingAssignmentCreate, TeachingAssignmentPublic, 
    TeachingAssignmentWithDetails, BulkUpdateRequest,
    PaginatedTeachingAssignmentResponse, TeacherTeachingSummary
)
from app.schemas.task import TaskStatus
from app.core.celery_app import celery_app


router = APIRouter()

@router.post("/", response_model=TeachingAssignmentPublic, status_code=status.HTTP_201_CREATED)
async def create_new_assignment(
    assignment_in: TeachingAssignmentCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    current_academic_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Membuat teaching assignment baru untuk periode akademik aktif.
    """
    academic_period_id = str(current_academic_period["_id"])
    return await crud_teaching_assignments.create_teaching_assignment(
        db=db, 
        assignment=assignment_in, 
        academic_period_id=academic_period_id
    )

@router.get("/", response_model=PaginatedTeachingAssignmentResponse)
async def read_assignments(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user),
    current_academic_period: dict = Depends(deps.get_current_academic_period),
    academic_period_id: Optional[str] = Query(None, description="Override academic period (admin only)"),
    class_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search in teacher name, subject name/code, class name, or expertise program"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000)
):
    """
    Mengambil daftar penugasan mengajar dengan filter dan paginasi.
    Default menggunakan periode akademik aktif, admin bisa override dengan parameter.
    """
    # Tentukan academic period yang akan digunakan
    target_academic_period_id = academic_period_id
    
    # Jika admin menyediakan academic_period_id, validasi akses
    if academic_period_id and "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=403, 
            detail="Only admin can access data from different academic periods"
        )
    
    # Jika tidak ada override, gunakan periode aktif
    if not target_academic_period_id:
        target_academic_period_id = str(current_academic_period["_id"])
    
    # Validasi academic_period_id jika disediakan
    if academic_period_id:
        if not ObjectId.is_valid(academic_period_id):
            raise HTTPException(status_code=400, detail="Invalid academic_period_id format")
        
        # Cek apakah academic period benar-benar ada
        ap_exists = await db["academic_periods"].find_one({"_id": ObjectId(academic_period_id)})
        if not ap_exists:
            raise HTTPException(status_code=404, detail="Academic period not found")
    
    skip = (page - 1) * limit
    
    filters = {"class_id": class_id, "teacher_id": teacher_id, "search": search}
    active_filters = {k: v for k, v in filters.items() if v is not None}

    all_filtered_ids_str = await crud_teaching_assignments.get_filtered_assignment_ids(
        db, target_academic_period_id, active_filters
    )
    total_items = len(all_filtered_ids_str)
    
    ids_for_page_str = all_filtered_ids_str[skip : skip + limit]
    ids_for_page_obj = [ObjectId(id_str) for id_str in ids_for_page_str]
    
    data = await crud_teaching_assignments.get_assignments_details_by_ids(db, assignment_ids=ids_for_page_obj)

    total_pages = (total_items + limit - 1) // limit

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": data
    }

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_assignment(
    assignment_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghapus teaching assignment berdasarkan ID.
    """
    deleted = await crud_teaching_assignments.delete_teaching_assignment(db=db, assignment_id=assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Teaching assignment not found")
    return

@router.post("/bulk-update", response_model=TaskStatus, status_code=202)
async def bulk_update_assignments(
    request_in: BulkUpdateRequest,
    current_user: dict = Depends(deps.get_current_active_admin),
    current_academic_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Memulai proses operasi massal (create, update, delete) untuk penugasan mengajar
    di latar belakang. Semua operasi dilakukan dalam periode akademik aktif.
    """
    # Mengubah objek Pydantic menjadi dictionary biasa agar aman untuk Celery
    actions_dict = [action.model_dump(mode='json') for action in request_in.actions]
    admin_user_id = str(current_user["_id"])
    academic_period_id = str(current_academic_period["_id"])

    task = celery_app.send_task(
        "app.tasks.bulk_operations_tasks.bulk_update_assignments_task",
        args=[actions_dict, admin_user_id, academic_period_id]
    )
    return {"task_id": task.id, "status": "Processing"}

@router.get("/teacher/teaching-summary", response_model=TeacherTeachingSummary)
async def get_teacher_teaching_summary(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_academic_period: dict = Depends(deps.get_current_academic_period),
    academic_period_id: Optional[str] = Query(None, description="Override academic period (admin only)")
):
    """
    Mengambil ringkasan kelas dan mata pelajaran yang diajar oleh guru.
    Data dikelompokkan berdasarkan kelas, termasuk detail expertise program dan jumlah siswa.
    Default menggunakan periode akademik aktif.
    """
    # Tentukan academic period yang akan digunakan
    target_academic_period_id = academic_period_id
    
    # Jika menyediakan academic_period_id, validasi akses (hanya admin atau guru bisa akses periode lain)
    if academic_period_id and "admin" not in current_user.get("roles", []):
        # Teacher bisa akses periode lain untuk melihat riwayat mengajar
        pass
    
    # Jika tidak ada override, gunakan periode aktif
    if not target_academic_period_id:
        target_academic_period_id = str(current_academic_period["_id"])
    
    # Validasi academic_period_id jika disediakan
    if academic_period_id:
        if not ObjectId.is_valid(academic_period_id):
            raise HTTPException(status_code=400, detail="Invalid academic_period_id format")
        
        # Cek apakah academic period benar-benar ada
        ap_exists = await db["academic_periods"].find_one({"_id": ObjectId(academic_period_id)})
        if not ap_exists:
            raise HTTPException(status_code=404, detail="Academic period not found")
    
    teacher_id = str(current_user["_id"])
    classes_data = await crud_teaching_assignments.get_teacher_teaching_summary(
        db=db, 
        teacher_id=teacher_id, 
        academic_period_id=target_academic_period_id
    )
    
    return {"classes": classes_data}