# ==============================================================================
# File: app/api/v1/endpoints/my_courses.py
# Deskripsi: API endpoints untuk Student Course Access (dengan lock calculation)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime

from app.api.v1.deps import get_database, get_current_user
from app.models.course import Course
from app.models.course_class_settings import CourseClassSettings
from app.models.student_progress import StudentProgress
from app.utils.course_locks import (
    calculate_module_lock_status,
    calculate_lesson_lock_status,
    check_content_accessible,
    get_next_unlocked_content
)
from app.schemas.student_progress import (
    MarkContentCompletedRequest,
    CourseProgressSummaryResponse,
    NextButtonResponse
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

async def get_student_course_access(
    db: AsyncIOMotorDatabase,
    student_id: str
) -> List[CourseClassSettings]:
    """Get courses that student has access to via their class"""
    # Get student's class
    student = await db["users"].find_one({"_id": ObjectId(student_id)})
    if not student or "class_id" not in student:
        return []
    
    class_id = student["class_id"]
    
    # Get active course assignments for this class
    assignments = await db["course_class_settings"].find({
        "class_id": class_id,
        "status": "active"
    }).to_list(length=None)
    
    return [CourseClassSettings.from_mongo(a) for a in assignments]


async def calculate_course_progress_summary(
    db: AsyncIOMotorDatabase,
    student_id: str,
    course_class_setting_id: str
) -> Dict[str, Any]:
    """Calculate aggregate progress summary for student in course"""
    # Get class settings
    class_settings = await db["course_class_settings"].find_one({
        "_id": ObjectId(course_class_setting_id)
    })
    if not class_settings:
        return None
    
    course_id = str(class_settings["course_id"])
    
    # Get course
    course_data = await db["courses"].find_one({"_id": ObjectId(course_id)})
    if not course_data:
        return None
    
    course = Course.from_mongo(course_data)
    
    # Get student progress
    progress_data = await db["student_progress"].find({
        "student_id": ObjectId(student_id),
        "course_class_setting_id": ObjectId(course_class_setting_id)
    }).to_list(length=None)
    
    student_progress = [StudentProgress.from_mongo(p) for p in progress_data]
    
    # Calculate summary
    total_modules = len(course.module_refs)
    completed_modules = len([
        p for p in student_progress
        if p.content_type == "module" and p.status == "completed"
    ])
    in_progress_modules = len([
        p for p in student_progress
        if p.content_type == "module" and p.status == "in_progress"
    ])
    
    # Get total lessons from all modules
    total_lessons = 0
    for module_ref in course.module_refs:
        module = await db["modules"].find_one({"_id": ObjectId(module_ref.module_id)})
        if module:
            total_lessons += len(module.get("lesson_refs", []))
    
    completed_lessons = len([
        p for p in student_progress
        if p.content_type == "lesson" and p.status == "completed"
    ])
    in_progress_lessons = len([
        p for p in student_progress
        if p.content_type == "lesson" and p.status == "in_progress"
    ])
    
    # Calculate completion percentage
    completion_percentage = 0.0
    if total_lessons > 0:
        completion_percentage = (completed_lessons / total_lessons) * 100
    
    # Calculate average score
    scores = [p.score for p in student_progress if p.score is not None and p.max_score is not None and p.max_score > 0]
    average_score = sum(scores) / len(scores) if scores else 0.0
    
    # Total time spent
    total_time_spent = sum(p.time_spent for p in student_progress)
    
    # Determine status
    if completed_lessons == 0:
        course_status = "not_started"
    elif completed_lessons == total_lessons:
        course_status = "completed"
    else:
        course_status = "in_progress"
    
    # Get dates
    started_progress = [p for p in student_progress if p.started_at is not None]
    started_at = min([p.started_at for p in started_progress]) if started_progress else None
    
    completed_progress = [p for p in student_progress if p.completed_at is not None]
    completed_at = max([p.completed_at for p in completed_progress]) if completed_progress and course_status == "completed" else None
    
    last_activity_progress = [p for p in student_progress if p.last_activity is not None]
    last_activity = max([p.last_activity for p in last_activity_progress]) if last_activity_progress else None
    
    return {
        "student_id": student_id,
        "course_class_setting_id": course_class_setting_id,
        "course_id": course_id,
        "course_title": course.title,
        "total_modules": total_modules,
        "completed_modules": completed_modules,
        "in_progress_modules": in_progress_modules,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "in_progress_lessons": in_progress_lessons,
        "completion_percentage": completion_percentage,
        "average_score": average_score,
        "total_time_spent": total_time_spent,
        "status": course_status,
        "started_at": started_at,
        "completed_at": completed_at,
        "last_activity": last_activity
    }


# ==================== STUDENT COURSE ENDPOINTS ====================

@router.get("/courses")
async def list_my_courses(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all courses accessible to student via their class.
    
    Returns courses with progress summary and accessibility info.
    """
    student_id = str(current_user["_id"])
    
    # Check if user is student
    if "student" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    try:
        # Get course assignments
        assignments = await get_student_course_access(db, student_id)
        
        # Build response for each course
        courses = []
        for assignment in assignments:
            # Get course
            course_data = await db["courses"].find_one({"_id": ObjectId(assignment.course_id)})
            if not course_data:
                continue
            
            course = Course.from_mongo(course_data)
            
            # Calculate progress summary
            progress_summary = await calculate_course_progress_summary(
                db, student_id, assignment.id
            )
            
            # Get student progress
            progress_data = await db["student_progress"].find({
                "student_id": ObjectId(student_id),
                "course_class_setting_id": ObjectId(assignment.id)
            }).to_list(length=None)
            
            student_progress = [StudentProgress.from_mongo(p) for p in progress_data]
            
            # Calculate module lock status
            modules_with_status = await calculate_module_lock_status(
                course, student_progress, assignment
            )
            
            courses.append({
                "course": {
                    "id": str(course_data["_id"]),
                    "title": course.title,
                    "description": course.description,
                    "total_modules": len(course.module_refs)
                },
                "assignment": {
                    "id": assignment.id,
                    "start_date": assignment.start_date,
                    "end_date": assignment.end_date
                },
                "progress": progress_summary,
                "modules": [m.to_dict() for m in modules_with_status]
            })
        
        return {
            "success": True,
            "total": len(courses),
            "courses": courses
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch courses: {str(e)}"
        )


@router.get("/courses/{course_id}")
async def get_my_course_detail(
    course_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed course info with lock status for all modules and lessons.
    
    This is the main endpoint for student course access.
    Returns complete course structure with calculated accessibility.
    """
    student_id = str(current_user["_id"])
    
    # Check if user is student
    if "student" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    try:
        # Get student's class
        student = await db["users"].find_one({"_id": ObjectId(student_id)})
        if not student or "class_id" not in student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student class not found"
            )
        
        class_id = student["class_id"]
        
        # Get course assignment for this class
        assignment_data = await db["course_class_settings"].find_one({
            "course_id": ObjectId(course_id),
            "class_id": class_id,
            "status": "active"
        })
        
        if not assignment_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not assigned to your class"
            )
        
        assignment = CourseClassSettings.from_mongo(assignment_data)
        
        # Get course
        course_data = await db["courses"].find_one({"_id": ObjectId(course_id)})
        if not course_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        course = Course.from_mongo(course_data)
        
        # Get student progress
        progress_data = await db["student_progress"].find({
            "student_id": ObjectId(student_id),
            "course_class_setting_id": ObjectId(assignment.id)
        }).to_list(length=None)
        
        student_progress = [StudentProgress.from_mongo(p) for p in progress_data]
        
        # Calculate module lock status
        modules_with_status = await calculate_module_lock_status(
            course, student_progress, assignment
        )
        
        # For each module, calculate lesson lock status
        modules_detailed = []
        for module_status in modules_with_status:
            # Get module details
            module_data = await db["modules"].find_one({"_id": ObjectId(module_status.module_id)})
            if not module_data:
                continue
            
            # Calculate lesson lock status
            lessons_with_status = await calculate_lesson_lock_status(
                db=db,
                module_id=module_status.module_id,
                student_progress=student_progress,
                class_settings=assignment,
                module_accessible=module_status.accessible
            )
            
            modules_detailed.append({
                "module_id": module_status.module_id,
                "title": module_data.get("title"),
                "order": module_status.order,
                "completed": module_status.completed,
                "locked": module_status.locked,
                "accessible": module_status.accessible,
                "override_unlocked": module_status.override_unlocked,
                "lessons": [l.to_dict() for l in lessons_with_status]
            })
        
        # Calculate progress summary
        progress_summary = await calculate_course_progress_summary(
            db, student_id, assignment.id
        )
        
        return {
            "success": True,
            "course": {
                "id": str(course_data["_id"]),
                "title": course.title,
                "description": course.description,
                "sequential_mode": course.sequential_mode,
                "total_modules": len(course.module_refs)
            },
            "progress": progress_summary,
            "modules": modules_detailed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch course: {str(e)}"
        )


