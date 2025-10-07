# ==============================================================================
# File: app/api/v1/endpoints/course_progress.py
# Deskripsi: API endpoints untuk Course Progress tracking (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path

from app.api.v1.deps import get_database, get_current_user
from app.crud.course_progress import course_progress_crud
from app.schemas.lesson_progress import (
    CourseEnrollmentRequest, CourseProgressResponse,
    CourseProgressDashboardResponse, ProgressOperationResponse
)
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

@router.post("/courses/{course_id}/enroll", response_model=CourseProgressResponse)
async def enroll_in_course(
    course_id: str,
    enrollment_data: CourseEnrollmentRequest = CourseEnrollmentRequest(),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Enroll in course"""
    progress = await course_progress_crud.enroll_student_in_course(
        db, str(current_user["_id"]), course_id, enrollment_data.enrollment_metadata
    )
    return CourseProgressResponse(**progress.dict())

@router.get("/courses/{course_id}/progress")
async def get_course_progress(
    course_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get course progress"""
    progress = await course_progress_crud.get_course_progress(
        db, str(current_user["_id"]), course_id
    )
    if not progress:
        raise HTTPException(404, "Progress not found")
    return progress.dict()

@router.get("/courses/{course_id}/dashboard")
async def get_dashboard(
    course_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get course dashboard"""
    return await course_progress_crud.get_course_progress_dashboard(
        db, str(current_user["_id"]), course_id
    )
