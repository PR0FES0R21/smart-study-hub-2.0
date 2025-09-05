# ==============================================================================
# File: app/tasks/exam_analytics_tasks.py
# Deskripsi: Background tasks untuk Exam Analytics cache warming
# ==============================================================================
import asyncio
import logging
from celery import Celery
from app.api.v1.deps import get_database
from app.crud.exam_analytics import exam_analytics_crud

logger = logging.getLogger(__name__)

# Initialize Celery (adjust based on your celery setup)
try:
    from app.core.celery_app import celery_app
except ImportError:
    # Fallback if celery not properly configured
    logger.warning("Celery app not found, creating fallback instance")
    celery_app = Celery("exam_analytics_tasks")
    celery_app.conf.update(task_always_eager=True)  # Run tasks synchronously in development

@celery_app.task(bind=True, max_retries=3)
def warm_exam_analytics_cache(self, exam_id: str, force_regenerate: bool = True):
    """
    Background task to warm analytics cache for all sessions in an exam.
    
    Args:
        exam_id: The exam ID to warm cache for
        force_regenerate: Whether to force regenerate analytics
    """
    try:
        # Validate exam_id format
        if not exam_id or len(exam_id) < 10:  # Basic ObjectId validation
            logger.error(f"Invalid exam_id format: {exam_id}")
            return
            
        asyncio.run(_warm_exam_analytics_cache_async(exam_id, force_regenerate))
        logger.info(f"Successfully warmed analytics cache for exam {exam_id}")
    except Exception as exc:
        logger.error(f"Error warming analytics cache for exam {exam_id}: {exc}")
        # Retry with exponential backoff
        if hasattr(self, 'request') and self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        else:
            logger.error(f"Failed to warm analytics cache for exam {exam_id} after {getattr(self, 'max_retries', 3)} retries")

async def _warm_exam_analytics_cache_async(exam_id: str, force_regenerate: bool = True):
    """
    Async implementation of cache warming for exam analytics.
    
    This will:
    1. Get all submitted/graded sessions for the exam
    2. Generate analytics for each session (in background)
    3. Cache the results for faster access
    """
    db = get_database()
    
    try:
        # Get all submitted/graded sessions for this exam
        exam_sessions = await db.exam_sessions.find({
            "exam_id": {"$eq": exam_id}, 
            "status": {"$in": ["submitted", "graded"]}
        }, {"_id": 1}).to_list(length=None)
        
        if not exam_sessions:
            logger.info(f"No submitted sessions found for exam {exam_id} - skipping cache warming")
            return
        
        logger.info(f"Warming analytics cache for {len(exam_sessions)} sessions in exam {exam_id}")
        
        # Generate analytics for each session
        successful_generations = 0
        failed_generations = 0
        
        for session in exam_sessions:
            session_id = str(session["_id"])
            try:
                # Generate analytics (will be cached automatically)
                await exam_analytics_crud.generate_exam_analytics(
                    exam_session_id=session_id,
                    force_regenerate=force_regenerate
                )
                successful_generations += 1
                logger.debug(f"Generated analytics for session {session_id}")
                
            except Exception as e:
                failed_generations += 1
                logger.warning(f"Failed to generate analytics for session {session_id}: {e}")
                # Continue with other sessions even if one fails
                continue
        
        logger.info(f"Cache warming completed for exam {exam_id}: {successful_generations} successful, {failed_generations} failed")
        
    except Exception as e:
        logger.error(f"Error in cache warming for exam {exam_id}: {e}")
        raise

@celery_app.task(bind=True, max_retries=2)  
def invalidate_and_warm_exam_analytics(self, exam_id: str):
    """
    Task to invalidate and then warm analytics cache for an exam.
    
    This is called after a student submits an exam to ensure
    all other students get updated analytics data.
    """
    try:
        # Validate exam_id format
        if not exam_id or len(exam_id) < 10:  # Basic ObjectId validation
            logger.error(f"Invalid exam_id format: {exam_id}")
            return
            
        asyncio.run(_invalidate_and_warm_async(exam_id))
    except Exception as exc:
        logger.error(f"Error in invalidate_and_warm for exam {exam_id}: {exc}")
        if hasattr(self, 'request') and self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries), exc=exc)

async def _invalidate_and_warm_async(exam_id: str):
    """Async implementation of invalidate and warm"""
    try:
        # Step 1: Invalidate existing cache
        invalidated_count = await exam_analytics_crud.invalidate_exam_analytics_cache(exam_id)
        logger.info(f"Invalidated {invalidated_count} analytics cache entries for exam {exam_id}")
        
        # Step 2: Warm the cache with fresh data
        await _warm_exam_analytics_cache_async(exam_id, force_regenerate=True)
        
    except Exception as e:
        logger.error(f"Error in invalidate_and_warm_async for exam {exam_id}: {e}")
        raise