@router.post("/courses/{course_id}/lessons/{lesson_id}/next")
async def handle_next_button(
    course_id: str,
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Handle 'Next' button click.
    
    Logic:
    1. Check if current lesson has quiz/assignment
    2. If yes, check if completed
    3. Mark current lesson as completed
    4. Get next unlocked content
    5. Return next content info
    """
    student_id = str(current_user["_id"])
    
    # Check if user is student
    if "student" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    try:
        # Get student's class and assignment
        student = await db["users"].find_one({"_id": ObjectId(student_id)})
        if not student or "class_id" not in student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student class not found"
            )
        
        assignment_data = await db["course_class_settings"].find_one({
            "course_id": ObjectId(course_id),
            "class_id": student["class_id"],
            "status": "active"
        })
        
        if not assignment_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not assigned to your class"
            )
        
        assignment_id = str(assignment_data["_id"])
        
        # Get current lesson
        lesson = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        # TODO: Check if lesson has quiz/assignment that must be completed
        # For now, simplified version
        
        # Mark current lesson as completed
        existing_progress = await db["student_progress"].find_one({
            "student_id": ObjectId(student_id),
            "course_class_setting_id": ObjectId(assignment_id),
            "lesson_id": ObjectId(lesson_id)
        })
        
        if existing_progress:
            # Update existing
            await db["student_progress"].update_one(
                {"_id": existing_progress["_id"]},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Create new progress entry
            progress = StudentProgress(
                student_id=ObjectId(student_id),
                course_class_setting_id=ObjectId(assignment_id),
                module_id=lesson.get("module_id"),
                lesson_id=ObjectId(lesson_id),
                content_type="lesson",
                status="completed",
                completed_at=datetime.utcnow()
            )
            await db["student_progress"].insert_one(progress.to_mongo())
        
        # Get next unlocked content
        next_content = await get_next_unlocked_content(
            db=db,
            student_id=student_id,
            course_class_setting_id=assignment_id,
            current_content_type="lesson",
            current_content_id=lesson_id
        )
        
        # Check if course completed
        # TODO: Check if all modules completed AND final assessment passed
        course_completed = False
        
        return {
            "success": True,
            "message": "Lesson completed!",
            "completed_content": {
                "content_type": "lesson",
                "lesson_id": lesson_id,
                "title": lesson.get("title")
            },
            "next_content": next_content,
            "has_next": next_content is not None,
            "course_completed": course_completed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process next button: {str(e)}"
        )


@router.get("/courses/{course_id}/progress")
async def get_my_course_progress(
    course_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get detailed progress for a course"""
    student_id = str(current_user["_id"])
    
    # Check if user is student
    if "student" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    try:
        # Get student's class
        student = await db["users"].find_one({"_id": ObjectId(student_id)})
        if not student or "class_id" not in student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student class not found"
            )
        
        # Get course assignment
        assignment_data = await db["course_class_settings"].find_one({
            "course_id": ObjectId(course_id),
            "class_id": student["class_id"],
            "status": "active"
        })
        
        if not assignment_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not assigned to your class"
            )
        
        assignment_id = str(assignment_data["_id"])
        
        # Calculate progress summary
        progress_summary = await calculate_course_progress_summary(
            db, student_id, assignment_id
        )
        
        # Get detailed progress list
        progress_data = await db["student_progress"].find({
            "student_id": ObjectId(student_id),
            "course_class_setting_id": ObjectId(assignment_id)
        }).to_list(length=None)
        
        progress_list = [StudentProgress.from_mongo(p) for p in progress_data]
        
        return {
            "success": True,
            "summary": progress_summary,
            "progress": [p.dict() for p in progress_list]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch progress: {str(e)}"
        )
