# ==============================================================================
# File: app/api/v1/routes/teacher_analytics.py
# Deskripsi: API Routes untuk Teacher Analytics (Exam-level Analytics)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from bson import ObjectId

from app.api.v1 import deps
from app.schemas.teacher_analytics import (
    ExamAnalytics, AnalyticsRequest, AnalyticsTask, 
    PaginatedAnalyticsResponse, AnalyticsListItem
)
from app.crud.crud_teacher_analytics import teacher_analytics_crud
from app.tasks.teacher_analytics_tasks import (
    generate_teacher_analytics, get_analytics_task_status,
    cancel_analytics_task, get_teacher_analytics_tasks
)

router = APIRouter()


@router.post("/exams/{exam_id}/analytics/generate")
async def generate_exam_analytics(
    exam_id: str,
    request: AnalyticsRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Trigger background analytics generation untuk ujian tertentu.
    Hanya guru pemilik ujian yang bisa mengakses.
    
    Returns:
        - task_id untuk tracking progress
        - status awal task
    """
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")
    
    # Validasi exam ownership
    exam = await db.exams.find_one({"_id": ObjectId(exam_id)})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    assignment = await db.teaching_assignments.find_one({"_id": exam["teaching_assignment_id"]})
    if not assignment or assignment["teacher_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=403, 
            detail="You are not authorized to generate analytics for this exam"
        )
    
    # Check if analytics already exists
    existing_analytics = await teacher_analytics_crud.get_analytics(exam_id, current_user["_id"])
    if existing_analytics and not request.force_regenerate:
        return {
            "message": "Analytics already exists for this exam",
            "status": "completed",
            "analytics_available": True,
            "generated_at": existing_analytics.generated_at,
            "force_regenerate_required": True
        }
    
    # Start background generation
    task_id = await generate_teacher_analytics(
        exam_id=exam_id,
        teacher_id=current_user["_id"],
        force_regenerate=request.force_regenerate,
        include_comparison=request.include_comparison
    )
    
    return {
        "message": "Analytics generation started",
        "task_id": task_id,
        "status": "pending",
        "estimated_time_minutes": 2,  # Rough estimate
        "check_status_endpoint": f"/teacher-analytics/tasks/{task_id}/status"
    }


@router.get("/exams/{exam_id}/analytics", response_model=ExamAnalytics)
async def get_exam_analytics(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Retrieve completed analytics untuk ujian tertentu.
    Akan error jika analytics belum di-generate.
    """
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")
    
    # Get analytics
    analytics = await teacher_analytics_crud.get_analytics(exam_id, current_user["_id"])
    if not analytics:
        raise HTTPException(
            status_code=404, 
            detail="Analytics not found. Please generate analytics first."
        )
    
    if analytics.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Analytics generation is still {analytics.status}. Please wait for completion."
        )
    
    return analytics


