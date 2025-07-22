# ==============================================================================
# File: app/api/v1/routes/teaching_assignments.py
# Deskripsi: Endpoint API untuk manajemen Penugasan Mengajar.
# --- DITAMBAHKAN ---
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
    PaginatedTeachingAssignmentResponse
)
from app.schemas.task import TaskStatus
from app.core.celery_app import celery_app


router = APIRouter()

@router.post("/", response_model=TeachingAssignmentPublic, status_code=status.HTTP_201_CREATED)
async def create_new_assignment(
    assignment_in: TeachingAssignmentCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    return await crud_teaching_assignments.create_teaching_assignment(db=db, assignment=assignment_in)

@router.get("/", response_model=PaginatedTeachingAssignmentResponse)
async def read_assignments(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user),
    class_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Mengambil daftar penugasan mengajar dengan filter dan paginasi.
    """
    skip = (page - 1) * limit
    
    filters = {"class_id": class_id, "teacher_id": teacher_id}
    active_filters = {k: v for k, v in filters.items() if v is not None}

    all_filtered_ids_str = await crud_teaching_assignments.get_filtered_assignment_ids(db, active_filters)
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
    deleted = await crud_teaching_assignments.delete_teaching_assignment(db=db, assignment_id=assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Teaching assignment not found")
    return

@router.post("/bulk-update", response_model=TaskStatus, status_code=202)
async def bulk_update_assignments(
    request_in: BulkUpdateRequest,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memulai proses operasi massal (create, update, delete) untuk penugasan mengajar
    di latar belakang.
    """
    # Mengubah objek Pydantic menjadi dictionary biasa agar aman untuk Celery
    actions_dict = [action.model_dump(mode='json') for action in request_in.actions]
    admin_user_id = str(current_user["_id"])

    task = celery_app.send_task(
        "app.tasks.bulk_operations_tasks.bulk_update_assignments_task",
        args=[actions_dict, admin_user_id]
    )
    return {"task_id": task.id, "status": "Processing"}