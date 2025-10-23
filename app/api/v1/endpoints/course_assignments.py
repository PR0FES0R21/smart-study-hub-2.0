# ==============================================================================
# File: app/api/v1/endpoints/course_assignments.py
# Deskripsi: API endpoints untuk Course Assignment (assign course to class)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime

from app.api.v1.deps import get_database, get_current_user
from app.crud.course_class_settings import course_class_settings_crud
from app.schemas.course_class_settings import (
    AssignCourseToClassRequest,
    UpdateCourseClassSettingsRequest,
    AddStudentOverrideRequest,
    RemoveStudentOverrideRequest,
    CourseClassSettingsResponse,
    CourseClassSettingsSummaryResponse,
    CourseClassAnalyticsResponse
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

async def check_teacher_permission(
    db: AsyncIOMotorDatabase,
    user_id: str,
    class_id: str
) -> bool:
    """Check if user is teacher of the class"""
    # Check if user has teaching_assignment for this class
    assignment = await db["teaching_assignments"].find_one({
        "teacher_id": ObjectId(user_id),
        "class_id": ObjectId(class_id),
        "status": "active"
    })
    return assignment is not None


async def enrich_assignment_response(
    db: AsyncIOMotorDatabase,
    assignment: Any,
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Enrich assignment with related data"""
    # Get course
    course = await db["courses"].find_one({"_id": ObjectId(assignment.course_id)})
    
    # Get class
    class_doc = await db["classes"].find_one({"_id": ObjectId(assignment.class_id)})
    
    # Get teacher
    teacher = await db["users"].find_one({"_id": ObjectId(assignment.teacher_id)})
    
    # Get teacher profile
    teacher_profile = None
    if teacher and teacher.get("profile_id"):
        teacher_profile = await db["profiles"].find_one({"_id": teacher["profile_id"]})
    
    # Build response
    response = assignment.dict()
    response["id"] = assignment.id
    response["course_title"] = course.get("title") if course else None
    response["class_name"] = class_doc.get("name") if class_doc else None
    
    if teacher_profile:
        response["teacher_name"] = teacher_profile.get("full_name")
    elif teacher:
        response["teacher_name"] = f"{teacher.get('profile', {}).get('first_name', '')} {teacher.get('profile', {}).get('last_name', '')}".strip()
    else:
        response["teacher_name"] = None
    
    # Check permissions
    user_id = str(current_user["_id"])
    response["can_edit"] = user_id == str(assignment.teacher_id) or "admin" in current_user.get("roles", [])
    response["can_delete"] = response["can_edit"]
    response["can_override"] = response["can_edit"]
    
    return response


# ==================== ASSIGNMENT ENDPOINTS ====================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def assign_course_to_class(
    request: AssignCourseToClassRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Assign course to class.
    
    Only teacher of the class can assign courses.
    """
    user_id = str(current_user["_id"])
    
    # Check if user is teacher of this class
    is_teacher = await check_teacher_permission(db, user_id, request.class_id)
    is_admin = "admin" in current_user.get("roles", [])
    
    if not is_teacher and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers of this class can assign courses"
        )
    
    try:
        # Create assignment
        assignment = await course_class_settings_crud.assign_course_to_class(
            db=db,
            course_id=request.course_id,
            class_id=request.class_id,
            teacher_id=user_id,
            start_date=request.start_date,
            end_date=request.end_date,
            settings=request.settings
        )
        
        # Enrich response
        response = await enrich_assignment_response(db, assignment, current_user)
        
        return {
            "success": True,
            "message": "Course assigned to class successfully",
            "assignment": response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign course: {str(e)}"
        )


@router.get("/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get assignment details"""
    assignment = await course_class_settings_crud.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Enrich response
    response = await enrich_assignment_response(db, assignment, current_user)
    
    return {
        "success": True,
        "assignment": response
    }


@router.get("/class/{class_id}")
async def list_class_assignments(
    class_id: str,
    include_archived: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all course assignments for a class"""
    assignments = await course_class_settings_crud.get_by_class(
        db, class_id, include_archived
    )
    
    # Enrich each assignment
    enriched_assignments = []
    for assignment in assignments:
        enriched = await enrich_assignment_response(db, assignment, current_user)
        enriched_assignments.append(enriched)
    
    return {
        "success": True,
        "total": len(enriched_assignments),
        "assignments": enriched_assignments
    }


@router.get("/course/{course_id}")
async def list_course_assignments(
    course_id: str,
    include_archived: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all class assignments for a course"""
    assignments = await course_class_settings_crud.get_by_course(
        db, course_id, include_archived
    )
    
    # Enrich each assignment
    enriched_assignments = []
    for assignment in assignments:
        enriched = await enrich_assignment_response(db, assignment, current_user)
        enriched_assignments.append(enriched)
    
    return {
        "success": True,
        "total": len(enriched_assignments),
        "assignments": enriched_assignments
    }


@router.put("/{assignment_id}/settings")
async def update_assignment_settings(
    assignment_id: str,
    request: UpdateCourseClassSettingsRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update class settings"""
    # Get assignment
    assignment = await course_class_settings_crud.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check permissions
    user_id = str(current_user["_id"])
    is_teacher = user_id == str(assignment.teacher_id)
    is_admin = "admin" in current_user.get("roles", [])
    
    if not is_teacher and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned teacher can update settings"
        )
    
    try:
        # Update settings
        updated_assignment = await course_class_settings_crud.update_settings(
            db=db,
            setting_id=assignment_id,
            start_date=request.start_date,
            end_date=request.end_date,
            settings=request.settings
        )
        
        # Enrich response
        response = await enrich_assignment_response(db, updated_assignment, current_user)
        
        return {
            "success": True,
            "message": "Settings updated successfully",
            "assignment": response
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.delete("/{assignment_id}")
async def archive_assignment(
    assignment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Archive assignment (soft delete)"""
    # Get assignment
    assignment = await course_class_settings_crud.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check permissions
    user_id = str(current_user["_id"])
    is_teacher = user_id == str(assignment.teacher_id)
    is_admin = "admin" in current_user.get("roles", [])
    
    if not is_teacher and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned teacher can archive assignment"
        )
    
    try:
        # Archive
        archived_assignment = await course_class_settings_crud.archive(
            db=db,
            setting_id=assignment_id,
            archived_by=user_id
        )
        
        return {
            "success": True,
            "message": "Assignment archived successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive assignment: {str(e)}"
        )


@router.post("/{assignment_id}/restore")
async def restore_assignment(
    assignment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Restore archived assignment"""
    # Get assignment
    assignment = await course_class_settings_crud.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check permissions
    user_id = str(current_user["_id"])
    is_teacher = user_id == str(assignment.teacher_id)
    is_admin = "admin" in current_user.get("roles", [])
    
    if not is_teacher and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned teacher can restore assignment"
        )
    
    try:
        # Restore
        restored_assignment = await course_class_settings_crud.restore(
            db=db,
            setting_id=assignment_id
        )
        
        # Enrich response
        response = await enrich_assignment_response(db, restored_assignment, current_user)
        
        return {
            "success": True,
            "message": "Assignment restored successfully",
            "assignment": response
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore assignment: {str(e)}"
        )


# ==================== OVERRIDE ENDPOINTS ====================

@router.post("/{assignment_id}/overrides")
async def add_student_override(
    assignment_id: str,
    request: AddStudentOverrideRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add or update student override (unlock modules/lessons).
    
    Teacher can override locks for specific students.
    """
    # Get assignment
    assignment = await course_class_settings_crud.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check permissions
    user_id = str(current_user["_id"])
    is_teacher = user_id == str(assignment.teacher_id)
    is_admin = "admin" in current_user.get("roles", [])
    
    if not is_teacher and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned teacher can add overrides"
        )
    
    try:
        # Add override
        updated_assignment = await course_class_settings_crud.add_student_override(
            db=db,
            setting_id=assignment_id,
            student_id=request.student_id,
            teacher_id=user_id,
            unlocked_modules=request.unlocked_modules,
            unlocked_lessons=request.unlocked_lessons,
            reason=request.reason
        )
        
        return {
            "success": True,
            "message": "Student override added successfully",
            "overrides": updated_assignment.class_overrides.dict()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add override: {str(e)}"
        )


@router.delete("/{assignment_id}/overrides/{student_id}")
async def remove_student_override(
    assignment_id: str,
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Remove student override"""
    # Get assignment
    assignment = await course_class_settings_crud.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check permissions
    user_id = str(current_user["_id"])
    is_teacher = user_id == str(assignment.teacher_id)
    is_admin = "admin" in current_user.get("roles", [])
    
    if not is_teacher and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned teacher can remove overrides"
        )
    
    try:
        # Remove override
        updated_assignment = await course_class_settings_crud.remove_student_override(
            db=db,
            setting_id=assignment_id,
            student_id=student_id
        )
        
        return {
            "success": True,
            "message": "Student override removed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove override: {str(e)}"
        )
