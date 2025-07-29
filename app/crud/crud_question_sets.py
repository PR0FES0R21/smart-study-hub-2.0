# ==============================================================================
# File: app/crud/crud_question_sets.py
# Deskripsi: CRUD operations untuk Question Sets (Enhanced).
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, status

from app.schemas.question_set import (
    QuestionSetCreate, 
    QuestionSetUpdate, 
    QuestionSetStatus,
    QuestionSetMetadata,
    AccessPermissions,
    DifficultyDistribution
)

async def create_question_set(
    db: AsyncIOMotorDatabase, 
    qset: QuestionSetCreate, 
    coordinator_id: ObjectId
) -> dict:
    """Membuat paket soal baru"""
    now = datetime.utcnow()
    
    qset_dict = {
        "name": qset.name,
        "subject_id": qset.subject_id,
        "grade_level": qset.grade_level,
        "created_by_coordinator_id": coordinator_id,
        "question_ids": [],
        "status": QuestionSetStatus.DRAFT,
        "access_permissions": {
            "can_view": [],
            "can_edit": [coordinator_id],
            "subject_teachers_auto_access": True
        },
        "metadata": {
            "total_questions": 0,
            "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
            "total_points": 0,
            "tags": qset.tags or []
        },
        "description": qset.description,
        "version": 1,
        "published_date": None,
        "created_at": now,
        "updated_at": now
    }
    
    result = await db["question_sets"].insert_one(qset_dict)
    return await db["question_sets"].find_one({"_id": result.inserted_id})

async def get_question_sets(
    db: AsyncIOMotorDatabase, 
    subject_id: ObjectId, 
    grade_level: int,
    status: Optional[QuestionSetStatus] = None,
    user_id: Optional[ObjectId] = None
) -> List[dict]:
    """Mengambil paket soal dengan filter dan access control"""
    query = {
        "subject_id": subject_id, 
        "grade_level": grade_level
    }
    
    if status:
        query["status"] = status
    
    # Access control filter
    if user_id:
        access_filter = {
            "$or": [
                {"access_permissions.subject_teachers_auto_access": True},
                {"access_permissions.can_view": user_id},
                {"created_by_coordinator_id": user_id}
            ]
        }
        query.update(access_filter)
    
    return await db["question_sets"].find(query).to_list(None)

async def get_question_set_by_id(
    db: AsyncIOMotorDatabase, 
    question_set_id: ObjectId,
    user_id: Optional[ObjectId] = None
) -> Optional[dict]:
    """Mengambil paket soal berdasarkan ID dengan access control"""
    query = {"_id": question_set_id}
    
    question_set = await db["question_sets"].find_one(query)
    if not question_set:
        return None
    
    # Check access permissions
    if user_id and not await _check_view_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this question set"
        )
    
    return question_set

async def update_question_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    qset_update: QuestionSetUpdate,
    user_id: ObjectId
) -> Optional[dict]:
    """Update paket soal (hanya koordinator)"""
    # Check if user has edit permission
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    if not await _check_edit_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can edit question sets"
        )
    
    update_data = qset_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    # Update version if status changes to published
    if qset_update.status == QuestionSetStatus.PUBLISHED and question_set["status"] != QuestionSetStatus.PUBLISHED:
        update_data["published_date"] = datetime.utcnow()
        update_data["version"] = question_set.get("version", 1) + 1
    
    await db["question_sets"].update_one(
        {"_id": question_set_id},
        {"$set": update_data}
    )
    
    return await db["question_sets"].find_one({"_id": question_set_id})

