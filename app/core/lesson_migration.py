# ==============================================================================
# File: app/core/lesson_migration.py
# Description: Migration System for Converting Teacher-owned Lessons to Independent Lessons
# ==============================================================================
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from dataclasses import dataclass
import logging

from app.models.lesson import IndependentLesson, TeacherAssignment, TeacherPermissions
from app.core.lesson_permissions import LessonPermissionManager
from app.core.teacher_assignment_system import TeacherAssignmentSystem

logger = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    """Statistics for migration process"""
    total_lessons: int = 0
    migrated_lessons: int = 0
    failed_lessons: int = 0
    skipped_lessons: int = 0
    coordination_assignments_created: int = 0
    teacher_assignments_created: int = 0
    errors: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class LessonMigrationManager:
    """Manager for migrating teacher-owned lessons to independent lesson system"""
    
    def __init__(self):
        self.permission_manager = LessonPermissionManager()
        self.assignment_system = TeacherAssignmentSystem(self.permission_manager)
    
    async def migrate_all_lessons(
        self,
        db: AsyncIOMotorDatabase,
        academic_period_id: Optional[str] = None,
        dry_run: bool = False,
        batch_size: int = 50
    ) -> MigrationStats:
        """Migrate all teacher-owned lessons to independent lesson system"""
        
        stats = MigrationStats()
        
        # Build query for lessons to migrate
        query = {
            "teacher_id": {"$exists": True, "$ne": None},
            "$or": [
                {"ownership": {"$exists": False}},
                {"teacher_assignments": {"$exists": False}},
                {"teacher_assignments": {"$size": 0}}
            ]
        }
        
        if academic_period_id:
            query["academic_period_id"] = ObjectId(academic_period_id)
        
        # Count total lessons
        stats.total_lessons = await db["lessons"].count_documents(query)
        
        logger.info(f"Starting lesson migration. Total lessons to migrate: {stats.total_lessons}")
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual changes will be made")
        
        # Process lessons in batches
        skip = 0
        while skip < stats.total_lessons:
            lessons = await db["lessons"].find(query).skip(skip).limit(batch_size).to_list(batch_size)
            
            for lesson_doc in lessons:
                try:
                    if dry_run:
                        # Just validate migration would work
                        await self._validate_lesson_migration(db, lesson_doc)
                        stats.migrated_lessons += 1
                    else:
                        # Actually migrate
                        result = await self._migrate_single_lesson(db, lesson_doc)
                        if result["success"]:
                            stats.migrated_lessons += 1
                            if result.get("teacher_assignments_created"):
                                stats.teacher_assignments_created += result["teacher_assignments_created"]
                        else:
                            stats.failed_lessons += 1
                            stats.errors.append({
                                "lesson_id": str(lesson_doc["_id"]),
                                "lesson_title": lesson_doc.get("title", "Unknown"),
                                "error": result.get("error", "Unknown error")
                            })
                            
                except Exception as e:
                    stats.failed_lessons += 1
                    stats.errors.append({
                        "lesson_id": str(lesson_doc["_id"]),
                        "lesson_title": lesson_doc.get("title", "Unknown"),
                        "error": str(e)
                    })
                    logger.error(f"Failed to migrate lesson {lesson_doc['_id']}: {str(e)}")
            
            skip += batch_size
            logger.info(f"Processed {min(skip, stats.total_lessons)}/{stats.total_lessons} lessons")
        
        # Log final stats
        logger.info(f"Migration completed. Success: {stats.migrated_lessons}, Failed: {stats.failed_lessons}")
        
        return stats
    
    async def _validate_lesson_migration(
        self,
        db: AsyncIOMotorDatabase,
        lesson_doc: Dict[str, Any]
    ) -> bool:
        """Validate that lesson can be migrated without errors"""
        
        # Check if teacher exists and is active
        teacher = await db["users"].find_one({
            "_id": lesson_doc["teacher_id"],
            "role": {"$in": ["teacher", "admin"]},
            "is_active": True
        })
        
        if not teacher:
            raise ValueError(f"Teacher {lesson_doc['teacher_id']} not found or inactive")
        
        # Check if subject exists
        subject = await db["subjects"].find_one({"_id": lesson_doc["subject_id"]})
        if not subject:
            raise ValueError(f"Subject {lesson_doc['subject_id']} not found")
        
        # Check academic period
        if lesson_doc.get("academic_period_id"):
            period = await db["academic_periods"].find_one({"_id": lesson_doc["academic_period_id"]})
            if not period:
                raise ValueError(f"Academic period {lesson_doc['academic_period_id']} not found")
        
        return True
    
    async def _migrate_single_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Migrate a single teacher-owned lesson to independent lesson system"""
        
        try:
            lesson_id = str(lesson_doc["_id"])
            teacher_id = str(lesson_doc["teacher_id"])
            
            # Validate lesson can be migrated
            await self._validate_lesson_migration(db, lesson_doc)
            
            # Step 1: Find or create coordination assignment
            coordination_result = await self._find_or_create_coordination_assignment(
                db, teacher_id, lesson_doc
            )
            
            if not coordination_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to create coordination assignment: {coordination_result['error']}"
                }
            
            coordination_assignment_id = coordination_result["coordination_assignment_id"]
            
            # Step 2: Convert lesson to independent lesson structure
            migration_data = await self._build_migration_data(db, lesson_doc, coordination_assignment_id)
            
            # Step 3: Update lesson with independent structure
            await db["lessons"].update_one(
                {"_id": lesson_doc["_id"]},
                {"$set": migration_data["lesson_updates"]}
            )
            
            # Step 4: Create teacher assignment for original teacher
            assignment = await self.assignment_system.assign_teacher_to_lesson(
                db=db,
                lesson_id=lesson_id,
                teacher_id=teacher_id,
                class_ids=migration_data["class_ids"],
                assigned_by=teacher_id,  # Self-assigned during migration
                assignment_type="primary",
                auto_assigned=True,
                notes="Migrated from teacher-owned lesson"
            )
            
            # Step 5: Log migration
            await self._log_migration(db, lesson_id, teacher_id, migration_data)
            
            return {
                "success": True,
                "lesson_id": lesson_id,
                "coordination_assignment_id": coordination_assignment_id,
                "teacher_assignments_created": 1
            }
            
        except Exception as e:
            logger.error(f"Error migrating lesson {lesson_doc['_id']}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _find_or_create_coordination_assignment(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        lesson_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find existing or create new coordination assignment for teacher"""
        
        try:
            subject_id = lesson_doc["subject_id"]
            academic_period_id = lesson_doc.get("academic_period_id")
            
            if not academic_period_id:
                # Find current active academic period
                period = await db["academic_periods"].find_one({"is_active": True})
                if not period:
                    return {"success": False, "error": "No active academic period found"}
                academic_period_id = period["_id"]
            
            # Determine grade level from class or default to 10
            grade_level = 10
            if lesson_doc.get("class_id"):
                class_doc = await db["classes"].find_one({"_id": lesson_doc["class_id"]})
                if class_doc and class_doc.get("grade_level"):
                    grade_level = class_doc["grade_level"]
            
            # Check if coordination assignment already exists
            coordination = await db["coordination_assignments"].find_one({
                "coordinator_id": ObjectId(teacher_id),
                "subject_id": subject_id,
                "grade_level": grade_level,
                "academic_period_id": academic_period_id,
                "is_active": True
            })
            
            if coordination:
                return {
                    "success": True,
                    "coordination_assignment_id": str(coordination["_id"]),
                    "created": False
                }
            
            # Create new coordination assignment
            coordination_doc = {
                "coordinator_id": ObjectId(teacher_id),
                "subject_id": subject_id,
                "grade_level": grade_level,
                "academic_period_id": academic_period_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "created_by": ObjectId(teacher_id),
                "migration_created": True,  # Flag to indicate this was created during migration
                "migration_notes": "Auto-created during lesson migration from teacher-owned to coordinated system"
            }
            
            result = await db["coordination_assignments"].insert_one(coordination_doc)
            
            return {
                "success": True,
                "coordination_assignment_id": str(result.inserted_id),
                "created": True
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _build_migration_data(
        self,
        db: AsyncIOMotorDatabase,
        lesson_doc: Dict[str, Any],
        coordination_assignment_id: str
    ) -> Dict[str, Any]:
        """Build migration data for converting lesson to independent structure"""
        
        teacher_id = lesson_doc["teacher_id"]
        
        # Build target scope
        target_scope = {
            "grade_level": 10,  # Default
            "expertise_ids": [],
            "class_ids": [],
            "scope_type": "class_specific"
        }
        
        class_ids = []
        
        # Handle class assignment
        if lesson_doc.get("class_id"):
            class_id = lesson_doc["class_id"]
            class_ids.append(str(class_id))
            target_scope["class_ids"] = [class_id]
            
            # Get class details for grade level and expertise
            class_doc = await db["classes"].find_one({"_id": class_id})
            if class_doc:
                target_scope["grade_level"] = class_doc.get("grade_level", 10)
                if class_doc.get("expertise_program_id"):
                    target_scope["expertise_ids"] = [class_doc["expertise_program_id"]]
        
        # Build ownership structure
        ownership = {
            "owner_type": "coordination",
            "primary_coordinator_id": teacher_id,
            "coordination_assignment_id": ObjectId(coordination_assignment_id)
        }
        
        # Build standardization settings (lenient for migrated lessons)
        standardization = {
            "is_standardized": False,
            "allow_customization": True,
            "customization_level": "full",
            "approval_required": False,
            "master_version": "1.0",
            "last_standardized_at": None,
            "last_standardized_by": None
        }
        
        # Prepare lesson updates
        lesson_updates = {
            "ownership": ownership,
            "target_scope": target_scope,
            "teacher_assignments": [],  # Will be populated by assignment system
            "standardization": standardization,
            
            # Migration metadata
            "migration_metadata": {
                "migrated_at": datetime.utcnow(),
                "migrated_from": "teacher_owned",
                "original_teacher_id": teacher_id,
                "migration_version": "1.0"
            },
            
            # Keep legacy fields for backward compatibility
            "teacher_id": teacher_id,  # Keep as deprecated field
            "class_id": lesson_doc.get("class_id"),  # Keep as deprecated field
            
            "updated_at": datetime.utcnow()
        }
        
        return {
            "lesson_updates": lesson_updates,
            "class_ids": class_ids,
            "target_scope": target_scope
        }
    
    async def _log_migration(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: str,
        migration_data: Dict[str, Any]
    ):
        """Log migration details for audit trail"""
        
        log_entry = {
            "lesson_id": ObjectId(lesson_id),
            "migration_type": "teacher_owned_to_independent",
            "original_teacher_id": ObjectId(teacher_id),
            "migrated_at": datetime.utcnow(),
            "migration_data": migration_data,
            "status": "completed"
        }
        
        await db["lesson_migration_logs"].insert_one(log_entry)
    
    async def migrate_lessons_by_subject(
        self,
        db: AsyncIOMotorDatabase,
        subject_id: str,
        academic_period_id: Optional[str] = None,
        dry_run: bool = False
    ) -> MigrationStats:
        """Migrate lessons for specific subject"""
        
        query = {
            "subject_id": ObjectId(subject_id),
            "teacher_id": {"$exists": True, "$ne": None},
            "$or": [
                {"ownership": {"$exists": False}},
                {"teacher_assignments": {"$exists": False}},
                {"teacher_assignments": {"$size": 0}}
            ]
        }
        
        if academic_period_id:
            query["academic_period_id"] = ObjectId(academic_period_id)
        
        return await self._migrate_lessons_with_query(db, query, dry_run)
    
    async def migrate_lessons_by_teacher(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        academic_period_id: Optional[str] = None,
        dry_run: bool = False
    ) -> MigrationStats:
        """Migrate lessons for specific teacher"""
        
        query = {
            "teacher_id": ObjectId(teacher_id),
            "$or": [
                {"ownership": {"$exists": False}},
                {"teacher_assignments": {"$exists": False}},
                {"teacher_assignments": {"$size": 0}}
            ]
        }
        
        if academic_period_id:
            query["academic_period_id"] = ObjectId(academic_period_id)
        
        return await self._migrate_lessons_with_query(db, query, dry_run)
    
    async def _migrate_lessons_with_query(
        self,
        db: AsyncIOMotorDatabase,
        query: Dict[str, Any],
        dry_run: bool = False
    ) -> MigrationStats:
        """Helper method to migrate lessons matching query"""
        
        stats = MigrationStats()
        
        # Get lessons to migrate
        lessons = await db["lessons"].find(query).to_list(None)
        stats.total_lessons = len(lessons)
        
        logger.info(f"Migrating {stats.total_lessons} lessons with query: {query}")
        
        for lesson_doc in lessons:
            try:
                if dry_run:
                    await self._validate_lesson_migration(db, lesson_doc)
                    stats.migrated_lessons += 1
                else:
                    result = await self._migrate_single_lesson(db, lesson_doc)
                    if result["success"]:
                        stats.migrated_lessons += 1
                        if result.get("teacher_assignments_created"):
                            stats.teacher_assignments_created += result["teacher_assignments_created"]
                    else:
                        stats.failed_lessons += 1
                        stats.errors.append({
                            "lesson_id": str(lesson_doc["_id"]),
                            "lesson_title": lesson_doc.get("title", "Unknown"),
                            "error": result.get("error", "Unknown error")
                        })
                        
            except Exception as e:
                stats.failed_lessons += 1
                stats.errors.append({
                    "lesson_id": str(lesson_doc["_id"]),
                    "lesson_title": lesson_doc.get("title", "Unknown"),
                    "error": str(e)
                })
                logger.error(f"Failed to migrate lesson {lesson_doc['_id']}: {str(e)}")
        
        return stats
    
    async def rollback_migration(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str
    ) -> Dict[str, Any]:
        """Rollback a migrated lesson to teacher-owned structure"""
        
        try:
            # Get lesson
            lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
            if not lesson_doc:
                return {"success": False, "error": "Lesson not found"}
            
            # Check if lesson was migrated
            if not lesson_doc.get("migration_metadata"):
                return {"success": False, "error": "Lesson was not migrated"}
            
            migration_metadata = lesson_doc["migration_metadata"]
            original_teacher_id = migration_metadata.get("original_teacher_id")
            
            if not original_teacher_id:
                return {"success": False, "error": "Original teacher ID not found in migration metadata"}
            
            # Remove independent lesson structure
            updates = {
                "$unset": {
                    "ownership": 1,
                    "target_scope": 1,
                    "teacher_assignments": 1,
                    "standardization": 1,
                    "migration_metadata": 1
                },
                "$set": {
                    "teacher_id": ObjectId(original_teacher_id),
                    "updated_at": datetime.utcnow()
                }
            }
            
            await db["lessons"].update_one({"_id": ObjectId(lesson_id)}, updates)
            
            # Log rollback
            await db["lesson_migration_logs"].insert_one({
                "lesson_id": ObjectId(lesson_id),
                "migration_type": "rollback_to_teacher_owned",
                "original_teacher_id": ObjectId(original_teacher_id),
                "rolled_back_at": datetime.utcnow(),
                "status": "completed"
            })
            
            return {"success": True, "lesson_id": lesson_id}
            
        except Exception as e:
            logger.error(f"Error rolling back lesson {lesson_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_migration_status(
        self,
        db: AsyncIOMotorDatabase,
        academic_period_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get migration status overview"""
        
        query = {}
        if academic_period_id:
            query["academic_period_id"] = ObjectId(academic_period_id)
        
        # Count lessons by migration status
        total_lessons = await db["lessons"].count_documents(query)
        
        migrated_query = query.copy()
        migrated_query["migration_metadata"] = {"$exists": True}
        migrated_lessons = await db["lessons"].count_documents(migrated_query)
        
        teacher_owned_query = query.copy()
        teacher_owned_query.update({
            "teacher_id": {"$exists": True, "$ne": None},
            "migration_metadata": {"$exists": False}
        })
        teacher_owned_lessons = await db["lessons"].count_documents(teacher_owned_query)
        
        # Get migration logs summary
        log_pipeline = [
            {"$match": {"migration_type": {"$in": ["teacher_owned_to_independent", "rollback_to_teacher_owned"]}}},
            {"$group": {
                "_id": "$migration_type",
                "count": {"$sum": 1},
                "latest": {"$max": "$migrated_at"}
            }}
        ]
        
        log_stats = await db["lesson_migration_logs"].aggregate(log_pipeline).to_list(None)
        
        return {
            "total_lessons": total_lessons,
            "migrated_lessons": migrated_lessons,
            "teacher_owned_lessons": teacher_owned_lessons,
            "migration_percentage": (migrated_lessons / total_lessons * 100) if total_lessons > 0 else 0,
            "migration_logs": {stat["_id"]: {"count": stat["count"], "latest": stat["latest"]} for stat in log_stats}
        }


# Utility functions for CLI or admin interface
async def run_migration_command(
    db: AsyncIOMotorDatabase,
    command: str,
    **kwargs
) -> MigrationStats:
    """Run migration command from CLI or admin interface"""
    
    manager = LessonMigrationManager()
    
    if command == "migrate_all":
        return await manager.migrate_all_lessons(db, **kwargs)
    elif command == "migrate_subject":
        return await manager.migrate_lessons_by_subject(db, **kwargs)
    elif command == "migrate_teacher":
        return await manager.migrate_lessons_by_teacher(db, **kwargs)
    else:
        raise ValueError(f"Unknown migration command: {command}")


async def check_migration_prerequisites(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Check if system is ready for migration"""
    
    checks = {
        "coordination_assignments_exist": False,
        "teaching_assignments_exist": False,
        "users_have_roles": False,
        "subjects_exist": False,
        "academic_periods_exist": False,
        "errors": []
    }
    
    try:
        # Check coordination assignments
        coordination_count = await db["coordination_assignments"].count_documents({})
        checks["coordination_assignments_exist"] = coordination_count > 0
        
        # Check teaching assignments
        teaching_count = await db["teaching_assignments"].count_documents({})
        checks["teaching_assignments_exist"] = teaching_count > 0
        
        # Check users have proper roles
        users_with_roles = await db["users"].count_documents({"role": {"$in": ["teacher", "admin", "coordinator"]}})
        checks["users_have_roles"] = users_with_roles > 0
        
        # Check subjects exist
        subjects_count = await db["subjects"].count_documents({})
        checks["subjects_exist"] = subjects_count > 0
        
        # Check academic periods exist
        periods_count = await db["academic_periods"].count_documents({})
        checks["academic_periods_exist"] = periods_count > 0
        
        checks["ready_for_migration"] = all([
            checks["users_have_roles"],
            checks["subjects_exist"],
            checks["academic_periods_exist"]
        ])
        
    except Exception as e:
        checks["errors"].append(str(e))
        checks["ready_for_migration"] = False
    
    return checks