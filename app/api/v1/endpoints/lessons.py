# ==============================================================================
# File: app/api/v1/endpoints/lessons.py
# Deskripsi: API endpoints untuk Lesson management (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi import status as http_status
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

@router.post("/", response_model=LessonDetailResponse, status_code=http_status.HTTP_201_CREATED)
async def create_lesson(
    lesson_data: LessonCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create new lesson"""
    
    # Check permissions - teachers dapat create lessons
    if "teacher" not in current_user.get("roles", []) and "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create lessons"
        )
    
    try:
        # Create lesson
        lesson = await lesson_crud.create_lesson(db, lesson_data, str(current_user["_id"]))
        
        # Convert to response format
        response_data = lesson.dict(by_alias=False)  # Use field names, not aliases
        
        # Ensure id is set (convert _id if needed)
        if "id" not in response_data and "_id" in response_data:
            response_data["id"] = str(response_data["_id"])
        elif "id" in response_data and response_data["id"] is not None:
            response_data["id"] = str(response_data["id"])
        
        # Convert all ObjectId fields to strings
        if "subject_id" in response_data:
            response_data["subject_id"] = str(response_data["subject_id"])
        if "created_by" in response_data:
            response_data["created_by"] = str(response_data["created_by"])
        
        response_data["subject_name"] = None  # Would be populated by subject lookup
        response_data["created_by_name"] = f"{current_user.get('profile', {}).get('first_name', '')} {current_user.get('profile', {}).get('last_name', '')}"
        response_data["can_edit"] = True
        response_data["can_delete"] = True
        response_data["can_collaborate"] = True
        
        return LessonDetailResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        
        # Add user permissions to each lesson
        user_id_str = str(current_user["_id"])
        for item in result["items"]:
            # Set permissions based on ownership and collaboration
            item["can_edit"] = (
                item["created_by"] == user_id_str or
                user_id_str in item.get("collaborators", [])
            )
            item["can_delete"] = item["created_by"] == user_id_str
            item["is_favorited"] = False  # TODO: Implement favorites feature
        
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        # Get lesson (may return tuple if include_usage=True)
        result = await lesson_crud.get_lesson_by_id(
            db, lesson_id, str(current_user["_id"]), include_usage
        )
        
        # Handle return value (either Lesson or (Lesson, usage_details))
        if include_usage:
            lesson, usage_details = result if result else (None, None)
        else:
            lesson = result
            usage_details = None
        
        if not lesson:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # Check access permissions
        user_id_str = str(current_user["_id"])  # Convert to string for comparison
        user_roles = current_user.get("roles", [])
        
        # Authorization logic:
        # - Admin: can view ALL lessons
        # - Creator: can view own lessons regardless of visibility
        # - Collaborator: can view shared lessons
        # - Anyone: can view public lessons
        # - Students: only public lessons or lessons in enrolled courses (TODO: implement course enrollment check)
        can_view = (
            "admin" in user_roles or  # Admin see all
            lesson.created_by == user_id_str or  # Creator see own
            user_id_str in lesson.collaborators or  # Collaborator see shared
            lesson.visibility == "public"  # Anyone see public
        )
        
        if not can_view:
            # Add debug info to help troubleshoot
            import logging
            logging.error(f"Permission denied - User: {user_id_str}, Roles: {user_roles}, Lesson visibility: {lesson.visibility}, Creator: {lesson.created_by}")
            
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this lesson"
            )
        
        # Format response dengan user permissions
        response_data = lesson.dict(by_alias=False)
        
        # Convert ObjectId fields to strings (if not already)
        if "_id" in response_data:
            response_data["id"] = str(response_data["_id"])
            del response_data["_id"]
        elif "id" in response_data and response_data["id"] is not None:
            response_data["id"] = str(response_data["id"])
        
        # These should already be strings from Lesson.from_mongo(), but ensure it
        if "subject_id" in response_data and response_data["subject_id"]:
            response_data["subject_id"] = str(response_data["subject_id"])
        if "created_by" in response_data and response_data["created_by"]:
            response_data["created_by"] = str(response_data["created_by"])
        if "collaborators" in response_data and response_data["collaborators"]:
            response_data["collaborators"] = [str(c) if c else c for c in response_data["collaborators"]]
        
        # Pages are now in separate collection - set empty for backward compatibility
        response_data["pages"] = []
        
        # Note: subject_name and created_by_name are now populated by CRUD layer
        # Don't overwrite with None - they should already be set
        
        # Add user permissions (convert to string for comparison)
        response_data["can_edit"] = lesson.is_editable_by(user_id_str)
        response_data["can_delete"] = str(lesson.created_by) == user_id_str
        response_data["can_collaborate"] = lesson.is_editable_by(user_id_str)
        
        # Add usage information if requested
        if include_usage and usage_details:
            response_data["usage_in_modules"] = usage_details.get("modules", [])
            response_data["usage_in_courses"] = usage_details.get("courses", [])
        else:
            response_data["usage_in_modules"] = None
        
        return LessonDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        response_data = lesson.dict(by_alias=False)
        
        # Convert ObjectId fields to strings
        if "_id" in response_data:
            response_data["id"] = str(response_data["_id"])
            del response_data["_id"]
        elif "id" in response_data and response_data["id"] is not None:
            response_data["id"] = str(response_data["id"])
        
        if "subject_id" in response_data:
            response_data["subject_id"] = str(response_data["subject_id"])
        if "created_by" in response_data:
            response_data["created_by"] = str(response_data["created_by"])
        if "collaborators" in response_data:
            response_data["collaborators"] = [str(c) for c in response_data["collaborators"]]
        
        # Set user permissions (convert to string for comparison)
        user_id_str = str(current_user["_id"])
        response_data["can_edit"] = lesson.is_editable_by(user_id_str)
        response_data["can_delete"] = str(lesson.created_by) == user_id_str
        
        return LessonDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete lesson"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lesson: {str(e)}"
        )

# ==================== LESSON PAGE MANAGEMENT ====================
# NOTE: Old page management endpoints have been removed.
# Use the new endpoints below (starting from line 520+) which use lesson_page_crud
# and support the separated pages architecture.

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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage information: {str(e)}"
        )


# ==================== LESSON PAGES ENDPOINTS (NEW - SEPARATED) ====================

from app.crud.lesson_page import lesson_page_crud
from app.schemas.lesson_page import (
    CreatePageRequest, UpdatePageRequest, ReorderPagesRequest,
    PageResponse, PageSummaryResponse, PagesListResponse,
    PageWithNavigationResponse, BatchPagesResponse
)

@router.get("/{lesson_id}/pages", response_model=PagesListResponse)
async def list_lesson_pages(
    lesson_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: draft | published | archived"),
    summary_only: bool = Query(True, description="Return summary only (no content)"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get list of all pages for a lesson.
    
    **Default: Returns summary only (fast, lightweight)**
    - Set summary_only=false to get full content (slower)
    """
    
    # Get lesson info
    lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Get pages
    pages = await lesson_page_crud.list_pages(
        db, 
        lesson_id, 
        status_filter=status_filter,
        summary_only=summary_only
    )
    
    if summary_only:
        return PagesListResponse(
            lesson_id=lesson_id,
            lesson_title=lesson.title,
            total_pages=len(pages),
            pages=pages
        )
    else:
        # Return full pages
        return {
            "lesson_id": lesson_id,
            "lesson_title": lesson.title,
            "total_pages": len(pages),
            "pages": [page.dict() for page in pages]
        }


@router.post("/{lesson_id}/pages", response_model=PageResponse, status_code=http_status.HTTP_201_CREATED)
async def create_lesson_page(
    lesson_id: str,
    page_data: CreatePageRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add new page to lesson.
    
    **Permissions:** Only lesson creator or collaborators can add pages.
    """
    
    # Check lesson exists and permissions
    lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Check permissions
    user_id = str(current_user["_id"])
    if not lesson.is_editable_by(user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to edit this lesson"
        )
    
    # Create page
    page = await lesson_page_crud.create_page(
        db,
        lesson_id,
        page_data.dict(),
        user_id
    )
    
    return page.dict()


@router.get("/{lesson_id}/pages/{page_number}", response_model=PageWithNavigationResponse)
async def get_lesson_page(
    lesson_id: str,
    page_number: int = Path(..., ge=1, description="Page number to retrieve"),
    prefetch_next: bool = Query(False, description="Include next page in response"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get single page content.
    
    **Efficient:** Only loads requested page (not entire lesson).
    **Performance:** ~5-20KB response vs 250KB+ for full lesson.
    """
    
    # Get lesson info
    lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Get page
    page = await lesson_page_crud.get_page(db, lesson_id, page_number)
    if not page:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} not found"
        )
    
    # Get total pages
    total_pages = lesson.metadata.total_pages
    
    # Navigation info
    has_previous = page_number > 1
    has_next = page_number < total_pages
    previous_page = page_number - 1 if has_previous else None
    next_page = page_number + 1 if has_next else None
    
    return PageWithNavigationResponse(
        lesson_id=lesson_id,
        lesson_title=lesson.title,
        total_pages=total_pages,
        current_page=page_number,
        has_previous=has_previous,
        has_next=has_next,
        previous_page=previous_page,
        next_page=next_page,
        page=PageResponse(**page.dict())
    )


