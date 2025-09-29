# ==============================================================================
# File: app/api/v1/routes/course_management.py
# Deskripsi: API endpoints untuk Course Management System (New Architecture)
# ==============================================================================
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.api.v1.deps import get_database as get_db, get_current_user
from app.schemas.base import PyObjectId
from app.schemas.course_version import (
    CourseFamilyCreateRequest, CourseFamilyResponse,
    TeacherForkCreateRequest, CourseVersionSummaryResponse, CourseVersionDetailResponse,
    CourseContentUpdateRequest, PullRequestCreateRequest, PullRequestSummaryResponse,
    PullRequestDetailResponse, PullRequestReviewRequest, ChangeHistoryResponse,
    CourseVersionFilters, PullRequestFilters, PaginatedCourseVersionResponse,
    PaginatedPullRequestResponse, PaginatedChangeHistoryResponse,
    CourseAnalyticsResponse, SystemHealthResponse
)
from app.crud.course_version import course_version_crud
from app.core.course_permissions import require_role, check_user_permission

router = APIRouter(prefix="/course-management", tags=["Course Management"])

# ==================== COURSE FAMILY ENDPOINTS ====================

@router.post("/families", response_model=CourseFamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_course_family(
    request: CourseFamilyCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create new course family dengan initial master version.
    Only coordinators can create course families.
    """
    # Verify user is coordinator
    await require_role(current_user, ["coordinator", "admin"])
    
    try:
        family_metadata, master_version = await course_version_crud.create_course_family(
            db=db,
            base_title=request.base_title,
            subject_id=request.subject_id,
            grade_level=request.grade_level,
            coordinator_id=PyObjectId(current_user["_id"]),
            initial_course_data={
                "description": request.description,
                "modules": [module.dict() for module in request.modules]
            }
        )
        
        return CourseFamilyResponse(
            id=family_metadata.id or str(family_metadata.course_family_id),
            course_family_id=str(family_metadata.course_family_id),
            base_title=family_metadata.base_title,
            subject_id=str(family_metadata.subject_id),
            grade_level=family_metadata.grade_level,
            coordinator_id=str(family_metadata.coordinator_id),
            current_master_version_id=str(family_metadata.current_master_version_id),
            current_version=family_metadata.current_version,
            total_versions=family_metadata.total_versions,
            total_forks=family_metadata.total_forks,
            total_pull_requests=family_metadata.total_pull_requests,
            created_at=family_metadata.created_at,
            updated_at=family_metadata.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course family: {str(e)}"
        )

@router.get("/families/{family_id}", response_model=CourseFamilyResponse)
async def get_course_family(
    family_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get course family details"""
    try:
        family = await course_version_crud.get_course_family(
            db=db,
            family_id=PyObjectId(family_id)
        )
        
        if not family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course family not found"
            )
        
        # Check user permission
        await check_user_permission(current_user, "view_course", family.subject_id)
        
        return CourseFamilyResponse(
            id=family.id or str(family.course_family_id),
            course_family_id=str(family.course_family_id),
            base_title=family.base_title,
            subject_id=str(family.subject_id),
            grade_level=family.grade_level,
            coordinator_id=str(family.coordinator_id),
            current_master_version_id=str(family.current_master_version_id),
            current_version=family.current_version,
            total_versions=family.total_versions,
            total_forks=family.total_forks,
            total_pull_requests=family.total_pull_requests,
            created_at=family.created_at,
            updated_at=family.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get course family: {str(e)}"
        )

# ==================== COURSE VERSION ENDPOINTS ====================

@router.get("/versions", response_model=PaginatedCourseVersionResponse)
async def list_course_versions(
    # Filters
    course_family_id: Optional[str] = Query(None),
    subject_id: Optional[str] = Query(None),
    grade_level: Optional[int] = Query(None),
    coordinator_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    is_master: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    fork_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    
    # Pagination
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List course versions dengan filtering dan pagination"""
    try:
        # Build filter
        filter_dict = {}
        
        if course_family_id:
            filter_dict["course_family_id"] = PyObjectId(course_family_id)
        if subject_id:
            filter_dict["subject_id"] = PyObjectId(subject_id)
        if grade_level is not None:
            filter_dict["grade_level"] = grade_level
        if coordinator_id:
            filter_dict["coordinator_id"] = PyObjectId(coordinator_id)
        if teacher_id:
            filter_dict["teacher_id"] = PyObjectId(teacher_id)
        if is_master is not None:
            filter_dict["is_master"] = is_master
        if is_active is not None:
            filter_dict["is_active"] = is_active
        if fork_type:
            filter_dict["fork_type"] = fork_type
        if status:
            filter_dict["status"] = status
        
        # Apply user-specific filters based on role
        if "teacher" in current_user.get("roles", []):
            # Teachers can only see their own forks + public masters
            filter_dict["$or"] = [
                {"is_master": True, "is_active": True},
                {"teacher_id": PyObjectId(current_user["_id"])}
            ]
        
        # Get total count
        total_count = await db.course_versions.count_documents(filter_dict)
        
        # Get paginated results
        skip = (page - 1) * limit
        cursor = db.course_versions.find(filter_dict).sort("updated_at", DESCENDING).skip(skip).limit(limit)
        versions = await cursor.to_list(length=limit)
        
        # Convert to response format
        items = []
        for version_data in versions:
            version = CourseVersionSummaryResponse(
                id=str(version_data["_id"]),
                course_family_id=str(version_data["course_family_id"]),
                version=version_data["version"],
                title=version_data["title"],
                subject_id=str(version_data["subject_id"]),
                grade_level=version_data["grade_level"],
                coordinator_id=str(version_data["coordinator_id"]),
                is_master=version_data["is_master"],
                is_active=version_data["is_active"],
                fork_type=version_data["fork_type"],
                teacher_id=str(version_data["teacher_id"]) if version_data.get("teacher_id") else None,
                modules_count=len(version_data.get("modules", [])),
                lessons_count=sum(len(module.get("lessons", [])) for module in version_data.get("modules", [])),
                total_duration=sum(module.get("estimated_duration", 0) for module in version_data.get("modules", [])),
                status=version_data["status"],
                created_at=version_data["created_at"],
                updated_at=version_data["updated_at"],
                usage_stats=version_data.get("usage_stats", {})
            )
            items.append(version)
        
        # Calculate additional statistics
        stats_pipeline = [
            {"$match": filter_dict},
            {
                "$group": {
                    "_id": None,
                    "total_master": {"$sum": {"$cond": [{"$eq": ["$is_master", True]}, 1, 0]}},
                    "total_forks": {"$sum": {"$cond": [{"$eq": ["$is_master", False]}, 1, 0]}},
                    "by_status": {
                        "$push": "$status"
                    }
                }
            }
        ]
        stats_result = await db.course_versions.aggregate(pipeline).to_list(1)
        stats = stats_result[0] if stats_result else {}
        
        return PaginatedCourseVersionResponse(
            items=items,
            total_count=total_count,
            page=page,
            page_size=limit,
            total_pages=(total_count + limit - 1) // limit,
            total_master_versions=stats.get("total_master", 0),
            total_teacher_forks=stats.get("total_forks", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list course versions: {str(e)}"
        )

@router.get("/versions/{version_id}", response_model=CourseVersionDetailResponse)
async def get_course_version(
    version_id: str,
    include_usage_stats: bool = Query(default=False),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed course version"""
    try:
        version = await course_version_crud.get_version_by_id(
            db=db,
            version_id=PyObjectId(version_id),
            include_usage_stats=include_usage_stats
        )
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course version not found"
            )
        
        # Check permissions
        await check_user_permission(current_user, "view_course", version.subject_id)
        
        # Check user permissions for actions
        user_can_edit = False
        user_can_delete = False
        user_can_fork = False
        user_can_create_pr = False
        
        if version.is_master:
            user_can_edit = (version.coordinator_id == PyObjectId(current_user["_id"]) or 
                           "admin" in current_user.get("roles", []))
            user_can_fork = "teacher" in current_user.get("roles", [])
        else:
            user_can_edit = (version.teacher_id == PyObjectId(current_user["_id"]) or 
                           "admin" in current_user.get("roles", []))
            user_can_create_pr = version.teacher_id == PyObjectId(current_user["_id"])
        
        user_can_delete = "admin" in current_user.get("roles", [])
        
        return CourseVersionDetailResponse(
            id=str(version.id),
            course_family_id=str(version.course_family_id),
            version=version.version,
            version_number=version.version_number,
            title=version.title,
            description=version.description,
            subject_id=str(version.subject_id),
            grade_level=version.grade_level,
            coordinator_id=str(version.coordinator_id),
            academic_period_id=str(version.academic_period_id) if version.academic_period_id else None,
            is_master=version.is_master,
            is_active=version.is_active,
            parent_version_id=str(version.parent_version_id) if version.parent_version_id else None,
            created_from_pr_id=str(version.created_from_pr_id) if version.created_from_pr_id else None,
            teacher_id=str(version.teacher_id) if version.teacher_id else None,
            class_ids=[str(class_id) for class_id in version.class_ids],
            fork_type=version.fork_type,
            modules=version.modules,
            changes_from_parent=[change.dict() for change in version.changes_from_parent],
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            archived_at=version.archived_at,
            created_by=str(version.created_by),
            usage_stats=version.usage_stats,
            settings=version.settings,
            user_can_edit=user_can_edit,
            user_can_delete=user_can_delete,
            user_can_fork=user_can_fork,
            user_can_create_pr=user_can_create_pr
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get course version: {str(e)}"
        )

@router.post("/versions/{master_version_id}/fork", response_model=CourseVersionDetailResponse)
async def create_teacher_fork(
    master_version_id: str,
    request: TeacherForkCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create teacher fork dari master version"""
    await require_role(current_user, ["teacher", "admin"])
    
    try:
        fork = await course_version_crud.create_teacher_fork(
            db=db,
            master_version_id=PyObjectId(master_version_id),
            teacher_id=PyObjectId(current_user["_id"]),
            class_ids=request.class_ids,
            fork_title_suffix=request.fork_title_suffix or ""
        )
        
        # Convert to response format
        return CourseVersionDetailResponse(
            id=str(fork.id),
            course_family_id=str(fork.course_family_id),
            version=fork.version,
            version_number=fork.version_number,
            title=fork.title,
            description=fork.description,
            subject_id=str(fork.subject_id),
            grade_level=fork.grade_level,
            coordinator_id=str(fork.coordinator_id),
            is_master=fork.is_master,
            is_active=fork.is_active,
            parent_version_id=str(fork.parent_version_id) if fork.parent_version_id else None,
            teacher_id=str(fork.teacher_id) if fork.teacher_id else None,
            class_ids=[str(class_id) for class_id in fork.class_ids],
            fork_type=fork.fork_type,
            modules=fork.modules,
            status=fork.status,
            created_at=fork.created_at,
            updated_at=fork.updated_at,
            created_by=str(fork.created_by),
            usage_stats=fork.usage_stats,
            settings=fork.settings,
            user_can_edit=True,  # Creator can always edit
            user_can_create_pr=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create teacher fork: {str(e)}"
        )

@router.put("/versions/{version_id}/content", response_model=CourseVersionDetailResponse)
async def update_course_content(
    version_id: str,
    request: CourseContentUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update course content"""
    try:
        updates = {}
        
        if request.modules is not None:
            updates["modules"] = [module.dict() for module in request.modules]
        if request.title is not None:
            updates["title"] = request.title
        if request.description is not None:
            updates["description"] = request.description
        if request.settings is not None:
            updates["settings"] = request.settings
        
        updated_version = await course_version_crud.update_course_content(
            db=db,
            version_id=PyObjectId(version_id),
            updates=updates,
            updated_by=PyObjectId(current_user["_id"])
        )
        
        # Convert to response (similar to get_course_version)
        return CourseVersionDetailResponse(
            id=str(updated_version.id),
            course_family_id=str(updated_version.course_family_id),
            version=updated_version.version,
            version_number=updated_version.version_number,
            title=updated_version.title,
            description=updated_version.description,
            subject_id=str(updated_version.subject_id),
            grade_level=updated_version.grade_level,
            coordinator_id=str(updated_version.coordinator_id),
            is_master=updated_version.is_master,
            is_active=updated_version.is_active,
            teacher_id=str(updated_version.teacher_id) if updated_version.teacher_id else None,
            class_ids=[str(class_id) for class_id in updated_version.class_ids],
            fork_type=updated_version.fork_type,
            modules=updated_version.modules,
            changes_from_parent=[change.dict() for change in updated_version.changes_from_parent],
            status=updated_version.status,
            created_at=updated_version.created_at,
            updated_at=updated_version.updated_at,
            created_by=str(updated_version.created_by),
            usage_stats=updated_version.usage_stats,
            settings=updated_version.settings,
            user_can_edit=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course content: {str(e)}"
        )

# ==================== PULL REQUEST ENDPOINTS ====================

@router.post("/versions/{source_version_id}/pull-requests", response_model=PullRequestDetailResponse)
async def create_pull_request(
    source_version_id: str,
    request: PullRequestCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create pull request untuk merge changes ke master"""
    await require_role(current_user, ["teacher", "coordinator", "admin"])
    
    try:
        pr = await course_version_crud.create_pull_request(
            db=db,
            source_version_id=PyObjectId(source_version_id),
            target_version_id=request.target_version_id,
            title=request.title,
            description=request.description,
            changes=[change.dict() for change in request.changes],
            requested_by=PyObjectId(current_user["_id"])
        )
        
        return PullRequestDetailResponse(
            id=str(pr.id),
            pr_number=pr.pr_number,
            course_family_id=str(pr.course_family_id),
            title=pr.title,
            description=pr.description,
            source_version_id=str(pr.source_version_id),
            target_version_id=str(pr.target_version_id),
            requested_by=str(pr.requested_by),
            changes=pr.changes,
            status=pr.status,
            priority=pr.priority,
            approval_workflow=[
                {
                    "step_number": step.step_number,
                    "action": step.action,
                    "actor_id": str(step.actor_id),
                    "timestamp": step.timestamp,
                    "comment": step.comment
                } for step in pr.approval_workflow
            ],
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            labels=pr.labels,
            category=pr.category,
            user_can_edit=pr.requested_by == PyObjectId(current_user["_id"]),
            user_can_review="coordinator" in current_user.get("roles", []) or "admin" in current_user.get("roles", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pull request: {str(e)}"
        )

@router.get("/pull-requests", response_model=PaginatedPullRequestResponse)
async def list_pull_requests(
    # Filters
    course_family_id: Optional[str] = Query(None),
    requested_by: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    
    # Pagination
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List pull requests"""
    try:
        # Build filter
        filter_dict = {}
        
        if course_family_id:
            filter_dict["course_family_id"] = PyObjectId(course_family_id)
        if requested_by:
            filter_dict["requested_by"] = PyObjectId(requested_by)
        if status:
            filter_dict["status"] = status
        if priority:
            filter_dict["priority"] = priority
        
        # Apply role-based filtering
        if "teacher" in current_user.get("roles", []) and "coordinator" not in current_user.get("roles", []):
            # Teachers can only see their own PRs
            filter_dict["requested_by"] = PyObjectId(current_user["_id"])
        
        # Get total count
        total_count = await db.course_pull_requests.count_documents(filter_dict)
        
        # Get paginated results
        skip = (page - 1) * limit
        cursor = db.course_pull_requests.find(filter_dict).sort("created_at", DESCENDING).skip(skip).limit(limit)
        prs = await cursor.to_list(length=limit)
        
        # Convert to response format
        items = []
        for pr_data in prs:
            pr = PullRequestSummaryResponse(
                id=str(pr_data["_id"]),
                pr_number=pr_data["pr_number"],
                title=pr_data["title"],
                course_family_id=str(pr_data["course_family_id"]),
                source_version_id=str(pr_data["source_version_id"]),
                target_version_id=str(pr_data["target_version_id"]),
                requested_by=str(pr_data["requested_by"]),
                status=pr_data["status"],
                priority=pr_data["priority"],
                created_at=pr_data["created_at"],
                assigned_reviewer=str(pr_data["assigned_reviewer"]) if pr_data.get("assigned_reviewer") else None,
                reviewed_at=pr_data.get("reviewed_at"),
                changes_count=len(pr_data.get("changes", [])),
                impact_level=pr_data.get("impact_assessment", {}).get("student_impact", "low")
            )
            items.append(pr)
        
        # Status statistics
        status_pipeline = [
            {"$match": filter_dict},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        status_stats = await db.course_pull_requests.aggregate(status_pipeline).to_list(None)
        status_counts = {stat["_id"]: stat["count"] for stat in status_stats}
        
        return PaginatedPullRequestResponse(
            items=items,
            total_count=total_count,
            page=page,
            page_size=limit,
            total_pages=(total_count + limit - 1) // limit,
            total_pending=status_counts.get("pending", 0),
            total_approved=status_counts.get("approved", 0),
            total_merged=status_counts.get("merged", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pull requests: {str(e)}"
        )

@router.get("/pull-requests/{pr_id}", response_model=PullRequestDetailResponse)
async def get_pull_request(
    pr_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed pull request"""
    try:
        pr_data = await db.course_pull_requests.find_one({"_id": PyObjectId(pr_id)})
        if not pr_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pull request not found"
            )
        
        # Check permissions
        if ("teacher" in current_user.get("roles", []) and 
            str(pr_data["requested_by"]) != str(current_user["_id"]) and
            "coordinator" not in current_user.get("roles", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Convert to response format
        return PullRequestDetailResponse(
            id=str(pr_data["_id"]),
            pr_number=pr_data["pr_number"],
            course_family_id=str(pr_data["course_family_id"]),
            title=pr_data["title"],
            description=pr_data["description"],
            source_version_id=str(pr_data["source_version_id"]),
            target_version_id=str(pr_data["target_version_id"]),
            requested_by=str(pr_data["requested_by"]),
            changes=pr_data["changes"],
            status=pr_data["status"],
            priority=pr_data["priority"],
            assigned_reviewer=str(pr_data["assigned_reviewer"]) if pr_data.get("assigned_reviewer") else None,
            reviewer_feedback=pr_data.get("reviewer_feedback"),
            impact_assessment=pr_data.get("impact_assessment", {}),
            approval_workflow=[
                {
                    "step_number": step["step_number"],
                    "action": step["action"],
                    "actor_id": str(step["actor_id"]),
                    "timestamp": step["timestamp"],
                    "comment": step.get("comment")
                } for step in pr_data.get("approval_workflow", [])
            ],
            created_at=pr_data["created_at"],
            updated_at=pr_data["updated_at"],
            reviewed_at=pr_data.get("reviewed_at"),
            merged_at=pr_data.get("merged_at"),
            merged_version_id=str(pr_data["merged_version_id"]) if pr_data.get("merged_version_id") else None,
            merge_commit_message=pr_data.get("merge_commit_message"),
            comments_count=len(pr_data.get("comments", [])),
            labels=pr_data.get("labels", []),
            category=pr_data.get("category"),
            user_can_edit=str(pr_data["requested_by"]) == str(current_user["_id"]),
            user_can_review="coordinator" in current_user.get("roles", []) or "admin" in current_user.get("roles", []),
            user_can_merge="coordinator" in current_user.get("roles", []) or "admin" in current_user.get("roles", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pull request: {str(e)}"
        )

@router.post("/pull-requests/{pr_id}/review", response_model=PullRequestDetailResponse)
async def review_pull_request(
    pr_id: str,
    request: PullRequestReviewRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Review dan approve/reject pull request"""
    await require_role(current_user, ["coordinator", "admin"])
    
    try:
        if request.decision == "approve":
            pr, new_master = await course_version_crud.approve_pull_request(
                db=db,
                pr_id=PyObjectId(pr_id),
                approved_by=PyObjectId(current_user["_id"]),
                approval_comment=request.comment
            )
            
            # Return updated PR
            return PullRequestDetailResponse(
                id=str(pr.id),
                pr_number=pr.pr_number,
                course_family_id=str(pr.course_family_id),
                title=pr.title,
                description=pr.description,
                source_version_id=str(pr.source_version_id),
                target_version_id=str(pr.target_version_id),
                requested_by=str(pr.requested_by),
                changes=pr.changes,
                status=pr.status,
                priority=pr.priority,
                merged_at=pr.merged_at,
                merged_version_id=str(pr.merged_version_id) if pr.merged_version_id else None,
                approval_workflow=[
                    {
                        "step_number": step.step_number,
                        "action": step.action,
                        "actor_id": str(step.actor_id),
                        "timestamp": step.timestamp,
                        "comment": step.comment
                    } for step in pr.approval_workflow
                ],
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                user_can_review=False  # Already reviewed
            )
        
        else:
            # Handle rejection or revision request
            # Implementation would go here
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Rejection/revision request not yet implemented"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review pull request: {str(e)}"
        )

# ==================== CHANGE HISTORY ENDPOINTS ====================

@router.get("/families/{family_id}/history", response_model=PaginatedChangeHistoryResponse)
async def get_course_change_history(
    family_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get change history untuk course family"""
    try:
        filter_dict = {"course_family_id": PyObjectId(family_id)}
        
        # Get total count
        total_count = await db.course_change_history.count_documents(filter_dict)
        
        # Get paginated results
        skip = (page - 1) * limit
        cursor = db.course_change_history.find(filter_dict).sort("timestamp", DESCENDING).skip(skip).limit(limit)
        history_items = await cursor.to_list(length=limit)
        
        # Convert to response format
        items = []
        for item in history_items:
            history = ChangeHistoryResponse(
                id=str(item["_id"]),
                course_family_id=str(item["course_family_id"]),
                version_id=str(item["version_id"]) if item.get("version_id") else None,
                change_type=item["change_type"],
                title=item["title"],
                description=item["description"],
                actor_id=str(item["actor_id"]),
                actor_type=item["actor_type"],
                timestamp=item["timestamp"],
                context=item.get("context", {}),
                changes_applied=item.get("changes_applied", []),
                impact_level=item.get("impact_level", "low"),
                notifications_sent=len(item.get("notifications_sent", []))
            )
            items.append(history)
        
        return PaginatedChangeHistoryResponse(
            items=items,
            total_count=total_count,
            page=page,
            page_size=limit,
            total_pages=(total_count + limit - 1) // limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get change history: {str(e)}"
        )

# ==================== ANALYTICS ENDPOINTS ====================

@router.get("/families/{family_id}/analytics", response_model=CourseAnalyticsResponse)
async def get_course_analytics(
    family_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get analytics untuk course family"""
    await require_role(current_user, ["coordinator", "admin"])
    
    try:
        # Basic statistics
        version_stats = await db.course_versions.aggregate([
            {"$match": {"course_family_id": PyObjectId(family_id)}},
            {"$group": {
                "_id": None,
                "total_versions": {"$sum": 1},
                "total_master": {"$sum": {"$cond": [{"$eq": ["$is_master", True]}, 1, 0]}},
                "total_forks": {"$sum": {"$cond": [{"$eq": ["$is_master", False]}, 1, 0]}},
                "active_forks": {"$sum": {"$cond": [
                    {"$and": [{"$eq": ["$is_master", False]}, {"$eq": ["$is_active", True]}]}, 1, 0
                ]}}
            }}
        ]).to_list(1)
        
        version_data = version_stats[0] if version_stats else {}
        
        # PR statistics
        pr_stats = await db.course_pull_requests.aggregate([
            {"$match": {"course_family_id": PyObjectId(family_id)}},
            {"$group": {
                "_id": None,
                "total_prs": {"$sum": 1},
                "approved_prs": {"$sum": {"$cond": [{"$eq": ["$status", "approved"]}, 1, 0]}}
            }}
        ]).to_list(1)
        
        pr_data = pr_stats[0] if pr_stats else {}
        
        return CourseAnalyticsResponse(
            course_family_id=family_id,
            total_versions=version_data.get("total_versions", 0),
            total_forks=version_data.get("total_forks", 0),
            active_forks=version_data.get("active_forks", 0),
            total_prs=pr_data.get("total_prs", 0),
            approved_prs=pr_data.get("approved_prs", 0),
            avg_review_time_hours=0.0,  # Would calculate from PR data
            total_enrolled_students=0,  # Would calculate from enrollment data
            average_completion_rate=0.0,  # Would calculate from progress data
            total_learning_time=0,  # Would calculate from progress data
            changes_last_30_days=0,  # Would calculate from change history
            most_active_teachers=[],  # Would calculate from change history
            content_growth_trend=[]  # Would calculate from version history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get course analytics: {str(e)}"
        )

@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get system health metrics"""
    await require_role(current_user, ["admin"])
    
    try:
        # Basic counts
        total_families = await db.course_families.count_documents({})
        total_versions = await db.course_versions.count_documents({})
        active_forks = await db.course_versions.count_documents({"is_master": False, "is_active": True})
        pending_prs = await db.course_pull_requests.count_documents({"status": "pending"})
        
        return SystemHealthResponse(
            total_course_families=total_families,
            total_versions=total_versions,
            total_active_forks=active_forks,
            pending_prs=pending_prs,
            avg_pr_review_time=0.0,  # Would calculate from PR data
            avg_fork_creation_time=0.0,  # Would calculate from creation logs
            storage_usage_mb=0.0,  # Would calculate from database size
            rollback_rate=0.0,  # Would calculate from rollback events
            error_rate=0.0,  # Would calculate from error logs
            user_satisfaction=0.0  # Would calculate from feedback data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )
