# ==============================================================================
# File: app/api/v1/endpoints/lesson_progress.py
# Deskripsi: API endpoints untuk Lesson Progress tracking (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_database, get_current_user
from app.crud.lesson_progress import lesson_progress_crud
from app.schemas.lesson_progress import (
    LessonProgressStartRequest, LessonProgressUpdateRequest,
    LessonProgressResponse, LessonProgressSummaryResponse,
    PaginatedLessonProgressResponse, ProgressOperationResponse,
    PageProgressRequest, ComponentProgressRequest,
    LessonAnalyticsResponse, ProgressFilters,
    ActivityRecordRequest, ActivityResponse,
    BatchProgressUpdateRequest, BatchProgressUpdateResponse
)
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

# ==================== LESSON PROGRESS CRUD ====================

@router.post("/lessons/{lesson_id}/start", response_model=LessonProgressResponse, status_code=status.HTTP_201_CREATED)
async def start_lesson_progress(
    lesson_id: str,
    start_data: LessonProgressStartRequest = LessonProgressStartRequest(),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Start progress tracking untuk lesson"""
    
    try:
        progress = await lesson_progress_crud.start_lesson_progress(
            db=db,
            student_id=str(current_user["_id"]),
            lesson_id=lesson_id,
            course_id=start_data.course_id,
            module_id=start_data.module_id,
            access_method=start_data.access_method
        )
        
        # Convert to response format
        response_data = progress.dict()
        response_data["id"] = progress.id
        response_data["student_id"] = str(progress.student_id)
        response_data["lesson_id"] = str(progress.lesson_id)
        response_data["course_id"] = str(progress.course_id) if progress.course_id else None
        response_data["module_id"] = str(progress.module_id) if progress.module_id else None
        
        return LessonProgressResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start lesson progress: {str(e)}"
        )

@router.get("/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get lesson progress untuk current user"""
    
    try:
        progress = await lesson_progress_crud.get_lesson_progress(
            db, str(current_user["_id"]), lesson_id
        )
        
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson progress not found"
            )
        
        # Get lesson info untuk response
        lesson_info = await db["lessons"].find_one(
            {"_id": progress.lesson_id},
            {"title": 1, "description": 1}
        )
        
        response_data = progress.dict()
        response_data["id"] = progress.id
        response_data["student_id"] = str(progress.student_id)
        response_data["lesson_id"] = str(progress.lesson_id)
        response_data["lesson_title"] = lesson_info.get("title") if lesson_info else None
        response_data["lesson_description"] = lesson_info.get("description") if lesson_info else None
        response_data["course_id"] = str(progress.course_id) if progress.course_id else None
        response_data["module_id"] = str(progress.module_id) if progress.module_id else None
        
        return LessonProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lesson progress: {str(e)}"
        )

