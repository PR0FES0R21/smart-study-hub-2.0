# ==============================================================================
# File: app/crud/course_class_settings.py
# Deskripsi: CRUD operations untuk CourseClassSettings
# ==============================================================================
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

from app.models.course_class_settings import CourseClassSettings, StudentOverride
from app.schemas.base import PyObjectId


class CourseClassSettingsCRUD:
    """CRUD operations untuk CourseClassSettings"""
    
    def __init__(self):
        self.collection = "course_class_settings"
        self.courses_collection = "courses"
        self.classes_collection = "classes"
        self.users_collection = "users"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def assign_course_to_class(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        class_id: str,
        teacher_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> CourseClassSettings:
        """Assign course to class"""
        
        # Check if course exists
        course = await db[self.courses_collection].find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Check if class exists
        class_doc = await db[self.classes_collection].find_one({"_id": ObjectId(class_id)})
        if not class_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found"
            )
        
        # Check if already assigned
        existing = await db[self.collection].find_one({
            "course_id": ObjectId(course_id),
            "class_id": ObjectId(class_id),
            "status": "active"
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course already assigned to this class"
            )
        
        # Create assignment
        assignment = CourseClassSettings(
            course_id=PyObjectId(course_id),
            class_id=PyObjectId(class_id),
            teacher_id=PyObjectId(teacher_id),
            start_date=start_date,
            end_date=end_date,
            settings=settings or {}
        )
        
        # Insert to database
        result = await db[self.collection].insert_one(assignment.to_mongo())
        assignment.id = str(result.inserted_id)
        
        return assignment
    
    # ==================== READ OPERATIONS ====================
    
    async def get_by_id(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str
    ) -> Optional[CourseClassSettings]:
        """Get assignment by ID"""
        data = await db[self.collection].find_one({"_id": ObjectId(setting_id)})
        if not data:
            return None
        return CourseClassSettings.from_mongo(data)
    
    async def get_by_course_and_class(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        class_id: str
    ) -> Optional[CourseClassSettings]:
        """Get assignment by course and class"""
        data = await db[self.collection].find_one({
            "course_id": ObjectId(course_id),
            "class_id": ObjectId(class_id),
            "status": "active"
        })
        if not data:
            return None
        return CourseClassSettings.from_mongo(data)
    
    async def get_by_class(
        self,
        db: AsyncIOMotorDatabase,
        class_id: str,
        include_archived: bool = False
    ) -> List[CourseClassSettings]:
        """Get all assignments for a class"""
        query = {"class_id": ObjectId(class_id)}
        if not include_archived:
            query["status"] = "active"
        
        cursor = db[self.collection].find(query).sort("assigned_at", DESCENDING)
        assignments = []
        async for data in cursor:
            assignments.append(CourseClassSettings.from_mongo(data))
        return assignments
    
    async def get_by_course(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        include_archived: bool = False
    ) -> List[CourseClassSettings]:
        """Get all assignments for a course"""
        query = {"course_id": ObjectId(course_id)}
        if not include_archived:
            query["status"] = "active"
        
        cursor = db[self.collection].find(query).sort("assigned_at", DESCENDING)
        assignments = []
        async for data in cursor:
            assignments.append(CourseClassSettings.from_mongo(data))
        return assignments
    
    async def get_by_teacher(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        include_archived: bool = False
    ) -> List[CourseClassSettings]:
        """Get all assignments by teacher"""
        query = {"teacher_id": ObjectId(teacher_id)}
        if not include_archived:
            query["status"] = "active"
        
        cursor = db[self.collection].find(query).sort("assigned_at", DESCENDING)
        assignments = []
        async for data in cursor:
            assignments.append(CourseClassSettings.from_mongo(data))
        return assignments
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_settings(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> CourseClassSettings:
        """Update class settings"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Update fields
        update_data = {"updated_at": datetime.utcnow()}
        if start_date is not None:
            update_data["start_date"] = start_date
            assignment.start_date = start_date
        if end_date is not None:
            update_data["end_date"] = end_date
            assignment.end_date = end_date
        if settings is not None:
            update_data["settings"] = settings
            assignment.settings = settings
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(setting_id)},
            {"$set": update_data}
        )
        
        assignment.updated_at = update_data["updated_at"]
        return assignment
    
    async def add_student_override(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str,
        student_id: str,
        teacher_id: str,
        unlocked_modules: List[str] = None,
        unlocked_lessons: List[str] = None,
        reason: str = None
    ) -> CourseClassSettings:
        """Add or update student override"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Add override using model method
        assignment.add_student_override(
            student_id=student_id,
            teacher_id=teacher_id,
            unlocked_modules=unlocked_modules,
            unlocked_lessons=unlocked_lessons,
            reason=reason
        )
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(setting_id)},
            {"$set": {
                "class_overrides": assignment.class_overrides.dict(),
                "updated_at": assignment.updated_at
            }}
        )
        
        return assignment
    
    async def remove_student_override(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str,
        student_id: str
    ) -> CourseClassSettings:
        """Remove student override"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Remove override using model method
        removed = assignment.remove_student_override(student_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student override not found"
            )
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(setting_id)},
            {"$set": {
                "class_overrides": assignment.class_overrides.dict(),
                "updated_at": assignment.updated_at
            }}
        )
        
        return assignment
    
    async def update_metadata(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str,
        metadata: Dict[str, Any]
    ) -> CourseClassSettings:
        """Update class metadata (calculated stats)"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Update metadata
        for key, value in metadata.items():
            if hasattr(assignment.metadata, key):
                setattr(assignment.metadata, key, value)
        
        assignment.metadata.last_calculated = datetime.utcnow()
        assignment.updated_at = datetime.utcnow()
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(setting_id)},
            {"$set": {
                "metadata": assignment.metadata.dict(),
                "updated_at": assignment.updated_at
            }}
        )
        
        return assignment
    
    # ==================== DELETE OPERATIONS ====================
    
    async def archive(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str,
        archived_by: str
    ) -> CourseClassSettings:
        """Archive assignment (soft delete)"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Archive using model method
        assignment.archive(archived_by)
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(setting_id)},
            {"$set": {
                "status": assignment.status,
                "archived_at": assignment.archived_at,
                "archived_by": ObjectId(archived_by),
                "updated_at": assignment.updated_at
            }}
        )
        
        return assignment
    
    async def restore(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str
    ) -> CourseClassSettings:
        """Restore archived assignment"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Restore using model method
        assignment.restore()
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(setting_id)},
            {"$set": {
                "status": assignment.status,
                "archived_at": None,
                "archived_by": None,
                "updated_at": assignment.updated_at
            }}
        )
        
        return assignment
    
    # ==================== HELPER METHODS ====================
    
    async def get_student_override(
        self,
        db: AsyncIOMotorDatabase,
        setting_id: str,
        student_id: str
    ) -> Optional[StudentOverride]:
        """Get student override"""
        assignment = await self.get_by_id(db, setting_id)
        if not assignment:
            return None
        return assignment.get_student_override(student_id)
    
    async def check_student_has_access(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> Optional[CourseClassSettings]:
        """Check if student has access to course via their class"""
        # Get student's class
        student = await db[self.users_collection].find_one({"_id": ObjectId(student_id)})
        if not student or "class_id" not in student:
            return None
        
        class_id = student["class_id"]
        
        # Get active assignment
        assignment = await self.get_by_course_and_class(db, course_id, str(class_id))
        return assignment


# Create singleton instance
course_class_settings_crud = CourseClassSettingsCRUD()
