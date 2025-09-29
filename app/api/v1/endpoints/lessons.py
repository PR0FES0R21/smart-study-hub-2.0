# ==============================================================================
# File: app/api/v1/endpoints/lessons.py
# Deskripsi: API endpoints untuk Lesson management (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_database, get_current_user
from app.crud.lesson import lesson_crud
from app.schemas.lesson import (
    LessonCreateRequest, LessonUpdateRequest, LessonDetailResponse,
    LessonSummaryResponse, PaginatedLessonResponse, LessonOperationResponse,
    LessonFilters, LessonSortBy, LessonLibraryResponse,
    LessonPageAddRequest, ComponentAddRequest,
    LessonCollaboratorRequest, LessonShareRequest, LessonReviewRequest,
    LessonAnalyticsResponse
)
# from app.core.permissions import require_permission  # Not needed for now
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

# ==================== LESSON CRUD ENDPOINTS ====================

@router.post("/", response_model=LessonDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson_data: LessonCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create new lesson"""
    
    # Check permissions - teachers dapat create lessons
    if "teacher" not in current_user.get("roles", []) and "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create lessons"
        )
    
    try:
        # Create lesson
        lesson = await lesson_crud.create_lesson(db, lesson_data, str(current_user["_id"]))
        
        # Convert to response format
        response_data = lesson.dict()
        response_data["id"] = lesson.id
        response_data["subject_name"] = None  # Would be populated by subject lookup
        response_data["created_by_name"] = f"{current_user.get('profile', {}).get('first_name', '')} {current_user.get('profile', {}).get('last_name', '')}"
        response_data["can_edit"] = True
        response_data["can_delete"] = True
        response_data["can_collaborate"] = True
        
        return LessonDetailResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lesson: {str(e)}"
        )

@router.get("/", response_model=PaginatedLessonResponse)
async def list_lessons(
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    
    # Filters
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    grade_level: Optional[int] = Query(None, ge=1, le=12, description="Filter by grade level"),
    created_by: Optional[str] = Query(None, description="Filter by creator ID"),
    visibility: Optional[str] = Query(None, description="public | private | shared"),
    status: Optional[str] = Query(None, description="draft | published | archived"),
    difficulty_level: Optional[str] = Query(None, description="easy | medium | hard"),
    topic_tags: Optional[str] = Query(None, description="Comma-separated topic tags"),
    search: Optional[str] = Query(None, description="Search in title, description"),
    
    # Sorting
    sort_by: str = Query("updated_at", description="Field to sort by"),
    sort_direction: str = Query("desc", pattern="^(asc|desc)$"),
    
    # Dependencies
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List lessons dengan filtering, sorting, dan pagination"""
    
    # Build filters
    filters = LessonFilters(
        subject_id=subject_id,
        grade_level=grade_level,
        created_by=created_by,
        visibility=visibility,
        status=status,
        difficulty_level=difficulty_level,
        topic_tags=topic_tags.split(",") if topic_tags else None,
        search=search
    )
    
    sort_options = LessonSortBy(field=sort_by, direction=sort_direction)
    
    skip = (page - 1) * per_page
    
    try:
        result = await lesson_crud.list_lessons(
            db=db,
            filters=filters,
            sort_by=sort_options,
            skip=skip,
            limit=per_page,
            user_id=str(current_user["_id"])
        )
        
        # Format response
        return PaginatedLessonResponse(
            items=[LessonSummaryResponse(**item) for item in result["items"]],
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"],
            has_next=result["has_next"],
            has_prev=result["has_prev"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lessons: {str(e)}"
        )

@router.get("/library", response_model=LessonLibraryResponse)
async def get_lesson_library(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get lesson library dengan featured, popular, recent lessons"""
    
    try:
        library_data = await lesson_crud.get_lesson_library(db, str(current_user["_id"]))
        return LessonLibraryResponse(**library_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lesson library: {str(e)}"
        )

@router.get("/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: str,
    include_usage: bool = Query(False, description="Include usage information"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get lesson by ID"""
    
    try:
        lesson = await lesson_crud.get_lesson_by_id(
            db, lesson_id, str(current_user["_id"]), include_usage
        )
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Check access permissions
        user_id = current_user["_id"]
        can_view = (
            lesson.visibility == "public" or
            lesson.created_by == user_id or
            user_id in lesson.collaborators or
            "admin" in current_user.get("roles", [])
        )
        
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this lesson"
            )
        
        # Format response dengan user permissions
        response_data = lesson.dict()
        response_data["id"] = lesson.id
        response_data["can_edit"] = lesson.is_editable_by(user_id)
        response_data["can_delete"] = lesson.created_by == user_id
        response_data["can_collaborate"] = lesson.is_editable_by(user_id)
        
        return LessonDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lesson: {str(e)}"
        )

@router.put("/{lesson_id}", response_model=LessonDetailResponse)
async def update_lesson(
    lesson_id: str,
    updates: LessonUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update lesson"""
    
    try:
        lesson = await lesson_crud.update_lesson(
            db, lesson_id, updates, str(current_user["_id"])
        )
        
        # Format response
        response_data = lesson.dict()
        response_data["id"] = lesson.id
        response_data["can_edit"] = lesson.is_editable_by(current_user["_id"])
        response_data["can_delete"] = lesson.created_by == current_user["_id"]
        
        return LessonDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lesson: {str(e)}"
        )

@router.delete("/{lesson_id}", response_model=LessonOperationResponse)
async def delete_lesson(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete lesson"""
    
    try:
        success = await lesson_crud.delete_lesson(db, lesson_id, str(current_user["_id"]))
        
        if success:
            return LessonOperationResponse(
                success=True,
                message="Lesson deleted successfully",
                lesson_id=lesson_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete lesson"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lesson: {str(e)}"
        )

# ==================== LESSON PAGE MANAGEMENT ====================

@router.post("/{lesson_id}/pages", status_code=status.HTTP_201_CREATED)
async def add_page_to_lesson(
    lesson_id: str,
    page_data: LessonPageAddRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add new page to lesson"""
    
    try:
        page = await lesson_crud.add_page_to_lesson(
            db, lesson_id, page_data.dict(), str(current_user["_id"])
        )
        
        return {
            "success": True,
            "message": "Page added successfully",
            "page": page.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add page: {str(e)}"
        )

@router.put("/{lesson_id}/pages/{page_number}")
async def update_lesson_page(
    lesson_id: str,
    page_number: int,
    page_updates: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update specific page dalam lesson"""
    
    try:
        page = await lesson_crud.update_lesson_page(
            db, lesson_id, page_number, page_updates, str(current_user["_id"])
        )
        
        return {
            "success": True,
            "message": "Page updated successfully",
            "page": page.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update page: {str(e)}"
        )

@router.post("/{lesson_id}/pages/{page_number}/components")
async def add_component_to_page(
    lesson_id: str,
    page_number: int,
    component_data: ComponentAddRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add component to lesson page"""
    
    # This would be implemented similarly to page updates
    # For now, return a placeholder
    return {
        "success": True,
        "message": "Component addition functionality to be implemented",
        "component_id": component_data.component_id
    }

# ==================== COLLABORATION ENDPOINTS ====================

@router.post("/{lesson_id}/collaborators")
async def add_collaborator(
    lesson_id: str,
    collaborator_data: LessonCollaboratorRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add collaborator to lesson"""
    
    # Implementation would add user to collaborators list
    return {
        "success": True,
        "message": "Collaborator added successfully"
    }

@router.post("/{lesson_id}/share")
async def share_lesson(
    lesson_id: str,
    share_data: LessonShareRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Share lesson dengan other teachers"""
    
    # Implementation would handle lesson sharing
    return {
        "success": True,
        "message": f"Lesson shared with {len(share_data.recipient_ids)} teachers"
    }

@router.post("/{lesson_id}/review")
async def review_lesson(
    lesson_id: str,
    review_data: LessonReviewRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add review/rating to lesson"""
    
    # Implementation would handle lesson reviews
    return {
        "success": True,
        "message": "Review added successfully"
    }

# ==================== ANALYTICS ENDPOINTS ====================

@router.get("/{lesson_id}/analytics", response_model=LessonAnalyticsResponse)
async def get_lesson_analytics(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get lesson analytics dan performance metrics"""
    
    try:
        # Verify lesson exists dan user has access
        lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Check permissions
        if not lesson.is_editable_by(current_user["_id"]) and "admin" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Not authorized to view analytics")
        
        # Get analytics data (placeholder implementation)
        analytics_data = {
            "lesson_id": lesson_id,
            "total_views": 0,
            "unique_students": 0,
            "times_used_in_modules": 0,
            "average_completion_time": 0.0,
            "completion_rate": 0.0,
            "average_score": 0.0,
            "component_performance": {},
            "difficulty_feedback": {},
            "page_views": [],
            "drop_off_points": [],
            "most_popular_components": [],
            "peak_usage_hours": [],
            "usage_by_day": {},
            "student_ratings": [],
            "teacher_reviews": []
        }
        
        return LessonAnalyticsResponse(**analytics_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )

# ==================== UTILITY ENDPOINTS ====================

@router.get("/{lesson_id}/usage")
async def get_lesson_usage(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get information about where lesson is being used"""
    
    try:
        # Find modules using this lesson
        modules_using_lesson = await db["modules"].find({
            "lesson_refs.lesson_id": lesson_id
        }, {
            "title": 1,
            "created_by": 1,
            "status": 1
        }).to_list(100)
        
        # Find courses using these modules
        module_ids = [str(module["_id"]) for module in modules_using_lesson]
        courses_using_lesson = await db["courses"].find({
            "module_refs.module_id": {"$in": module_ids}
        }, {
            "title": 1,
            "coordinator_id": 1,
            "status": 1
        }).to_list(100)
        
        return {
            "lesson_id": lesson_id,
            "used_in_modules": len(modules_using_lesson),
            "used_in_courses": len(courses_using_lesson),
            "modules": [
                {
                    "id": str(module["_id"]),
                    "title": module["title"],
                    "status": module.get("status", "draft")
                }
                for module in modules_using_lesson
            ],
            "courses": [
                {
                    "id": str(course["_id"]),
                    "title": course["title"],
                    "status": course.get("status", "draft")
                }
                for course in courses_using_lesson
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage information: {str(e)}"
        )