@router.put("/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: str,
    updates: LessonProgressUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update lesson progress"""
    
    try:
        progress = await lesson_progress_crud.update_lesson_progress_status(
            db=db,
            student_id=str(current_user["_id"]),
            lesson_id=lesson_id,
            status=updates.status if updates.status else None,
            metadata={
                "current_page": updates.current_page,
                "estimated_time_remaining": updates.estimated_time_remaining,
                "device_type": updates.device_type
            }
        )
        
        # Format response
        response_data = progress.dict()
        response_data["id"] = progress.id
        response_data["student_id"] = str(progress.student_id)
        response_data["lesson_id"] = str(progress.lesson_id)
        response_data["course_id"] = str(progress.course_id) if progress.course_id else None
        response_data["module_id"] = str(progress.module_id) if progress.module_id else None
        
        return LessonProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lesson progress: {str(e)}"
        )

# ==================== PAGE PROGRESS MANAGEMENT ====================

@router.put("/lessons/{lesson_id}/pages/{page_number}/progress")
async def update_page_progress(
    lesson_id: str,
    page_number: int,
    progress_data: PageProgressRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update progress untuk specific page"""
    
    try:
        # Convert request to dict format
        update_data = {
            "status": progress_data.status,
            "time_spent": progress_data.time_spent,
            "completion_percentage": progress_data.completion_percentage,
            "component_progress": [comp.dict() for comp in progress_data.component_progress]
        }
        
        progress = await lesson_progress_crud.update_page_progress(
            db=db,
            student_id=str(current_user["_id"]),
            lesson_id=lesson_id,
            page_number=page_number,
            progress_data=update_data
        )
        
        return {
            "success": True,
            "message": "Page progress updated successfully",
            "lesson_id": lesson_id,
            "page_number": page_number,
            "completion_percentage": progress.completion_percentage,
            "next_page": page_number + 1 if page_number < len(progress.page_progress) else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update page progress: {str(e)}"
        )

@router.post("/lessons/{lesson_id}/pages/{page_number}/components/{component_id}/complete")
async def complete_component(
    lesson_id: str,
    page_number: int,
    component_id: str,
    completion_data: ComponentProgressRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Mark component as completed"""
    
    try:
        progress = await lesson_progress_crud.complete_component(
            db=db,
            student_id=str(current_user["_id"]),
            lesson_id=lesson_id,
            page_number=page_number,
            component_id=component_id,
            completion_data=completion_data.dict()
        )
        
        return {
            "success": True,
            "message": "Component completed successfully",
            "component_id": component_id,
            "score": completion_data.score,
            "lesson_progress": progress.completion_percentage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete component: {str(e)}"
        )

# ==================== STUDENT PROGRESS LIST ====================

@router.get("/students/me/lesson-progress", response_model=PaginatedLessonProgressResponse)
async def get_my_lesson_progress(
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    
    # Filters
    course_id: Optional[str] = Query(None, description="Filter by course"),
    module_id: Optional[str] = Query(None, description="Filter by module"),
    status: Optional[str] = Query(None, description="Filter by status"),
    access_method: Optional[str] = Query(None, description="Filter by access method"),
    
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get lesson progress list untuk current user"""
    
    try:
        filters = {
            "course_id": course_id,
            "module_id": module_id,
            "status": status,
            "access_method": access_method
        }
        
        skip = (page - 1) * per_page
        
        result = await lesson_progress_crud.get_student_lesson_progress_list(
            db=db,
            student_id=str(current_user["_id"]),
            filters=filters,
            skip=skip,
            limit=per_page
        )
        
        # Format response
        return PaginatedLessonProgressResponse(
            items=[LessonProgressSummaryResponse(**item) for item in result["items"]],
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
            detail=f"Failed to get lesson progress list: {str(e)}"
        )

# ==================== LESSON ANALYTICS (TEACHER) ====================

@router.get("/lessons/{lesson_id}/analytics", response_model=LessonAnalyticsResponse)
async def get_lesson_analytics(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get lesson progress analytics (untuk teachers)"""
    
    # Check if user is teacher/admin
    user_roles = current_user.get("roles", [])
    if not any(role in user_roles for role in ["teacher", "admin", "coordinator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view lesson analytics"
        )
    
    try:
        # Verify lesson exists dan user has access
        lesson = await db["lessons"].find_one({"_id": lesson_id})
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Check if user created lesson or has admin role
        if lesson.get("created_by") != current_user["_id"] and "admin" not in user_roles:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to view analytics for this lesson"
            )
        
        analytics_data = await lesson_progress_crud.get_lesson_progress_analytics(
            db, lesson_id, str(current_user["_id"])
        )
        
        return LessonAnalyticsResponse(**analytics_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lesson analytics: {str(e)}"
        )

# ==================== ACTIVITY TRACKING ====================

@router.post("/lessons/{lesson_id}/activity")
async def record_lesson_activity(
    lesson_id: str,
    activity_data: ActivityRecordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Record activity dalam lesson"""
    
    try:
        # Get or create lesson progress
        progress = await lesson_progress_crud.get_lesson_progress(
            db, str(current_user["_id"]), lesson_id
        )
        
        if not progress:
            # Auto-start progress if not exists
            progress = await lesson_progress_crud.start_lesson_progress(
                db, str(current_user["_id"]), lesson_id
            )
        
        # Update activity timestamp dan time spent
        updates = [
            {
                "student_id": str(current_user["_id"]),
                "lesson_id": lesson_id,
                "total_time_spent": progress.total_time_spent + activity_data.time_spent
            }
        ]
        
        updated_count = await lesson_progress_crud.bulk_update_activity_timestamps(db, updates)
        
        return ActivityResponse(
            success=updated_count > 0,
            message="Activity recorded successfully" if updated_count > 0 else "Failed to record activity",
            updated_progress={
                "lesson_id": lesson_id,
                "total_time_spent": progress.total_time_spent + activity_data.time_spent
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record activity: {str(e)}"
        )

# ==================== BATCH OPERATIONS ====================

@router.post("/lessons/batch-update", response_model=BatchProgressUpdateResponse)
async def batch_update_lesson_progress(
    update_request: BatchProgressUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Batch update lesson progress"""
    
    # Only allow for current user's progress
    user_id = str(current_user["_id"])
    
    try:
        updated_count = 0
        failed_count = 0
        errors = []
        
        if update_request.update_type == "activity_timestamp":
            # Validate all updates are for current user
            valid_updates = []
            for update in update_request.updates:
                if update.get("student_id") == user_id:
                    valid_updates.append(update)
                else:
                    failed_count += 1
                    errors.append(f"Unauthorized update for student {update.get('student_id')}")
            
            if valid_updates:
                updated_count = await lesson_progress_crud.bulk_update_activity_timestamps(
                    db, valid_updates
                )
        
        return BatchProgressUpdateResponse(
            success=updated_count > 0,
            updated_count=updated_count,
            failed_count=failed_count,
            errors=errors
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch update progress: {str(e)}"
        )

# ==================== PROGRESS RESET/DELETE ====================

@router.delete("/lessons/{lesson_id}/progress", response_model=ProgressOperationResponse)
async def reset_lesson_progress(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Reset lesson progress (delete dan restart)"""
    
    try:
        # Delete existing progress
        deleted = await lesson_progress_crud.delete_lesson_progress(
            db, str(current_user["_id"]), lesson_id
        )
        
        if deleted:
            return ProgressOperationResponse(
                success=True,
                message="Lesson progress reset successfully",
                progress_id=lesson_id,
                next_steps=[
                    {
                        "action": "restart_lesson",
                        "lesson_id": lesson_id,
                        "message": "You can now restart this lesson"
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
            detail=f"Failed to reset lesson progress: {str(e)}"
        )

# ==================== UTILITY ENDPOINTS ====================

@router.get("/lessons/{lesson_id}/next-page")
async def get_next_page(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get next page untuk lesson berdasarkan current progress"""
    
    try:
        progress = await lesson_progress_crud.get_lesson_progress(
            db, str(current_user["_id"]), lesson_id
        )
        
        if not progress:
            return {
                "next_page": 1,
                "total_pages": 0,
                "message": "Start lesson to begin progress tracking"
            }
        
        # Find next incomplete page
        next_page = None
        for page in progress.page_progress:
            if page.status != "completed":
                next_page = page.page_number
                break
        
        if next_page is None:
            next_page = len(progress.page_progress)  # Last page if all completed
        
        return {
            "next_page": next_page,
            "total_pages": len(progress.page_progress),
            "current_progress": progress.completion_percentage,
            "message": "Ready to continue" if next_page <= len(progress.page_progress) else "Lesson completed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next page: {str(e)}"
        )