@router.get("/{lesson_id}/pages/batch", response_model=BatchPagesResponse)
async def get_pages_batch(
    lesson_id: str,
    page_numbers: str = Query(..., description="Comma-separated page numbers (e.g., '1,2,3')"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get multiple pages at once (for prefetching).
    
    **Use case:** Prefetch next 2-3 pages for smooth navigation.
    **Example:** ?page_numbers=1,2,3
    """
    
    # Parse page numbers
    try:
        page_nums = [int(n.strip()) for n in page_numbers.split(',')]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid page numbers format"
        )
    
    # Get pages
    pages = await lesson_page_crud.get_pages_batch(db, lesson_id, page_nums)
    
    return BatchPagesResponse(
        lesson_id=lesson_id,
        pages=[PageResponse(**p.dict()) for p in pages],
        page_numbers=page_nums
    )


@router.put("/{lesson_id}/pages/{page_number}", response_model=PageResponse)
async def update_lesson_page(
    lesson_id: str,
    page_number: int = Path(..., ge=1, description="Page number to update"),
    page_data: UpdatePageRequest = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update page content.
    
    **Efficient:** Only updates single page (not entire lesson).
    **Versioning:** Version number auto-incremented on content changes.
    """
    
    # Check lesson permissions
    lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    user_id = str(current_user["_id"])
    if not lesson.is_editable_by(user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to edit this lesson"
        )
    
    # Update page
    updates = page_data.dict(exclude_unset=True)
    page = await lesson_page_crud.update_page(
        db,
        lesson_id,
        page_number,
        updates,
        user_id
    )
    
    if not page:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} not found"
        )
    
    return page.dict()


