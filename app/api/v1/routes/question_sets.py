# ==============================================================================
# File: app/api/v1/routes/question_sets.py
# Deskripsi: Endpoint API untuk manajemen Paket Soal (Enhanced with Teaching Assignment Access).
# ==============================================================================
from fastapi import APIRouter, Depends, status, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_sets
from app.schemas.question_set import (
    QuestionSetCreate, 
    QuestionSetUpdate,
    QuestionSetPublic,
    QuestionSetSummary,
    QuestionSetAddQuestions,
    QuestionSetRemoveQuestions,
    QuestionSetStatus,
    PermissionManagement
)

router = APIRouter()

@router.post("/", response_model=QuestionSetPublic, status_code=status.HTTP_201_CREATED)
async def create_new_question_set(
    qset_in: QuestionSetCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Membuat paket soal baru. 
    Hanya koordinator yang bisa membuat paket soal.
    Koordinator menentukan apakah question set public atau private.
    """
    coordinator_id = ObjectId(current_user["id"])
    
    # TODO: Add validation to check if user is actually a coordinator
    # Example: await validate_coordinator_role(db, coordinator_id, qset_in.subject_id)
    
    return await crud_question_sets.create_question_set(db, qset_in, coordinator_id)

@router.get("/", response_model=List[QuestionSetSummary])
async def get_accessible_question_sets(
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    status: Optional[QuestionSetStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in question set names"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil semua question sets yang dapat diakses oleh user.
    
    Access logic:
    1. Public question sets - semua guru bisa akses
    2. Private question sets - hanya guru yang mengajar subject & grade yang sama
    3. Question sets dengan explicit permission
    4. Question sets yang dibuat sendiri
    
    Semua parameter adalah optional filters.
    """
    user_id = ObjectId(current_user["id"])
    subject_obj_id = ObjectId(subject_id) if subject_id else None
    
    return await crud_question_sets.get_accessible_question_sets(
        db,
        user_id,
        subject_id=subject_obj_id,
        grade_level=grade_level,
        status=status,
        search=search,
        is_public=is_public
    )

@router.get("/my", response_model=List[QuestionSetSummary])
async def get_my_question_sets(
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil paket soal yang dibuat oleh current user.
    """
    user_id = ObjectId(current_user["id"])
    subject_obj_id = ObjectId(subject_id) if subject_id else None
    
    return await crud_question_sets.get_my_question_sets(
        db, 
        user_id, 
        subject_id=subject_obj_id
    )

@router.get("/{question_set_id}", response_model=QuestionSetPublic)
async def get_question_set_detail(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil detail paket soal berdasarkan ID.
    Dengan access control berdasarkan public/private dan teaching assignment.
    """
    user_id = ObjectId(current_user["id"])
    
    question_set = await crud_question_sets.get_question_set_by_id(
        db, 
        ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    return question_set

@router.put("/{question_set_id}", response_model=QuestionSetPublic)
async def update_question_set(
    question_set_id: str,
    qset_update: QuestionSetUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Update paket soal. 
    Hanya koordinator creator atau user dengan edit permission yang bisa mengedit.
    """
    user_id = ObjectId(current_user["id"])
    
    updated_qset = await crud_question_sets.update_question_set(
        db,
        ObjectId(question_set_id),
        qset_update,
        user_id
    )
    
    if not updated_qset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    return updated_qset

@router.post("/{question_set_id}/questions", response_model=QuestionSetPublic)
async def add_questions_to_set(
    question_set_id: str,
    questions_data: QuestionSetAddQuestions,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menambahkan soal ke paket soal. 
    Hanya koordinator creator atau user dengan manage_questions permission.
    """
    user_id = ObjectId(current_user["id"])
    
    return await crud_question_sets.add_questions_to_set(
        db,
        ObjectId(question_set_id),
        questions_data.question_ids,
        user_id
    )

@router.delete("/{question_set_id}/questions", response_model=QuestionSetPublic)
async def remove_questions_from_set(
    question_set_id: str,
    questions_data: QuestionSetRemoveQuestions,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menghapus soal dari paket soal.
    Hanya koordinator creator atau user dengan manage_questions permission.
    """
    user_id = ObjectId(current_user["id"])
    
    return await crud_question_sets.remove_questions_from_set(
        db,
        ObjectId(question_set_id),
        questions_data.question_ids,
        user_id
    )

@router.post("/{question_set_id}/publish", response_model=QuestionSetPublic)
async def publish_question_set(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Publish paket soal (mengubah status dari DRAFT ke PUBLISHED).
    Hanya koordinator creator atau user dengan publish permission.
    """
    user_id = ObjectId(current_user["id"])
    
    # Update status ke PUBLISHED
    qset_update = QuestionSetUpdate(status=QuestionSetStatus.PUBLISHED)
    
    updated_qset = await crud_question_sets.update_question_set(
        db,
        ObjectId(question_set_id),
        qset_update,
        user_id
    )
    
    if not updated_qset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    return updated_qset

@router.post("/{question_set_id}/archive", response_model=QuestionSetPublic)
async def archive_question_set(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Archive paket soal (mengubah status ke ARCHIVED).
    Hanya koordinator creator atau user dengan publish permission.
    """
    user_id = ObjectId(current_user["id"])
    
    # Update status ke ARCHIVED
    qset_update = QuestionSetUpdate(status=QuestionSetStatus.ARCHIVED)
    
    updated_qset = await crud_question_sets.update_question_set(
        db,
        ObjectId(question_set_id),
        qset_update,
        user_id
    )
    
    if not updated_qset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    return updated_qset

@router.put("/{question_set_id}/permissions", response_model=QuestionSetPublic)
async def manage_question_set_permissions(
    question_set_id: str,
    permission_data: PermissionManagement,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Grant atau revoke permissions ke user lain.
    Hanya creator question set yang bisa manage permissions.
    """
    requester_id = ObjectId(current_user["id"])
    
    return await crud_question_sets.manage_permissions(
        db,
        ObjectId(question_set_id),
        permission_data.user_id,
        permission_data.permissions,
        permission_data.action,
        requester_id
    )

@router.delete("/{question_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_set(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menghapus paket soal.
    Hanya creator yang bisa menghapus, dengan safety checks untuk exam yang aktif.
    """
    user_id = ObjectId(current_user["id"])
    
    success = await crud_question_sets.delete_question_set(
        db,
        ObjectId(question_set_id),
        user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )

@router.get("/{question_set_id}/questions", response_model=List[dict])
async def get_questions_in_set(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil semua soal dalam paket soal.
    Dengan access control sama seperti view question set.
    """
    user_id = ObjectId(current_user["id"])
    
    # Check access permission dulu
    question_set = await crud_question_sets.get_question_set_by_id(
        db, 
        ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Get questions
    question_ids = question_set.get("question_ids", [])
    if not question_ids:
        return []
    
    questions = await db["questions"].find(
        {"_id": {"$in": question_ids}}
    ).to_list(None)
    
    return questions

@router.get("/{question_set_id}/stats", response_model=dict)
async def get_question_set_statistics(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil statistik detail untuk paket soal.
    Dengan access control sama seperti view question set.
    """
    user_id = ObjectId(current_user["id"])
    
    # Check access permission dulu
    question_set = await crud_question_sets.get_question_set_by_id(
        db, 
        ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Get detailed statistics
    stats = {
        "basic": question_set.get("metadata", {}),
        "usage": {
            "times_used_in_exams": await db["exams"].count_documents({
                "question_set_id": ObjectId(question_set_id)
            }),
            "active_exams": await db["exams"].count_documents({
                "question_set_id": ObjectId(question_set_id),
                "status": {"$in": ["scheduled", "active"]}
            })
        },
        "permissions": {
            "can_edit": user_id in question_set.get("access_permissions", {}).get("can_edit", []) or 
                       question_set.get("created_by_coordinator_id") == user_id,
            "can_manage_questions": user_id in question_set.get("access_permissions", {}).get("can_manage_questions", []) or 
                                  question_set.get("created_by_coordinator_id") == user_id,
            "can_publish": user_id in question_set.get("access_permissions", {}).get("can_publish", []) or 
                          question_set.get("created_by_coordinator_id") == user_id,
            "is_creator": question_set.get("created_by_coordinator_id") == user_id
        }
    }
    
    return stats

@router.post("/{question_set_id}/duplicate", response_model=QuestionSetPublic)
async def duplicate_question_set(
    question_set_id: str,
    new_name: Optional[str] = Query(None, description="Name for duplicated question set"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Duplicate paket soal yang accessible.
    Hasil duplicate selalu private dan owned by current user.
    """
    user_id = ObjectId(current_user["id"])
    
    # Check access permission dulu
    original_qset = await crud_question_sets.get_question_set_by_id(
        db, 
        ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not original_qset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Create duplicate
    duplicate_name = new_name or f"Copy of {original_qset['name']}"
    
    duplicate_data = QuestionSetCreate(
        name=duplicate_name,
        subject_id=original_qset["subject_id"],
        grade_level=original_qset["grade_level"],
        description=f"Duplicated from: {original_qset['name']}",
        is_public=False,  # Always create as private
        tags=original_qset.get("metadata", {}).get("tags", [])
    )
    
    # Create new question set
    new_qset = await crud_question_sets.create_question_set(db, duplicate_data, user_id)
    
    # Copy questions if any
    if original_qset.get("question_ids"):
        await crud_question_sets.add_questions_to_set(
            db,
            new_qset["_id"],
            original_qset["question_ids"],
            user_id
        )
    
    return await crud_question_sets.get_question_set_by_id(db, new_qset["_id"])