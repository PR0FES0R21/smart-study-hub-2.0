# ==============================================================================
# File: app/api/v1/routes/lesson_migration.py
# Description: API endpoints for lesson migration management
# ==============================================================================
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_database
from app.core.lesson_migration import (
    LessonMigrationManager, MigrationStats, 
    run_migration_command, check_migration_prerequisites
)
from app.core.security import get_current_user
from app.schemas.user import UserInDB

router = APIRouter()
migration_manager = LessonMigrationManager()


@router.get("/prerequisites")
async def check_migration_readiness(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Check if system is ready for lesson migration"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can check migration prerequisites"
        )
    
    checks = await check_migration_prerequisites(db)
    
    return {
        "migration_readiness": checks,
        "recommendation": "System is ready for migration" if checks["ready_for_migration"] else "Please fix the issues before migrating"
    }


@router.get("/status")
async def get_migration_status(
    academic_period_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current migration status overview"""
    
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view migration status"
        )
    
    status_info = await migration_manager.get_migration_status(db, academic_period_id)
    
    return {
        "migration_status": status_info,
        "academic_period_id": academic_period_id
    }


@router.post("/dry-run")
async def run_migration_dry_run(
    migration_request: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Run migration in dry-run mode to preview results"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can run migration dry-run"
        )
    
    migration_type = migration_request.get("type", "all")
    academic_period_id = migration_request.get("academic_period_id")
    batch_size = migration_request.get("batch_size", 50)
    
    try:
        if migration_type == "all":
            stats = await migration_manager.migrate_all_lessons(
                db=db,
                academic_period_id=academic_period_id,
                dry_run=True,
                batch_size=batch_size
            )
        elif migration_type == "subject":
            subject_id = migration_request.get("subject_id")
            if not subject_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="subject_id is required for subject migration"
                )
            stats = await migration_manager.migrate_lessons_by_subject(
                db=db,
                subject_id=subject_id,
                academic_period_id=academic_period_id,
                dry_run=True
            )
        elif migration_type == "teacher":
            teacher_id = migration_request.get("teacher_id")
            if not teacher_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="teacher_id is required for teacher migration"
                )
            stats = await migration_manager.migrate_lessons_by_teacher(
                db=db,
                teacher_id=teacher_id,
                academic_period_id=academic_period_id,
                dry_run=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid migration type. Must be 'all', 'subject', or 'teacher'"
            )
        
        return {
            "dry_run": True,
            "migration_type": migration_type,
            "preview_results": {
                "total_lessons": stats.total_lessons,
                "would_migrate": stats.migrated_lessons,
                "would_fail": stats.failed_lessons,
                "potential_errors": stats.errors[:10],  # Limit to first 10 errors
                "estimated_teacher_assignments": stats.teacher_assignments_created
            },
            "warnings": [
                "This is a preview only. No actual changes were made.",
                f"Migration would affect {stats.total_lessons} lessons."
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run migration dry-run: {str(e)}"
        )


@router.post("/execute")
async def execute_migration(
    migration_request: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Execute actual lesson migration"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can execute migration"
        )
    
    # Check prerequisites first
    checks = await check_migration_prerequisites(db)
    if not checks["ready_for_migration"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"System not ready for migration. Issues: {checks['errors']}"
        )
    
    migration_type = migration_request.get("type", "all")
    academic_period_id = migration_request.get("academic_period_id")
    batch_size = migration_request.get("batch_size", 50)
    confirm = migration_request.get("confirm", False)
    
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Migration requires explicit confirmation. Set 'confirm': true in request."
        )
    
    try:
        if migration_type == "all":
            stats = await migration_manager.migrate_all_lessons(
                db=db,
                academic_period_id=academic_period_id,
                dry_run=False,
                batch_size=batch_size
            )
        elif migration_type == "subject":
            subject_id = migration_request.get("subject_id")
            if not subject_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="subject_id is required for subject migration"
                )
            stats = await migration_manager.migrate_lessons_by_subject(
                db=db,
                subject_id=subject_id,
                academic_period_id=academic_period_id,
                dry_run=False
            )
        elif migration_type == "teacher":
            teacher_id = migration_request.get("teacher_id")
            if not teacher_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="teacher_id is required for teacher migration"
                )
            stats = await migration_manager.migrate_lessons_by_teacher(
                db=db,
                teacher_id=teacher_id,
                academic_period_id=academic_period_id,
                dry_run=False
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid migration type. Must be 'all', 'subject', or 'teacher'"
            )
        
        success_rate = (stats.migrated_lessons / stats.total_lessons * 100) if stats.total_lessons > 0 else 0
        
        response = {
            "migration_completed": True,
            "migration_type": migration_type,
            "results": {
                "total_lessons": stats.total_lessons,
                "successfully_migrated": stats.migrated_lessons,
                "failed_migrations": stats.failed_lessons,
                "success_rate": round(success_rate, 2),
                "teacher_assignments_created": stats.teacher_assignments_created,
                "coordination_assignments_created": stats.coordination_assignments_created
            },
            "summary": f"Migration completed with {success_rate:.1f}% success rate. {stats.migrated_lessons}/{stats.total_lessons} lessons migrated successfully."
        }
        
        # Include errors if any
        if stats.errors:
            response["errors"] = stats.errors
            response["warnings"] = [
                f"{len(stats.errors)} lessons failed to migrate. Check errors for details."
            ]
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )


@router.post("/rollback/{lesson_id}")
async def rollback_lesson_migration(
    lesson_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Rollback a specific lesson migration"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can rollback migrations"
        )
    
    try:
        result = await migration_manager.rollback_migration(db, lesson_id)
        
        if result["success"]:
            return {
                "rollback_completed": True,
                "lesson_id": lesson_id,
                "message": "Lesson successfully rolled back to teacher-owned structure"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rollback failed: {result['error']}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.get("/logs")
async def get_migration_logs(
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    migration_type: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get migration logs with pagination"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view migration logs"
        )
    
    query = {}
    if migration_type:
        query["migration_type"] = migration_type
    
    # Get logs with pagination
    logs = await db["lesson_migration_logs"].find(query) \
        .sort("migrated_at", -1) \
        .skip(skip) \
        .limit(limit) \
        .to_list(limit)
    
    # Convert ObjectIds to strings for JSON response
    for log in logs:
        log["id"] = str(log["_id"])
        log["lesson_id"] = str(log["lesson_id"])
        if log.get("original_teacher_id"):
            log["original_teacher_id"] = str(log["original_teacher_id"])
    
    # Get total count
    total_count = await db["lesson_migration_logs"].count_documents(query)
    
    return {
        "migration_logs": logs,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "skip": skip,
            "has_more": (skip + len(logs)) < total_count
        }
    }


@router.get("/lessons-needing-migration")
async def get_lessons_needing_migration(
    academic_period_id: Optional[str] = Query(None),
    subject_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get lessons that still need migration"""
    
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Build query for unmigrated lessons
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
    if subject_id:
        query["subject_id"] = ObjectId(subject_id)
    if teacher_id:
        query["teacher_id"] = ObjectId(teacher_id)
    
    # Get lessons
    lessons = await db["lessons"].find(query).limit(limit).to_list(limit)
    
    # Populate with additional info
    result = []
    for lesson in lessons:
        # Get teacher info
        teacher = await db["users"].find_one({"_id": lesson["teacher_id"]})
        
        # Get subject info
        subject = await db["subjects"].find_one({"_id": lesson["subject_id"]})
        
        # Get class info
        class_info = None
        if lesson.get("class_id"):
            class_info = await db["classes"].find_one({"_id": lesson["class_id"]})
        
        result.append({
            "lesson_id": str(lesson["_id"]),
            "title": lesson.get("title"),
            "teacher_name": teacher.get("full_name") if teacher else "Unknown Teacher",
            "subject_name": subject.get("name") if subject else "Unknown Subject",
            "class_name": class_info.get("name") if class_info else "No Class Assigned",
            "created_at": lesson.get("created_at"),
            "status": lesson.get("status", "unknown")
        })
    
    total_needing_migration = await db["lessons"].count_documents(query)
    
    return {
        "lessons_needing_migration": result,
        "total_count": total_needing_migration,
        "showing": len(result),
        "filters": {
            "academic_period_id": academic_period_id,
            "subject_id": subject_id,
            "teacher_id": teacher_id
        }
    }


@router.post("/batch-migrate")
async def batch_migrate_lessons(
    batch_request: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Migrate specific batch of lessons by IDs"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can execute batch migration"
        )
    
    lesson_ids = batch_request.get("lesson_ids", [])
    if not lesson_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_ids array is required"
        )
    
    confirm = batch_request.get("confirm", False)
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch migration requires explicit confirmation"
        )
    
    stats = MigrationStats()
    stats.total_lessons = len(lesson_ids)
    
    for lesson_id in lesson_ids:
        try:
            # Get lesson
            lesson_doc = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
            if not lesson_doc:
                stats.failed_lessons += 1
                stats.errors.append({
                    "lesson_id": lesson_id,
                    "error": "Lesson not found"
                })
                continue
            
            # Migrate lesson
            result = await migration_manager._migrate_single_lesson(db, lesson_doc)
            if result["success"]:
                stats.migrated_lessons += 1
                if result.get("teacher_assignments_created"):
                    stats.teacher_assignments_created += result["teacher_assignments_created"]
            else:
                stats.failed_lessons += 1
                stats.errors.append({
                    "lesson_id": lesson_id,
                    "lesson_title": lesson_doc.get("title", "Unknown"),
                    "error": result.get("error", "Unknown error")
                })
                
        except Exception as e:
            stats.failed_lessons += 1
            stats.errors.append({
                "lesson_id": lesson_id,
                "error": str(e)
            })
    
    success_rate = (stats.migrated_lessons / stats.total_lessons * 100) if stats.total_lessons > 0 else 0
    
    return {
        "batch_migration_completed": True,
        "results": {
            "total_requested": stats.total_lessons,
            "successfully_migrated": stats.migrated_lessons,
            "failed_migrations": stats.failed_lessons,
            "success_rate": round(success_rate, 2),
            "teacher_assignments_created": stats.teacher_assignments_created
        },
        "errors": stats.errors if stats.errors else None
    }