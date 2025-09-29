# ==============================================================================
# File: app/api/v1/endpoints/modules.py
# Deskripsi: API endpoints untuk Module management (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_database, get_current_user
from app.crud.module import module_crud
from app.crud.lesson import lesson_crud
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

# ==================== MODULE CRUD ENDPOINTS ====================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_module(
    module_data: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create new module"""
    
    # Check permissions
    if "teacher" not in current_user.get("roles", []) and "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create modules"
        )
    
    try:
        module = await module_crud.create_module(db, module_data, str(current_user["_id"]))
        
        response_data = module.dict()
        response_data["id"] = module.id
        response_data["can_edit"] = True
        response_data["can_delete"] = True
        
        return {
            "success": True,
            "message": "Module created successfully",
            "module": response_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create module: {str(e)}"
        )

@router.get("/")
async def list_modules(
    # Pagination
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    
    # Filters
    subject_id: Optional[str] = Query(None),
    grade_level: Optional[int] = Query(None, ge=1, le=12),
    created_by: Optional[str] = Query(None),
    visibility: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    difficulty_level: Optional[str] = Query(None),
    topic_tags: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    
    # Sorting
    sort_by: str = Query("updated_at"),
    sort_direction: str = Query("desc", pattern="^(asc|desc)$"),
    
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List modules dengan filtering dan pagination"""
    
    # Build filters
    filters = {
        "subject_id": subject_id,
        "grade_level": grade_level,
        "created_by": created_by,
        "visibility": visibility,
        "status": status,
        "difficulty_level": difficulty_level,
        "search": search
    }
    
    if topic_tags:
        filters["topic_tags"] = topic_tags.split(",")
    
    skip = (page - 1) * per_page
    
    try:
        result = await module_crud.list_modules(
            db=db,
            filters=filters,
            skip=skip,
            limit=per_page,
            sort_field=sort_by,
            sort_direction=sort_direction,
            user_id=str(current_user["_id"])
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve modules: {str(e)}"
        )