async def add_questions_to_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    question_ids: List[ObjectId],
    user_id: ObjectId
) -> dict:
    """Menambahkan soal ke paket soal"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    if not await _check_edit_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can add questions"
        )
    
    # Avoid duplicates
    existing_ids = set(str(qid) for qid in question_set.get("question_ids", []))
    new_ids = [qid for qid in question_ids if str(qid) not in existing_ids]
    
    if not new_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All questions are already in the set"
        )
    
    # Update question_ids and metadata
    updated_question_ids = question_set.get("question_ids", []) + new_ids
    metadata = await _calculate_metadata(db, updated_question_ids)
    
    await db["question_sets"].update_one(
        {"_id": question_set_id},
        {
            "$set": {
                "question_ids": updated_question_ids,
                "metadata": metadata,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return await db["question_sets"].find_one({"_id": question_set_id})

async def remove_questions_from_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    question_ids: List[ObjectId],
    user_id: ObjectId
) -> dict:
    """Menghapus soal dari paket soal"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    if not await _check_edit_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can remove questions"
        )
    
    # Remove specified questions
    remove_ids = set(str(qid) for qid in question_ids)
    updated_question_ids = [
        qid for qid in question_set.get("question_ids", [])
        if str(qid) not in remove_ids
    ]
    
    # Update metadata
    metadata = await _calculate_metadata(db, updated_question_ids)
    
    await db["question_sets"].update_one(
        {"_id": question_set_id},
        {
            "$set": {
                "question_ids": updated_question_ids,
                "metadata": metadata,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return await db["question_sets"].find_one({"_id": question_set_id})

async def delete_question_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    user_id: ObjectId
) -> bool:
    """Menghapus paket soal (hanya koordinator)"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    if not await _check_edit_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators can delete question sets"
        )
    
    # Check if question set is being used in any active exams
    active_exams = await db["exams"].count_documents({
        "question_set_id": question_set_id,
        "status": {"$in": ["scheduled", "active"]}
    })
    
    if active_exams > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete question set that is used in active exams"
        )
    
    result = await db["question_sets"].delete_one({"_id": question_set_id})
    return result.deleted_count > 0

async def get_my_question_sets(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    subject_id: Optional[ObjectId] = None
) -> List[dict]:
    """Mengambil paket soal yang dibuat oleh koordinator"""
    query = {"created_by_coordinator_id": user_id}
    
    if subject_id:
        query["subject_id"] = subject_id
    
    return await db["question_sets"].find(query).to_list(None)

# Helper functions
async def _check_view_permission(question_set: dict, user_id: ObjectId) -> bool:
    """Check if user has view permission"""
    permissions = question_set.get("access_permissions", {})
    
    # Creator always has access
    if question_set.get("created_by_coordinator_id") == user_id:
        return True
    
    # Explicit view permission
    if user_id in permissions.get("can_view", []):
        return True
    
    # Subject teachers auto access (would need to check user's subjects)
    if permissions.get("subject_teachers_auto_access", False):
        # TODO: Implement check if user teaches this subject
        return True
    
    return False

async def _check_edit_permission(question_set: dict, user_id: ObjectId) -> bool:
    """Check if user has edit permission"""
    permissions = question_set.get("access_permissions", {})
    
    # Creator always has edit access
    if question_set.get("created_by_coordinator_id") == user_id:
        return True
    
    # Explicit edit permission
    if user_id in permissions.get("can_edit", []):
        return True
    
    return False

async def _calculate_metadata(db: AsyncIOMotorDatabase, question_ids: List[ObjectId]) -> dict:
    """Calculate metadata for question set"""
    if not question_ids:
        return {
            "total_questions": 0,
            "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
            "total_points": 0,
            "tags": []
        }
    
    # Aggregate questions data
    pipeline = [
        {"$match": {"_id": {"$in": question_ids}}},
        {
            "$group": {
                "_id": None,
                "total_questions": {"$sum": 1},
                "total_points": {"$sum": "$points"},
                "difficulties": {"$push": "$difficulty"},
                "all_tags": {"$push": "$tags"}
            }
        }
    ]
    
    result = await db["questions"].aggregate(pipeline).to_list(1)
    if not result:
        return {
            "total_questions": 0,
            "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
            "total_points": 0,
            "tags": []
        }
    
    data = result[0]
    
    # Count difficulty distribution
    difficulties = data.get("difficulties", [])
    difficulty_dist = {
        "easy": difficulties.count("easy"),
        "medium": difficulties.count("medium"),
        "hard": difficulties.count("hard")
    }
    
    # Flatten and unique tags
    all_tags = []
    for tag_list in data.get("all_tags", []):
        all_tags.extend(tag_list or [])
    unique_tags = list(set(all_tags))
    
    return {
        "total_questions": data.get("total_questions", 0),
        "difficulty_distribution": difficulty_dist,
        "total_points": data.get("total_points", 0),
        "tags": unique_tags
    }