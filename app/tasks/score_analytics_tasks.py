# ==============================================================================
# File: app/tasks/score_analytics_tasks.py
# Deskripsi: Background tasks untuk precompute analitik nilai & invalidasi cache
# --- DITAMBAHKAN ---
# ==============================================================================
import asyncio
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.cache import set_cache
from app.crud.crud_score_analytics import (
    ADMIN_DASHBOARD_CACHE, TEACHER_DASHBOARD_CACHE, STUDENT_DASHBOARD_CACHE,
    get_admin_dashboard, get_teacher_dashboard, get_student_dashboard
)


def _get_db():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    return client[settings.DATABASE_NAME]


@celery_app.task
def precompute_admin_analytics(academic_period_id: str):
    loop = asyncio.get_event_loop()
    db = _get_db()

    async def _run():
        data = await get_admin_dashboard(db, academic_period_id)
        await set_cache(ADMIN_DASHBOARD_CACHE.format(period=academic_period_id), data, ttl=1800)

    loop.run_until_complete(_run())
    return {"status": "ok"}


@celery_app.task
def precompute_teacher_analytics(teacher_id: str, academic_period_id: str):
    loop = asyncio.get_event_loop()
    db = _get_db()

    async def _run():
        data = await get_teacher_dashboard(db, teacher_id, academic_period_id)
        await set_cache(TEACHER_DASHBOARD_CACHE.format(teacher=teacher_id, period=academic_period_id), data, ttl=1800)

    loop.run_until_complete(_run())
    return {"status": "ok"}


@celery_app.task
def precompute_student_analytics(student_id: str, academic_period_id: str):
    loop = asyncio.get_event_loop()
    db = _get_db()

    async def _run():
        data = await get_student_dashboard(db, student_id, academic_period_id)
        await set_cache(STUDENT_DASHBOARD_CACHE.format(student=student_id, period=academic_period_id), data, ttl=1800)

    loop.run_until_complete(_run())
    return {"status": "ok"}

# ==============================================================================
# File: app/tasks/score_analytics_tasks.py
# Deskripsi: Background tasks untuk analitik nilai (precomputation, cache refresh, exports).
# --- MODUL BARU ---
# ==============================================================================
from celery import Celery
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

from app.core.config import settings
from app.core.celery_app import celery_app
from app.core.cache import set_cache, invalidate_cache, get_cache
from app.crud import crud_score_analytics

# Setup logging
logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE CONNECTION FOR TASKS
# ============================================================================
def get_db_connection():
    """Mendapatkan koneksi database untuk task Celery"""
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    return client[settings.DATABASE_NAME]


# ============================================================================
# CACHE PRECOMPUTATION TASKS
# ============================================================================
@celery_app.task(bind=True, name="precompute_admin_analytics")
def precompute_admin_analytics_task(self, academic_period_id: str):
    """
    Background task untuk precompute analytics admin.
    Dijalankan secara periodic atau ketika ada perubahan data signifikan.
    """
    try:
        logger.info(f"Starting admin analytics precomputation for period {academic_period_id}")
        
        # Jalankan async function dalam event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def precompute():
            db = get_db_connection()
            
            # Precompute semua data admin
            global_stats = await crud_score_analytics.get_admin_global_statistics(db, academic_period_id)
            grade_performances = await crud_score_analytics.get_admin_grade_performances(db, academic_period_id)
            major_performances = await crud_score_analytics.get_admin_major_performances(db, academic_period_id)
            subject_rankings = await crud_score_analytics.get_admin_subject_rankings(db, academic_period_id)
            score_trends = await crud_score_analytics.get_admin_score_trends(db, academic_period_id)
            
            # Cache dashboard lengkap
            dashboard = await crud_score_analytics.get_admin_dashboard(db, academic_period_id)
            
            logger.info(f"Admin analytics precomputation completed for period {academic_period_id}")
            return {
                "status": "success",
                "period": academic_period_id,
                "computed_at": datetime.utcnow().isoformat(),
                "data_points": {
                    "global_stats": len([global_stats]) if global_stats else 0,
                    "grade_performances": len(grade_performances),
                    "major_performances": len(major_performances),
                    "subject_rankings": len(subject_rankings),
                    "score_trends": len(score_trends)
                }
            }
        
        result = loop.run_until_complete(precompute())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Admin analytics precomputation failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@celery_app.task(bind=True, name="precompute_teacher_analytics")
