# ==============================================================================
# File: app/api/v1/endpoints/courses.py
# Deskripsi: API endpoints untuk Course management (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime

from app.api.v1.deps import get_database, get_current_user
from app.models.course import Course, ModuleReference
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import re

router = APIRouter()

# ==================== COURSE CRUD ENDPOINTS ====================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create new course"""
    
    # Check permissions - only coordinators/admins can create courses
    user_roles = current_user.get("roles", [])
    if not any(role in user_roles for role in ["coordinator", "admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coordinators and admins can create courses"
        )
    
    try:
        # Generate slug
        slug = re.sub(r'[^\w\s-]', '', course_data["title"].lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        timestamp = int(datetime.utcnow().timestamp())
        slug = f"{slug}-{timestamp}"
        
        # Create course object
        course = Course(
            title=course_data["title"],
            description=course_data["description"],
            slug=slug,
            subject_id=course_data["subject_id"],
            grade_level=course_data["grade_level"],
            coordinator_id=current_user["_id"],
            instructor_ids=course_data.get("instructor_ids", []),
            difficulty_level=course_data.get("difficulty_level", "medium"),
            learning_objectives=course_data.get("learning_objectives", []),
            prerequisites=course_data.get("prerequisites", []),
            visibility=course_data.get("visibility", "institutional"),
            auto_enroll_students=course_data.get("auto_enroll_students", False),
            self_paced=course_data.get("self_paced", False),
            course_start=course_data.get("course_start"),
            course_end=course_data.get("course_end")
        )
        
        # Insert to database
        result = await db["courses"].insert_one(course.to_mongo())
        course.id = str(result.inserted_id)
        
        response_data = course.dict()
        response_data["id"] = course.id
        response_data["can_edit"] = True
        response_data["can_delete"] = True
        
        return {
            "success": True,
            "message": "Course created successfully",
            "course": response_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}"
        )

@router.get("/")
async def list_courses(
    # Pagination
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    
    # Filters
    subject_id: Optional[str] = Query(None),
    grade_level: Optional[int] = Query(None, ge=1, le=12),
    coordinator_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    visibility: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    my_courses: bool = Query(False, description="Show only my courses"),
    
    # Sorting
    sort_by: str = Query("updated_at"),
    sort_direction: str = Query("desc", pattern="^(asc|desc)$"),
    
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List courses dengan filtering dan pagination"""
    
    try:
        # Build query filter
        query_filter = {}
        
        if subject_id:
            query_filter["subject_id"] = ObjectId(subject_id)
        if grade_level:
            query_filter["grade_level"] = grade_level
        if coordinator_id:
            query_filter["coordinator_id"] = ObjectId(coordinator_id)
        if status:
            query_filter["status"] = status
        if visibility:
            query_filter["visibility"] = visibility
        if search:
            query_filter["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        # My courses filter
        if my_courses:
            query_filter["$or"] = [
                {"coordinator_id": current_user["_id"]},
                {"instructor_ids": current_user["_id"]}
            ]
        
        # Apply visibility filters untuk non-admin users
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in ["admin", "coordinator"]):
            # Regular users can only see public and institutional courses
            if "visibility" not in query_filter:
                query_filter["visibility"] = {"$in": ["public", "institutional"]}
        
        # Get total count
        total_count = await db["courses"].count_documents(query_filter)
        
        # Build aggregation pipeline
        skip = (page - 1) * per_page
        sort_direction_val = -1 if sort_direction == "desc" else 1
        
        pipeline = [
            {"$match": query_filter},
            
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
            
            # Lookup coordinator
            {
                "$lookup": {
                    "from": "users",
                    "localField": "coordinator_id",
                    "foreignField": "_id",
                    "as": "coordinator_info"
                }
            },
            {"$unwind": {"path": "$coordinator_info", "preserveNullAndEmptyArrays": True}},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "subject_name": "$subject_info.name",
                    "coordinator_name": {
                        "$concat": [
                            {"$ifNull": ["$coordinator_info.profile.first_name", ""]},
                            " ",
                            {"$ifNull": ["$coordinator_info.profile.last_name", ""]}
                        ]
                    },
                    "total_modules": "$metadata.total_modules",
                    "enrolled_students": "$metadata.enrolled_students"
                }
            },
            
            # Sort and paginate
            {"$sort": {sort_by: sort_direction_val}},
            {"$skip": skip},
            {"$limit": per_page},
            
            # Project needed fields
            {
                "$project": {
                    "id": 1,
                    "title": 1,
                    "description": 1,
                    "slug": 1,
                    "course_code": 1,
                    "subject_id": {"$toString": "$subject_id"},
                    "subject_name": 1,
                    "grade_level": 1,
                    "coordinator_id": {"$toString": "$coordinator_id"},
                    "coordinator_name": 1,
                    "total_modules": 1,
                    "enrolled_students": 1,
                    "difficulty_level": 1,
                    "visibility": 1,
                    "status": 1,
                    "course_start": 1,
                    "course_end": 1,
                    "created_at": 1,
                    "updated_at": 1
                }
            }
        ]
        
        courses = await db["courses"].aggregate(pipeline).to_list(per_page)
        
        # Add user permissions
        for course in courses:
            user_id = current_user["_id"]
            course["can_edit"] = (
                course["coordinator_id"] == str(user_id) or
                "admin" in user_roles
            )
            course["can_delete"] = (
                course["coordinator_id"] == str(user_id) or
                "admin" in user_roles
            )
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        current_page = page
        
        return {
            "items": courses,
            "total": total_count,
            "page": current_page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": skip + per_page < total_count,
            "has_prev": skip > 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve courses: {str(e)}"
        )

@router.get("/{course_id}")
async def get_course(
    course_id: str,
    include_modules: bool = Query(False, description="Include module details"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get course by ID"""
    
    try:
        course_data = await db["courses"].find_one({"_id": ObjectId(course_id)})
        if not course_data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = Course.from_mongo(course_data)
        
        # Check access permissions
        user_id = current_user["_id"]
        user_roles = current_user.get("roles", [])
        can_view = (
            course.visibility in ["public", "institutional"] or
            course.coordinator_id == user_id or
            user_id in course.instructor_ids or
            "admin" in user_roles
        )
        
        if not can_view:
            raise HTTPException(status_code=403, detail="Not authorized to view this course")
        
        result = {"course": course.dict()}
        result["course"]["id"] = course.id
        
        # Add module details if requested
        if include_modules and course.module_refs:
            module_ids = [ObjectId(ref.module_id) for ref in course.module_refs]
            modules = await db["modules"].find({
                "_id": {"$in": module_ids}
            }).to_list(1000)
            
            # Create lookup dict
            module_lookup = {str(module["_id"]): module for module in modules}
            
            # Combine module data dengan references
            module_details = []
            for ref in sorted(course.module_refs, key=lambda x: x.order):
                module_data = module_lookup.get(str(ref.module_id))
                if module_data:
                    module_info = {
                        "module_id": str(ref.module_id),
                        "order": ref.order,
                        "required": ref.required,
                        "custom_title": ref.custom_title,
                        "weight": ref.weight,
                        "unlock_condition": ref.unlock_condition,
                        
                        # Module details
                        "title": module_data.get("title"),
                        "description": module_data.get("description"),
                        "total_lessons": module_data.get("metadata", {}).get("total_lessons", 0),
                        "total_duration": module_data.get("metadata", {}).get("total_duration", 0),
                        "difficulty_level": module_data.get("difficulty_level"),
                        "status": module_data.get("status")
                    }
                    module_details.append(module_info)
            
            result["modules"] = module_details
        else:
            result["modules"] = []
        
        # Add user permissions
        result["course"]["can_edit"] = course.is_manageable_by(user_id) or "admin" in user_roles
        result["course"]["can_delete"] = course.coordinator_id == user_id or "admin" in user_roles
        result["course"]["can_enroll"] = course.can_enroll()
        result["course"]["is_active"] = course.is_active()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course: {str(e)}"
        )

# ==================== MODULE MANAGEMENT IN COURSES ====================

@router.post("/{course_id}/modules")
async def add_module_to_course(
    course_id: str,
    module_data: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add module to course"""
    
    try:
        # Get course and verify permissions
        course_doc = await db["courses"].find_one({"_id": ObjectId(course_id)})
        if not course_doc:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = Course.from_mongo(course_doc)
        
        if not course.is_manageable_by(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to edit this course")
        
        # Verify module exists
        module_id = module_data.get("module_id")
        if not module_id:
            raise HTTPException(status_code=400, detail="module_id is required")
        
        module = await db["modules"].find_one({"_id": ObjectId(module_id)})
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Check if module already in course
        if course.get_module_reference(ObjectId(module_id)):
            raise HTTPException(status_code=400, detail="Module already in this course")
        
        # Add module reference
        course.add_module_reference(
            module_id=ObjectId(module_id),
            order=module_data.get("order"),
            required=module_data.get("required", True),
            custom_title=module_data.get("custom_title"),
            weight=module_data.get("weight", 1.0),
            unlock_condition=module_data.get("unlock_condition", "sequential")
        )
        
        # Update in database
        await db["courses"].update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "module_refs": [ref.dict() for ref in course.module_refs],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Module added to course successfully",
            "course_id": course_id,
            "module_id": module_id,
            "total_modules": len(course.module_refs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add module to course: {str(e)}"
        )

@router.delete("/{course_id}/modules/{module_id}")
async def remove_module_from_course(
    course_id: str,
    module_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Remove module from course"""
    
    try:
        # Get course and verify permissions
        course_doc = await db["courses"].find_one({"_id": ObjectId(course_id)})
        if not course_doc:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = Course.from_mongo(course_doc)
        
        if not course.is_manageable_by(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to edit this course")
        
        # Remove module reference
        removed = course.remove_module_reference(ObjectId(module_id))
        if not removed:
            raise HTTPException(status_code=404, detail="Module not found in this course")
        
        # Update in database
        await db["courses"].update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "module_refs": [ref.dict() for ref in course.module_refs],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Module removed from course successfully",
            "course_id": course_id,
            "module_id": module_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove module from course: {str(e)}"
        )

# ==================== COURSE ANALYTICS ====================

@router.get("/{course_id}/analytics")
async def get_course_analytics(
    course_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get course analytics dan performance metrics"""
    
    try:
        # Verify course exists dan user has access
        course_doc = await db["courses"].find_one({"_id": ObjectId(course_id)})
        if not course_doc:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = Course.from_mongo(course_doc)
        
        # Check permissions
        if not course.is_manageable_by(current_user["_id"]) and "admin" not in current_user.get("roles", []):
            raise HTTPException(status_code=403, detail="Not authorized to view analytics")
        
        # Get student progress data
        course_progress = await db["course_progress"].find({
            "course_id": ObjectId(course_id)
        }).to_list(1000)
        
        # Get module progress data
        module_progress = await db["module_progress"].find({
            "course_id": ObjectId(course_id)
        }).to_list(1000)
        
        # Calculate analytics
        total_students = len(course_progress)
        completed_students = sum(1 for cp in course_progress if cp.get("status") == "completed")
        active_students = sum(1 for cp in course_progress if (datetime.utcnow() - cp.get("last_activity", datetime.utcnow())).days < 7)
        
        analytics_data = {
            "course_id": course_id,
            "enrollment_stats": {
                "total_enrolled": total_students,
                "active_students": active_students,
                "completed_students": completed_students,
                "dropout_rate": ((total_students - completed_students - active_students) / total_students * 100) if total_students > 0 else 0
            },
            "performance_metrics": {
                "average_completion_rate": (completed_students / total_students * 100) if total_students > 0 else 0,
                "average_score": sum(cp.get("score", 0) for cp in course_progress if cp.get("score")) / len([cp for cp in course_progress if cp.get("score")]) if course_progress else 0,
                "average_time_to_completion": sum(cp.get("total_time_spent", 0) for cp in course_progress) / len(course_progress) / 3600 if course_progress else 0  # hours
            },
            "module_performance": [],
            "engagement_metrics": {
                "daily_active_users": {},
                "peak_activity_hours": [],
                "most_challenging_modules": []
            },
            "feedback_summary": {
                "average_rating": course.metadata.rating,
                "total_reviews": course.metadata.review_count,
                "sentiment_analysis": {}
            }
        }
        
        return analytics_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course analytics: {str(e)}"
        )
