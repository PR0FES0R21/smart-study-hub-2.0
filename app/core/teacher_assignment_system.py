# ==============================================================================
# File: app/core/teacher_assignment_system.py
# Description: Dynamic Teacher Assignment System with Seamless Transitions
# ==============================================================================
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from app.models.lesson import IndependentLesson, TeacherAssignment, TeacherPermissions
from app.core.lesson_permissions import LessonPermissionManager, UserRole
from app.schemas.base import PyObjectId


class TeacherAssignmentSystem:
    """Dynamic Teacher Assignment System untuk Independent Lessons"""
    
    def __init__(self, permission_manager: LessonPermissionManager):
        self.permission_manager = permission_manager
        self.DEFAULT_ASSIGNMENT_DURATION = timedelta(days=365)  # 1 year default
    
    async def create_coordinated_lesson_from_assignments(
        self,
        db: AsyncIOMotorDatabase,
        coordinator_id: str,
        coordination_assignment_id: str,
        lesson_data: Dict[str, Any]
    ) -> IndependentLesson:
        """Create new coordinated lesson and auto-assign teachers from teaching assignments"""
        
        # Get coordination assignment
        coordination = await db["coordination_assignments"].find_one({
            "_id": ObjectId(coordination_assignment_id),
            "coordinator_id": ObjectId(coordinator_id),
            "is_active": True
        })
        
        if not coordination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coordination assignment not found"
            )
        
        # Get teaching assignments untuk same subject and grade
        teaching_assignments = await db["teaching_assignments"].find({
            "subject_id": coordination["subject_id"],
            "academic_period_id": coordination["academic_period_id"],
            "is_active": True
        }).to_list(None)
        
        # Get classes for the target grade level
        target_grade = lesson_data.get("target_scope", {}).get("grade_level")
        if target_grade:
            # Filter classes by grade level
            class_query = {"grade_level": target_grade, "is_active": True}
            if lesson_data.get("target_scope", {}).get("expertise_ids"):
                class_query["expertise_program_id"] = {
                    "$in": [ObjectId(exp_id) for exp_id in lesson_data["target_scope"]["expertise_ids"]]
                }
            
            target_classes = await db["classes"].find(class_query).to_list(None)
            class_ids = [cls["_id"] for cls in target_classes]
        else:
            class_ids = lesson_data.get("target_scope", {}).get("class_ids", [])
        
        # Create lesson with coordination ownership
        lesson_doc = {
            "title": lesson_data["title"],
            "description": lesson_data["description"],
            "subject_id": coordination["subject_id"],
            "academic_period_id": coordination["academic_period_id"],
            
            # Coordination ownership
            "ownership": {
                "owner_type": "coordination",
                "primary_coordinator_id": ObjectId(coordinator_id),
                "coordination_assignment_id": ObjectId(coordination_assignment_id)
            },
            
            # Target scope
            "target_scope": {
                "grade_level": target_grade or 10,
                "expertise_ids": [ObjectId(exp_id) for exp_id in lesson_data.get("target_scope", {}).get("expertise_ids", [])],
                "class_ids": [ObjectId(cls_id) for cls_id in class_ids],
                "scope_type": lesson_data.get("target_scope", {}).get("scope_type", "grade_wide")
            },
            
            # Auto-assign teachers
            "teacher_assignments": [],
            
            # Standardization settings
            "standardization": lesson_data.get("standardization", {
                "is_standardized": True,
                "allow_customization": True,
                "customization_level": "moderate",
                "approval_required": False
            }),
            
            # Other lesson data
            "lesson_order": lesson_data.get("lesson_order", 0),
            "category": lesson_data.get("category", "general"),
            "lesson_type": lesson_data.get("lesson_type", "standard"),
            "status": "draft",
            "is_published": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            
            # Default settings
            "file_upload_settings": lesson_data.get("file_upload_settings", {}),
            "access_settings": lesson_data.get("access_settings", {}),
            "metadata": lesson_data.get("metadata", {}),
            "stats": {"total_enrollments": 0, "completed_count": 0}
        }
        
        # Insert lesson
        result = await db["lessons"].insert_one(lesson_doc)
        lesson_id = result.inserted_id
        
        # Auto-assign teachers based on teaching assignments
        assigned_teachers = []
        for teaching_assignment in teaching_assignments:
            # Check if teacher's classes overlap with lesson target classes
            teacher_classes = teaching_assignment.get("class_ids", [teaching_assignment.get("class_id")])
            if teacher_classes and any(cls_id in class_ids for cls_id in teacher_classes):
                # Find overlapping classes
                overlapping_classes = [cls_id for cls_id in teacher_classes if cls_id in class_ids]
                
                # Create teacher assignment
                teacher_assignment = await self.assign_teacher_to_lesson(
                    db=db,
                    lesson_id=str(lesson_id),
                    teacher_id=str(teaching_assignment["teacher_id"]),
                    class_ids=[str(cls_id) for cls_id in overlapping_classes],
                    assigned_by=coordinator_id,
                    assignment_type="primary",
                    auto_assigned=True,
                    notes=f"Auto-assigned based on teaching assignment {teaching_assignment['_id']}"
                )
                assigned_teachers.append(teacher_assignment)
        
        # Get created lesson
        lesson_doc = await db["lessons"].find_one({"_id": lesson_id})
        lesson = IndependentLesson.from_mongo(lesson_doc)
        
        return lesson
    
    async def assign_teacher_to_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        class_ids: List[str],
        assigned_by: str,
        assignment_type: str = "primary",
        custom_permissions: Optional[Dict[str, bool]] = None,
        notes: Optional[str] = None,
        auto_assigned: bool = False,
        effective_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None
    ) -> TeacherAssignment:
        """Assign teacher to lesson with enhanced options"""
        
        # Validate teacher exists and has proper role
        teacher = await db["users"].find_one({
            "_id": ObjectId(teacher_id),
            "role": {"$in": ["teacher", "admin"]},
            "is_active": True
        })
        
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher not found or inactive"
            )
        
        # Get lesson to validate
        lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
        if not lesson_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        lesson = IndependentLesson.from_mongo(lesson_doc)
        
        # Check if assigner has permission (coordinator or admin)
        has_permission = await self.permission_manager.check_permission(
            db, assigned_by, lesson, "assign_teachers", UserRole.COORDINATOR
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to assign teachers"
            )
        
        # Check for existing active assignment
        existing_assignment = await self.get_teacher_assignment(db, lesson_id, teacher_id)
        if existing_assignment and existing_assignment.is_active:
            # Update existing assignment
            return await self.update_teacher_assignment(
                db, lesson_id, teacher_id, {
                    "class_ids": [ObjectId(cls_id) for cls_id in class_ids],
                    "assignment_type": assignment_type,
                    "notes": notes or existing_assignment.notes
                }, assigned_by
            )
        
        # Apply permission template
        permissions = await self.permission_manager.apply_permission_template(
            assignment_type, custom_permissions
        )
        
        # Create assignment
        assignment = TeacherAssignment(
            teacher_id=ObjectId(teacher_id),
            class_ids=[ObjectId(cls_id) for cls_id in class_ids],
            permissions=permissions,
            assigned_by=ObjectId(assigned_by),
            assignment_type=assignment_type,
            notes=notes,
            assigned_at=effective_date or datetime.utcnow(),
            is_active=True
        )
        
        # Add additional fields for enhanced tracking
        assignment_dict = assignment.dict()
        assignment_dict.update({
            "auto_assigned": auto_assigned,
            "effective_date": effective_date or datetime.utcnow(),
            "expiry_date": expiry_date,
            "assignment_history": [{
                "action": "assigned",
                "by": ObjectId(assigned_by),
                "at": datetime.utcnow(),
                "details": f"Assigned as {assignment_type}"
            }]
        })
        
        # Update lesson
        await db["lessons"].update_one(
            {"_id": ObjectId(lesson_id)},
            {
                "$push": {"teacher_assignments": assignment_dict},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Log assignment
        await self.log_assignment_action(
            db, lesson_id, teacher_id, "assigned", assigned_by,
            {"assignment_type": assignment_type, "class_count": len(class_ids)}
        )
        
        return assignment
    
    async def transfer_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        old_teacher_id: str,
        new_teacher_id: str,
        transferred_by: str,
        transfer_reason: str = "teacher_change",
        maintain_permissions: bool = True,
        transition_period_days: int = 7,
        notify_students: bool = True
    ) -> Dict[str, Any]:
        """Advanced teacher assignment transfer with transition period"""
        
        # Validate both teachers
        old_teacher = await db["users"].find_one({"_id": ObjectId(old_teacher_id)})
        new_teacher = await db["users"].find_one({
            "_id": ObjectId(new_teacher_id),
            "role": {"$in": ["teacher", "admin"]},
            "is_active": True
        })
        
        if not new_teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New teacher not found or inactive"
            )
        
        # Get current assignment
        current_assignment = await self.get_teacher_assignment(db, lesson_id, old_teacher_id)
        if not current_assignment or not current_assignment.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Current teacher assignment not found"
            )
        
        # Prepare transition
        transition_end = datetime.utcnow() + timedelta(days=transition_period_days)
        
        # Create new assignment
        new_permissions = current_assignment.permissions if maintain_permissions else await self.permission_manager.apply_permission_template("assigned_teacher")
        
        new_assignment = TeacherAssignment(
            teacher_id=ObjectId(new_teacher_id),
            class_ids=current_assignment.class_ids,
            permissions=new_permissions,
            assigned_by=ObjectId(transferred_by),
            assignment_type=current_assignment.assignment_type,
            notes=f"Transferred from teacher {old_teacher_id}. Reason: {transfer_reason}"
        )
        
        new_assignment_dict = new_assignment.dict()
        new_assignment_dict.update({
            "transferred_from": ObjectId(old_teacher_id),
            "transfer_reason": transfer_reason,
            "transition_end": transition_end,
            "assignment_history": [{
                "action": "transferred_in",
                "by": ObjectId(transferred_by),
                "at": datetime.utcnow(),
                "details": f"Transferred from {old_teacher_id}"
            }]
        })
        
        # Update lesson with atomic operations
        result = await db["lessons"].update_one(
            {
                "_id": ObjectId(lesson_id),
                "teacher_assignments.teacher_id": ObjectId(old_teacher_id),
                "teacher_assignments.is_active": True
            },
            {
                "$set": {
                    "teacher_assignments.$.is_active": False,
                    "teacher_assignments.$.transferred_to": ObjectId(new_teacher_id),
                    "teacher_assignments.$.transferred_at": datetime.utcnow(),
                    "teacher_assignments.$.transfer_reason": transfer_reason,
                    "teacher_assignments.$.transition_end": transition_end,
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "teacher_assignments": new_assignment_dict,
                    "teacher_assignments.$.assignment_history": {
                        "action": "transferred_out",
                        "by": ObjectId(transferred_by),
                        "at": datetime.utcnow(),
                        "details": f"Transferred to {new_teacher_id}"
                    }
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to transfer assignment"
            )
        
        # Create transition record for tracking
        transition_record = {
            "lesson_id": ObjectId(lesson_id),
            "old_teacher_id": ObjectId(old_teacher_id),
            "new_teacher_id": ObjectId(new_teacher_id),
            "transferred_by": ObjectId(transferred_by),
            "transfer_reason": transfer_reason,
            "started_at": datetime.utcnow(),
            "ends_at": transition_end,
            "status": "active",
            "notify_students": notify_students,
            "students_notified": False
        }
        
        await db["teacher_transitions"].insert_one(transition_record)
        
        # Log the transfer
        await self.log_assignment_action(
            db, lesson_id, old_teacher_id, "transferred_out", transferred_by,
            {"new_teacher_id": new_teacher_id, "reason": transfer_reason}
        )
        
        await self.log_assignment_action(
            db, lesson_id, new_teacher_id, "transferred_in", transferred_by,
            {"old_teacher_id": old_teacher_id, "reason": transfer_reason}
        )
        
        # Prepare student notifications if needed
        if notify_students:
            await self.prepare_student_notifications(
                db, lesson_id, old_teacher_id, new_teacher_id, transition_end
            )
        
        return {
            "success": True,
            "old_teacher_id": old_teacher_id,
            "new_teacher_id": new_teacher_id,
            "transition_end": transition_end,
            "transition_record_id": str(transition_record["_id"])
        }
    
    async def get_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str
    ) -> Optional[TeacherAssignment]:
        """Get teacher assignment for lesson"""
        
        lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
        if not lesson_doc:
            return None
        
        lesson = IndependentLesson.from_mongo(lesson_doc)
        
        for assignment in lesson.teacher_assignments:
            if str(assignment.teacher_id) == teacher_id:
                return assignment
        
        return None
    
    async def update_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        updates: Dict[str, Any],
        updated_by: str
    ) -> TeacherAssignment:
        """Update existing teacher assignment"""
        
        # Build update query
        update_fields = {}
        for field, value in updates.items():
            if field == "permissions" and isinstance(value, dict):
                for perm, perm_value in value.items():
                    update_fields[f"teacher_assignments.$.permissions.{perm}"] = perm_value
            else:
                update_fields[f"teacher_assignments.$.{field}"] = value
        
        # Add metadata
        update_fields["teacher_assignments.$.updated_at"] = datetime.utcnow()
        update_fields["teacher_assignments.$.updated_by"] = ObjectId(updated_by)
        update_fields["updated_at"] = datetime.utcnow()
        
        result = await db["lessons"].update_one(
            {
                "_id": ObjectId(lesson_id),
                "teacher_assignments.teacher_id": ObjectId(teacher_id),
                "teacher_assignments.is_active": True
            },
            {
                "$set": update_fields,
                "$push": {
                    "teacher_assignments.$.assignment_history": {
                        "action": "updated",
                        "by": ObjectId(updated_by),
                        "at": datetime.utcnow(),
                        "details": f"Updated: {', '.join(updates.keys())}"
                    }
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher assignment not found"
            )
        
        # Return updated assignment
        return await self.get_teacher_assignment(db, lesson_id, teacher_id)
    
    async def remove_teacher_assignment(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        removed_by: str,
        removal_reason: str = "unassigned",
        effective_date: Optional[datetime] = None
    ) -> bool:
        """Remove teacher assignment with proper tracking"""
        
        effective_date = effective_date or datetime.utcnow()
        
        result = await db["lessons"].update_one(
            {
                "_id": ObjectId(lesson_id),
                "teacher_assignments.teacher_id": ObjectId(teacher_id),
                "teacher_assignments.is_active": True
            },
            {
                "$set": {
                    "teacher_assignments.$.is_active": False,
                    "teacher_assignments.$.removed_at": effective_date,
                    "teacher_assignments.$.removed_by": ObjectId(removed_by),
                    "teacher_assignments.$.removal_reason": removal_reason,
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "teacher_assignments.$.assignment_history": {
                        "action": "removed",
                        "by": ObjectId(removed_by),
                        "at": datetime.utcnow(),
                        "details": f"Removed: {removal_reason}"
                    }
                }
            }
        )
        
        if result.modified_count > 0:
            await self.log_assignment_action(
                db, lesson_id, teacher_id, "removed", removed_by,
                {"reason": removal_reason}
            )
        
        return result.modified_count > 0
    
    async def get_lesson_teacher_assignments(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        include_inactive: bool = False,
        populate_teacher_info: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all teacher assignments for lesson with populated info"""
        
        lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
        if not lesson_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
        
        assignments = lesson_doc.get("teacher_assignments", [])
        
        if not include_inactive:
            assignments = [a for a in assignments if a.get("is_active", True)]
        
        # Populate teacher information
        if populate_teacher_info:
            teacher_ids = [a["teacher_id"] for a in assignments]
            teachers = await db["users"].find({"_id": {"$in": teacher_ids}}).to_list(None)
            teacher_map = {str(t["_id"]): t for t in teachers}
            
            for assignment in assignments:
                teacher_id = str(assignment["teacher_id"])
                if teacher_id in teacher_map:
                    teacher = teacher_map[teacher_id]
                    assignment["teacher_name"] = teacher.get("full_name", teacher.get("username"))
                    assignment["teacher_email"] = teacher.get("email")
                    assignment["teacher_status"] = "active" if teacher.get("is_active") else "inactive"
        
        return assignments
    
    async def get_teacher_lessons(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        academic_period_id: Optional[str] = None,
        include_legacy: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all lessons assigned to teacher"""
        
        query = {
            "$or": [
                {"teacher_assignments.teacher_id": ObjectId(teacher_id), "teacher_assignments.is_active": True}
            ]
        }
        
        # Include legacy teacher_id field
        if include_legacy:
            query["$or"].append({"teacher_id": ObjectId(teacher_id)})
        
        if academic_period_id:
            query["academic_period_id"] = ObjectId(academic_period_id)
        
        lessons = await db["lessons"].find(query).to_list(None)
        
        # Add assignment details to each lesson
        for lesson in lessons:
            lesson["id"] = str(lesson["_id"])
            
            # Find teacher's assignment in this lesson
            teacher_assignment = None
            for assignment in lesson.get("teacher_assignments", []):
                if str(assignment["teacher_id"]) == teacher_id and assignment.get("is_active", True):
                    teacher_assignment = assignment
                    break
            
            lesson["teacher_assignment"] = teacher_assignment
            lesson["assignment_type"] = teacher_assignment.get("assignment_type") if teacher_assignment else "legacy"
            lesson["assigned_classes"] = teacher_assignment.get("class_ids", []) if teacher_assignment else lesson.get("target_scope", {}).get("class_ids", [])
        
        return lessons
    
    async def log_assignment_action(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        action: str,
        performed_by: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log teacher assignment actions for audit trail"""
        
        log_entry = {
            "lesson_id": ObjectId(lesson_id),
            "teacher_id": ObjectId(teacher_id),
            "action": action,
            "performed_by": ObjectId(performed_by),
            "performed_at": datetime.utcnow(),
            "details": details or {}
        }
        
        await db["teacher_assignment_logs"].insert_one(log_entry)
    
    async def prepare_student_notifications(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        old_teacher_id: str,
        new_teacher_id: str,
        transition_end: datetime
    ):
        """Prepare student notifications for teacher transitions"""
        
        # Get students enrolled in lesson
        enrollments = await db["lesson_enrollments"].find({
            "lesson_id": ObjectId(lesson_id),
            "is_active": True
        }).to_list(None)
        
        # Get teacher names
        old_teacher = await db["users"].find_one({"_id": ObjectId(old_teacher_id)})
        new_teacher = await db["users"].find_one({"_id": ObjectId(new_teacher_id)})
        
        old_teacher_name = old_teacher.get("full_name", "Previous Teacher") if old_teacher else "Previous Teacher"
        new_teacher_name = new_teacher.get("full_name", "New Teacher") if new_teacher else "New Teacher"
        
        # Create notification records
        notifications = []
        for enrollment in enrollments:
            notifications.append({
                "user_id": enrollment["user_id"],
                "lesson_id": ObjectId(lesson_id),
                "type": "teacher_change",
                "title": "Teacher Assignment Change",
                "message": f"Your teacher for this lesson has changed from {old_teacher_name} to {new_teacher_name}. Transition period ends on {transition_end.strftime('%Y-%m-%d')}.",
                "data": {
                    "old_teacher_id": old_teacher_id,
                    "new_teacher_id": new_teacher_id,
                    "old_teacher_name": old_teacher_name,
                    "new_teacher_name": new_teacher_name,
                    "transition_end": transition_end
                },
                "is_read": False,
                "created_at": datetime.utcnow()
            })
        
        if notifications:
            await db["notifications"].insert_many(notifications)
    
    async def get_assignment_statistics(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: Optional[str] = None,
        coordinator_id: Optional[str] = None,
        academic_period_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get teacher assignment statistics"""
        
        pipeline = []
        
        # Match stage
        match_conditions = {}
        if lesson_id:
            match_conditions["_id"] = ObjectId(lesson_id)
        if coordinator_id:
            match_conditions["ownership.primary_coordinator_id"] = ObjectId(coordinator_id)
        if academic_period_id:
            match_conditions["academic_period_id"] = ObjectId(academic_period_id)
        
        if match_conditions:
            pipeline.append({"$match": match_conditions})
        
        # Unwind teacher assignments
        pipeline.extend([
            {"$unwind": {"path": "$teacher_assignments", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": None,
                    "total_lessons": {"$sum": 1},
                    "total_assignments": {
                        "$sum": {"$cond": [{"$ne": ["$teacher_assignments", None]}, 1, 0]}
                    },
                    "active_assignments": {
                        "$sum": {"$cond": [{"$eq": ["$teacher_assignments.is_active", True]}, 1, 0]}
                    },
                    "primary_assignments": {
                        "$sum": {"$cond": [{"$eq": ["$teacher_assignments.assignment_type", "primary"]}, 1, 0]}
                    },
                    "substitute_assignments": {
                        "$sum": {"$cond": [{"$eq": ["$teacher_assignments.assignment_type", "substitute"]}, 1, 0]}
                    },
                    "unique_teachers": {"$addToSet": "$teacher_assignments.teacher_id"}
                }
            },
            {
                "$project": {
                    "total_lessons": 1,
                    "total_assignments": 1,
                    "active_assignments": 1,
                    "primary_assignments": 1,
                    "substitute_assignments": 1,
                    "unique_teachers_count": {"$size": {"$ifNull": ["$unique_teachers", []]}}
                }
            }
        ])
        
        result = await db["lessons"].aggregate(pipeline).to_list(1)
        
        if result:
            stats = result[0]
            stats.pop("_id", None)
            return stats
        
        return {
            "total_lessons": 0,
            "total_assignments": 0,
            "active_assignments": 0,
            "primary_assignments": 0,
            "substitute_assignments": 0,
            "unique_teachers_count": 0
        }


# Utility functions for common operations
async def auto_assign_teachers_to_coordinated_lessons(
    db: AsyncIOMotorDatabase,
    coordinator_id: str,
    academic_period_id: str,
    assignment_system: TeacherAssignmentSystem
):
    """Auto-assign teachers to all coordinated lessons based on teaching assignments"""
    
    # Get coordinated lessons without teacher assignments
    coordinated_lessons = await db["lessons"].find({
        "ownership.primary_coordinator_id": ObjectId(coordinator_id),
        "academic_period_id": ObjectId(academic_period_id),
        "teacher_assignments": {"$size": 0}
    }).to_list(None)
    
    assignments_created = 0
    
    for lesson_doc in coordinated_lessons:
        lesson = IndependentLesson.from_mongo(lesson_doc)
        
        # Get teaching assignments for this subject
        teaching_assignments = await db["teaching_assignments"].find({
            "subject_id": lesson.subject_id,
            "academic_period_id": ObjectId(academic_period_id),
            "is_active": True
        }).to_list(None)
        
        # Assign teachers to lesson
        for teaching_assignment in teaching_assignments:
            try:
                await assignment_system.assign_teacher_to_lesson(
                    db=db,
                    lesson_id=str(lesson.id),
                    teacher_id=str(teaching_assignment["teacher_id"]),
                    class_ids=[str(teaching_assignment.get("class_id", ""))],
                    assigned_by=coordinator_id,
                    assignment_type="primary",
                    auto_assigned=True
                )
                assignments_created += 1
            except Exception as e:
                print(f"Failed to assign teacher {teaching_assignment['teacher_id']} to lesson {lesson.id}: {e}")
                continue
    
    return assignments_created