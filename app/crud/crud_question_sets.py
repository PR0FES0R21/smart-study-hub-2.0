# ==============================================================================
# File: app/crud/crud_question_sets.py
# Deskripsi: CRUD operations untuk Question Sets (Enhanced with Teaching Assignment Access).
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
        "is_public": qset.is_public,  # Koordinator tentukan public/private
        "access_permissions": {
            "can_view": [],
            "can_edit": [coordinator_id],
            "can_manage_questions": [coordinator_id],
            "can_publish": [coordinator_id]
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

async def get_accessible_question_sets(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    subject_id: Optional[ObjectId] = None,
    grade_level: Optional[int] = None,
    status: Optional[QuestionSetStatus] = None,
    search: Optional[str] = None,
    is_public: Optional[bool] = None
) -> List[dict]:
    """
    Mengambil semua question sets yang bisa diakses user berdasarkan:
    1. Public question sets
    2. Private question sets yang sesuai dengan teaching assignment
    3. Question sets dengan explicit permission
    """
    
    # Get user's teaching assignments
    user_subjects_grades = await _get_user_teaching_subjects_grades(db, user_id)
    
    # Build base query
    query = {}
    
    # Optional filters
    if subject_id:
        query["subject_id"] = subject_id
    if grade_level:
        query["grade_level"] = grade_level
    if status:
        query["status"] = status
    if is_public is not None:
        query["is_public"] = is_public
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    # Access control: Public OR (Private + Teaching Assignment) OR Explicit Permission
    access_conditions = [
        {"is_public": True},  # Public question sets
        {"created_by_coordinator_id": user_id}  # Created by user
    ]
    
    # Private question sets user can access via teaching assignment
    if user_subjects_grades:
        teaching_conditions = []
        for sg in user_subjects_grades:
            teaching_conditions.append({
                "is_public": False,
                "subject_id": sg["subject_id"],
                "grade_level": sg["grade_level"]
            })
        
        if teaching_conditions:
            access_conditions.append({"$or": teaching_conditions})
    
    # Explicit permissions
    access_conditions.extend([
        {"access_permissions.can_view": user_id},
        {"access_permissions.can_edit": user_id},
        {"access_permissions.can_manage_questions": user_id},
        {"access_permissions.can_publish": user_id}
    ])
    
    # Combine with access control
    final_query = {
        "$and": [
            query,
            {"$or": access_conditions}
        ]
    } if query else {"$or": access_conditions}
    
    return await db["question_sets"].find(final_query).to_list(None)

async def get_question_set_by_id(
    db: AsyncIOMotorDatabase, 
    question_set_id: ObjectId,
    user_id: Optional[ObjectId] = None
) -> Optional[dict]:
    """Mengambil paket soal berdasarkan ID dengan access control"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        return None
    
    # Check access permissions
    if user_id and not await _check_view_permission(db, question_set, user_id):
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
    """Update paket soal (koordinator atau user dengan permission)"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    if not await _check_edit_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this question set"
        )
    
    update_data = qset_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    # Update version if status changes to published
    if qset_update.status == QuestionSetStatus.PUBLISHED and question_set["status"] != QuestionSetStatus.PUBLISHED:
        # Check publish permission
        if not await _check_publish_permission(question_set, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to publish this question set"
            )
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
    
    if not await _check_manage_questions_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage questions in this set"
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
    
    if not await _check_manage_questions_permission(question_set, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage questions in this set"
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

async def manage_permissions(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    target_user_id: ObjectId,
    permissions: List[str],
    action: str,  # "grant" or "revoke"
    requester_user_id: ObjectId
) -> dict:
    """Grant atau revoke permissions ke user lain"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Only creator can manage permissions
    if question_set.get("created_by_coordinator_id") != requester_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator can manage permissions"
        )
    
    current_permissions = question_set.get("access_permissions", {})
    
    # Process each permission
    for permission in permissions:
        permission_field = f"can_{permission}"
        if permission_field not in current_permissions:
            continue
            
        current_list = current_permissions[permission_field]
        
        if action == "grant":
            if target_user_id not in current_list:
                current_list.append(target_user_id)
        elif action == "revoke":
            if target_user_id in current_list:
                current_list.remove(target_user_id)
    
    # Update database
    await db["question_sets"].update_one(
        {"_id": question_set_id},
        {
            "$set": {
                "access_permissions": current_permissions,
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
    """Menghapus paket soal (hanya creator)"""
    question_set = await db["question_sets"].find_one({"_id": question_set_id})
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Only creator can delete
    if question_set.get("created_by_coordinator_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator can delete question sets"
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
    """Mengambil paket soal yang dibuat oleh user"""
    query = {"created_by_coordinator_id": user_id}
    
    if subject_id:
        query["subject_id"] = subject_id
    
    return await db["question_sets"].find(query).to_list(None)

# Helper functions
async def _get_user_teaching_subjects_grades(db: AsyncIOMotorDatabase, user_id: ObjectId) -> List[dict]:
    """Get subjects and grade levels that user teaches"""
    # Get teaching assignments
    assignments = await db["teaching_assignments"].find(
        {"teacher_id": user_id}
    ).to_list(None)
    
    if not assignments:
        return []
    
    # Get class information for grade levels
    class_ids = [assignment["class_id"] for assignment in assignments]
    classes = await db["classes"].find(
        {"_id": {"$in": class_ids}}
    ).to_list(None)
    
    # Create class_id -> grade_level mapping
    class_grade_map = {cls["_id"]: cls["grade_level"] for cls in classes}
    
    # Build subject-grade combinations
    subjects_grades = []
    for assignment in assignments:
        grade_level = class_grade_map.get(assignment["class_id"])
        if grade_level:
            subjects_grades.append({
                "subject_id": assignment["subject_id"],
                "grade_level": grade_level
            })
    
    return subjects_grades

async def _check_view_permission(db: AsyncIOMotorDatabase, question_set: dict, user_id: ObjectId) -> bool:
    """Check if user has view permission"""
    # Public question sets
    if question_set.get("is_public", False):
        return True
    
    # Creator always has access
    if question_set.get("created_by_coordinator_id") == user_id:
        return True
    
    # Explicit permissions
    permissions = question_set.get("access_permissions", {})
    if user_id in permissions.get("can_view", []):
        return True
    if user_id in permissions.get("can_edit", []):
        return True
    if user_id in permissions.get("can_manage_questions", []):
        return True
    if user_id in permissions.get("can_publish", []):
        return True
    
    # Check teaching assignment for private question sets
    if not question_set.get("is_public", False):
        user_subjects_grades = await _get_user_teaching_subjects_grades(db, user_id)
        for sg in user_subjects_grades:
            if (sg["subject_id"] == question_set["subject_id"] and 
                sg["grade_level"] == question_set["grade_level"]):
                return True
    
    return False

async def _check_edit_permission(question_set: dict, user_id: ObjectId) -> bool:
    """Check if user has edit permission"""
    # Creator always has edit access
    if question_set.get("created_by_coordinator_id") == user_id:
        return True
    
    # Explicit edit permission
    permissions = question_set.get("access_permissions", {})
    if user_id in permissions.get("can_edit", []):
        return True
    
    return False

async def _check_manage_questions_permission(question_set: dict, user_id: ObjectId) -> bool:
    """Check if user has manage questions permission"""
    # Creator always has access
    if question_set.get("created_by_coordinator_id") == user_id:
        return True
    
    # Explicit permission
    permissions = question_set.get("access_permissions", {})
    if user_id in permissions.get("can_manage_questions", []):
        return True
    
    return False

async def _check_publish_permission(question_set: dict, user_id: ObjectId) -> bool:
    """Check if user has publish permission"""
    # Creator always has access
    if question_set.get("created_by_coordinator_id") == user_id:
        return True
    
    # Explicit permission
    permissions = question_set.get("access_permissions", {})
    if user_id in permissions.get("can_publish", []):
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