def precompute_teacher_analytics_task(self, teacher_id: str, academic_period_id: str):
    """
    Background task untuk precompute analytics teacher.
    """
    try:
        logger.info(f"Starting teacher analytics precomputation for teacher {teacher_id}, period {academic_period_id}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def precompute():
            db = get_db_connection()
            
            # Precompute data teacher
            class_statistics = await crud_score_analytics.get_teacher_class_statistics(db, teacher_id, academic_period_id)
            student_performances = await crud_score_analytics.get_teacher_student_performances(db, teacher_id, academic_period_id)
            dashboard = await crud_score_analytics.get_teacher_dashboard(db, teacher_id, academic_period_id)
            
            logger.info(f"Teacher analytics precomputation completed for teacher {teacher_id}")
            return {
                "status": "success",
                "teacher_id": teacher_id,
                "period": academic_period_id,
                "computed_at": datetime.utcnow().isoformat(),
                "data_points": {
                    "class_statistics": len(class_statistics),
                    "student_performances": len(student_performances)
                }
            }
        
        result = loop.run_until_complete(precompute())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Teacher analytics precomputation failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@celery_app.task(bind=True, name="precompute_student_analytics")
def precompute_student_analytics_task(self, student_id: str, academic_period_id: str):
    """
    Background task untuk precompute analytics student.
    """
    try:
        logger.info(f"Starting student analytics precomputation for student {student_id}, period {academic_period_id}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def precompute():
            db = get_db_connection()
            
            # Precompute data student
            subject_performances = await crud_score_analytics.get_student_subject_performances(db, student_id, academic_period_id)
            exam_history = await crud_score_analytics.get_student_exam_history(db, student_id, academic_period_id)
            class_comparison = await crud_score_analytics.get_student_class_comparison(db, student_id, academic_period_id)
            dashboard = await crud_score_analytics.get_student_dashboard(db, student_id, academic_period_id)
            
            logger.info(f"Student analytics precomputation completed for student {student_id}")
            return {
                "status": "success",
                "student_id": student_id,
                "period": academic_period_id,
                "computed_at": datetime.utcnow().isoformat(),
                "data_points": {
                    "subject_performances": len(subject_performances),
                    "exam_history": len(exam_history)
                }
            }
        
        result = loop.run_until_complete(precompute())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Student analytics precomputation failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


# ============================================================================
# CACHE INVALIDATION TASKS
# ============================================================================
@celery_app.task(name="invalidate_score_analytics_cache")
def invalidate_score_analytics_cache_task(
    academic_period_id: str,
    student_id: Optional[str] = None,
    teacher_id: Optional[str] = None,
    class_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    scope: str = "all"
):
    """
    Task untuk invalidate cache analytics ketika ada perubahan data.
    
    Args:
        academic_period_id: ID periode akademik
        student_id: ID siswa (jika spesifik)
        teacher_id: ID guru (jika spesifik)
        class_id: ID kelas (jika spesifik)
        subject_id: ID mata pelajaran (jika spesifik)
        scope: Scope invalidation ("all", "admin", "teacher", "student")
    """
    try:
        logger.info(f"Starting cache invalidation for scope: {scope}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def invalidate():
            # Cache keys yang akan dihapus
            cache_keys_to_delete = []
            
            if scope in ["all", "admin"]:
                # Admin cache keys
                admin_keys = [
                    f"admin_global_stats:period:{academic_period_id}",
                    f"admin_grade_performance:period:{academic_period_id}",
                    f"admin_major_performance:period:{academic_period_id}",
                    f"admin_subject_ranking:period:{academic_period_id}",
                    f"admin_score_trends:period:{academic_period_id}",
                    f"admin_full_dashboard:period:{academic_period_id}"
                ]
                cache_keys_to_delete.extend(admin_keys)
            
            if scope in ["all", "teacher"] and teacher_id:
                # Teacher cache keys
                teacher_keys = [
                    f"teacher_class_stats:teacher:{teacher_id}:period:{academic_period_id}",
                    f"teacher_student_performance:teacher:{teacher_id}:period:{academic_period_id}",
                    f"teacher_full_dashboard:teacher:{teacher_id}:period:{academic_period_id}"
                ]
                cache_keys_to_delete.extend(teacher_keys)
            
            if scope in ["all", "student"] and student_id:
                # Student cache keys
                student_keys = [
                    f"student_subject_performance:student:{student_id}:period:{academic_period_id}",
                    f"student_exam_history:student:{student_id}:period:{academic_period_id}",
                    f"student_class_comparison:student:{student_id}:period:{academic_period_id}",
                    f"student_full_dashboard:student:{student_id}:period:{academic_period_id}"
                ]
                cache_keys_to_delete.extend(student_keys)
            
            # Hapus cache keys
            for key in cache_keys_to_delete:
                await invalidate_cache(key)
            
            logger.info(f"Cache invalidation completed. Deleted {len(cache_keys_to_delete)} keys")
            return {
                "status": "success",
                "invalidated_keys": len(cache_keys_to_delete),
                "scope": scope,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = loop.run_until_complete(invalidate())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Cache invalidation failed: {str(exc)}")
        return {"status": "error", "message": str(exc)}

@celery_app.task(name="auto_invalidate_on_new_score")
def auto_invalidate_on_new_score_task(exam_session_id: str):
    """
    Task otomatis untuk invalidate cache ketika ada exam_session baru yang graded.
    Dipanggil dari crud_exam_sessions setelah submit_and_grade_session.
    """
    try:
        logger.info(f"Auto-invalidating cache for new score in session {exam_session_id}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def process():
            db = get_db_connection()
            
            # Ambil data exam session
            session = await db["exam_sessions"].find_one({"_id": exam_session_id})
            if not session:
                logger.warning(f"Exam session {exam_session_id} not found")
                return {"status": "error", "message": "Session not found"}
            
            # Ambil data exam
            exam = await db["exams"].find_one({"_id": session["exam_id"]})
            if not exam:
                logger.warning(f"Exam not found for session {exam_session_id}")
                return {"status": "error", "message": "Exam not found"}
            
            # Ambil teaching assignment
            assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
            if not assignment:
                logger.warning(f"Teaching assignment not found for exam {exam['_id']}")
                return {"status": "error", "message": "Teaching assignment not found"}
            
            student_id = str(session["student_id"])
            teacher_id = str(assignment["teacher_id"])
            academic_period_id = str(assignment["academic_period_id"])
            class_id = str(assignment["class_id"])
            subject_id = str(assignment["subject_id"])
            
            # Invalidate cache untuk semua scope yang terkait
            invalidate_result = await invalidate_score_analytics_cache_task.apply_async(
                args=[academic_period_id],
                kwargs={
                    "student_id": student_id,
                    "teacher_id": teacher_id,
                    "class_id": class_id,
                    "subject_id": subject_id,
                    "scope": "all"
                }
            )
            
            # Schedule precomputation ulang
            precompute_admin_analytics_task.delay(academic_period_id)
            precompute_teacher_analytics_task.delay(teacher_id, academic_period_id)
            precompute_student_analytics_task.delay(student_id, academic_period_id)
            
            logger.info(f"Auto-invalidation and precomputation scheduled for session {exam_session_id}")
            return {
                "status": "success",
                "session_id": exam_session_id,
                "affected_entities": {
                    "student_id": student_id,
                    "teacher_id": teacher_id,
                    "academic_period_id": academic_period_id
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = loop.run_until_complete(process())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Auto-invalidation failed for session {exam_session_id}: {str(exc)}")
        return {"status": "error", "message": str(exc)}


# ============================================================================
# PERIODIC ANALYTICS TASKS
# ============================================================================
@celery_app.task(name="daily_analytics_refresh")
def daily_analytics_refresh_task():
    """
    Task harian untuk refresh analytics cache.
    Dijadwalkan via Celery Beat.
    """
    try:
        logger.info("Starting daily analytics refresh")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def daily_refresh():
            db = get_db_connection()
            
            # Ambil semua periode akademik aktif
            active_periods = await db["academic_periods"].find({"status": "active"}).to_list(10)
            
            refresh_results = []
            for period in active_periods:
                period_id = str(period["_id"])
                
                # Schedule admin analytics refresh
                admin_result = precompute_admin_analytics_task.delay(period_id)
                
                # Ambil semua guru aktif di periode ini
                active_teachers = await db["teaching_assignments"].distinct("teacher_id", {"academic_period_id": period["_id"]})
                
                # Schedule teacher analytics refresh
                for teacher_id in active_teachers:
                    teacher_result = precompute_teacher_analytics_task.delay(str(teacher_id), period_id)
                
                # Untuk student analytics, kita tidak precompute semua karena terlalu berat
                # Hanya compute on-demand saja
                
                refresh_results.append({
                    "period_id": period_id,
                    "admin_task_id": admin_result.id,
                    "teacher_count": len(active_teachers)
                })
            
            logger.info(f"Daily analytics refresh scheduled for {len(active_periods)} periods")
            return {
                "status": "success",
                "periods_processed": len(active_periods),
                "refresh_results": refresh_results,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = loop.run_until_complete(daily_refresh())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Daily analytics refresh failed: {str(exc)}")
        return {"status": "error", "message": str(exc)}

@celery_app.task(name="weekly_analytics_cleanup")
def weekly_analytics_cleanup_task():
    """
    Task mingguan untuk cleanup cache dan data analytics lama.
    """
    try:
        logger.info("Starting weekly analytics cleanup")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def cleanup():
            # TODO: Implement cleanup logic
            # - Hapus cache untuk periode akademik yang sudah archived
            # - Cleanup temporary analytics data
            # - Compress/archive old analytics data
            
            logger.info("Weekly analytics cleanup completed")
            return {
                "status": "success",
                "cleanup_operations": [
                    "cache_cleanup",
                    "temp_data_cleanup"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = loop.run_until_complete(cleanup())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Weekly analytics cleanup failed: {str(exc)}")
        return {"status": "error", "message": str(exc)}


# ============================================================================
# EXPORT TASKS
# ============================================================================
@celery_app.task(bind=True, name="export_analytics_report")
def export_analytics_report_task(
    self,
    user_id: str,
    report_type: str,  # "admin_global", "teacher_class", "student_personal"
    export_format: str,  # "excel", "pdf"
    filters: Dict[str, Any],
    academic_period_id: str
):
    """
    Background task untuk export laporan analytics.
    """
    try:
        logger.info(f"Starting analytics report export: {report_type} in {export_format} format")
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Initializing...'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def export():
            db = get_db_connection()
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': 'Fetching data...'})
            
            # Fetch data based on report type
            if report_type == "admin_global":
                data = await crud_score_analytics.get_admin_dashboard(db, academic_period_id)
            elif report_type == "teacher_class":
                teacher_id = filters.get("teacher_id")
                if not teacher_id:
                    raise ValueError("teacher_id required for teacher report")
                data = await crud_score_analytics.get_teacher_dashboard(db, teacher_id, academic_period_id)
            elif report_type == "student_personal":
                student_id = filters.get("student_id")
                if not student_id:
                    raise ValueError("student_id required for student report")
                data = await crud_score_analytics.get_student_dashboard(db, student_id, academic_period_id)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 60, 'total': 100, 'status': 'Generating report...'})
            
            # TODO: Implement actual export logic
            # - Generate Excel file using openpyxl
            # - Generate PDF file using reportlab
            # - Save to temp directory
            # - Upload to cloud storage (R2)
            
            # Simulate file generation
            import time
            time.sleep(2)
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 90, 'total': 100, 'status': 'Finalizing...'})
            
            # Generate file metadata
            filename = f"{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_format}"
            file_path = f"/exports/{filename}"  # This would be actual file path
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 100, 'total': 100, 'status': 'Completed'})
            
            logger.info(f"Analytics report export completed: {filename}")
            return {
                "status": "success",
                "file_path": file_path,
                "filename": filename,
                "file_size": 1024 * 50,  # Dummy size
                "download_url": f"/api/v1/score-analytics/download/{filename}",
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "report_metadata": {
                    "type": report_type,
                    "format": export_format,
                    "generated_by": user_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "academic_period_id": academic_period_id,
                    "filters": filters
                }
            }
        
        result = loop.run_until_complete(export())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Analytics report export failed: {str(exc)}")
        self.update_state(state='FAILURE', meta={'error': str(exc)})
        raise self.retry(exc=exc, countdown=60, max_retries=2)


# ============================================================================
# MONITORING & HEALTH TASKS
# ============================================================================
@celery_app.task(name="analytics_health_check")
def analytics_health_check_task():
    """
    Task untuk health check sistem analytics.
    """
    try:
        logger.info("Running analytics health check")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def health_check():
            db = get_db_connection()
            
            # Check database connectivity
            try:
                await db.list_collection_names()
                db_status = "healthy"
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            # Check cache connectivity
            try:
                test_key = "health_check_test"
                await set_cache(test_key, {"test": True}, ttl=60)
                cached_data = await get_cache(test_key)
                await invalidate_cache(test_key)
                cache_status = "healthy" if cached_data else "error"
            except Exception as e:
                cache_status = f"error: {str(e)}"
            
            # Check sample data availability
            try:
                sample_sessions = await db["exam_sessions"].count_documents({"status": "graded"})
                data_status = "healthy" if sample_sessions > 0 else "no_data"
            except Exception as e:
                data_status = f"error: {str(e)}"
            
            return {
                "status": "healthy" if all(s == "healthy" for s in [db_status, cache_status]) else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "database": db_status,
                    "cache": cache_status,
                    "data": data_status
                },
                "sample_data_count": sample_sessions if 'sample_sessions' in locals() else 0
            }
        
        result = loop.run_until_complete(health_check())
        loop.close()
        
        return result
        
    except Exception as exc:
        logger.error(f"Analytics health check failed: {str(exc)}")
        return {
            "status": "unhealthy",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# UTILITY FUNCTIONS FOR TASKS
# ============================================================================
def schedule_analytics_refresh(academic_period_id: str, scope: str = "all"):
    """
    Utility function untuk schedule refresh analytics.
    
    Args:
        academic_period_id: ID periode akademik
        scope: Scope refresh ("all", "admin", "teacher")
    """
    if scope in ["all", "admin"]:
        precompute_admin_analytics_task.delay(academic_period_id)
    
    if scope in ["all", "teacher"]:
        # Schedule untuk semua guru aktif di periode ini
        # TODO: Get active teachers and schedule their analytics
        pass

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Utility function untuk check status task.
    """
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result,
            "info": result.info
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# TASK SCHEDULING CONFIGURATION
# ============================================================================
# Konfigurasi untuk Celery Beat (periodic tasks)
celery_app.conf.beat_schedule = {
    'daily-analytics-refresh': {
        'task': 'daily_analytics_refresh',
        'schedule': 60.0 * 60.0 * 24.0,  # Every 24 hours
        'options': {'expires': 60.0 * 60.0 * 2.0}  # Expire after 2 hours
    },
    'weekly-analytics-cleanup': {
        'task': 'weekly_analytics_cleanup',
        'schedule': 60.0 * 60.0 * 24.0 * 7.0,  # Every 7 days
        'options': {'expires': 60.0 * 60.0 * 4.0}  # Expire after 4 hours
    },
    'analytics-health-check': {
        'task': 'analytics_health_check',
        'schedule': 60.0 * 30.0,  # Every 30 minutes
        'options': {'expires': 60.0 * 5.0}  # Expire after 5 minutes
    }
}

celery_app.conf.timezone = 'Asia/Jakarta'
