# ==============================================================================
# File: app/api/v1/routes/question_sets.py
# Deskripsi: Endpoint API untuk manajemen Paket Soal (Enhanced).
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
    QuestionSetStatus
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
    """
    coordinator_id = ObjectId(current_user["id"])
    
    # TODO: Add validation to check if user is actually a coordinator
    # Example: await validate_coordinator_role(db, coordinator_id, qset_in.subject_id)
    
    return await crud_question_sets.create_question_set(db, qset_in, coordinator_id)

@router.get("/", response_model=List[QuestionSetSummary])
async def get_question_sets(
    subject_id: str,
    grade_level: int,
    status: Optional[QuestionSetStatus] = Query(None, description="Filter by status"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil daftar paket soal berdasarkan mata pelajaran dan jenjang kelas.
    Dengan access control berdasarkan role dan permissions.
    """
    user_id = ObjectId(current_user["id"])
    
    return await crud_question_sets.get_question_sets(
        db, 
        ObjectId(subject_id), 
        grade_level,
        status=status,
        user_id=user_id
    )

@router.get("/my", response_model=List[QuestionSetSummary])
async def get_my_question_sets(
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil paket soal yang dibuat oleh koordinator (current user).
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
    Dengan access control.
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
    Update paket soal. Hanya koordinator yang bisa mengedit.
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
    Hanya koordinator yang bisa menambahkan soal.
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
    Hanya koordinator yang bisa menghapus soal.
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
    Mempublikasikan paket soal. 
    Hanya koordinator yang bisa publish.
    """
    user_id = ObjectId(current_user["id"])
    
    # Validate that question set has questions before publishing
    question_set = await crud_question_sets.get_question_set_by_id(
        db, ObjectId(question_set_id), user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    if not question_set.get("question_ids") or len(question_set["question_ids"]) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish empty question set"
        )
    
    update_data = QuestionSetUpdate(status=QuestionSetStatus.PUBLISHED)
    
    return await crud_question_sets.update_question_set(
        db,
        ObjectId(question_set_id),
        update_data,
        user_id
    )

@router.post("/{question_set_id}/archive", response_model=QuestionSetPublic)
async def archive_question_set(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengarsipkan paket soal.
    Hanya koordinator yang bisa archive.
    """
    user_id = ObjectId(current_user["id"])
    
    update_data = QuestionSetUpdate(status=QuestionSetStatus.ARCHIVED)
    
    return await crud_question_sets.update_question_set(
        db,
        ObjectId(question_set_id),
        update_data,
        user_id
    )

@router.delete("/{question_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_set(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menghapus paket soal.
    Hanya koordinator yang bisa menghapus, dan tidak bisa dihapus jika sedang digunakan.
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

# Additional utility endpoints

@router.get("/{question_set_id}/questions", response_model=List[dict])
async def get_question_set_questions(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Mengambil detail soal-soal dalam paket soal.
    """
    user_id = ObjectId(current_user["id"])
    
    question_set = await crud_question_sets.get_question_set_by_id(
        db, ObjectId(question_set_id), user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    question_ids = question_set.get("question_ids", [])
    if not question_ids:
        return []
    
    # Get detailed questions from questions collection
    questions = await db["questions"].find(
        {"_id": {"$in": question_ids}}
    ).to_list(None)
    
    return questions

@router.post("/{question_set_id}/duplicate", response_model=QuestionSetPublic)
async def duplicate_question_set(
    question_set_id: str,
    new_name: str = Query(..., description="Name for the duplicated question set"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Menduplikasi paket soal.
    Koordinator bisa menduplikasi paket soal untuk dimodifikasi.
    """
    user_id = ObjectId(current_user["id"])
    
    # Get original question set
    original_qset = await crud_question_sets.get_question_set_by_id(
        db, ObjectId(question_set_id), user_id
    )
    
    if not original_qset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Create new question set with same properties
    create_data = QuestionSetCreate(
        name=new_name,
        subject_id=original_qset["subject_id"],
        grade_level=original_qset["grade_level"],
        description=f"Copy of {original_qset['name']}",
        tags=original_qset.get("metadata", {}).get("tags", [])
    )
    
    new_qset = await crud_question_sets.create_question_set(db, create_data, user_id)
    
    # Copy questions if original has any
    if original_qset.get("question_ids"):
        await crud_question_sets.add_questions_to_set(
            db,
            new_qset["_id"],
            original_qset["question_ids"],
            user_id
        )
        
        # Get updated question set with metadata
        new_qset = await crud_question_sets.get_question_set_by_id(
            db, new_qset["_id"], user_id
        )
    
    return new_qset