# ==============================================================================
# File: app/api/v1/routes/exam_analytics.py
# Deskripsi: API endpoints untuk exam analytics system
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
import logging

from app.api.v1 import deps
from app.crud.exam_analytics import exam_analytics_crud
from app.schemas.exam_analytics import (
    ExamSessionAnalytics, ExamAnalyticsRequest, ExamAnalyticsSummary,
    BatchAnalyticsResponse, CheatDetectionReport, LearningInsights
)
from app.schemas.score_trend_analytics import (
    ScoreTrendAnalytics, ScoreTrendRequest
)
from app.crud.score_trend_analytics import score_trend_crud
from app.schemas.subject_mastery_analytics import (
    SubjectMasteryAnalytics, SubjectMasteryRequest, StudentMasteryResponse,
    ClassMasteryResponse, SchoolMasteryResponse
)
from app.crud.subject_mastery_analytics import subject_mastery_crud

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# MAIN ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/session/{exam_session_id}", response_model=ExamSessionAnalytics)
async def get_exam_session_analytics(
    exam_session_id: str,
    force_regenerate: bool = Query(False, description="Force regenerate analytics"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get comprehensive analytics untuk exam session tertentu
    
    Features:
    - Complete performance metrics
    - Question-by-question analysis
    - Timeline events and scoring progression
    - Violation analytics and cheat detection
    - Class comparison and ranking
    - Behavioral insights and recommendations
    """
    try:
        # Check if user has permission to view analytics
        await _check_analytics_permission(exam_session_id, current_user, db)
        
        # Generate or retrieve analytics
        analytics = await exam_analytics_crud.generate_exam_analytics(
            exam_session_id, force_regenerate
        )
        
        logger.info(f"Analytics retrieved for session {exam_session_id} by user {current_user['_id']}")
        return analytics
        
    except ValueError as e:
        logger.error(f"ValueError in get_exam_session_analytics for session {exam_session_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        logger.error(f"PermissionError in get_exam_session_analytics for session {exam_session_id}: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error retrieving analytics for session {exam_session_id}: {str(e)}")
        logger.exception(f"Full traceback for session {exam_session_id}:")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/session/{exam_session_id}/summary", response_model=ExamAnalyticsSummary)
async def get_exam_analytics_summary(
    exam_session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get quick summary analytics untuk dashboard display
    
    Returns essential metrics without detailed breakdowns for fast loading
    """
    try:
        await _check_analytics_permission(exam_session_id, current_user, db)
        
        summary = await exam_analytics_crud.get_analytics_summary(exam_session_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Analytics not found")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving analytics summary for session {exam_session_id}: {str(e)}")
        logger.exception(f"Full traceback for analytics summary {exam_session_id}:")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/generate", response_model=ExamSessionAnalytics)
async def generate_exam_analytics(
    request: ExamAnalyticsRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Manually trigger analytics generation dengan options khusus
    
    Useful untuk:
    - Force regeneration of analytics
    - Selective analytics generation
    - Testing dan debugging
    """
    try:
        await _check_analytics_permission(str(request.exam_session_id), current_user, db)
        
        analytics = await exam_analytics_crud.generate_exam_analytics(
            str(request.exam_session_id),
            force_regenerate=request.force_regenerate
        )
        
        return analytics
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# BATCH ANALYTICS (FOR TEACHERS/ADMINS)
# ============================================================================

@router.get("/exam/{exam_id}/batch", response_model=BatchAnalyticsResponse)
async def get_batch_exam_analytics(
    exam_id: str,
    include_flagged_only: bool = Query(False, description="Include only flagged sessions"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get batch analytics untuk seluruh exam (teacher/admin only)
    
    Returns analytics summaries untuk semua students dalam exam tertentu
    """
    try:
        # Check if user is teacher/admin
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in ["teacher", "admin"]):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get exam information first
        exam = await db.exams.find_one({"_id": ObjectId(exam_id)})
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Check if user owns this exam (for teachers)
        user_roles = current_user.get("roles", [])
        if "teacher" in user_roles and str(exam["teacher_id"]) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not your exam")
        
        # Get all exam sessions for this exam
        sessions_query = {
            "exam_id": ObjectId(exam_id),
            "status": "submitted"
        }
        
        exam_sessions = await db.exam_sessions.find(sessions_query).to_list(length=None)
        
        # Generate analytics summaries
        analytics_summaries = []
        flagged_count = 0
        total_violations = 0
        
        for session in exam_sessions:
            try:
                summary = await exam_analytics_crud.get_analytics_summary(str(session["_id"]))
                if summary:
                    # Filter flagged sessions if requested
                    if include_flagged_only and not summary.is_flagged:
                        continue
                        
                    analytics_summaries.append(summary)
                    if summary.is_flagged:
                        flagged_count += 1
                    total_violations += summary.total_violations
            except Exception as e:
                logger.warning(f"Failed to get analytics for session {session['_id']}: {e}")
                continue
        
        # Calculate class statistics
        if analytics_summaries:
            scores = [s.score for s in analytics_summaries]
            accuracy_rates = [s.accuracy for s in analytics_summaries]
            
            class_statistics = {
                "total_sessions": len(exam_sessions),
                "analytics_available": len(analytics_summaries),
                "average_score": sum(scores) / len(scores),
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "average_accuracy": sum(accuracy_rates) / len(accuracy_rates),
                "flagged_sessions": flagged_count,
                "total_violations": total_violations,
                "completion_rate": (len(exam_sessions) / len(exam.get("students", [])) * 100) if exam.get("students") else 0
            }
        else:
            class_statistics = {
                "total_sessions": len(exam_sessions),
                "analytics_available": 0,
                "message": "No analytics data available"
            }
        
        return BatchAnalyticsResponse(
            exam_id=ObjectId(exam_id),
            exam_title=exam["title"],
            total_sessions=len(exam_sessions),
            analytics_summaries=analytics_summaries,
            class_statistics=class_statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# SPECIALIZED ANALYTICS
# ============================================================================

@router.get("/session/{exam_session_id}/cheat-detection", response_model=CheatDetectionReport)
async def get_cheat_detection_report(
    exam_session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get detailed cheat detection report (teacher/admin only)
    
    Returns comprehensive fraud analysis dengan recommended actions
    """
    try:
        # Only teachers and admins can access cheat detection reports
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in ["teacher", "admin"]):
            raise HTTPException(status_code=403, detail="Insufficient permissions for cheat detection")
        
        # Get full analytics first
        analytics = await exam_analytics_crud.generate_exam_analytics(exam_session_id)
        
        # Build cheat detection report
        violations = analytics.violation_analytics
        
        # Analyze suspicious patterns
        suspicious_patterns = []
        
        # Time-based patterns
        if analytics.performance_metrics.average_time_per_question < 15:  # Very fast
            suspicious_patterns.append({
                "type": "time_anomaly",
                "description": "Unusually fast response times",
                "severity": "medium",
                "evidence": f"Average {analytics.performance_metrics.average_time_per_question:.1f}s per question"
            })
        
        # Pattern-based suspicion
        answer_patterns = analytics.answer_pattern_analysis
        if answer_patterns.get("max_correct_streak", 0) >= 10:
            suspicious_patterns.append({
                "type": "streak_anomaly", 
                "description": "Unusually long correct answer streak",
                "severity": "low",
                "evidence": f"{answer_patterns['max_correct_streak']} consecutive correct answers"
            })
        
        # High accuracy with many violations
        if analytics.performance_metrics.accuracy_percentage >= 90 and violations.total_violations >= 5:
            suspicious_patterns.append({
                "type": "performance_violation_mismatch",
                "description": "High performance despite multiple violations",
                "severity": "high", 
                "evidence": f"{analytics.performance_metrics.accuracy_percentage:.1f}% accuracy with {violations.total_violations} violations"
            })
        
        # Determine recommended actions
        recommended_actions = []
        requires_manual_review = False
        
        if violations.fraud_score >= 0.7:
            recommended_actions.append("Flag exam for manual review")
            recommended_actions.append("Consider voiding exam results")
            requires_manual_review = True
        elif violations.fraud_score >= 0.4:
            recommended_actions.append("Schedule meeting with student")
            recommended_actions.append("Review exam footage if available")
            requires_manual_review = True
        elif violations.total_violations >= 3:
            recommended_actions.append("Send warning to student")
            recommended_actions.append("Monitor future exam sessions closely")
        
        if not recommended_actions:
            recommended_actions.append("No action required - clean exam session")
        
        # Calculate confidence level
        confidence_factors = []
        if violations.total_violations >= 5:
            confidence_factors.append(0.3)
        if violations.fraud_score >= 0.5:
            confidence_factors.append(0.4)
        if len(suspicious_patterns) >= 2:
            confidence_factors.append(0.2)
        if analytics.performance_metrics.accuracy_percentage >= 95:
            confidence_factors.append(0.1)
        
        confidence_level = min(sum(confidence_factors), 1.0)
        
        report = CheatDetectionReport(
            exam_session_id=analytics.exam_session_id,
            student_id=analytics.student_id,
            overall_fraud_score=violations.fraud_score,
            risk_assessment=violations.risk_level.upper(),
            violation_summary=violations,
            suspicious_patterns=suspicious_patterns,
            recommended_actions=recommended_actions,
            requires_manual_review=requires_manual_review,
            confidence_level=confidence_level
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating cheat detection report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/session/{exam_session_id}/learning-insights", response_model=LearningInsights)
async def get_learning_insights(
    exam_session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get personalized learning insights untuk student
    
    Returns tailored recommendations based on performance patterns
    """
    try:
        await _check_analytics_permission(exam_session_id, current_user, db)
        
        analytics = await exam_analytics_crud.generate_exam_analytics(exam_session_id)
        
        # Analyze strengths and weaknesses
        strengths = []
        weaknesses = []
        
        # Performance-based analysis
        if analytics.performance_metrics.accuracy_percentage >= 85:
            strengths.append("Strong overall subject mastery")
        elif analytics.performance_metrics.accuracy_percentage >= 70:
            strengths.append("Good foundational understanding")
        
        if analytics.performance_metrics.completion_percentage == 100:
            strengths.append("Excellent time management")
        elif analytics.performance_metrics.completion_percentage < 80:
            weaknesses.append("Time management needs improvement")
        
        # Question difficulty analysis
        difficulty_performance = {}
        for q_analysis in analytics.questions_analytics:
            difficulty = q_analysis.difficulty
            if difficulty not in difficulty_performance:
                difficulty_performance[difficulty] = {"correct": 0, "total": 0}
            
            difficulty_performance[difficulty]["total"] += 1
            if q_analysis.is_correct:
                difficulty_performance[difficulty]["correct"] += 1
        
        # Calculate mastery by difficulty
        difficulty_progression = {}
        for difficulty, stats in difficulty_performance.items():
            if stats["total"] > 0:
                mastery = stats["correct"] / stats["total"]
                difficulty_progression[difficulty] = mastery
                
                if mastery >= 0.8:
                    strengths.append(f"Strong performance on {difficulty} questions")
                elif mastery < 0.5:
                    weaknesses.append(f"Struggles with {difficulty} questions")
        
        # Question type analysis
        question_type_mastery = {}
        type_performance = {}
        
        for q_analysis in analytics.questions_analytics:
            q_type = q_analysis.question_type
            if q_type not in type_performance:
                type_performance[q_type] = {"correct": 0, "total": 0}
            
            type_performance[q_type]["total"] += 1
            if q_analysis.is_correct:
                type_performance[q_type]["correct"] += 1
        
        for q_type, stats in type_performance.items():
            if stats["total"] > 0:
                mastery = stats["correct"] / stats["total"]
                question_type_mastery[q_type] = mastery
                
                if mastery >= 0.8:
                    strengths.append(f"Excellent at {q_type} questions")
                elif mastery < 0.5:
                    weaknesses.append(f"Needs practice with {q_type} questions")
        
        # Generate study recommendations
        study_recommendations = []
        
        if analytics.performance_metrics.accuracy_percentage < 70:
            study_recommendations.extend([
                "Review fundamental concepts in this subject",
                "Create summary notes of key topics",
                "Practice with similar question types daily"
            ])
        
        # Difficulty-based recommendations
        if difficulty_progression.get("hard", 1) < 0.5:
            study_recommendations.append("Focus on advanced practice problems")
        if difficulty_progression.get("easy", 1) < 0.8:
            study_recommendations.append("Solidify basic concepts first")
        
        # Generate time management tips
        time_management_tips = []
        
        if analytics.performance_metrics.average_time_per_question > 120:
            time_management_tips.extend([
                "Practice timed question sets",
                "Learn to identify quick-win questions first",
                "Set time limits per question type"
            ])
        elif analytics.performance_metrics.average_time_per_question < 30:
            time_management_tips.extend([
                "Take more time to read questions carefully", 
                "Double-check answers before submitting",
                "Consider all options in multiple choice questions"
            ])
        
        if analytics.performance_metrics.completion_percentage < 100:
            time_management_tips.extend([
                "Practice full-length timed exams",
                "Prioritize easier questions first",
                "Avoid spending too much time on difficult questions"
            ])
        
        # Default recommendations if lists are empty
        if not study_recommendations:
            study_recommendations.append("Continue current study approach - performance is strong")
        
        if not time_management_tips:
            time_management_tips.append("Current pacing is appropriate for your style")
        
        return LearningInsights(
            strengths=strengths[:5],
            weaknesses=weaknesses[:5], 
            study_recommendations=study_recommendations[:5],
            time_management_tips=time_management_tips[:5],
            difficulty_progression=difficulty_progression,
            question_type_mastery=question_type_mastery
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating learning insights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# SCORE TREND ANALYTICS
# ============================================================================

@router.get("/score-trend", response_model=ScoreTrendAnalytics)
async def get_score_trend_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for trend analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for trend analysis"),
    class_id: Optional[str] = Query(None, description="Filter by class ID"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    expertise_id: Optional[str] = Query(None, description="Filter by expertise program ID"),
    teacher_id: Optional[str] = Query(None, description="Filter by teacher ID (admin only)"),
    student_id: Optional[str] = Query(None, description="Filter by student ID (admin only)"),
    academic_period_id: Optional[str] = Query(None, description="Filter by academic period"),
    group_by: str = Query("class", description="Group data by: class, subject, grade, teacher, student"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get score trend analytics dengan role-based filtering
    
    Features per role:
    - **Student**: Hanya dapat melihat trend nilai pribadi
    - **Teacher**: Dapat melihat trend kelas dan mata pelajaran yang diajar
    - **Admin**: Dapat melihat semua trend dengan filtering lengkap
    
    Parameters yang dapat digunakan berdasarkan role:
    - Student: start_date, end_date
    - Teacher: start_date, end_date, class_id, subject_id, group_by
    - Admin: semua parameter
    """
    try:
        # Build request object
        request = ScoreTrendRequest(
            start_date=start_date,
            end_date=end_date,
            class_id=ObjectId(class_id) if class_id else None,
            grade_level=grade_level,
            subject_id=ObjectId(subject_id) if subject_id else None,
            expertise_id=ObjectId(expertise_id) if expertise_id else None,
            teacher_id=ObjectId(teacher_id) if teacher_id else None,
            student_id=ObjectId(student_id) if student_id else None,
            academic_period_id=ObjectId(academic_period_id) if academic_period_id else None,
            group_by=group_by
        )
        
        # Get analytics
        analytics = await score_trend_crud.get_score_trend_analytics(request, current_user)
        
        logger.info(f"Score trend analytics retrieved for user {current_user['_id']} with {len(analytics.series)} series")
        return analytics
        
    except ValueError as e:
        logger.error(f"ValueError in score trend analytics: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        logger.error(f"PermissionError in score trend analytics: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in score trend analytics: {str(e)}")
        logger.exception(f"Full traceback for score trend analytics:")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/score-trend", response_model=ScoreTrendAnalytics)
async def get_score_trend_analytics_post(
    request: ScoreTrendRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Alternative POST endpoint untuk score trend analytics dengan request body
    
    Berguna untuk complex filtering atau ketika parameter terlalu banyak untuk GET request
    """
    try:
        analytics = await score_trend_crud.get_score_trend_analytics(request, current_user)
        
        logger.info(f"Score trend analytics (POST) retrieved for user {current_user['_id']} with {len(analytics.series)} series")
        return analytics
        
    except ValueError as e:
        logger.error(f"ValueError in score trend analytics (POST): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        logger.error(f"PermissionError in score trend analytics (POST): {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in score trend analytics (POST): {str(e)}")
        logger.exception(f"Full traceback for score trend analytics (POST):")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ============================================================================
# SUBJECT MASTERY ANALYTICS (RADAR CHART)
# ============================================================================

@router.get("/subject-mastery", response_model=Union[StudentMasteryResponse, ClassMasteryResponse, SchoolMasteryResponse])
async def get_subject_mastery_analytics(
    student_id: Optional[str] = Query(None, description="Specific student ID (admin/teacher only)"),
    class_id: Optional[str] = Query(None, description="Filter by class ID"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    expertise_id: Optional[str] = Query(None, description="Filter by expertise program"),
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    academic_period_id: Optional[str] = Query(None, description="Filter by academic period"),
    include_zero_scores: bool = Query(False, description="Include subjects with 0 exams"),
    min_exams_per_subject: int = Query(1, ge=1, description="Minimum exams per subject"),
    use_cache: bool = Query(True, description="Use cached results (15min TTL)"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Get Subject Mastery Analytics untuk Radar Chart visualization
    
    **Performance Optimized** dengan smart caching dan efficient aggregation.
    
    Features per role:
    - **Student**: Personal subject mastery radar (own data only)
    - **Teacher**: Class-level subject mastery comparison (classes taught only)
    - **Admin**: School-wide subject mastery analysis dengan flexible filtering
    
    **Radar Chart Ready**: Output format optimized untuk Chart.js radar charts
    
    **Caching**: Results cached untuk 15 minutes untuk optimal performance
    """
    try:
        # Build optimized request
        request = SubjectMasteryRequest(
            student_id=ObjectId(student_id) if student_id else None,
            class_id=ObjectId(class_id) if class_id else None,
            grade_level=grade_level,
            expertise_id=ObjectId(expertise_id) if expertise_id else None,
            start_date=start_date,
            end_date=end_date,
            academic_period_id=ObjectId(academic_period_id) if academic_period_id else None,
            include_zero_scores=include_zero_scores,
            min_exams_per_subject=min_exams_per_subject,
            use_cache=use_cache
        )
        
        # Get analytics with performance optimization
        start_time = datetime.utcnow()
        result = await subject_mastery_crud.get_subject_mastery_analytics(request, current_user)
        end_time = datetime.utcnow()
        
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Subject mastery analytics completed in {processing_time:.3f}s for user {current_user['_id']}")
        
        return result
        
    except ValueError as e:
        logger.error(f"ValueError in subject mastery analytics: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        logger.error(f"PermissionError in subject mastery analytics: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in subject mastery analytics: {str(e)}")
        logger.exception(f"Full traceback for subject mastery analytics:")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/subject-mastery", response_model=Union[StudentMasteryResponse, ClassMasteryResponse, SchoolMasteryResponse])
async def get_subject_mastery_analytics_post(
    request: SubjectMasteryRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Alternative POST endpoint untuk Subject Mastery Analytics
    
    **Advanced Options**: Supports more complex filtering options through request body
    
    **Performance Features**:
    - Smart caching dengan customizable TTL
    - Role-based query optimization
    - Minimal data transfer
    - Efficient MongoDB aggregation pipelines
    """
    try:
        start_time = datetime.utcnow()
        result = await subject_mastery_crud.get_subject_mastery_analytics(request, current_user)
        end_time = datetime.utcnow()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Log performance metrics
        entity_count = 1 if hasattr(result, 'entity_id') else len(getattr(result, 'entities', []))
        cache_status = "HIT" if processing_time < 0.1 else "MISS"
        
        logger.info(
            f"Subject mastery (POST) - {processing_time:.3f}s, {entity_count} entities, "
            f"Cache: {cache_status}, User: {current_user['_id']}"
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"ValueError in subject mastery analytics (POST): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        logger.error(f"PermissionError in subject mastery analytics (POST): {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in subject mastery analytics (POST): {str(e)}")
        logger.exception(f"Full traceback for subject mastery analytics (POST):")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/subject-mastery/cache")
async def clear_subject_mastery_cache(
    cache_pattern: str = Query("subject_mastery:*", description="Cache pattern to clear"),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Clear Subject Mastery Analytics cache (admin only)
    
    Useful untuk:
    - Force refresh after data updates
    - Performance troubleshooting
    - Cache management
    """
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin access required untuk cache management")
    
    try:
        from app.core.cache import invalidate_cache
        await invalidate_cache(cache_pattern)
        
        logger.info(f"Subject mastery cache cleared by admin {current_user['_id']}: {cache_pattern}")
        
        return {
            "message": f"Cache cleared for pattern: {cache_pattern}",
            "timestamp": datetime.utcnow().isoformat(),
            "cleared_by": current_user.get("_id")
        }
        
    except Exception as e:
        logger.error(f"Error clearing subject mastery cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear error: {str(e)}")

# ============================================================================
# MANAGEMENT ENDPOINTS
# ============================================================================

@router.delete("/session/{exam_session_id}")
async def delete_exam_analytics(
    exam_session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    Delete cached analytics data (admin only)
    
    Forces regeneration on next access
    """
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        success = await exam_analytics_crud.delete_analytics(exam_session_id)
        
        if success:
            return JSONResponse(
                content={"message": f"Analytics deleted for session {exam_session_id}"},
                status_code=200
            )
        else:
            raise HTTPException(status_code=404, detail="Analytics not found")
            
    except Exception as e:
        logger.error(f"Error deleting analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def analytics_health_check(
    db: AsyncIOMotorDatabase = Depends(deps.get_database)
):
    """
    Health check endpoint untuk analytics system
    """
    try:
        # Test collection access
        await db.exam_analytics.find_one({}, {"_id": 1})
        
        return JSONResponse(
            content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "exam_analytics"
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _check_analytics_permission(exam_session_id: str, current_user: dict, db: AsyncIOMotorDatabase):
    """
    Check if user has permission to view analytics untuk session ini
    """
    # Get exam session
    try:
        session_object_id = ObjectId(exam_session_id)
    except Exception:
        raise ValueError("Invalid exam session ID format")
    
    exam_session = await db.exam_sessions.find_one({"_id": session_object_id})
    if not exam_session:
        raise ValueError("Exam session not found")
    
    user_roles = current_user.get("roles", [])
    
    # Admin can view all analytics
    if "admin" in user_roles:
        return True
    
    # Students can only view their own analytics
    if "student" in user_roles:
        if str(exam_session["student_id"]) != str(current_user["_id"]):
            raise PermissionError("You can only view your own exam analytics")
        return True
    
    # Teachers can view analytics untuk their exams
    if "teacher" in user_roles:
        exam = await db.exams.find_one({"_id": exam_session["exam_id"]})
        if not exam:
            raise ValueError("Exam not found")
        
        if str(exam["teacher_id"]) != str(current_user["_id"]):
            raise PermissionError("You can only view analytics for your own exams")
        return True
    
    # Default deny
    raise PermissionError("Insufficient permissions")
