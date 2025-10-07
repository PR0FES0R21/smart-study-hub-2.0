# ==============================================================================
# File: app/api/v1/endpoints/module_progress.py
# Deskripsi: API endpoints untuk Module Progress tracking (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_database, get_current_user
from app.crud.module_progress import module_progress_crud
from app.schemas.lesson_progress import (
    ModuleProgressResponse, ModuleProgressWithLessonsResponse,
    PaginatedModuleProgressResponse, ProgressOperationResponse,
    ModuleAnalyticsResponse, ProgressFilters
)
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

# ==================== MODULE PROGRESS CRUD ====================

@router.post("/modules/{module_id}/start", response_model=ModuleProgressResponse, status_code=status.HTTP_201_CREATED)
async def start_module_progress(
    module_id: str ,
    course_id: Optional[str] = Query(None, description="Course ID if accessed via course"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Start progress tracking untuk module"""
    
    try:
        progress = await module_progress_crud.start_module_progress(
            db=db,
            student_id=str(current_user["_id"]),
            module_id=module_id,
            course_id=course_id
        )
        
        # Get module info
        module_info = await db["modules"].find_one(
            {"_id": progress.module_id},
            {"title": 1, "description": 1}
        )
        
        # Convert to response format
        response_data = progress.dict()
        response_data["id"] = progress.id
        response_data["student_id"] = str(progress.student_id)
        response_data["module_id"] = str(progress.module_id)
        response_data["module_title"] = module_info.get("title") if module_info else None
        response_data["module_description"] = module_info.get("description") if module_info else None
        response_data["course_id"] = str(progress.course_id) if progress.course_id else None
        response_data["current_lesson_id"] = str(progress.current_lesson_id) if progress.current_lesson_id else None
        response_data["lesson_completion_order"] = [str(lid) for lid in progress.lesson_completion_order]
        
        return ModuleProgressResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start module progress: {str(e)}"
        )

@router.get("/modules/{module_id}/progress", response_model=ModuleProgressResponse)
async def get_module_progress(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get module progress untuk current user"""
    
    try:
        progress = await module_progress_crud.get_module_progress(
            db, str(current_user["_id"]), module_id
        )
        
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Module progress not found"
            )
        
        # Get module info
        module_info = await db["modules"].find_one(
            {"_id": progress.module_id},
            {"title": 1, "description": 1}
        )
        
        response_data = progress.dict()
        response_data["id"] = progress.id
        response_data["student_id"] = str(progress.student_id)
        response_data["module_id"] = str(progress.module_id)
        response_data["module_title"] = module_info.get("title") if module_info else None
        response_data["module_description"] = module_info.get("description") if module_info else None
        response_data["course_id"] = str(progress.course_id) if progress.course_id else None
        response_data["current_lesson_id"] = str(progress.current_lesson_id) if progress.current_lesson_id else None
        response_data["lesson_completion_order"] = [str(lid) for lid in progress.lesson_completion_order]
        
        return ModuleProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get module progress: {str(e)}"
        )