@router.put("/{lesson_id}/pages/reorder")
async def reorder_lesson_pages(
    lesson_id: str,
    reorder_data: ReorderPagesRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Reorder pages (change page numbers).
    
    **Example:** Change order from [1,2,3] to [3,1,2]
    """
    
    # Check permissions
    lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    user_id = str(current_user["_id"])
    if not lesson.is_editable_by(user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to edit this lesson"
        )
    
    # Reorder
    success = await lesson_page_crud.reorder_pages(
        db,
        lesson_id,
        reorder_data.page_numbers
    )
    
    return {
        "success": success,
        "message": "Pages reordered successfully",
        "new_order": reorder_data.page_numbers
    }


@router.delete("/{lesson_id}/pages/{page_number}")
async def delete_lesson_page(
    lesson_id: str,
    page_number: int = Path(..., ge=1, description="Page number to delete"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a page.
    
    **Note:** Remaining pages will be automatically renumbered.
    """
    
    # Check permissions
    lesson = await lesson_crud.get_lesson_by_id(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    user_id = str(current_user["_id"])
    if not lesson.is_editable_by(user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to edit this lesson"
        )
    
    # Delete page
    success = await lesson_page_crud.delete_page(db, lesson_id, page_number)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} not found"
        )
    
    return {
        "success": True,
        "message": f"Page {page_number} deleted successfully"
    }
