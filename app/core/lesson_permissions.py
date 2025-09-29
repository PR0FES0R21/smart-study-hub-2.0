# ==============================================================================
# File: app/core/lesson_permissions.py
# Description: Advanced Permission Management System for Independent Lessons
# ==============================================================================
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from app.models.lesson import (
    IndependentLesson, TeacherAssignment, TeacherPermissions, 
    LessonOwnership, LessonStandardization
)
from app.schemas.base import PyObjectId


class UserRole(str, Enum):
    """User roles dalam sistem"""
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    TEACHER = "teacher"
    STUDENT = "student"


class PermissionLevel(str, Enum):
    """Permission levels untuk lessons"""
    FULL_ACCESS = "full_access"
    COORDINATOR = "coordinator" 
    ASSIGNED_TEACHER = "assigned_teacher"
    SUBSTITUTE_TEACHER = "substitute_teacher"
    VIEW_ONLY = "view_only"
    NO_ACCESS = "no_access"


class LessonPermissionManager:
    """Advanced Permission Manager for Independent Lesson System"""
    
    def __init__(self):
        # Permission templates untuk different roles
        self.PERMISSION_TEMPLATES = {
            "coordinator": TeacherPermissions(
                can_edit_content=True,
                can_publish=True,
                can_manage_assignments=True,
                can_view_analytics=True,
                can_manage_enrollments=True,
                can_assign_teachers=True,
                can_standardize=True,
                can_approve_changes=True
            ),
            "assigned_teacher": TeacherPermissions(
                can_edit_content=True,
                can_publish=False,  # Configurable by coordinator
                can_manage_assignments=True,
                can_view_analytics=True,
                can_manage_enrollments=False,
                can_assign_teachers=False,
                can_standardize=False,
                can_approve_changes=False
            ),
            "substitute_teacher": TeacherPermissions(
                can_edit_content=False,
                can_publish=False,
                can_manage_assignments=True,
                can_view_analytics=True,
                can_manage_enrollments=False,
                can_assign_teachers=False,
                can_standardize=False,
                can_approve_changes=False
            ),
            "guest_teacher": TeacherPermissions(
                can_edit_content=False,
                can_publish=False,
                can_manage_assignments=False,
                can_view_analytics=True,
                can_manage_enrollments=False,
                can_assign_teachers=False,
                can_standardize=False,
                can_approve_changes=False
            )
        }
    
    async def check_coordinator_access(
        self,
        db: AsyncIOMotorDatabase,
        user_id: str,
        lesson: IndependentLesson
    ) -> bool:
        """Check if user is coordinator for this lesson"""
        
        # Direct coordinator check
        if lesson.ownership.primary_coordinator_id and str(lesson.ownership.primary_coordinator_id) == user_id:
            return True
        
        # Check via coordination assignment
        if lesson.ownership.coordination_assignment_id:
            coordination = await db["coordination_assignments"].find_one({
                "_id": ObjectId(lesson.ownership.coordination_assignment_id),
                "coordinator_id": ObjectId(user_id),
                "is_active": True
            })
            return coordination is not None
        
        return False
    
    async def check_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        lesson: IndependentLesson,
        class_id: Optional[str] = None
    ) -> Optional[TeacherAssignment]:
        """Check if teacher is assigned to lesson and return assignment details"""
        
        for assignment in lesson.teacher_assignments:
            if str(assignment.teacher_id) == teacher_id and assignment.is_active:
                # If class_id specified, check if teacher assigned to that class
                if class_id and ObjectId(class_id) not in assignment.class_ids:
                    continue
                return assignment
        
        return None
    
    async def get_user_permission_level(
        self,
        db: AsyncIOMotorDatabase,
        user_id: str,
        lesson: IndependentLesson,
        user_role: UserRole
    ) -> PermissionLevel:
        """Determine user's permission level for lesson"""
        
        # Admin has full access
        if user_role == UserRole.ADMIN:
            return PermissionLevel.FULL_ACCESS
        
        # Check coordinator access
        is_coordinator = await self.check_coordinator_access(db, user_id, lesson)
        if is_coordinator:
            return PermissionLevel.COORDINATOR
        
        # Check teacher assignment
        if user_role == UserRole.TEACHER:
            assignment = await self.check_teacher_assignment(db, user_id, lesson)
            if assignment:
                if assignment.assignment_type == "primary":
                    return PermissionLevel.ASSIGNED_TEACHER
                elif assignment.assignment_type == "substitute":
                    return PermissionLevel.SUBSTITUTE_TEACHER
                else:  # guest
                    return PermissionLevel.VIEW_ONLY
        
        # Students get view access if enrolled
        if user_role == UserRole.STUDENT:
            # Check enrollment (would need to implement enrollment check)
            return PermissionLevel.VIEW_ONLY
        
        return PermissionLevel.NO_ACCESS
    
    async def check_permission(
        self,
        db: AsyncIOMotorDatabase,
        user_id: str,
        lesson: IndependentLesson,
        action: str,
        user_role: UserRole,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if user has permission to perform specific action"""
        
        permission_level = await self.get_user_permission_level(db, user_id, lesson, user_role)
        
        # Admin and Coordinator have full access
        if permission_level in [PermissionLevel.FULL_ACCESS, PermissionLevel.COORDINATOR]:
            return True
        
        # No access
        if permission_level == PermissionLevel.NO_ACCESS:
            return False
        
        # View only access
        if permission_level == PermissionLevel.VIEW_ONLY:
            return action in ["view_lesson", "view_content", "view_analytics"]
        
        # Teacher permissions
        if permission_level in [PermissionLevel.ASSIGNED_TEACHER, PermissionLevel.SUBSTITUTE_TEACHER]:
            assignment = await self.check_teacher_assignment(db, user_id, lesson)
            if not assignment:
                return False
            
            permissions = assignment.permissions
            
            # Map actions to permissions
            action_permission_map = {
                "edit_content": permissions.can_edit_content,
                "publish_lesson": permissions.can_publish,
                "manage_assignments": permissions.can_manage_assignments,
                "view_analytics": permissions.can_view_analytics,
                "manage_enrollments": permissions.can_manage_enrollments,
                "assign_teachers": permissions.can_assign_teachers,
                "standardize_content": permissions.can_standardize,
                "approve_changes": permissions.can_approve_changes
            }
            
            return action_permission_map.get(action, False)
        
        return False
    
    async def apply_permission_template(
        self,
        template_name: str,
        custom_permissions: Optional[Dict[str, bool]] = None
    ) -> TeacherPermissions:
        """Apply permission template dengan custom overrides"""
        
        if template_name not in self.PERMISSION_TEMPLATES:
            raise ValueError(f"Unknown permission template: {template_name}")
        
        base_permissions = self.PERMISSION_TEMPLATES[template_name].copy()
        
        if custom_permissions:
            for perm, value in custom_permissions.items():
                if hasattr(base_permissions, perm):
                    setattr(base_permissions, perm, value)
        
        return base_permissions
    
    async def assign_teacher_to_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        class_ids: List[str],
        assigned_by: str,
        assignment_type: str = "primary",
        custom_permissions: Optional[Dict[str, bool]] = None,
        notes: Optional[str] = None
    ) -> TeacherAssignment:
        """Assign teacher to lesson with permissions"""
        
        # Determine permission template based on assignment type
        template_name = "assigned_teacher"
        if assignment_type == "substitute":
            template_name = "substitute_teacher"
        elif assignment_type == "guest":
            template_name = "guest_teacher"
        
        # Apply permissions
        permissions = await self.apply_permission_template(template_name, custom_permissions)
        
        # Create assignment
        assignment = TeacherAssignment(
            teacher_id=ObjectId(teacher_id),
            class_ids=[ObjectId(cls_id) for cls_id in class_ids],
            permissions=permissions,
            assigned_by=ObjectId(assigned_by),
            assignment_type=assignment_type,
            notes=notes
        )
        
        # Update lesson in database
        await db["lessons"].update_one(
            {"_id": ObjectId(lesson_id)},
            {
                "$push": {"teacher_assignments": assignment.dict()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return assignment
    
    async def remove_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        removed_by: str
    ) -> bool:
        """Remove teacher assignment from lesson"""
        
        result = await db["lessons"].update_one(
            {
                "_id": ObjectId(lesson_id),
                "teacher_assignments.teacher_id": ObjectId(teacher_id)
            },
            {
                "$set": {
                    "teacher_assignments.$.is_active": False,
                    "teacher_assignments.$.removed_at": datetime.utcnow(),
                    "teacher_assignments.$.removed_by": ObjectId(removed_by),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def transfer_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        old_teacher_id: str,
        new_teacher_id: str,
        transferred_by: str,
        maintain_permissions: bool = True
    ) -> bool:
        """Transfer teacher assignment from one teacher to another"""
        
        # Get current lesson
        lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
        if not lesson_doc:
            return False
        
        lesson = IndependentLesson.from_mongo(lesson_doc)
        old_assignment = None
        
        # Find old assignment
        for assignment in lesson.teacher_assignments:
            if str(assignment.teacher_id) == old_teacher_id and assignment.is_active:
                old_assignment = assignment
                break
        
        if not old_assignment:
            return False
        
        # Create new assignment with same or modified permissions
        permissions = old_assignment.permissions if maintain_permissions else self.PERMISSION_TEMPLATES["assigned_teacher"]
        
        new_assignment = TeacherAssignment(
            teacher_id=ObjectId(new_teacher_id),
            class_ids=old_assignment.class_ids,
            permissions=permissions,
            assigned_by=ObjectId(transferred_by),
            assignment_type=old_assignment.assignment_type,
            notes=f"Transferred from teacher {old_teacher_id}"
        )
        
        # Update lesson with atomic operation
        result = await db["lessons"].update_one(
            {
                "_id": ObjectId(lesson_id),
                "teacher_assignments.teacher_id": ObjectId(old_teacher_id)
            },
            {
                "$set": {
                    "teacher_assignments.$.is_active": False,
                    "teacher_assignments.$.transferred_to": ObjectId(new_teacher_id),
                    "teacher_assignments.$.transferred_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                "$push": {"teacher_assignments": new_assignment.dict()}
            }
        )
        
        return result.modified_count > 0
    
    async def update_teacher_permissions(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        new_permissions: Dict[str, bool],
        updated_by: str
    ) -> bool:
        """Update teacher's permissions in lesson"""
        
        # Build update query for nested permissions
        update_fields = {}
        for perm, value in new_permissions.items():
            update_fields[f"teacher_assignments.$.permissions.{perm}"] = value
        
        update_fields["teacher_assignments.$.permissions_updated_at"] = datetime.utcnow()
        update_fields["teacher_assignments.$.permissions_updated_by"] = ObjectId(updated_by)
        update_fields["updated_at"] = datetime.utcnow()
        
        result = await db["lessons"].update_one(
            {
                "_id": ObjectId(lesson_id),
                "teacher_assignments.teacher_id": ObjectId(teacher_id),
                "teacher_assignments.is_active": True
            },
            {"$set": update_fields}
        )
        
        return result.modified_count > 0
    
    async def check_content_modification_permission(
        self,
        db: AsyncIOMotorDatabase,
        user_id: str,
        lesson: IndependentLesson,
        user_role: UserRole
    ) -> Dict[str, bool]:
        """Check content modification permissions with standardization rules"""
        
        result = {
            "can_edit": False,
            "can_publish": False,
            "requires_approval": False,
            "reason": ""
        }
        
        # Check basic permission
        has_edit_permission = await self.check_permission(
            db, user_id, lesson, "edit_content", user_role
        )
        
        if not has_edit_permission:
            result["reason"] = "No edit permission"
            return result
        
        # Check standardization rules
        if lesson.is_standardized():
            # If standardized and doesn't allow customization
            if not lesson.standardization.allow_customization:
                is_coordinator = await self.check_coordinator_access(db, user_id, lesson)
                if not is_coordinator:
                    result["reason"] = "Standardized content, no customization allowed"
                    return result
            
            # If requires approval
            if lesson.requires_approval():
                is_coordinator = await self.check_coordinator_access(db, user_id, lesson)
                if not is_coordinator:
                    result["requires_approval"] = True
        
        result["can_edit"] = True
        
        # Check publish permission
        result["can_publish"] = await self.check_permission(
            db, user_id, lesson, "publish_lesson", user_role
        )
        
        return result
    
    async def get_user_lessons_with_permissions(
        self,
        db: AsyncIOMotorDatabase,
        user_id: str,
        user_role: UserRole,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get lessons with user's permissions for each"""
        
        # Base query
        query = filters or {}
        
        # Filter based on user role and access
        if user_role == UserRole.COORDINATOR:
            # Get coordination assignments
            coordinations = await db["coordination_assignments"].find({
                "coordinator_id": ObjectId(user_id),
                "is_active": True
            }).to_list(None)
            
            coordination_ids = [coord["_id"] for coord in coordinations]
            
            query.update({
                "$or": [
                    {"ownership.coordination_assignment_id": {"$in": coordination_ids}},
                    {"ownership.primary_coordinator_id": ObjectId(user_id)}
                ]
            })
            
        elif user_role == UserRole.TEACHER:
            query.update({
                "$or": [
                    {"teacher_assignments.teacher_id": ObjectId(user_id), "teacher_assignments.is_active": True},
                    {"teacher_id": ObjectId(user_id)}  # Legacy compatibility
                ]
            })
        
        # Get lessons
        lessons = await db["lessons"].find(query).to_list(None)
        
        # Add permission info to each lesson
        result = []
        for lesson_doc in lessons:
            lesson = IndependentLesson.from_mongo(lesson_doc)
            
            permission_level = await self.get_user_permission_level(
                db, user_id, lesson, user_role
            )
            
            lesson_with_perms = lesson_doc.copy()
            lesson_with_perms["user_permission_level"] = permission_level.value
            lesson_with_perms["user_can_edit"] = await self.check_permission(
                db, user_id, lesson, "edit_content", user_role
            )
            lesson_with_perms["user_can_publish"] = await self.check_permission(
                db, user_id, lesson, "publish_lesson", user_role
            )
            lesson_with_perms["user_can_assign_teachers"] = await self.check_permission(
                db, user_id, lesson, "assign_teachers", user_role
            )
            
            result.append(lesson_with_perms)
        
        return result


# Utility functions
async def require_lesson_permission(
    db: AsyncIOMotorDatabase,
    user_id: str,
    lesson_id: str,
    action: str,
    user_role: UserRole,
    permission_manager: LessonPermissionManager
) -> IndependentLesson:
    """Decorator helper function to require specific lesson permission"""
    
    # Get lesson
    lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if not lesson_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    lesson = IndependentLesson.from_mongo(lesson_doc)
    
    # Check permission
    has_permission = await permission_manager.check_permission(
        db, user_id, lesson, action, user_role
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for action: {action}"
        )
    
    return lesson


async def require_coordinator_access(
    db: AsyncIOMotorDatabase,
    user_id: str,
    lesson_id: str,
    permission_manager: LessonPermissionManager
) -> IndependentLesson:
    """Require coordinator access to lesson"""
    
    lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    if not lesson_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    lesson = IndependentLesson.from_mongo(lesson_doc)
    
    is_coordinator = await permission_manager.check_coordinator_access(db, user_id, lesson)
    if not is_coordinator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coordinator access required"
        )
    
    return lesson