@router.get("/modules/{module_id}/progress/detailed", response_model=ModuleProgressWithLessonsResponse)
async def get_module_progress_with_lessons(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get detailed module progress dengan lesson details"""
    
    try:
        result = await module_progress_crud.get_module_progress_with_lessons(
            db, str(current_user["_id"]), module_id
        )
        
        # Format module progress
        module_progress = result["module_progress"]
        module_progress_data = {
            "id": str(module_progress["_id"]) if "_id" in module_progress else module_progress.get("id"),
            "student_id": str(module_progress["student_id"]),
            "module_id": str(module_progress["module_id"]),
            "course_id": str(module_progress["course_id"]) if module_progress.get("course_id") else None,
            "status": module_progress.get("status", "not_started"),
            "completion_percentage": module_progress.get("completion_percentage", 0.0),
            "score": module_progress.get("score"),
            "total_lessons": module_progress.get("total_lessons", 0),
            "completed_lessons": module_progress.get("completed_lessons", 0),
            "in_progress_lessons": module_progress.get("in_progress_lessons", 0),
            "current_lesson_id": str(module_progress["current_lesson_id"]) if module_progress.get("current_lesson_id") else None,
            "lesson_completion_order": [str(lid) for lid in module_progress.get("lesson_completion_order", [])],
            "total_time_spent": module_progress.get("total_time_spent", 0),
            "estimated_time_remaining": module_progress.get("estimated_time_remaining"),
            "started_at": module_progress.get("started_at"),
            "completed_at": module_progress.get("completed_at"),
            "last_activity": module_progress.get("last_activity"),
            "created_at": module_progress.get("created_at")
        }
        
        return ModuleProgressWithLessonsResponse(
            module_progress=ModuleProgressResponse(**module_progress_data),
            lesson_details=result["lesson_details"],
            learning_path=result["learning_path"],
            next_lesson=result["next_lesson"],
            completion_summary=result["completion_summary"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get detailed module progress: {str(e)}"
        )

@router.put("/modules/{module_id}/progress/refresh")
async def refresh_module_progress(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Refresh module progress berdasarkan lesson progress"""
    
    try:
        progress = await module_progress_crud.update_module_progress_from_lessons(
            db, str(current_user["_id"]), module_id
        )
        
        return {
            "success": True,
            "message": "Module progress refreshed successfully",
            "module_id": module_id,
            "completion_percentage": progress.completion_percentage,
            "completed_lessons": progress.completed_lessons,
            "total_lessons": progress.total_lessons
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh module progress: {str(e)}"
        )

@router.put("/modules/{module_id}/progress/status")
async def update_module_status(
    module_id: str ,
    status_update: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update module progress status"""
    
    try:
        progress = await module_progress_crud.update_module_progress_status(
            db=db,
            student_id=str(current_user["_id"]),
            module_id=module_id,
            status=status_update.get("status"),
            metadata=status_update.get("metadata", {})
        )
        
        return {
            "success": True,
            "message": "Module status updated successfully",
            "module_id": module_id,
            "status": progress.status,
            "completion_percentage": progress.completion_percentage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update module status: {str(e)}"
        )

# ==================== STUDENT PROGRESS LIST ====================

@router.get("/students/me/module-progress", response_model=PaginatedModuleProgressResponse)
async def get_my_module_progress(
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    
    # Filters
    course_id: Optional[str] = Query(None, description="Filter by course"),
    status: Optional[str] = Query(None, description="Filter by status"),
    
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get module progress list untuk current user"""
    
    try:
        filters = {
            "course_id": course_id,
            "status": status
        }
        
        skip = (page - 1) * per_page
        
        result = await module_progress_crud.get_student_module_progress_list(
            db=db,
            student_id=str(current_user["_id"]),
            filters=filters,
            skip=skip,
            limit=per_page
        )
        
        # Format items
        formatted_items = []
        for item in result["items"]:
            formatted_item = {
                "id": item["id"],
                "student_id": item["student_id"],
                "module_id": item["module_id"],
                "module_title": item.get("module_title"),
                "module_description": item.get("module_description"),
                "course_id": item.get("course_id"),
                "status": item.get("status", "not_started"),
                "completion_percentage": item.get("completion_percentage", 0.0),
                "score": item.get("score"),
                "total_lessons": item.get("total_lessons", 0),
                "completed_lessons": item.get("completed_lessons", 0),
                "in_progress_lessons": item.get("in_progress_lessons", 0),
                "current_lesson_id": None,
                "lesson_completion_order": [],
                "total_time_spent": item.get("total_time_spent", 0),
                "estimated_time_remaining": item.get("estimated_time_remaining"),
                "started_at": item.get("started_at"),
                "completed_at": item.get("completed_at"),
                "last_activity": item.get("last_activity"),
                "created_at": item.get("created_at")
            }
            formatted_items.append(ModuleProgressResponse(**formatted_item))
        
        return PaginatedModuleProgressResponse(
            items=formatted_items,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=(result["total"] + per_page - 1) // per_page,
            has_next=result["has_next"],
            has_prev=result["has_prev"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get module progress list: {str(e)}"
        )

# ==================== MODULE ANALYTICS (TEACHER) ====================

@router.get("/modules/{module_id}/analytics", response_model=ModuleAnalyticsResponse)
async def get_module_analytics(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get module progress analytics (untuk teachers)"""
    
    # Check if user is teacher/admin
    user_roles = current_user.get("roles", [])
    if not any(role in user_roles for role in ["teacher", "admin", "coordinator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view module analytics"
        )
    
    try:
        # Verify module exists dan user has access
        from bson import ObjectId
        module = await db["modules"].find_one({"_id": ObjectId(module_id)})
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Check if user created module or has admin role
        if module.get("created_by") != current_user["_id"] and "admin" not in user_roles:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to view analytics for this module"
            )
        
        analytics_data = await module_progress_crud.get_module_progress_analytics(
            db, module_id, str(current_user["_id"])
        )
        
        return ModuleAnalyticsResponse(**analytics_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get module analytics: {str(e)}"
        )

# ==================== PROGRESS RESET/DELETE ====================

@router.delete("/modules/{module_id}/progress", response_model=ProgressOperationResponse)
async def reset_module_progress(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Reset module progress"""
    
    try:
        deleted = await module_progress_crud.delete_module_progress(
            db, str(current_user["_id"]), module_id
        )
        
        if deleted:
            return ProgressOperationResponse(
                success=True,
                message="Module progress reset successfully",
                progress_id=module_id,
                next_steps=[
                    {
                        "action": "restart_module",
                        "module_id": module_id,
                        "message": "You can now restart this module"
                    }
                ]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No progress found to reset"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset module progress: {str(e)}"
        )

# ==================== UTILITY ENDPOINTS ====================

@router.get("/modules/{module_id}/next-lesson")
async def get_next_lesson(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get next lesson untuk module berdasarkan progress"""
    
    try:
        result = await module_progress_crud.get_module_progress_with_lessons(
            db, str(current_user["_id"]), module_id
        )
        
        next_lesson = result.get("next_lesson")
        
        if next_lesson:
            return {
                "has_next": True,
                "next_lesson": next_lesson,
                "message": f"Next lesson: {next_lesson['title']}"
            }
        else:
            return {
                "has_next": False,
                "next_lesson": None,
                "message": "All lessons completed or no lessons available"
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next lesson: {str(e)}"
        )

@router.get("/modules/{module_id}/learning-path")
async def get_module_learning_path(
    module_id: str ,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get learning path untuk module"""
    
    try:
        result = await module_progress_crud.get_module_progress_with_lessons(
            db, str(current_user["_id"]), module_id
        )
        
        return {
            "module_id": module_id,
            "learning_path": result.get("learning_path", []),
            "completion_summary": result.get("completion_summary", {}),
            "next_lesson": result.get("next_lesson")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning path: {str(e)}"
        )
