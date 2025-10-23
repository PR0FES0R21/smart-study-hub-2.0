# ==============================================================================
# File: app/utils/course_locks.py
# Deskripsi: Utility functions untuk sequential lock calculation
# ==============================================================================
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.course import Course
from app.models.course_class_settings import CourseClassSettings
from app.models.student_progress import StudentProgress


class ModuleWithLockStatus:
    """Module dengan lock status calculated"""
    def __init__(
        self,
        module_id: str,
        order: int,
        completed: bool = False,
        locked: bool = False,
        accessible: bool = True,
        override_unlocked: bool = False
    ):
        self.module_id = module_id
        self.order = order
        self.completed = completed
        self.locked = locked
        self.accessible = accessible
        self.override_unlocked = override_unlocked
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "order": self.order,
            "completed": self.completed,
            "locked": self.locked,
            "accessible": self.accessible,
            "override_unlocked": self.override_unlocked
        }


class LessonWithLockStatus:
    """Lesson dengan lock status calculated"""
    def __init__(
        self,
        lesson_id: str,
        order: int,
        module_id: str,
        completed: bool = False,
        locked: bool = False,
        accessible: bool = True,
        override_unlocked: bool = False
    ):
        self.lesson_id = lesson_id
        self.order = order
        self.module_id = module_id
        self.completed = completed
        self.locked = locked
        self.accessible = accessible
        self.override_unlocked = override_unlocked
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "order": self.order,
            "module_id": self.module_id,
            "completed": self.completed,
            "locked": self.locked,
            "accessible": self.accessible,
            "override_unlocked": self.override_unlocked
        }


async def calculate_module_lock_status(
    course: Course,
    student_progress: List[StudentProgress],
    class_settings: CourseClassSettings
) -> List[ModuleWithLockStatus]:
    """
    Calculate lock status untuk semua modules dalam course.
    
    Logic:
    1. Get list completed modules dari student_progress
    2. Find first incomplete module
    3. Lock semua modules BELOW first incomplete
    4. Check overrides (class-level & student-level)
    
    Args:
        course: Course object
        student_progress: List of StudentProgress untuk student ini
        class_settings: CourseClassSettings untuk class ini
    
    Returns:
        List of ModuleWithLockStatus
    """
    
    # Get completed module IDs
    completed_module_ids = [
        str(p.module_id) for p in student_progress
        if p.content_type == "module" and p.status == "completed"
    ]
    
    # Get class-level overrides
    class_unlocked_modules = class_settings.class_overrides.unlocked_modules
    
    # Get student-level overrides (if any)
    student_override = None
    for override in class_settings.class_overrides.student_overrides:
        # Assuming student_id is available in context, would need to be passed
        # For now, we'll handle this in the API endpoint
        pass
    
    # Find first incomplete module index
    first_incomplete_index = None
    for i, module_ref in enumerate(course.module_refs):
        if str(module_ref.module_id) not in completed_module_ids:
            first_incomplete_index = i
            break
    
    # If all modules completed, no locks
    if first_incomplete_index is None:
        first_incomplete_index = len(course.module_refs)
    
    # Build result with lock status
    modules_with_status = []
    for i, module_ref in enumerate(course.module_refs):
        module_id = str(module_ref.module_id)
        completed = module_id in completed_module_ids
        
        # Check if override unlocked
        override_unlocked = module_id in class_unlocked_modules
        
        # Sequential lock logic
        if course.sequential_mode:
            # Lock if AFTER first incomplete
            locked = i > first_incomplete_index
            
            # But if override unlocked, make accessible
            accessible = not locked or override_unlocked
        else:
            # Non-sequential: all unlocked
            locked = False
            accessible = True
        
        modules_with_status.append(
            ModuleWithLockStatus(
                module_id=module_id,
                order=module_ref.order,
                completed=completed,
                locked=locked,
                accessible=accessible,
                override_unlocked=override_unlocked
            )
        )
    
    return modules_with_status


async def calculate_lesson_lock_status(
    db: AsyncIOMotorDatabase,
    module_id: str,
    student_progress: List[StudentProgress],
    class_settings: CourseClassSettings,
    module_accessible: bool = True
) -> List[LessonWithLockStatus]:
    """
    Calculate lock status untuk lessons dalam module.
    
    Logic:
    1. If module locked, all lessons locked
    2. Otherwise, apply sequential logic to lessons
    
    Args:
        db: Database connection
        module_id: Module ID
        student_progress: List of StudentProgress
        class_settings: CourseClassSettings
        module_accessible: Whether parent module is accessible
    
    Returns:
        List of LessonWithLockStatus
    """
    
    # If module not accessible, all lessons locked
    if not module_accessible:
        # Get module to get lessons
        module = await db["modules"].find_one({"_id": ObjectId(module_id)})
        if not module:
            return []
        
        lessons = []
        for i, lesson_ref in enumerate(module.get("lesson_refs", [])):
            lessons.append(
                LessonWithLockStatus(
                    lesson_id=str(lesson_ref["lesson_id"]),
                    order=i + 1,
                    module_id=module_id,
                    completed=False,
                    locked=True,
                    accessible=False
                )
            )
        return lessons
    
    # Get completed lesson IDs for this module
    completed_lesson_ids = [
        str(p.lesson_id) for p in student_progress
        if p.content_type == "lesson" 
        and p.status == "completed"
        and str(p.module_id) == module_id
    ]
    
    # Get module
    module = await db["modules"].find_one({"_id": ObjectId(module_id)})
    if not module:
        return []
    
    # Get student-level overrides
    student_unlocked_lessons = []
    # Would need student_id passed to check overrides
    
    # Find first incomplete lesson
    first_incomplete_index = None
    lesson_refs = module.get("lesson_refs", [])
    for i, lesson_ref in enumerate(lesson_refs):
        if str(lesson_ref["lesson_id"]) not in completed_lesson_ids:
            first_incomplete_index = i
            break
    
    # If all lessons completed
    if first_incomplete_index is None:
        first_incomplete_index = len(lesson_refs)
    
    # Build result
    lessons_with_status = []
    for i, lesson_ref in enumerate(lesson_refs):
        lesson_id = str(lesson_ref["lesson_id"])
        completed = lesson_id in completed_lesson_ids
        
        # Check override
        override_unlocked = lesson_id in student_unlocked_lessons
        
        # Sequential logic (lessons always sequential within module)
        locked = i > first_incomplete_index
        accessible = not locked or override_unlocked
        
        lessons_with_status.append(
            LessonWithLockStatus(
                lesson_id=lesson_id,
                order=i + 1,
                module_id=module_id,
                completed=completed,
                locked=locked,
                accessible=accessible,
                override_unlocked=override_unlocked
            )
        )
    
    return lessons_with_status


