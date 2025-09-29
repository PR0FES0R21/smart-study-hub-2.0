# ==============================================================================
# File: app/api/v1/routes/independent_lessons.py
# Description: API Endpoints for Independent Lesson System
# ==============================================================================
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.db import get_database
from app.core.lesson_permissions import (
    LessonPermissionManager, UserRole, PermissionLevel,
    require_lesson_permission, require_coordinator_access
)
from app.core.teacher_assignment_system import TeacherAssignmentSystem
from app.models.lesson import IndependentLesson, TeacherAssignment, LessonTargetScope
from app.schemas.base import PyObjectId
from app.core.security import get_current_user
from app.schemas.user import UserInDB

router = APIRouter()

# Initialize systems
permission_manager = LessonPermissionManager()
assignment_system = TeacherAssignmentSystem(permission_manager)


# ==================== LESSON MANAGEMENT ENDPOINTS ====================

@router.post("/coordinated", response_model=Dict[str, Any])
async def create_coordinated_lesson(
    lesson_data: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create new coordinated lesson with automatic teacher assignments"""
    
    # Validate coordinator role
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators and admins can create coordinated lessons"
        )
    
    # Validate required fields
    if not all(key in lesson_data for key in ["title", "description", "coordination_assignment_id", "target_scope"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: title, description, coordination_assignment_id, target_scope"
        )
    
    try:
        lesson = await assignment_system.create_coordinated_lesson_from_assignments(
            db=db,
            coordinator_id=str(current_user.id),
            coordination_assignment_id=lesson_data["coordination_assignment_id"],
            lesson_data=lesson_data
        )
        
        return {
            "success": True,
            "lesson_id": lesson.id,
            "message": "Coordinated lesson created successfully with automatic teacher assignments",
            "lesson": lesson.dict()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create coordinated lesson: {str(e)}"
        )


@router.get("/my-lessons", response_model=List[Dict[str, Any]])
async def get_my_lessons(
    academic_period_id: Optional[str] = Query(None),
    include_permissions: bool = Query(True),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get lessons accessible to current user with permissions"""
    
    user_role = UserRole(current_user.role)
    filters = {}
    
    if academic_period_id:
        filters["academic_period_id"] = ObjectId(academic_period_id)
    
    if include_permissions:
        lessons = await permission_manager.get_user_lessons_with_permissions(
            db=db,
            user_id=str(current_user.id),
            user_role=user_role,
            filters=filters
        )
    else:
        # Simple query without permission details
        if user_role == UserRole.COORDINATOR:
            filters.update({
                "$or": [
                    {"ownership.primary_coordinator_id": ObjectId(current_user.id)},
                    {"teacher_assignments.teacher_id": ObjectId(current_user.id)}
                ]
            })
        elif user_role == UserRole.TEACHER:
            filters.update({
                "$or": [
                    {"teacher_assignments.teacher_id": ObjectId(current_user.id), "teacher_assignments.is_active": True},
                    {"teacher_id": ObjectId(current_user.id)}  # Legacy
                ]
            })
        
        lessons = await db["lessons"].find(filters).to_list(None)
        for lesson in lessons:
            lesson["id"] = str(lesson["_id"])
    
    return lessons


@router.get("/{lesson_id}", response_model=Dict[str, Any])
async def get_lesson_detail(
    lesson_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get detailed lesson information with user permissions"""
    
    lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if not lesson_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    lesson = IndependentLesson.from_mongo(lesson_doc)
    user_role = UserRole(current_user.role)
    
    # Check if user can view lesson
    can_view = await permission_manager.check_permission(
        db, str(current_user.id), lesson, "view_lesson", user_role
    )
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view lesson"
        )
    
    # Add permission info
    permission_level = await permission_manager.get_user_permission_level(
        db, str(current_user.id), lesson, user_role
    )
    
    content_permissions = await permission_manager.check_content_modification_permission(
        db, str(current_user.id), lesson, user_role
    )
    
    # Populate related data
    lesson_dict = lesson_doc.copy()
    lesson_dict["id"] = str(lesson_dict["_id"])
    
    # Add populated data
    if lesson_dict.get("subject_id"):
        subject = await db["subjects"].find_one({"_id": lesson_dict["subject_id"]})
        lesson_dict["subject_name"] = subject.get("name") if subject else None
    
    # Add teacher assignments with populated info
    lesson_dict["teacher_assignments"] = await assignment_system.get_lesson_teacher_assignments(
        db, lesson_id, populate_teacher_info=True
    )
    
    # Add user permissions
    lesson_dict.update({
        "user_permission_level": permission_level.value,
        "user_can_edit": content_permissions["can_edit"],
        "user_can_publish": content_permissions["can_publish"],
        "user_requires_approval": content_permissions["requires_approval"],
        "user_can_assign_teachers": await permission_manager.check_permission(
            db, str(current_user.id), lesson, "assign_teachers", user_role
        ),
        "user_can_manage_enrollments": await permission_manager.check_permission(
            db, str(current_user.id), lesson, "manage_enrollments", user_role
        )
    })
    
    return lesson_dict


@router.put("/{lesson_id}", response_model=Dict[str, Any])
async def update_lesson(
    lesson_id: str,
    updates: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update lesson with permission checks"""
    
    lesson = await require_lesson_permission(
        db, str(current_user.id), lesson_id, "edit_content", 
        UserRole(current_user.role), permission_manager
    )
    
    # Check content modification rules
    content_permissions = await permission_manager.check_content_modification_permission(
        db, str(current_user.id), lesson, UserRole(current_user.role)
    )
    
    if not content_permissions["can_edit"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=content_permissions["reason"]
        )
    
    # If requires approval, mark as pending
    if content_permissions["requires_approval"]:
        updates["status"] = "pending_approval"
        updates["pending_approval"] = {
            "requested_by": ObjectId(current_user.id),
            "requested_at": datetime.utcnow(),
            "changes": updates.copy()
        }
    
    # Update lesson
    updates["updated_at"] = datetime.utcnow()
    
    result = await db["lessons"].update_one(
        {"_id": ObjectId(lesson_id)},
        {"$set": updates}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update lesson"
        )
    
    return {
        "success": True,
        "message": "Lesson updated successfully" + (" (pending approval)" if content_permissions["requires_approval"] else ""),
        "requires_approval": content_permissions["requires_approval"]
    }


@router.post("/{lesson_id}/publish")
async def publish_lesson(
    lesson_id: str,
    publish_data: Dict[str, Any] = Body({}),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Publish or unpublish lesson"""
    
    lesson = await require_lesson_permission(
        db, str(current_user.id), lesson_id, "publish_lesson", 
        UserRole(current_user.role), permission_manager
    )
    
    publish = publish_data.get("publish", True)
    publish_message = publish_data.get("message", "")
    
    update_data = {
        "is_published": publish,
        "updated_at": datetime.utcnow()
    }
    
    if publish:
        update_data["published_at"] = datetime.utcnow()
        update_data["published_by"] = ObjectId(current_user.id)
        update_data["status"] = "published"
    else:
        update_data["status"] = "draft"
        update_data["unpublished_at"] = datetime.utcnow()
        update_data["unpublished_by"] = ObjectId(current_user.id)
    
    if publish_message:
        update_data["publish_message"] = publish_message
    
    await db["lessons"].update_one(
        {"_id": ObjectId(lesson_id)},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": f"Lesson {'published' if publish else 'unpublished'} successfully"
    }


# ==================== TEACHER ASSIGNMENT ENDPOINTS ====================

@router.post("/{lesson_id}/assign-teacher")
async def assign_teacher(
    lesson_id: str,
    assignment_data: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Assign teacher to lesson"""
    
    await require_coordinator_access(
        db, str(current_user.id), lesson_id, permission_manager
    )
    
    # Validate required fields
    required_fields = ["teacher_id", "class_ids"]
    if not all(field in assignment_data for field in required_fields):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {required_fields}"
        )
    
    try:
        assignment = await assignment_system.assign_teacher_to_lesson(
            db=db,
            lesson_id=lesson_id,
            teacher_id=assignment_data["teacher_id"],
            class_ids=assignment_data["class_ids"],
            assigned_by=str(current_user.id),
            assignment_type=assignment_data.get("assignment_type", "primary"),
            custom_permissions=assignment_data.get("custom_permissions"),
            notes=assignment_data.get("notes"),
            auto_assigned=False
        )
        
        return {
            "success": True,
            "message": "Teacher assigned successfully",
            "assignment": assignment.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign teacher: {str(e)}"
        )


@router.post("/{lesson_id}/transfer-teacher")
async def transfer_teacher(
    lesson_id: str,
    transfer_data: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Transfer teacher assignment to another teacher"""
    
    await require_coordinator_access(
        db, str(current_user.id), lesson_id, permission_manager
    )
    
    required_fields = ["old_teacher_id", "new_teacher_id"]
    if not all(field in transfer_data for field in required_fields):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {required_fields}"
        )
    
    try:
        result = await assignment_system.transfer_teacher_assignment(
            db=db,
            lesson_id=lesson_id,
            old_teacher_id=transfer_data["old_teacher_id"],
            new_teacher_id=transfer_data["new_teacher_id"],
            transferred_by=str(current_user.id),
            transfer_reason=transfer_data.get("transfer_reason", "teacher_change"),
            maintain_permissions=transfer_data.get("maintain_permissions", True),
            transition_period_days=transfer_data.get("transition_period_days", 7),
            notify_students=transfer_data.get("notify_students", True)
        )
        
        return {
            "success": True,
            "message": "Teacher assignment transferred successfully",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to transfer teacher: {str(e)}"
        )


@router.delete("/{lesson_id}/remove-teacher/{teacher_id}")
async def remove_teacher_assignment(
    lesson_id: str,
    teacher_id: str,
    removal_reason: str = Query("unassigned"),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Remove teacher assignment from lesson"""
    
    await require_coordinator_access(
        db, str(current_user.id), lesson_id, permission_manager
    )
    
    success = await assignment_system.remove_teacher_assignment(
        db=db,
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        removed_by=str(current_user.id),
        removal_reason=removal_reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher assignment not found"
        )
    
    return {
        "success": True,
        "message": "Teacher assignment removed successfully"
    }


@router.put("/{lesson_id}/update-teacher-permissions/{teacher_id}")
async def update_teacher_permissions(
    lesson_id: str,
    teacher_id: str,
    permissions: Dict[str, bool] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update teacher's permissions in lesson"""
    
    await require_coordinator_access(
        db, str(current_user.id), lesson_id, permission_manager
    )
    
    success = await permission_manager.update_teacher_permissions(
        db=db,
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        new_permissions=permissions,
        updated_by=str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher assignment not found"
        )
    
    return {
        "success": True,
        "message": "Teacher permissions updated successfully"
    }


@router.get("/{lesson_id}/teacher-assignments")
async def get_lesson_teacher_assignments(
    lesson_id: str,
    include_inactive: bool = Query(False),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all teacher assignments for lesson"""
    
    await require_lesson_permission(
        db, str(current_user.id), lesson_id, "view_lesson",
        UserRole(current_user.role), permission_manager
    )
    
    assignments = await assignment_system.get_lesson_teacher_assignments(
        db=db,
        lesson_id=lesson_id,
        include_inactive=include_inactive,
        populate_teacher_info=True
    )
    
    return {
        "lesson_id": lesson_id,
        "assignments": assignments,
        "total_count": len(assignments),
        "active_count": len([a for a in assignments if a.get("is_active", True)])
    }


@router.get("/teacher/{teacher_id}/lessons")
async def get_teacher_lessons(
    teacher_id: str,
    academic_period_id: Optional[str] = Query(None),
    include_legacy: bool = Query(True),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all lessons assigned to teacher"""
    
    # Check permission - can view own lessons or coordinator can view teacher's lessons
    if str(current_user.id) != teacher_id and current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view teacher lessons"
        )
    
    lessons = await assignment_system.get_teacher_lessons(
        db=db,
        teacher_id=teacher_id,
        academic_period_id=academic_period_id,
        include_legacy=include_legacy
    )
    
    return {
        "teacher_id": teacher_id,
        "lessons": lessons,
        "total_count": len(lessons)
    }


# ==================== STANDARDIZATION ENDPOINTS ====================

@router.post("/{lesson_id}/standardize")
async def standardize_lesson(
    lesson_id: str,
    standardization_data: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Standardize lesson content across all classes"""
    
    lesson = await require_coordinator_access(
        db, str(current_user.id), lesson_id, permission_manager
    )
    
    # Update standardization settings
    standardization_settings = {
        "is_standardized": standardization_data.get("is_standardized", True),
        "allow_customization": standardization_data.get("allow_customization", True),
        "customization_level": standardization_data.get("customization_level", "moderate"),
        "approval_required": standardization_data.get("approval_required", False),
        "last_standardized_at": datetime.utcnow(),
        "last_standardized_by": ObjectId(current_user.id)
    }
    
    await db["lessons"].update_one(
        {"_id": ObjectId(lesson_id)},
        {
            "$set": {
                "standardization": standardization_settings,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Lesson standardization settings updated successfully",
        "standardization": standardization_settings
    }


@router.post("/{lesson_id}/approve-changes")
async def approve_lesson_changes(
    lesson_id: str,
    approval_data: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Approve pending lesson changes"""
    
    lesson = await require_coordinator_access(
        db, str(current_user.id), lesson_id, permission_manager
    )
    
    lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    pending_approval = lesson_doc.get("pending_approval")
    
    if not pending_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending changes to approve"
        )
    
    approve = approval_data.get("approve", True)
    approval_notes = approval_data.get("notes", "")
    
    if approve:
        # Apply pending changes
        changes = pending_approval.get("changes", {})
        changes.update({
            "status": "published",
            "approved_at": datetime.utcnow(),
            "approved_by": ObjectId(current_user.id),
            "approval_notes": approval_notes,
            "updated_at": datetime.utcnow()
        })
        
        await db["lessons"].update_one(
            {"_id": ObjectId(lesson_id)},
            {
                "$set": changes,
                "$unset": {"pending_approval": 1}
            }
        )
        
        message = "Changes approved and applied successfully"
    else:
        # Reject changes
        await db["lessons"].update_one(
            {"_id": ObjectId(lesson_id)},
            {
                "$set": {
                    "status": "draft",
                    "rejected_at": datetime.utcnow(),
                    "rejected_by": ObjectId(current_user.id),
                    "rejection_notes": approval_notes,
                    "updated_at": datetime.utcnow()
                },
                "$unset": {"pending_approval": 1}
            }
        )
        
        message = "Changes rejected successfully"
    
    return {
        "success": True,
        "message": message,
        "approved": approve
    }


# ==================== STATISTICS & ANALYTICS ENDPOINTS ====================

@router.get("/statistics/assignments")
async def get_assignment_statistics(
    lesson_id: Optional[str] = Query(None),
    coordinator_id: Optional[str] = Query(None),
    academic_period_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get teacher assignment statistics"""
    
    # Permission check - coordinator can view their stats, admin can view all
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view statistics"
        )
    
    # If not admin, filter to current coordinator
    if current_user.role == "coordinator" and not coordinator_id:
        coordinator_id = str(current_user.id)
    elif current_user.role == "coordinator" and coordinator_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own statistics"
        )
    
    stats = await assignment_system.get_assignment_statistics(
        db=db,
        lesson_id=lesson_id,
        coordinator_id=coordinator_id,
        academic_period_id=academic_period_id
    )
    
    return {
        "statistics": stats,
        "filters": {
            "lesson_id": lesson_id,
            "coordinator_id": coordinator_id,
            "academic_period_id": academic_period_id
        }
    }


@router.get("/{lesson_id}/analytics")
async def get_lesson_analytics(
    lesson_id: str,
    include_teacher_breakdown: bool = Query(False),
    include_student_progress: bool = Query(False),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get comprehensive lesson analytics"""
    
    lesson = await require_lesson_permission(
        db, str(current_user.id), lesson_id, "view_analytics",
        UserRole(current_user.role), permission_manager
    )
    
    # Get basic lesson stats
    lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    
    analytics = {
        "lesson_id": lesson_id,
        "title": lesson_doc.get("title"),
        "basic_stats": lesson_doc.get("stats", {}),
        "teacher_assignments": len([a for a in lesson_doc.get("teacher_assignments", []) if a.get("is_active", True)]),
        "target_classes": len(lesson_doc.get("target_scope", {}).get("class_ids", [])),
        "is_standardized": lesson_doc.get("standardization", {}).get("is_standardized", False)
    }
    
    # Add teacher breakdown if requested
    if include_teacher_breakdown:
        assignments = await assignment_system.get_lesson_teacher_assignments(
            db, lesson_id, populate_teacher_info=True
        )
        analytics["teacher_breakdown"] = assignments
    
    # Add student progress if requested
    if include_student_progress:
        enrollments = await db["lesson_enrollments"].find({
            "lesson_id": ObjectId(lesson_id),
            "is_active": True
        }).to_list(None)
        
        progress_stats = {
            "total_enrolled": len(enrollments),
            "completed": len([e for e in enrollments if e.get("completion_status") == "completed"]),
            "in_progress": len([e for e in enrollments if e.get("completion_status") == "in_progress"]),
            "not_started": len([e for e in enrollments if e.get("completion_status") == "not_started"])
        }
        
        analytics["student_progress"] = progress_stats
    
    return analytics


# ==================== UTILITY ENDPOINTS ====================

@router.post("/auto-assign-teachers")
async def auto_assign_teachers(
    academic_period_id: str = Body(..., embed=True),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Auto-assign teachers to all coordinated lessons for coordinator"""
    
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators and admins can auto-assign teachers"
        )
    
    from app.core.teacher_assignment_system import auto_assign_teachers_to_coordinated_lessons
    
    assignments_created = await auto_assign_teachers_to_coordinated_lessons(
        db=db,
        coordinator_id=str(current_user.id),
        academic_period_id=academic_period_id,
        assignment_system=assignment_system
    )
    
    return {
        "success": True,
        "message": f"Auto-assigned teachers to lessons successfully",
        "assignments_created": assignments_created
    }


@router.get("/permission-templates")
async def get_permission_templates(
    current_user: UserInDB = Depends(get_current_user)
):
    """Get available permission templates"""
    
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    templates = {}
    for template_name, permissions in permission_manager.PERMISSION_TEMPLATES.items():
        templates[template_name] = permissions.dict()
    
    return {
        "templates": templates,
        "assignment_types": ["primary", "substitute", "guest"]
    }


@router.get("/coordination-lessons/{coordination_assignment_id}")
async def get_coordination_lessons(
    coordination_assignment_id: str,
    academic_period_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all lessons under specific coordination assignment"""
    
    # Verify user has access to this coordination
    coordination = await db["coordination_assignments"].find_one({
        "_id": ObjectId(coordination_assignment_id),
        "$or": [
            {"coordinator_id": ObjectId(current_user.id)},
            {"is_active": True}  # Admin can view all
        ]
    })
    
    if not coordination and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to coordination assignment"
        )
    
    query = {"ownership.coordination_assignment_id": ObjectId(coordination_assignment_id)}
    if academic_period_id:
        query["academic_period_id"] = ObjectId(academic_period_id)
    
    lessons = await db["lessons"].find(query).to_list(None)
    
    # Add basic info to each lesson
    for lesson in lessons:
        lesson["id"] = str(lesson["_id"])
        lesson["active_teachers"] = len([
            a for a in lesson.get("teacher_assignments", []) 
            if a.get("is_active", True)
        ])
    
    return {
        "coordination_assignment_id": coordination_assignment_id,
        "lessons": lessons,
        "total_count": len(lessons)
    }