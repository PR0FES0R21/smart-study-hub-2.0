# ==============================================================================
# File: app/api/v1/api.py
# Deskripsi: File untuk menggabungkan semua router API v1.
# --- DIUBAH ---
# ==============================================================================
from fastapi import APIRouter
from .routes import (
        auth, users, subjects, expertise_programs, 
        classes, teaching_assignments, question_banks, 
        exams, exam_sessions, analytics, academic_actions,
        data_jobs, ws, ws_exam_room, activity_logs,
        academic_periods, profiles
    )

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(expertise_programs.router, prefix="/expertise-programs", tags=["expertise-programs"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(teaching_assignments.router, prefix="/teaching-assignments", tags=["teaching-assignments"]) # --- DITAMBAHKAN ---
api_router.include_router(question_banks.router, prefix="/question-banks", tags=["question-banks"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(exam_sessions.router, prefix="/exam-sessions", tags=["exam-sessions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(academic_actions.router, prefix="/academic-actions", tags=["academic-actions"])
api_router.include_router(data_jobs.router, prefix="/jobs", tags=["data-jobs"])
api_router.include_router(ws.router)
api_router.include_router(ws_exam_room.router, prefix="/ws")
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["activity-logs"])
api_router.include_router(academic_periods.router, prefix="/academic-periods", tags=["academic-periods"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(ws.router, prefix="/ws")