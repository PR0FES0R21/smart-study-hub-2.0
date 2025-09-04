# ==============================================================================
# File: app/tasks/teacher_analytics_tasks.py
# Deskripsi: Background tasks untuk Teacher Analytics generation
# ==============================================================================
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from bson import ObjectId

from app.api.v1.deps import get_database
from app.crud.crud_teacher_analytics import teacher_analytics_crud
from app.schemas.teacher_analytics import AnalyticsTask

logger = logging.getLogger(__name__)

# Global task storage (in production, gunakan Redis atau database)
_task_storage: Dict[str, AnalyticsTask] = {}


class TeacherAnalyticsTaskManager:
    """Manager untuk background analytics tasks"""
    
    @staticmethod
    def generate_task_id(exam_id: str, teacher_id: ObjectId) -> str:
        """Generate unique task ID"""
        return f"analytics_{exam_id}_{teacher_id}_{int(datetime.utcnow().timestamp())}"
    
    @staticmethod
    async def start_analytics_generation(
        exam_id: str, 
        teacher_id: ObjectId, 
        force_regenerate: bool = False,
        include_comparison: bool = True
    ) -> str:
        """
        Start background analytics generation
        Returns task_id untuk tracking
        """
        # Generate task ID
        task_id = TeacherAnalyticsTaskManager.generate_task_id(exam_id, teacher_id)
        
        # Create task record
        # Convert exam_id to ObjectId if it's a valid ObjectId string
        exam_obj_id = ObjectId(exam_id) if ObjectId.is_valid(exam_id) else exam_id
        
        task = AnalyticsTask(
            task_id=task_id,
            exam_id=exam_obj_id,
            teacher_id=teacher_id,
            status="pending",
            progress=0.0,
            started_at=datetime.utcnow()
        )
        
        # Store task
        _task_storage[task_id] = task
        
        # Start background processing
        asyncio.create_task(
            TeacherAnalyticsTaskManager._process_analytics_generation(
                task_id, exam_id, teacher_id, force_regenerate, include_comparison
            )
        )
        
        logger.info(f"Started analytics generation task {task_id} for exam {exam_id}")
        return task_id
    
    @staticmethod
    async def _process_analytics_generation(
        task_id: str,
        exam_id: str,
        teacher_id: ObjectId,
        force_regenerate: bool,
        include_comparison: bool
    ):
        """
        Background process untuk generate analytics
        """
        try:
            # Update task status to processing
            await TeacherAnalyticsTaskManager.update_task_status(task_id, "processing", 10.0)
            
            # Check if analytics already exists and force_regenerate is False
            if not force_regenerate:
                existing = await teacher_analytics_crud.get_analytics(exam_id, teacher_id)
                if existing and existing.status == "completed":
                    logger.info(f"Analytics already exists for exam {exam_id}, skipping generation")
                    await TeacherAnalyticsTaskManager.update_task_status(task_id, "completed", 100.0)
                    return
            
            # Update progress
            await TeacherAnalyticsTaskManager.update_task_progress(task_id, 25.0)
            
            # Generate analytics (this is the heavy operation)
            logger.info(f"Starting analytics generation for exam {exam_id}")
            
            analytics = await teacher_analytics_crud.generate_exam_analytics(
                exam_id=exam_id,
                teacher_id=teacher_id,
                force_regenerate=force_regenerate,
                include_comparison=include_comparison
            )
            
            # Update progress - generation complete
            await TeacherAnalyticsTaskManager.update_task_progress(task_id, 90.0)
            
            # Final update - completed
            await TeacherAnalyticsTaskManager.update_task_status(task_id, "completed", 100.0)
            
            logger.info(f"Analytics generation completed for exam {exam_id}")
            
        except Exception as e:
            logger.error(f"Error in analytics generation task {task_id}: {str(e)}")
            await TeacherAnalyticsTaskManager.update_task_status(
                task_id, 
                "failed", 
                error_message=str(e)
            )
    
    @staticmethod
    async def update_task_status(
        task_id: str, 
        status: str, 
        progress: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Update task status"""
        if task_id not in _task_storage:
            return
        
        task = _task_storage[task_id]
        task.status = status
        
        if progress is not None:
            task.progress = progress
        
        if error_message:
            task.error_message = error_message
        
        if status in ["completed", "failed"]:
            task.completed_at = datetime.utcnow()
        
        # In production, save to database/Redis
        await TeacherAnalyticsTaskManager._save_task_to_db(task)
    
    @staticmethod
    async def update_task_progress(task_id: str, progress: float):
        """Update task progress"""
        await TeacherAnalyticsTaskManager.update_task_status(task_id, "processing", progress)
    
    @staticmethod
    async def get_task_status(task_id: str) -> Optional[AnalyticsTask]:
        """Get task status"""
        # First check memory
        if task_id in _task_storage:
            return _task_storage[task_id]
        
        # Then check database
        return await TeacherAnalyticsTaskManager._load_task_from_db(task_id)
    
    @staticmethod
    async def _save_task_to_db(task: AnalyticsTask):
        """Save task to database for persistence"""
        try:
            db = get_database()
            task_dict = task.model_dump(mode='python')
            
            await db.analytics_tasks.update_one(
                {"task_id": task.task_id},
                {"$set": task_dict},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving task to database: {str(e)}")
    
    @staticmethod
    async def _load_task_from_db(task_id: str) -> Optional[AnalyticsTask]:
        """Load task from database"""
        try:
            db = get_database()
            result = await db.analytics_tasks.find_one({"task_id": task_id})
            
            if result:
                return AnalyticsTask(**result)
            return None
        except Exception as e:
            logger.error(f"Error loading task from database: {str(e)}")
            return None
    
    @staticmethod
    async def cleanup_old_tasks(days_old: int = 7):
        """Cleanup old completed tasks"""
        try:
            db = get_database()
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Remove from memory
            tasks_to_remove = []
            for task_id, task in _task_storage.items():
                if task.completed_at and task.completed_at < cutoff_date:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del _task_storage[task_id]
            
            # Remove from database
            result = await db.analytics_tasks.delete_many({
                "completed_at": {"$lt": cutoff_date},
                "status": {"$in": ["completed", "failed"]}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old analytics tasks")
            
        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {str(e)}")
    
    @staticmethod
    async def get_teacher_tasks(teacher_id: ObjectId, limit: int = 20) -> list:
        """Get recent tasks for a teacher"""
        try:
            db = get_database()
            cursor = db.analytics_tasks.find(
                {"teacher_id": teacher_id}
            ).sort("started_at", -1).limit(limit)
            
            results = await cursor.to_list(length=limit)
            return [AnalyticsTask(**result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting teacher tasks: {str(e)}")
            return []
    
    @staticmethod
    async def cancel_task(task_id: str, teacher_id: ObjectId) -> bool:
        """Cancel a running task"""
        try:
            task = await TeacherAnalyticsTaskManager.get_task_status(task_id)
            if not task:
                return False
            
            # Verify ownership
            if task.teacher_id != teacher_id:
                return False
            
            # Only cancel if still processing
            if task.status in ["pending", "processing"]:
                await TeacherAnalyticsTaskManager.update_task_status(task_id, "cancelled")
                logger.info(f"Cancelled analytics task {task_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling task: {str(e)}")
            return False


# Convenience functions untuk digunakan di routes
async def generate_teacher_analytics(
    exam_id: str, 
    teacher_id: ObjectId,
    force_regenerate: bool = False,
    include_comparison: bool = True
) -> str:
    """
    Start teacher analytics generation
    Returns task_id
    """
    return await TeacherAnalyticsTaskManager.start_analytics_generation(
        exam_id, teacher_id, force_regenerate, include_comparison
    )

async def get_analytics_task_status(task_id: str) -> Optional[AnalyticsTask]:
    """Get analytics task status"""
    return await TeacherAnalyticsTaskManager.get_task_status(task_id)

async def cancel_analytics_task(task_id: str, teacher_id: ObjectId) -> bool:
    """Cancel analytics task"""
    return await TeacherAnalyticsTaskManager.cancel_task(task_id, teacher_id)

async def get_teacher_analytics_tasks(teacher_id: ObjectId, limit: int = 20) -> list:
    """Get teacher's recent analytics tasks"""
    return await TeacherAnalyticsTaskManager.get_teacher_tasks(teacher_id, limit)