@router.delete("/exams/{exam_id}/analytics", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam_analytics(
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Delete analytics untuk ujian tertentu.
    Useful untuk force regeneration atau cleanup.
    """
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")
    
    deleted = await teacher_analytics_crud.delete_analytics(exam_id, current_user["_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Analytics not found")


@router.get("/tasks/{task_id}/status", response_model=AnalyticsTask)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Check status dari background analytics generation task.
    
    Status bisa:
    - pending: Task baru dibuat, belum diproses
    - processing: Sedang generate analytics
    - completed: Selesai, analytics siap digunakan
    - failed: Error, lihat error_message
    - cancelled: Task dibatalkan
    """
    task = await get_analytics_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify ownership
    if task.teacher_id != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this task")
    
    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Cancel running analytics generation task.
    Hanya bisa cancel task yang sedang pending/processing.
    """
    success = await cancel_analytics_task(task_id, current_user["_id"])
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Task not found, already completed, or not cancellable"
        )
    
    return {"message": "Task cancelled successfully"}


@router.get("/tasks", response_model=List[AnalyticsTask])
async def get_my_tasks(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get daftar recent analytics tasks untuk guru yang login.
    Berguna untuk monitoring dan debugging.
    """
    tasks = await get_teacher_analytics_tasks(current_user["_id"], limit)
    return tasks


@router.get("/", response_model=PaginatedAnalyticsResponse)
async def list_analytics(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    List semua ujian milik guru dengan status analytics-nya.
    Menampilkan overview: ujian mana yang sudah ada analytics, 
    mana yang belum, dan basic stats.
    """
    skip = (page - 1) * limit
    
    # Get analytics list
    analytics_list = await teacher_analytics_crud.list_analytics(
        teacher_id=current_user["_id"],
        skip=skip,
        limit=limit
    )
    
    # For pagination, we need total count
    db = deps.get_database()
    
    total_exams = await db.exams.count_documents({
        "teaching_assignment_id": {
            "$in": await _get_teacher_assignment_ids(db, current_user["_id"])
        }
    })
    
    total_pages = (total_exams + limit - 1) // limit
    
    return PaginatedAnalyticsResponse(
        total_items=total_exams,
        total_pages=total_pages,
        current_page=page,
        limit=limit,
        data=analytics_list
    )


@router.get("/dashboard")
async def get_analytics_dashboard(
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Get dashboard overview untuk teacher analytics.
    Menampilkan summary statistics untuk guru.
    
    Returns:
    - Total exams yang dimiliki
    - Berapa yang sudah ada analytics
    - Recent activity
    - Quick stats
    """
    db = deps.get_database()
    teacher_id = current_user["_id"]
    
    # Get teacher's assignment IDs
    assignment_ids = await _get_teacher_assignment_ids(db, teacher_id)
    
    # Total exams
    total_exams = await db.exams.count_documents({
        "teaching_assignment_id": {"$in": assignment_ids}
    })
    
    # Exams with analytics
    analytics_count = await db.teacher_analytics.count_documents({
        "exam_metadata.exam_id": {
            "$in": await _get_teacher_exam_ids(db, assignment_ids)
        }
    })
    
    # Recent tasks
    recent_tasks = await get_teacher_analytics_tasks(teacher_id, 5)
    
    # Basic stats from recent analytics
    recent_analytics = await db.teacher_analytics.find({
        "exam_metadata.exam_id": {
            "$in": await _get_teacher_exam_ids(db, assignment_ids)
        }
    }).sort("generated_at", -1).limit(10).to_list(10)
    
    # Calculate average class performance
    avg_class_performance = 0
    total_students_taught = 0
    
    if recent_analytics:
        for analytics in recent_analytics:
            class_stats = analytics.get("class_statistics", {})
            avg_class_performance += class_stats.get("class_average", 0)
            total_students_taught += class_stats.get("total_students", 0)
        
        avg_class_performance /= len(recent_analytics)
    
    return {
        "total_exams": total_exams,
        "exams_with_analytics": analytics_count,
        "analytics_coverage": (analytics_count / total_exams * 100) if total_exams > 0 else 0,
        "total_students_taught": total_students_taught,
        "average_class_performance": round(avg_class_performance, 1),
        "recent_tasks": recent_tasks,
        "pending_tasks": len([t for t in recent_tasks if t.status == "processing"]),
        "failed_tasks": len([t for t in recent_tasks if t.status == "failed"])
    }


@router.get("/export/{exam_id}")
async def export_analytics(
    exam_id: str,
    format: str = Query("json", regex="^(json|csv|excel)$"),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Export analytics data dalam berbagai format.
    
    Supported formats:
    - json: Complete analytics data
    - csv: Student performance data only  
    - excel: Comprehensive report (future enhancement)
    """
    if not ObjectId.is_valid(exam_id):
        raise HTTPException(status_code=400, detail="Invalid exam ID")
    
    # Get analytics
    analytics = await teacher_analytics_crud.get_analytics(exam_id, current_user["_id"])
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found")
    
    if format == "json":
        # Return full analytics as JSON
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=analytics.model_dump(mode='json'),
            headers={
                "Content-Disposition": f"attachment; filename=analytics_{exam_id}.json"
            }
        )
    
    elif format == "csv":
        # Return student performance as CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV Headers
        writer.writerow([
            "Rank", "Student Name", "Score", "Percentage", "Grade", 
            "Duration (min)", "Violations", "Status"
        ])
        
        # Student data
        for student in analytics.student_performances:
            writer.writerow([
                student.rank,
                student.student_name,
                student.score,
                student.percentage,
                student.grade,
                round(student.duration_taken, 1),
                student.violations_count,
                student.status
            ])
        
        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=student_performance_{exam_id}.csv"
            }
        )
    
    else:
        # Excel format - future enhancement
        raise HTTPException(status_code=501, detail="Excel export not implemented yet")


# Helper functions
async def _get_teacher_assignment_ids(db, teacher_id: ObjectId) -> List[ObjectId]:
    """Get all assignment IDs for teacher"""
    assignments = await db.teaching_assignments.find(
        {"teacher_id": teacher_id}
    ).to_list(None)
    
    return [a["_id"] for a in assignments]


async def _get_teacher_exam_ids(db, assignment_ids: List[ObjectId]) -> List[ObjectId]:
    """Get all exam IDs from assignment IDs"""
    exams = await db.exams.find(
        {"teaching_assignment_id": {"$in": assignment_ids}}
    ).to_list(None)
    
    return [e["_id"] for e in exams]