@router.get("/{module_id}")
async def get_module(
    module_id: str,
    include_lessons: bool = Query(False, description="Include lesson details"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get module by ID"""
    
    try:
        if include_lessons:
            # Get module dengan detailed lesson information
            result = await module_crud.get_module_with_lessons(db, module_id, str(current_user["_id"]))
        else:
            # Get basic module information
            module = await module_crud.get_module_by_id(db, module_id)
            if not module:
                raise HTTPException(status_code=404, detail="Module not found")
            
            result = {
                "module": module.dict(),
                "lessons": [],
                "total_lessons": len(module.lesson_refs),
                "total_duration": module.metadata.total_duration
            }
        
        # Add user permissions
        module_data = result["module"]
        user_id = current_user["_id"]
        module_data["can_edit"] = module_data["created_by"] == str(user_id) or str(user_id) in module_data.get("collaborators", [])
        module_data["can_delete"] = module_data["created_by"] == str(user_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve module: {str(e)}"
        )

@router.put("/{module_id}")
async def update_module(
    module_id: str,
    updates: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update module"""
    
    try:
        module = await module_crud.update_module(db, module_id, updates, str(current_user["_id"]))
        
        response_data = module.dict()
        response_data["id"] = module.id
        response_data["can_edit"] = module.is_editable_by(current_user["_id"])
        response_data["can_delete"] = module.created_by == current_user["_id"]
        
        return {
            "success": True,
            "message": "Module updated successfully",
            "module": response_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update module: {str(e)}"
        )

@router.delete("/{module_id}")
async def delete_module(
    module_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete module"""
    
    try:
        success = await module_crud.delete_module(db, module_id, str(current_user["_id"]))
        
        if success:
            return {
                "success": True,
                "message": "Module deleted successfully",
                "module_id": module_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete module"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete module: {str(e)}"
        )

# ==================== LESSON MANAGEMENT IN MODULES ====================

@router.post("/{module_id}/lessons")
async def add_lesson_to_module(
    module_id: str,
    lesson_data: Dict[str, Any],  # Should contain lesson_id and optional config
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add lesson to module"""
    
    try:
        lesson_id = lesson_data.get("lesson_id")
        if not lesson_id:
            raise HTTPException(status_code=400, detail="lesson_id is required")
        
        config = lesson_data.get("config", {})
        
        module = await module_crud.add_lesson_to_module(
            db, module_id, lesson_id, str(current_user["_id"]), config
        )
        
        return {
            "success": True,
            "message": "Lesson added to module successfully",
            "module_id": module_id,
            "lesson_id": lesson_id,
            "total_lessons": len(module.lesson_refs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add lesson to module: {str(e)}"
        )

@router.delete("/{module_id}/lessons/{lesson_id}")
async def remove_lesson_from_module(
    module_id: str,
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Remove lesson from module"""
    
    try:
        success = await module_crud.remove_lesson_from_module(
            db, module_id, lesson_id, str(current_user["_id"])
        )
        
        return {
            "success": success,
            "message": "Lesson removed from module successfully" if success else "Failed to remove lesson",
            "module_id": module_id,
            "lesson_id": lesson_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove lesson from module: {str(e)}"
        )

@router.put("/{module_id}/lessons/reorder")
async def reorder_module_lessons(
    module_id: str,
    lesson_order: Dict[str, List[str]],  # {"lesson_ids": ["id1", "id2", "id3"]}
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Reorder lessons dalam module"""
    
    try:
        lesson_ids = lesson_order.get("lesson_ids", [])
        if not lesson_ids:
            raise HTTPException(status_code=400, detail="lesson_ids is required")
        
        module = await module_crud.reorder_module_lessons(
            db, module_id, lesson_ids, str(current_user["_id"])
        )
        
        return {
            "success": True,
            "message": "Lessons reordered successfully",
            "module_id": module_id,
            "new_order": lesson_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder lessons: {str(e)}"
        )

# ==================== MODULE ANALYTICS ====================

@router.get("/{module_id}/analytics")
async def get_module_analytics(
    module_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get module analytics dan performance metrics"""
    
    try:
        # Verify module exists dan user has access
        module = await module_crud.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Check permissions
        if not module.is_editable_by(current_user["_id"]) and "admin" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Not authorized to view analytics")
        
        # Get module usage in courses
        courses_using_module = await db["courses"].find({
            "module_refs.module_id": module_id
        }).to_list(100)
        
        # Get student progress data (placeholder)
        student_progress = await db["module_progress"].find({
            "module_id": module_id
        }).to_list(1000)
        
        # Calculate analytics
        analytics_data = {
            "module_id": module_id,
            "total_lessons": len(module.lesson_refs),
            "used_in_courses": len(courses_using_module),
            "enrolled_students": len(student_progress),
            "average_completion_rate": 0.0,
            "average_completion_time": 0.0,
            "lesson_performance": [],
            "student_engagement": {
                "active_students": 0,
                "completion_trend": [],
                "difficulty_feedback": {}
            },
            "usage_statistics": {
                "peak_usage_hours": [],
                "daily_engagement": {},
                "most_accessed_lessons": []
            }
        }
        
        if student_progress:
            completed = sum(1 for sp in student_progress if sp.get("status") == "completed")
            analytics_data["average_completion_rate"] = (completed / len(student_progress)) * 100
            analytics_data["average_completion_time"] = sum(sp.get("total_time_spent", 0) for sp in student_progress) / len(student_progress) / 3600  # Convert to hours
        
        return analytics_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve module analytics: {str(e)}"
        )

# ==================== MODULE LIBRARY ====================

@router.get("/library/featured")
async def get_featured_modules(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get featured modules"""
    
    try:
        # Get highly rated published modules
        pipeline = [
            {"$match": {"status": "published", "visibility": "public"}},
            {"$match": {"metadata.rating": {"$gte": 4.0}}},
            {"$sort": {"metadata.usage_count": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "subjects",
                    "localField": "subject_id", 
                    "foreignField": "_id",
                    "as": "subject_info"
                }
            },
            {"$unwind": {"path": "$subject_info", "preserveNullAndEmptyArrays": True}},
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "subject_name": "$subject_info.name"
                }
            }
        ]
        
        featured_modules = await db["modules"].aggregate(pipeline).to_list(limit)
        
        return {
            "featured_modules": featured_modules,
            "total": len(featured_modules)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve featured modules: {str(e)}"
        )

# ==================== UTILITY ENDPOINTS ====================

@router.get("/{module_id}/usage")
async def get_module_usage(
    module_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get information about where module is being used"""
    
    try:
        # Find courses using this module
        courses_using_module = await db["courses"].find({
            "module_refs.module_id": module_id
        }, {
            "title": 1,
            "coordinator_id": 1,
            "status": 1,
            "metadata.enrolled_students": 1
        }).to_list(100)
        
        total_students = sum(course.get("metadata", {}).get("enrolled_students", 0) for course in courses_using_module)
        
        return {
            "module_id": module_id,
            "used_in_courses": len(courses_using_module),
            "total_enrolled_students": total_students,
            "courses": [
                {
                    "id": str(course["_id"]),
                    "title": course["title"],
                    "status": course.get("status", "draft"),
                    "enrolled_students": course.get("metadata", {}).get("enrolled_students", 0)
                }
                for course in courses_using_module
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve module usage: {str(e)}"
        )