async def check_content_accessible(
    db: AsyncIOMotorDatabase,
    student_id: str,
    course_class_setting_id: str,
    content_type: str,
    content_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if student can access specific content.
    
    Args:
        db: Database connection
        student_id: Student user ID
        course_class_setting_id: CourseClassSettings ID
        content_type: "module" | "lesson" | "page"
        content_id: Content ID (module_id, lesson_id, etc)
    
    Returns:
        Tuple of (accessible: bool, reason: Optional[str])
    """
    
    # Get class settings
    class_settings_data = await db["course_class_settings"].find_one({
        "_id": ObjectId(course_class_setting_id)
    })
    if not class_settings_data:
        return False, "Course assignment not found"
    
    from app.models.course_class_settings import CourseClassSettings
    class_settings = CourseClassSettings.from_mongo(class_settings_data)
    
    # Get course
    course_data = await db["courses"].find_one({
        "_id": ObjectId(class_settings.course_id)
    })
    if not course_data:
        return False, "Course not found"
    
    course = Course.from_mongo(course_data)
    
    # Get student progress
    progress_data = await db["student_progress"].find({
        "student_id": ObjectId(student_id),
        "course_class_setting_id": ObjectId(course_class_setting_id)
    }).to_list(length=None)
    
    student_progress = [
        StudentProgress.from_mongo(p) for p in progress_data
    ]
    
    # Calculate lock status
    if content_type == "module":
        modules_with_status = await calculate_module_lock_status(
            course, student_progress, class_settings
        )
        
        # Find this module
        for module in modules_with_status:
            if module.module_id == content_id:
                if module.accessible:
                    return True, None
                else:
                    return False, "Complete previous modules first"
        
        return False, "Module not found in course"
    
    elif content_type == "lesson":
        # Need to find which module this lesson belongs to
        # Then check both module and lesson locks
        
        # For now, simplified check
        # In real implementation, would need to traverse module structure
        return True, None  # Placeholder
    
    return False, "Invalid content type"


async def get_next_unlocked_content(
    db: AsyncIOMotorDatabase,
    student_id: str,
    course_class_setting_id: str,
    current_content_type: str,
    current_content_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get next unlocked content after current.
    
    Used for "Next" button logic.
    
    Args:
        db: Database connection
        student_id: Student user ID
        course_class_setting_id: CourseClassSettings ID
        current_content_type: Current content type
        current_content_id: Current content ID
    
    Returns:
        Dict with next content info or None if no next
    """
    
    # Get class settings
    class_settings_data = await db["course_class_settings"].find_one({
        "_id": ObjectId(course_class_setting_id)
    })
    if not class_settings_data:
        return None
    
    from app.models.course_class_settings import CourseClassSettings
    class_settings = CourseClassSettings.from_mongo(class_settings_data)
    
    # Get course
    course_data = await db["courses"].find_one({
        "_id": ObjectId(class_settings.course_id)
    })
    if not course_data:
        return None
    
    course = Course.from_mongo(course_data)
    
    # Logic depends on current content type
    if current_content_type == "lesson":
        # Get module that contains this lesson
        module = await db["modules"].find_one({
            "lesson_refs.lesson_id": ObjectId(current_content_id)
        })
        if not module:
            return None
        
        # Find current lesson index
        lesson_refs = module.get("lesson_refs", [])
        current_index = None
        for i, ref in enumerate(lesson_refs):
            if str(ref["lesson_id"]) == current_content_id:
                current_index = i
                break
        
        if current_index is None:
            return None
        
        # Check if there's next lesson in module
        if current_index + 1 < len(lesson_refs):
            next_lesson_id = str(lesson_refs[current_index + 1]["lesson_id"])
            return {
                "content_type": "lesson",
                "content_id": next_lesson_id,
                "module_id": str(module["_id"])
            }
        
        # No more lessons, move to next module
        # Find current module index in course
        current_module_index = None
        for i, module_ref in enumerate(course.module_refs):
            if str(module_ref.module_id) == str(module["_id"]):
                current_module_index = i
                break
        
        if current_module_index is None:
            return None
        
        # Check if there's next module
        if current_module_index + 1 < len(course.module_refs):
            next_module_id = str(course.module_refs[current_module_index + 1].module_id)
            
            # Get first lesson of next module
            next_module = await db["modules"].find_one({"_id": ObjectId(next_module_id)})
            if next_module and next_module.get("lesson_refs"):
                first_lesson_id = str(next_module["lesson_refs"][0]["lesson_id"])
                return {
                    "content_type": "lesson",
                    "content_id": first_lesson_id,
                    "module_id": next_module_id
                }
            
            # Module has no lessons, return module itself
            return {
                "content_type": "module",
                "content_id": next_module_id
            }
        
        # No more modules, course completed
        return None
    
    return None
