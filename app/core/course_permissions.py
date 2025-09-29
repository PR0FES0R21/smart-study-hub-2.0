# ==============================================================================
# File: app/core/course_permissions.py
# Deskripsi: Permission management untuk Course Management System
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
# from app.schemas.user import User  # Using dict instead
from app.schemas.base import PyObjectId

class CoursePermissionManager:
    """Permission manager untuk course management system"""
    
    async def check_coordinator_access(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        subject_id: PyObjectId,
        grade_level: int
    ) -> bool:
        """Check if user adalah coordinator untuk subject/grade"""
        
        if "admin" in user.get("roles", []):
            return True
            
        if "coordinator" not in user.get("roles", []):
            return False
        
        # Check coordination assignment
        assignment = await db.coordination_assignments.find_one({
            "coordinator_id": PyObjectId(user["_id"]),
            "subject_id": subject_id,
            "$or": [
                {"grade_level": grade_level},
                {"grade_level": None}  # Coordinator untuk semua grade levels
            ]
        })
        
        return assignment is not None
    
    async def check_teacher_access(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        subject_id: PyObjectId,
        class_ids: List[PyObjectId]
    ) -> bool:
        """Check if teacher dapat access subject untuk classes tertentu"""
        
        if "admin" in user.get("roles", []):
            return True
            
        if "teacher" not in user.get("roles", []):
            return False
        
        # Check teaching assignments untuk setiap class
        for class_id in class_ids:
            assignment = await db.teaching_assignments.find_one({
                "teacher_id": PyObjectId(user["_id"]),
                "subject_id": subject_id,
                "class_id": class_id
            })
            
            if not assignment:
                return False  # Teacher tidak ada akses ke salah satu class
        
        return True
    
    async def check_course_view_permission(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        course_family_id: PyObjectId
    ) -> bool:
        """Check if user dapat view course family"""
        
        # Admin dapat view semua
        if "admin" in user.get("roles", []):
            return True
        
        # Get course family info
        family = await db.course_families.find_one({"course_family_id": course_family_id})
        if not family:
            return False
        
        # Coordinator dapat view courses yang dia kelola
        if "coordinator" in user.get("roles", []):
            is_coordinator = await self.check_coordinator_access(
                db, user, family["subject_id"], family["grade_level"]
            )
            if is_coordinator:
                return True
        
        # Teacher dapat view jika ada teaching assignment
        if "teacher" in user.get("roles", []):
            assignment = await db.teaching_assignments.find_one({
                "teacher_id": PyObjectId(user["_id"]),
                "subject_id": family["subject_id"]
            })
            if assignment:
                return True
        
        # Student dapat view jika enrolled
        if "student" in user.get("roles", []):
            # Check enrollment (would need to implement enrollment system)
            return True  # Placeholder - semua student dapat view untuk sekarang
        
        return False
    
    async def check_course_edit_permission(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        course_version_id: PyObjectId
    ) -> bool:
        """Check if user dapat edit specific course version"""
        
        # Admin dapat edit semua
        if "admin" in user.get("roles", []):
            return True
        
        # Get course version info
        version = await db.course_versions.find_one({"_id": course_version_id})
        if not version:
            return False
        
        # Master course: Only coordinator can edit
        if version["is_master"]:
            if "coordinator" not in user.get("roles", []):
                return False
            
            return version["coordinator_id"] == PyObjectId(user["_id"])
        
        # Teacher fork: Only owner teacher can edit
        else:
            if "teacher" not in user.get("roles", []):
                return False
                
            return version.get("teacher_id") == PyObjectId(user["_id"])
    
    async def check_pr_create_permission(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        source_version_id: PyObjectId
    ) -> bool:
        """Check if user dapat create PR dari source version"""
        
        if "admin" in user.get("roles", []):
            return True
        
        # Get source version
        source = await db.course_versions.find_one({"_id": source_version_id})
        if not source:
            return False
        
        # Can only create PR from your own fork
        if source["is_master"]:
            # Can create PR from master only if you're coordinator
            return ("coordinator" in user.get("roles", []) and 
                   source["coordinator_id"] == PyObjectId(user["_id"]))
        else:
            # Can create PR from fork only if you're the owner
            return ("teacher" in user.get("roles", []) and 
                   source.get("teacher_id") == PyObjectId(user["_id"]))
    
    async def check_pr_review_permission(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        pr_id: PyObjectId
    ) -> bool:
        """Check if user dapat review PR"""
        
        if "admin" in user.get("roles", []):
            return True
            
        if "coordinator" not in user.get("roles", []):
            return False
        
        # Get PR info
        pr = await db.course_pull_requests.find_one({"_id": pr_id})
        if not pr:
            return False
        
        # Get target version to check if user is coordinator
        target_version = await db.course_versions.find_one({"_id": pr["target_version_id"]})
        if not target_version:
            return False
        
        return target_version["coordinator_id"] == PyObjectId(user["_id"])
    
    async def check_fork_create_permission(
        self,
        db: AsyncIOMotorDatabase,
        user: dict,
        master_version_id: PyObjectId,
        class_ids: List[PyObjectId]
    ) -> bool:
        """Check if teacher dapat create fork untuk classes"""
        
        if "admin" in user.get("roles", []):
            return True
            
        if "teacher" not in user.get("roles", []):
            return False
        
        # Get master version
        master = await db.course_versions.find_one({"_id": master_version_id})
        if not master or not master["is_master"]:
            return False
        
        # Check if teacher has access to subject and classes
        return await self.check_teacher_access(
            db, user, master["subject_id"], class_ids
        )

# Convenience functions untuk dependency injection
async def require_role(user: dict, required_roles: List[str]):
    """Require user to have one of the specified roles"""
    user_roles = user.get("roles", [])
    if not any(role in user_roles for role in required_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {', '.join(required_roles)}"
        )

async def check_user_permission(user: dict, action: str, resource_id: Optional[PyObjectId] = None):
    """General permission check - placeholder untuk sekarang"""
    # This would implement more granular permissions later
    # For now, basic role checking
    
    user_roles = user.get("roles", [])
    
    if action == "view_course":
        if not any(role in user_roles for role in ["admin", "coordinator", "teacher", "student"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    elif action in ["edit_course", "create_pr", "review_pr"]:
        if not any(role in user_roles for role in ["admin", "coordinator", "teacher"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # More specific checks would go here

# Create singleton instance
permission_manager = CoursePermissionManager()
