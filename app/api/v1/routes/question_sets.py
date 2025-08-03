# ==============================================================================
# Enhanced Router
# ==============================================================================
from fastapi import APIRouter, Depends, status, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_sets
from app.schemas.pagination import PaginatedResponse
from app.schemas.question_set import (
    QuestionSetCreate, QuestionSetUpdate, QuestionSetDetailedPublic,
    QuestionSetSummaryEnhanced, QuestionSetStatus, PermissionManagement,
    PermissionHolders, QuestionSetRemoveQuestions, QuestionSetPublic,
    QuestionSetAddQuestions
)
from app.schemas.user import TeacherBasic

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[QuestionSetSummaryEnhanced])
async def get_accessible_question_sets_paginated(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    status: Optional[QuestionSetStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in question set names"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get paginated list of accessible question sets with enhanced info.
    
    Features:
    - Pagination with configurable page size
    - Multiple filters
    - Creator info with profile picture
    - User permissions for each question set
    - Cached for performance
    
    Access logic:
    1. Public question sets - all teachers can access
    2. Private question sets - only teachers teaching same subject & grade
    3. Question sets with explicit permissions
    4. Question sets created by user
    """
    user_id = ObjectId(current_user["_id"])
    subject_obj_id = ObjectId(subject_id) if subject_id else None
    
    return await crud_question_sets.get_accessible_question_sets_paginated(
        db=db,
        user_id=user_id,
        page=page,
        limit=limit,
        subject_id=subject_obj_id,
        grade_level=grade_level,
        status=status,
        search=search,
        is_public=is_public
    )

@router.get("/{question_set_id}", response_model=QuestionSetDetailedPublic)
async def get_question_set_detail_enhanced(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get detailed question set with all permission holders info.
    
    Returns:
    - Complete question set details
    - Subject and creator info
    - List of all users with various permissions (view, edit, manage, publish)
    - Current user's specific permissions
    - Cached for performance
    """
    user_id = ObjectId(current_user["_id"])
    
    question_set = await crud_question_sets.get_question_set_detail_with_permissions(
        db=db,
        question_set_id=ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    return question_set

@router.get("/", response_model=List[QuestionSetSummaryEnhanced])
async def get_accessible_question_sets_simple(
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    status: Optional[QuestionSetStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in question set names"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Simple list endpoint (backward compatibility).
    Returns first 50 items without pagination.
    """
    user_id = ObjectId(current_user["_id"])
    subject_obj_id = ObjectId(subject_id) if subject_id else None
    
    result = await crud_question_sets.get_accessible_question_sets_paginated(
        db=db,
        user_id=user_id,
        page=1,
        limit=50,
        subject_id=subject_obj_id,
        grade_level=grade_level,
        status=status,
        search=search,
        is_public=is_public
    )
    
    return result.data

@router.get("/my/paginated", response_model=PaginatedResponse[QuestionSetSummaryEnhanced])
async def get_my_question_sets_paginated(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    status: Optional[QuestionSetStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in names"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get paginated list of question sets created by current user.
    """
    user_id = ObjectId(current_user["_id"])
    subject_obj_id = ObjectId(subject_id) if subject_id else None
    
    # Build filters to only show user's question sets
    filters = {"created_by_coordinator_id": user_id}
    if subject_obj_id:
        filters["subject_id"] = subject_obj_id
    if status:
        filters["status"] = status
    if search:
        filters["name"] = {"$regex": search, "$options": "i"}
    
    # Use aggregation pipeline for consistency
    pipeline = [
        {"$match": filters},
        
        # Lookup subject
        {
            "$lookup": {
                "from": "subjects",
                "localField": "subject_id",
                "foreignField": "_id",
                "as": "subject_info"
            }
        },
        {"$unwind": {"path": "$subject_info", "preserveNullAndEmptyArrays": True}},
        
        # Lookup creator (self)
        {
            "$lookup": {
                "from": "profiles",
                "localField": "created_by_coordinator_id",
                "foreignField": "user_id",
                "as": "creator_profile"
            }
        },
        {"$unwind": {"path": "$creator_profile", "preserveNullAndEmptyArrays": True}},
        
        # Count total
        {
            "$facet": {
                "total_count": [{"$count": "count"}],
                "data": [
                    {"$skip": (page - 1) * limit},
                    {"$limit": limit},
                    {
                        "$project": {
                            "_id": 1,
                            "name": 1,
                            "description": 1,
                            "grade_level": 1,
                            "status": 1,
                            "is_public": 1,
                            "metadata": 1,
                            "created_at": 1,
                            "updated_at": 1,
                            
                            "subject": {
                                "_id": "$subject_info._id",
                                "name": "$subject_info.name",
                                "code": "$subject_info.code"
                            },
                            
                            "created_by": {
                                "_id": "$created_by_coordinator_id",
                                "full_name": "$creator_profile.full_name",
                                "profile_picture_url": "$creator_profile.profile_picture_url"
                            },
                            
                            "can_edit": True,  # Always true for own question sets
                            "can_manage_questions": True,
                            "is_creator": True
                        }
                    },
                    {"$sort": {"created_at": -1}}
                ]
            }
        }
    ]
    
    results = await db["question_sets"].aggregate(pipeline).to_list(1)
    
    if not results:
        total_items = 0
        data = []
    else:
        total_items = results[0]["total_count"][0]["count"] if results[0]["total_count"] else 0
        data = results[0]["data"]
    
    total_pages = (total_items + limit - 1) // limit
    
    return PaginatedResponse(
        total_items=total_items,
        total_pages=total_pages,
        current_page=page,
        limit=limit,
        data=data
    )

@router.post("/", response_model=QuestionSetDetailedPublic, status_code=status.HTTP_201_CREATED)
async def create_new_question_set(
    qset_in: QuestionSetCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Create new question set with enhanced response.
    """
    coordinator_id = ObjectId(current_user["_id"])
    
    created_qset = await crud_question_sets.create_question_set(db, qset_in, coordinator_id)
    
    # Return detailed version
    return await crud_question_sets.get_question_set_detail_with_permissions(
        db=db,
        question_set_id=created_qset["_id"],
        user_id=coordinator_id
    )

@router.put("/{question_set_id}", response_model=QuestionSetDetailedPublic)
async def update_question_set_enhanced(
    question_set_id: str,
    qset_update: QuestionSetUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Update question set with enhanced response.
    """
    user_id = ObjectId(current_user["_id"])
    
    await crud_question_sets.update_question_set(
        db=db,
        question_set_id=ObjectId(question_set_id),
        qset_update=qset_update,
        user_id=user_id
    )
    
    # Return detailed version
    updated_qset = await crud_question_sets.get_question_set_detail_with_permissions(
        db=db,
        question_set_id=ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not updated_qset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    return updated_qset

@router.put("/{question_set_id}/permissions", response_model=QuestionSetDetailedPublic)
async def manage_question_set_permissions_enhanced(
    question_set_id: str,
    permission_data: PermissionManagement,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Manage permissions with enhanced response showing all permission holders.
    """
    requester_id = ObjectId(current_user["_id"])
    
    await crud_question_sets.manage_permissions(
        db=db,
        question_set_id=ObjectId(question_set_id),
        target_user_id=permission_data.user_id,
        permissions=permission_data.permissions,
        action=permission_data.action,
        requester_user_id=requester_id
    )
    
    # Return detailed version with updated permissions
    return await crud_question_sets.get_question_set_detail_with_permissions(
        db=db,
        question_set_id=ObjectId(question_set_id),
        user_id=requester_id
    )

@router.get("/{question_set_id}/permission-holders", response_model=PermissionHolders)
async def get_question_set_permission_holders(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get list of all users who have permissions on this question set.
    Only creator or users with edit permission can see this.
    """
    user_id = ObjectId(current_user["_id"])
    
    question_set = await crud_question_sets.get_question_set_detail_with_permissions(
        db=db,
        question_set_id=ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Check if user can manage permissions
    if not question_set["current_user_permissions"]["is_creator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator can view permission holders"
        )
    
    return question_set["permission_holders"]

@router.get("/{question_set_id}/stats", response_model=dict)
async def get_question_set_statistics_enhanced(
    question_set_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get enhanced statistics for question set.
    """
    user_id = ObjectId(current_user["_id"])
    
    question_set = await crud_question_sets.get_question_set_detail_with_permissions(
        db=db,
        question_set_id=ObjectId(question_set_id),
        user_id=user_id
    )
    
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Get usage statistics
    usage_stats = await db["exams"].aggregate([
        {"$match": {"question_set_id": ObjectId(question_set_id)}},
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]).to_list(None)
    
    usage_by_status = {stat["_id"]: stat["count"] for stat in usage_stats}
    
    # Get permission statistics
    permission_counts = {
        "can_view": len(question_set["permission_holders"]["can_view"]),
        "can_edit": len(question_set["permission_holders"]["can_edit"]),
        "can_manage_questions": len(question_set["permission_holders"]["can_manage_questions"]),
        "can_publish": len(question_set["permission_holders"]["can_publish"]),
    }
    
    return {
        "basic": question_set["metadata"],
        "usage": {
            "total_exams": sum(usage_by_status.values()),
            "by_status": usage_by_status,
            "active_exams": usage_by_status.get("active", 0) + usage_by_status.get("scheduled", 0)
        },
        "permissions": {
            "counts": permission_counts,
            "current_user": question_set["current_user_permissions"]
        },
        "questions": {
            "total": len(question_set.get("question_ids", [])),
            "difficulty_breakdown": question_set["metadata"].get("difficulty_distribution", {})
        }
    }

# Utility endpoints for managing users and permissions

@router.get("/users/search", response_model=List[TeacherBasic])
async def search_users_for_permissions(
    q: str = Query(..., min_length=2, description="Search query for user names"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Search for users to add permissions.
    Only returns teachers and coordinators.
    """
    
    pipeline = [
        {
            "$match": {
                "roles": {"$in": ["teacher", "coordinator"]},
                "is_active": True
            }
        },
        {
            "$lookup": {
                "from": "profiles",
                "localField": "profile_id",
                "foreignField": "_id",
                "as": "profile"
            }
        },
        {"$unwind": "$profile"},
        {
            "$match": {
                "profile.full_name": {"$regex": q, "$options": "i"}
            }
        },
        {
            "$project": {
                "_id": 1,
                "full_name": "$profile.full_name",
                "profile_picture_url": "$profile.profile_picture_url"
            }
        },
        {"$limit": limit}
    ]
    
    users = await db["users"].aggregate(pipeline).to_list(limit)
    return users


@router.post("/{question_set_id}/questions", response_model=QuestionSetPublic)
async def add_questions_to_set(
    question_set_id: str,
    questions_data: QuestionSetAddQuestions,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    print(questions_data)
    print(question_set_id)
    """
    Menambahkan soal ke paket soal. 
    Hanya koordinator creator atau user dengan manage_questions permission.
    """
    user_id = ObjectId(current_user["_id"])
    
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
    print(questions_data)
    """
    Menghapus soal dari paket soal.
    Hanya koordinator creator atau user dengan manage_questions permission.
    """
    user_id = ObjectId(current_user["_id"])
    
    return await crud_question_sets.remove_questions_from_set(
        db,
        ObjectId(question_set_id),
        questions_data.question_ids,
        user_id
    )