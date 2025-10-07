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
        academic_periods, profiles, coordination_assignments, 
        question_sets, question_submissions, score_analytics, exam_analytics,
        teacher_analytics, exports, admin_exports, admin_export_files
    )
from .endpoints import lessons

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(expertise_programs.router, prefix="/expertise-programs", tags=["expertise-programs"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(teaching_assignments.router, prefix="/teaching-assignments", tags=["teaching-assignments"])
api_router.include_router(question_banks.router, prefix="/question-banks", tags=["question-banks"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(exam_sessions.router, prefix="/exam-sessions", tags=["exam-sessions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(score_analytics.router, prefix="/score-analytics", tags=["score-analytics"])
api_router.include_router(exam_analytics.router, prefix="/exam-analytics", tags=["exam-analytics"])
api_router.include_router(teacher_analytics.router, prefix="/teacher-analytics", tags=["teacher-analytics"])
api_router.include_router(academic_actions.router, prefix="/academic-actions", tags=["academic-actions"])
api_router.include_router(data_jobs.router, prefix="/jobs", tags=["data-jobs"])
api_router.include_router(ws.router)
api_router.include_router(ws_exam_room.router, prefix="/ws")
api_router.include_router(activity_logs.router, prefix="/activity-logs", tags=["activity-logs"])
api_router.include_router(academic_periods.router, prefix="/academic-periods", tags=["academic-periods"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(ws.router, prefix="/ws")
api_router.include_router(coordination_assignments.router, prefix="/coordination-assignments", tags=["coordination-assignments"])
api_router.include_router(question_sets.router, prefix="/question-sets", tags=["question-sets"])
api_router.include_router(question_submissions.router, prefix="/question-submissions", tags=["question-submissions"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(admin_exports.router, prefix="/admin/exports", tags=["admin-exports"])
api_router.include_router(admin_export_files.router, prefix="/admin/exports", tags=["admin-export-files"])

# LMS Endpoints - Modular Architecture
from .endpoints import modules, courses, lesson_progress, module_progress, course_progress, media
api_router.include_router(lessons.router, prefix="/lessons", tags=["LMS - Lessons"])
api_router.include_router(modules.router, prefix="/modules", tags=["LMS - Modules"])
api_router.include_router(courses.router, prefix="/courses", tags=["LMS - Courses"])
api_router.include_router(media.router, prefix="/media", tags=["LMS - Media Upload"])

# LMS Progress Tracking
api_router.include_router(lesson_progress.router, prefix="/progress", tags=["LMS - Progress Tracking"])
api_router.include_router(module_progress.router, prefix="/progress", tags=["LMS - Progress Tracking"])
api_router.include_router(course_progress.router, prefix="/progress", tags=["LMS - Progress Tracking"])

# LMS Endpoints - Legacy Course Management System
# from .routes import course_management
# api_router.include_router(course_management.router, tags=["Course Management System - Legacy"])
