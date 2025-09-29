# ==============================================================================
# File: app/core/lms_permissions.py
# Deskripsi: Permission system untuk LMS yang terintegrasi dengan existing auth
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.db import get_database
from app.core.security import get_current_active_user
from app.schemas.user import UserPublic

class LMSPermissionError(HTTPException):
    """Custom exception untuk LMS permission errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class LMSPermissions:
    """LMS Permission management yang terintegrasi dengan existing system"""
    
    @staticmethod
    async def check_teacher_access(
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        subject_id: Optional[str] = None,
        class_id: Optional[str] = None
    ) -> bool:
        """
        Check apakah teacher memiliki akses ke subject/class tertentu
        menggunakan existing teaching_assignments collection
        """
        
        if not ObjectId.is_valid(teacher_id):
            return False
        
        match_criteria = {"teacher_id": ObjectId(teacher_id)}
        
        if subject_id and ObjectId.is_valid(subject_id):
            match_criteria["subject_id"] = ObjectId(subject_id)
        
        if class_id and ObjectId.is_valid(class_id):
            match_criteria["class_id"] = ObjectId(class_id)
        
        assignment = await db["teaching_assignments"].find_one(match_criteria)
        return assignment is not None
    
    @staticmethod
    async def check_lesson_access(
        db: AsyncIOMotorDatabase,
        user_id: str,
        lesson_id: str,
        required_access: str = "read"
    ) -> Dict[str, Any]:
        """
        Check apakah user memiliki akses ke lesson dengan level tertentu
        
        Returns:
        - access_granted: bool
        - access_level: str (read, participate, comment, edit)
        - access_source: str (owner, enrollment, class_member, admin)
        """
        
        if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(lesson_id):
            return {"access_granted": False, "access_level": None, "access_source": None}
        
        user_obj_id = ObjectId(user_id)
        lesson_obj_id = ObjectId(lesson_id)
        
        # Get lesson data
        lesson = await db["lessons"].find_one({"_id": lesson_obj_id})
        if not lesson:
            return {"access_granted": False, "access_level": None, "access_source": None}
        
        # Check if user is lesson owner (teacher)
        if lesson["teacher_id"] == user_obj_id:
            return {
                "access_granted": True,
                "access_level": "edit",
                "access_source": "owner"
            }
        
        # Check if user is admin
        user = await db["users"].find_one({"_id": user_obj_id})
        if user and "admin" in user.get("roles", []):
            return {
                "access_granted": True,
                "access_level": "edit",
                "access_source": "admin"
            }
        
        # Check direct enrollment
        enrollment = await db["lesson_enrollments"].find_one({
            "lesson_id": lesson_obj_id,
            "user_id": user_obj_id,
            "is_active": True
        })
        
        if enrollment:
            return {
                "access_granted": True,
                "access_level": enrollment.get("access_level", "read"),
                "access_source": "enrollment"
            }
        
        # Check class-based access
        if lesson.get("class_id"):
            user_profile = await db["profiles"].find_one({"user_id": user_obj_id})
            if user_profile and user_profile.get("class_id") == lesson["class_id"]:
                # Check if lesson allows class access
                access_settings = lesson.get("access_settings", {})
                default_access = access_settings.get("default_access", "class_only")
                
                if default_access in ["class_only", "open"]:
                    return {
                        "access_granted": True,
                        "access_level": "read",
                        "access_source": "class_member"
                    }
        
        # Check if lesson is open access
        access_settings = lesson.get("access_settings", {})
        if access_settings.get("default_access") == "open":
            return {
                "access_granted": True,
                "access_level": "read",
                "access_source": "open_access"
            }
        
        return {"access_granted": False, "access_level": None, "access_source": None}
    
    @staticmethod
    async def check_content_access(
        db: AsyncIOMotorDatabase,
        user_id: str,
        content_id: str
    ) -> bool:
        """Check apakah user memiliki akses ke content tertentu"""
        
        if not ObjectId.is_valid(content_id):
            return False
        
        # Get content and its lesson
        content = await db["lesson_content"].find_one({"_id": ObjectId(content_id)})
        if not content:
            return False
        
        # Check lesson access
        lesson_access = await LMSPermissions.check_lesson_access(
            db, user_id, str(content["lesson_id"])
        )
        
        if not lesson_access["access_granted"]:
            return False
        
        # Check content-specific visibility settings
        content_visibility = content.get("visibility", "all")
        
        if content_visibility == "all":
            return True
        elif content_visibility == "enrolled_only":
            return lesson_access["access_source"] in ["owner", "enrollment", "admin"]
        elif content_visibility == "premium":
            # Future: implement premium access logic
            return lesson_access["access_source"] in ["owner", "admin"]
        
        return False
    
    @staticmethod
    async def check_assignment_access(
        db: AsyncIOMotorDatabase,
        user_id: str,
        assignment_id: str,
        action: str = "view"
    ) -> Dict[str, Any]:
        """
        Check assignment access untuk different actions
        
        Actions: view, submit, grade, edit, delete
        """
        
        if not ObjectId.is_valid(assignment_id):
            return {"access_granted": False, "can_perform_action": False}
        
        assignment = await db["lesson_assignments"].find_one({"_id": ObjectId(assignment_id)})
        if not assignment:
            return {"access_granted": False, "can_perform_action": False}
        
        # Get lesson access if assignment belongs to lesson
        lesson_access = None
        if assignment.get("lesson_id"):
            lesson_access = await LMSPermissions.check_lesson_access(
                db, user_id, str(assignment["lesson_id"])
            )
        
        user_obj_id = ObjectId(user_id)
        
        # Check based on action
        if action == "view":
            if assignment["teacher_id"] == user_obj_id:
                return {"access_granted": True, "can_perform_action": True, "reason": "owner"}
            
            if lesson_access and lesson_access["access_granted"]:
                return {"access_granted": True, "can_perform_action": True, "reason": "lesson_access"}
            
            return {"access_granted": False, "can_perform_action": False}
        
        elif action == "submit":
            # Only students can submit
            user = await db["users"].find_one({"_id": user_obj_id})
            if not user or "student" not in user.get("roles", []):
                return {"access_granted": False, "can_perform_action": False, "reason": "not_student"}
            
            if lesson_access and lesson_access["access_granted"]:
                return {"access_granted": True, "can_perform_action": True, "reason": "student_access"}
            
            return {"access_granted": False, "can_perform_action": False}
        
        elif action in ["grade", "edit", "delete"]:
            # Only assignment owner or admin
            if assignment["teacher_id"] == user_obj_id:
                return {"access_granted": True, "can_perform_action": True, "reason": "owner"}
            
            user = await db["users"].find_one({"_id": user_obj_id})
            if user and "admin" in user.get("roles", []):
                return {"access_granted": True, "can_perform_action": True, "reason": "admin"}
            
            return {"access_granted": False, "can_perform_action": False}
        
        return {"access_granted": False, "can_perform_action": False}

# Dependency functions untuk FastAPI
async def require_teacher_role(
    current_user: UserPublic = Depends(get_current_active_user)
) -> UserPublic:
    """Require user to be teacher atau admin"""
    if "teacher" not in current_user.roles and "admin" not in current_user.roles:
        raise LMSPermissionError("Teacher role required")
    return current_user

async def require_admin_role(
    current_user: UserPublic = Depends(get_current_active_user)
) -> UserPublic:
    """Require user to be admin"""
    if "admin" not in current_user.roles:
        raise LMSPermissionError("Admin role required")
    return current_user

async def require_lesson_access(
    lesson_id: str,
    required_access: str = "read",
    current_user: UserPublic = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """Require specific access level to lesson"""
    
    access_info = await LMSPermissions.check_lesson_access(
        db, str(current_user.id), lesson_id, required_access
    )
    
    if not access_info["access_granted"]:
        raise LMSPermissionError("Access denied to this lesson")
    
    # Check if access level is sufficient
    access_levels = ["read", "participate", "comment", "edit"]
    current_level_index = access_levels.index(access_info["access_level"])
    required_level_index = access_levels.index(required_access)
    
    if current_level_index < required_level_index:
        raise LMSPermissionError(f"Insufficient access level. Required: {required_access}")
    
    return access_info

async def require_content_access(
    content_id: str,
    current_user: UserPublic = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> bool:
    """Require access to specific content"""
    
    has_access = await LMSPermissions.check_content_access(
        db, str(current_user.id), content_id
    )
    
    if not has_access:
        raise LMSPermissionError("Access denied to this content")
    
    return True

async def require_assignment_action(
    assignment_id: str,
    action: str = "view",
    current_user: UserPublic = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """Require specific action permission on assignment"""
    
    access_info = await LMSPermissions.check_assignment_access(
        db, str(current_user.id), assignment_id, action
    )
    
    if not access_info["can_perform_action"]:
        raise LMSPermissionError(f"Permission denied to {action} this assignment")
    
    return access_info

# Utility functions
async def get_user_lesson_permissions(
    db: AsyncIOMotorDatabase,
    user_id: str,
    lesson_id: str
) -> Dict[str, bool]:
    """Get all permissions for user on specific lesson"""
    
    access_info = await LMSPermissions.check_lesson_access(db, user_id, lesson_id)
    
    if not access_info["access_granted"]:
        return {
            "can_view": False,
            "can_participate": False,
            "can_comment": False,
            "can_edit": False,
            "can_delete": False,
            "can_manage_enrollments": False
        }
    
    access_level = access_info["access_level"]
    access_source = access_info["access_source"]
    
    return {
        "can_view": True,
        "can_participate": access_level in ["participate", "comment", "edit"],
        "can_comment": access_level in ["comment", "edit"],
        "can_edit": access_level == "edit",
        "can_delete": access_source in ["owner", "admin"],
        "can_manage_enrollments": access_source in ["owner", "admin"]
    }

# Create singleton instance
lms_permissions = LMSPermissions()
