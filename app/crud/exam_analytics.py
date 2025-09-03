# ==============================================================================
# File: app/crud/exam_analytics.py
# Deskripsi: CRUD operations untuk analytics hasil ujian
# ==============================================================================

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..api.v1.deps import get_database
from ..schemas.exam_analytics import (
    ExamSessionAnalytics, QuestionAnalytics, TimelineEvent, ScoreTimeline,
    ViolationAnalytics, PerformanceMetrics, ClassComparison, QuestionDifficultyAnalysis,
    ExamAnalyticsSummary, CheatDetectionReport, LearningInsights
)
import asyncio
import logging

logger = logging.getLogger(__name__)

class ExamAnalyticsCRUD:
    def __init__(self):
        pass

    async def _get_db(self):
        """Get database instance"""
        return get_database()

    # ========================================================================
    # CORE ANALYTICS GENERATION
    # ========================================================================

    async def generate_exam_analytics(
        self, 
        exam_session_id: str,
        force_regenerate: bool = False
    ) -> ExamSessionAnalytics:
        """
        Generate comprehensive analytics untuk exam session
        """
        db = await self._get_db()
        
        # Check if analytics already exists and not expired
        if not force_regenerate:
            try:
                existing = await db.exam_analytics.find_one({
                    "exam_session_id": ObjectId(exam_session_id),
                    "cache_expires_at": {"$gt": datetime.utcnow()}
                })
                if existing:
                    logger.info(f"Returning cached analytics for session {exam_session_id}")
                    return ExamSessionAnalytics(**existing)
            except Exception as e:
                logger.warning(f"Error loading cached analytics for session {exam_session_id}: {e}")
                # Continue with generation if cache load fails

        # Get exam session data
        try:
            session_object_id = ObjectId(exam_session_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format for exam_session_id {exam_session_id}: {e}")
            raise ValueError(f"Invalid exam session ID format: {exam_session_id}")
            
        exam_session = await db.exam_sessions.find_one({"_id": session_object_id})
        if not exam_session:
            logger.error(f"Exam session not found in database: {exam_session_id}")
            raise ValueError(f"Exam session {exam_session_id} not found")
            
        logger.info(f"Found exam session {exam_session_id}, exam_id: {exam_session.get('exam_id', 'N/A')}")

        # Get related data
        try:
            exam = await db.exams.find_one({"_id": exam_session["exam_id"]})
            if not exam:
                logger.error(f"Exam not found for ID: {exam_session.get('exam_id', 'N/A')}")
                raise ValueError(f"Exam not found for session {exam_session_id}")
            logger.info(f"Found exam: {exam.get('title', 'N/A')} for session {exam_session_id}")
        except Exception as e:
            logger.error(f"Error retrieving exam data for session {exam_session_id}: {e}")
            raise
            
        try:
            student = await db.users.find_one({"_id": exam_session["student_id"]})
            if not student:
                logger.error(f"Student not found for ID: {exam_session.get('student_id', 'N/A')}")
                raise ValueError(f"Student not found for session {exam_session_id}")
            student_name = f"{student.get('first_name', '')} {student.get('last_name', '')}" if student else "Unknown"
            logger.info(f"Found student: {student_name} for session {exam_session_id}")
        except Exception as e:
            logger.error(f"Error retrieving student data for session {exam_session_id}: {e}")
            raise
        
        # Handle different database structures - get teacher from teaching_assignment
        teacher = None
        subject = None
        class_info = None
        
        if "teaching_assignment_id" in exam:
            # New structure - get data from teaching assignment
            teaching_assignment = await db.teaching_assignments.find_one({"_id": exam["teaching_assignment_id"]})
            if teaching_assignment:
                teacher = await db.users.find_one({"_id": teaching_assignment["teacher_id"]})
                subject = await db.subjects.find_one({"_id": teaching_assignment["subject_id"]})
                class_info = await db.classes.find_one({"_id": teaching_assignment["class_id"]})
        else:
            # Old structure - direct references
            if "teacher_id" in exam:
                teacher = await db.users.find_one({"_id": exam["teacher_id"]})
            if "subject_id" in exam:
                subject = await db.subjects.find_one({"_id": exam["subject_id"]})
            if "class_id" in exam:
                class_info = await db.classes.find_one({"_id": exam["class_id"]})

        logger.info(f"Generating analytics for exam session {exam_session_id}")

        # Generate all analytics components with error handling
        try:
            performance_metrics = await self._generate_performance_metrics(exam_session, exam)
            logger.debug("Performance metrics generated successfully")
        except Exception as e:
            logger.error(f"Error generating performance metrics: {e}")
            raise
            
        try:
            questions_analytics = await self._generate_questions_analytics(exam_session, exam)
            logger.debug("Questions analytics generated successfully")
        except Exception as e:
            logger.error(f"Error generating questions analytics: {e}")
            raise
            
        try:
            timeline_events = await self._generate_timeline_events(exam_session, exam)
            logger.debug("Timeline events generated successfully")
        except Exception as e:
            logger.error(f"Error generating timeline events: {e}")
            raise
            
        try:
            score_timeline = await self._generate_score_timeline(exam_session, exam)
            logger.debug("Score timeline generated successfully")
        except Exception as e:
            logger.error(f"Error generating score timeline: {e}")
            raise
            
        try:
            violation_analytics = await self._generate_violation_analytics(exam_session)
            logger.debug("Violation analytics generated successfully")
        except Exception as e:
            logger.error(f"Error generating violation analytics: {e}")
            raise
            
        try:
            class_comparison = await self._generate_class_comparison(exam_session, exam)
            logger.debug("Class comparison generated successfully")
        except Exception as e:
            logger.error(f"Error generating class comparison: {e}")
            raise
            
        try:
            question_difficulty_analysis = await self._generate_question_difficulty_analysis(exam)
            logger.debug("Question difficulty analysis generated successfully")
        except Exception as e:
            logger.error(f"Error generating question difficulty analysis: {e}")
            raise
        
        # Generate advanced analytics with error handling
        try:
            answer_pattern_analysis = await self._analyze_answer_patterns(exam_session)
            logger.debug("Answer pattern analysis generated successfully")
        except Exception as e:
            logger.error(f"Error generating answer pattern analysis: {e}")
            answer_pattern_analysis = {}
            
        try:
            time_allocation_analysis = await self._analyze_time_allocation(exam_session, exam)
            logger.debug("Time allocation analysis generated successfully")
        except Exception as e:
            logger.error(f"Error generating time allocation analysis: {e}")
            time_allocation_analysis = {}
            
        try:
            behavioral_insights = await self._generate_behavioral_insights(
                exam_session, performance_metrics, violation_analytics
            )
            logger.debug("Behavioral insights generated successfully")
        except Exception as e:
            logger.error(f"Error generating behavioral insights: {e}")
            behavioral_insights = []
            
        try:
            recommendations = await self._generate_recommendations(
                performance_metrics, violation_analytics, class_comparison
            )
            logger.debug("Recommendations generated successfully")
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations = []

        # Create the complete analytics object
        try:
            logger.info(f"Creating analytics object for session {exam_session_id}")
            
            # Validate required fields
            if not exam_session.get("started_at") or not exam_session.get("submitted_at"):
                logger.error(f"Missing timing data for session {exam_session_id}")
                raise ValueError("Exam session missing required timing data")
            
            duration_taken = (exam_session["submitted_at"] - exam_session["started_at"]).total_seconds() / 60
            duration_allowed = exam.get("duration", exam.get("duration_minutes", 60))
            is_overtime = duration_taken > duration_allowed
            
            analytics = ExamSessionAnalytics(
                # Metadata
                exam_session_id=ObjectId(exam_session_id),
                exam_id=exam_session["exam_id"],
                student_id=exam_session["student_id"],
                exam_title=exam.get("title", "Unknown Exam"),
                exam_type=exam.get("exam_type", "regular"),
                subject_name=subject["name"] if subject else "Unknown",
                teacher_name=f"{teacher.get('first_name', '')} {teacher.get('last_name', '')}" if teacher else "Unknown",
                class_name=class_info["name"] if class_info else "Unknown",
                academic_period=exam.get("academic_period", "Unknown"),
                
                # Timing
                started_at=exam_session["started_at"],
                submitted_at=exam_session["submitted_at"],
                duration_allowed=duration_allowed,
                duration_taken=duration_taken,
                is_overtime=is_overtime,
                
                # Core analytics
                performance_metrics=performance_metrics,
                questions_analytics=questions_analytics,
                timeline_events=timeline_events,
                score_timeline=score_timeline,
                violation_analytics=violation_analytics,
                class_comparison=class_comparison,
                
                # Advanced analytics
                question_difficulty_analysis=question_difficulty_analysis,
                answer_pattern_analysis=answer_pattern_analysis,
                time_allocation_analysis=time_allocation_analysis,
                behavioral_insights=behavioral_insights,
                recommendations=recommendations,
                
                # Technical metadata
                client_info=exam_session.get("client_info", {}),
                generated_at=datetime.utcnow(),
                cache_expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            logger.info(f"Analytics object created successfully for session {exam_session_id}")
            
        except Exception as e:
            logger.error(f"Error creating analytics object for session {exam_session_id}: {str(e)}")
            logger.exception(f"Full traceback for analytics object creation:")
            raise

        # Save to database
        try:
            save_result = await self._save_analytics(analytics)
            if not save_result:
                logger.warning(f"Failed to save analytics to database for session {exam_session_id}")
            else:
                logger.info(f"Analytics saved successfully to database for session {exam_session_id}")
        except Exception as e:
            logger.error(f"Error saving analytics for session {exam_session_id}: {e}")
            # Continue anyway, return the generated analytics even if save fails
        
        logger.info(f"Analytics generated and cached for session {exam_session_id}")
        return analytics

    async def _generate_performance_metrics(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> PerformanceMetrics:
        """Generate performance metrics"""
        answers = exam_session.get("answers", [])
        if not isinstance(answers, list):
            answers = []
            
        # Handle different question structures
        if "questions" in exam:
            questions = exam.get("questions", [])
            total_questions = len(questions) if isinstance(questions, list) else 0
        else:
            question_ids = exam.get("question_ids", [])
            total_questions = len(question_ids) if isinstance(question_ids, list) else 0
        
        # Calculate basic metrics
        answered_questions = len([a for a in answers if isinstance(a, dict) and (a.get("selected_option") or a.get("answer_text"))])
        correct_answers = len([a for a in answers if isinstance(a, dict) and a.get("is_correct", False)])
        wrong_answers = answered_questions - correct_answers
        unanswered_questions = total_questions - answered_questions
        
        # Calculate percentages
        accuracy_percentage = (correct_answers / answered_questions * 100) if answered_questions > 0 else 0
        completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
        
        # Calculate time metrics
        total_time = (exam_session["submitted_at"] - exam_session["started_at"]).total_seconds() if exam_session.get("submitted_at") and exam_session.get("started_at") else 0
        answer_times = [a.get("time_spent", 0) for a in answers if isinstance(a, dict) and a.get("time_spent") and isinstance(a.get("time_spent"), (int, float))]
        avg_time_per_question = sum(answer_times) / len(answer_times) if answer_times else 0
        fastest_answer = min(answer_times) if answer_times else 0
        slowest_answer = max(answer_times) if answer_times else 0
        
        # Calculate scores
        score = exam_session.get("score", 0)
        # Handle different question structures for max score calculation
        if "questions" in exam:
            max_possible_score = sum([q.get("points", 1) for q in exam.get("questions", [])])
        else:
            # Estimate based on answers or default to total questions
            max_possible_score = len(exam.get("question_ids", [])) * 10  # Assume 10 points per question

        return PerformanceMetrics(
            total_questions=total_questions,
            answered_questions=answered_questions,
            correct_answers=correct_answers,
            wrong_answers=wrong_answers,
            unanswered_questions=unanswered_questions,
            accuracy_percentage=accuracy_percentage,
            completion_percentage=completion_percentage,
            total_time_taken=total_time,
            average_time_per_question=avg_time_per_question,
            fastest_answer=fastest_answer,
            slowest_answer=slowest_answer,
            score=score,
            max_possible_score=max_possible_score
        )

    async def _generate_questions_analytics(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> List[QuestionAnalytics]:
        """Generate analytics untuk setiap soal"""
        db = await self._get_db()
        questions_data = []
        
        # Handle different question structures
        session_answers = {str(a["question_id"]): a for a in exam_session.get("answers", []) if isinstance(a, dict) and a.get("question_id") is not None}
        questions_to_process = []
        
        if "questions" in exam:
            # Old structure
            questions_to_process = exam.get("questions", [])
        else:
            # New structure - questions are referenced by IDs
            question_ids = exam.get("question_ids", [])
            for idx, question_id in enumerate(question_ids):
                # Create a fake question object for compatibility
                q = {
                    "question_id": question_id,
                    "position": idx + 1,
                    "points": 1,  # Default points, will be overridden by answer data
                    "original_position": idx + 1
                }
                questions_to_process.append(q)
        
        # Process all questions
        for idx, q in enumerate(questions_to_process):
            question_id = str(q["question_id"])
            answer = session_answers.get(question_id, {})
            
            # Get question details from database
            question_doc = await db.questions.find_one({"_id": ObjectId(question_id)})
            if not question_doc:
                continue
                
            # Determine correct answer
            if question_doc["type"] == "multiple_choice":
                correct_option = next((opt for opt in question_doc["options"] if opt.get("is_correct")), None)
                correct_answer = str(correct_option["_id"]) if correct_option else None
                correct_answer_text = correct_option.get("text", "") if correct_option else ""
            else:
                correct_answer = question_doc.get("correct_answer", "")
                correct_answer_text = correct_answer
            
            # Student answer
            student_answer = answer.get("selected_option") or answer.get("answer_text")
            if question_doc["type"] == "multiple_choice" and student_answer:
                selected_option = next((opt for opt in question_doc["options"] 
                                      if str(opt["_id"]) == student_answer), None)
                student_answer_text = selected_option.get("text", "") if selected_option else ""
            else:
                student_answer_text = student_answer or ""
            
            questions_data.append(QuestionAnalytics(
                question_id=ObjectId(question_id),
                original_position=q.get("original_position", idx + 1),
                displayed_position=q.get("position", idx + 1),
                question_text=question_doc["question_text"],
                question_type=question_doc["type"],
                difficulty=question_doc.get("difficulty", "medium"),
                points=q.get("points", 1),
                student_answer=student_answer,
                correct_answer=correct_answer,
                student_answer_text=student_answer_text,
                correct_answer_text=correct_answer_text,
                is_correct=answer.get("is_correct", False),
                points_earned=q.get("points", 1) if answer.get("is_correct", False) else 0,
                time_spent=answer.get("time_spent"),
                answer_timestamp=answer.get("answered_at"),
                change_count=answer.get("change_count", 0),
                options=[{
                    "id": str(opt["_id"]),
                    "text": opt["text"],
                    "is_correct": opt.get("is_correct", False)
                } for opt in question_doc.get("options", [])]
            ))
        
        return questions_data

    async def _generate_timeline_events(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> List[TimelineEvent]:
        """Generate timeline events dari exam session"""
        events = []
        
        # Answer submission events
        answers = exam_session.get("answers", [])
        if not isinstance(answers, list):
            answers = []
            
        for answer in answers:
            if not isinstance(answer, dict) or not answer.get("answered_at"):
                continue
                
            events.append(TimelineEvent(
                timestamp=answer["answered_at"],
                event_type="answer_submitted",
                question_id=answer["question_id"],
                displayed_position=answer.get("position"),
                is_correct=answer.get("is_correct", False),
                details={
                    "answer": answer.get("selected_option") or answer.get("answer_text"),
                    "time_spent": answer.get("time_spent", 0)
                }
            ))
        
        # Violation events
        violations = exam_session.get("violations", [])
        if not isinstance(violations, list):
            violations = []
            
        for violation in violations:
            if not isinstance(violation, dict) or not violation.get("detected_at"):
                continue
                
            events.append(TimelineEvent(
                timestamp=violation["detected_at"],
                event_type="violation",
                details={
                    "violation_type": violation.get("violation_type", "unknown"),
                    "severity": violation.get("severity", "low"),
                    "description": violation.get("description", "")
                }
            ))
        
        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp)
        
        # Add cumulative scores
        cumulative_score = 0
        for event in events:
            if event.event_type == "answer_submitted" and event.is_correct:
                cumulative_score += 1
            event.cumulative_score = cumulative_score
        
        return events

    async def _generate_score_timeline(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> List[ScoreTimeline]:
        """Generate score timeline progresif"""
        timeline = []
        cumulative_correct = 0
        cumulative_wrong = 0
        cumulative_score = 0
        
        # Sort answers by timestamp
        exam_answers = exam_session.get("answers", [])
        if not isinstance(exam_answers, list):
            exam_answers = []
            
        valid_answers = []
        for a in exam_answers:
            if isinstance(a, dict) and a.get("answered_at"):
                valid_answers.append(a)
                
        answers = sorted(valid_answers, key=lambda x: x["answered_at"])
        
        for idx, answer in enumerate(answers):
            if not isinstance(answer, dict):
                continue
                
            is_correct = answer.get("is_correct", False)
            points = answer.get("points_earned", 0)
            
            if is_correct:
                cumulative_correct += 1
                score_change = 1
                cumulative_score += points
            else:
                cumulative_wrong += 1
                score_change = -1 if cumulative_score > 0 else 0
            
            timeline.append(ScoreTimeline(
                timestamp=answer["answered_at"],
                question_position=answer.get("position", idx + 1),
                question_id=answer["question_id"],
                is_correct=is_correct,
                cumulative_correct=cumulative_correct,
                cumulative_wrong=cumulative_wrong,
                cumulative_score=cumulative_score,
                score_change=score_change
            ))
        
        return timeline

    async def _generate_violation_analytics(
        self, 
        exam_session: Dict
    ) -> ViolationAnalytics:
        """Generate analytics untuk violations"""
        violations = exam_session.get("violations", [])
        if not isinstance(violations, list):
            violations = []
        
        # Count by severity and type
        violations_by_severity = {}
        violations_by_type = {}
        
        for v in violations:
            # Ensure v is a dictionary before trying to access it
            if not isinstance(v, dict):
                continue
                
            severity = v.get("severity", "low")
            v_type = v.get("violation_type", "unknown")
            
            violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1
            violations_by_type[v_type] = violations_by_type.get(v_type, 0) + 1
        
        # Calculate fraud score
        fraud_score = self._calculate_fraud_score(violations)
        risk_level = self._determine_risk_level(fraud_score, len(violations))
        
        return ViolationAnalytics(
            total_violations=len(violations),
            violations_by_severity=violations_by_severity,
            violations_by_type=violations_by_type,
            violation_timeline=[{
                "timestamp": v["detected_at"].isoformat() if v.get("detected_at") else datetime.utcnow().isoformat(),
                "type": v.get("violation_type", "unknown"),
                "severity": v.get("severity", "low"),
                "description": v.get("description", "")
            } for v in violations if isinstance(v, dict)],
            fraud_score=fraud_score,
            is_flagged=fraud_score > 0.5,
            risk_level=risk_level
        )

    def _calculate_fraud_score(self, violations: List[Dict]) -> float:
        """Calculate fraud score based on violations"""
        if not violations:
            return 0.0
        
        severity_weights = {"low": 0.1, "medium": 0.3, "high": 0.7, "critical": 1.0}
        total_weight = sum(severity_weights.get(v.get("severity", "low"), 0.1) for v in violations)
        
        # Normalize to 0-1 scale
        max_possible = len(violations) * 1.0  # Assuming all critical
        return min(total_weight / max_possible, 1.0) if max_possible > 0 else 0.0

    def _determine_risk_level(self, fraud_score: float, violation_count: int) -> str:
        """Determine risk level based on fraud score and violation count"""
        if fraud_score >= 0.8 or violation_count >= 10:
            return "critical"
        elif fraud_score >= 0.5 or violation_count >= 5:
            return "high"
        elif fraud_score >= 0.2 or violation_count >= 2:
            return "medium"
        else:
            return "low"

    async def _generate_class_comparison(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> ClassComparison:
        """Generate class comparison analytics"""
        db = await self._get_db()
        
        # Get all sessions for this exam
        all_sessions = await db.exam_sessions.find({
            "exam_id": exam["_id"],
            "status": "submitted"
        }).to_list(length=None)
        
        if not all_sessions:
            # Return default comparison if no other sessions
            return ClassComparison(
                class_average_score=exam_session.get("score", 0),
                class_highest_score=exam_session.get("score", 0),
                class_lowest_score=exam_session.get("score", 0),
                student_rank=1,
                total_participants=1,
                percentile=100.0,
                above_average=True,
                score_distribution=[]
            )
        
        # Calculate class statistics
        scores = [session.get("score", 0) for session in all_sessions]
        student_score = exam_session.get("score", 0)
        
        class_average = sum(scores) / len(scores)
        class_highest = max(scores)
        class_lowest = min(scores)
        
        # Calculate rank (1 = highest)
        sorted_scores = sorted(scores, reverse=True)
        student_rank = sorted_scores.index(student_score) + 1
        
        # Calculate percentile
        scores_below = len([s for s in scores if s < student_score])
        percentile = (scores_below / len(scores)) * 100 if len(scores) > 0 else 100
        
        # Create score distribution
        score_ranges = [(i*10, (i+1)*10) for i in range(10)]  # 0-10, 10-20, etc.
        distribution = []
        
        for min_score, max_score in score_ranges:
            count = len([s for s in scores if min_score <= s < max_score])
            if count > 0:
                distribution.append({
                    "range": f"{min_score}-{max_score}",
                    "count": count,
                    "percentage": (count / len(scores)) * 100
                })
        
        return ClassComparison(
            class_average_score=class_average,
            class_highest_score=class_highest,
            class_lowest_score=class_lowest,
            student_rank=student_rank,
            total_participants=len(all_sessions),
            percentile=percentile,
            above_average=student_score > class_average,
            score_distribution=distribution
        )

    async def _generate_question_difficulty_analysis(
        self, 
        exam: Dict
    ) -> List[QuestionDifficultyAnalysis]:
        """Analyze question difficulty based on class performance"""
        db = await self._get_db()
        analysis = []
        
        # Get all sessions for this exam
        all_sessions = await db.exam_sessions.find({
            "exam_id": exam["_id"],
            "status": "submitted"
        }).to_list(length=None)
        
        if not all_sessions:
            return analysis
        
        # Analyze each question - handle different structures
        questions_to_analyze = []
        if "questions" in exam:
            questions_to_analyze = exam.get("questions", [])
        else:
            # Create question objects from question_ids
            for idx, question_id in enumerate(exam.get("question_ids", [])):
                questions_to_analyze.append({
                    "question_id": question_id,
                    "position": idx + 1,
                    "points": 1
                })
        
        for q in questions_to_analyze:
            question_id = str(q["question_id"])
            
            # Get question details
            question_doc = await db.questions.find_one({"_id": ObjectId(question_id)})
            if not question_doc:
                continue
            
            # Calculate class accuracy for this question
            correct_answers = 0
            total_answers = 0
            total_time = 0
            time_count = 0
            
            for session in all_sessions:
                for answer in session.get("answers", []):
                    if str(answer["question_id"]) == question_id:
                        total_answers += 1
                        if answer.get("is_correct", False):
                            correct_answers += 1
                        if answer.get("time_spent"):
                            total_time += answer["time_spent"]
                            time_count += 1
            
            if total_answers == 0:
                continue
            
            class_accuracy = correct_answers / total_answers
            avg_time = total_time / time_count if time_count > 0 else 0
            
            # Determine actual difficulty based on performance
            if class_accuracy >= 0.8:
                actual_difficulty = "easy"
            elif class_accuracy >= 0.5:
                actual_difficulty = "medium"
            else:
                actual_difficulty = "hard"
            
            # Time difficulty score (higher = more difficult)
            time_difficulty_score = avg_time / 60 if avg_time > 0 else 0  # Convert to minutes
            
            # Check if problematic (big discrepancy between intended and actual)
            intended_difficulty = question_doc.get("difficulty", "medium")
            difficulty_order = {"easy": 1, "medium": 2, "hard": 3}
            is_problematic = abs(
                difficulty_order[actual_difficulty] - difficulty_order[intended_difficulty]
            ) >= 2
            
            analysis.append(QuestionDifficultyAnalysis(
                question_id=ObjectId(question_id),
                intended_difficulty=intended_difficulty,
                actual_difficulty=actual_difficulty,
                class_accuracy=class_accuracy,
                time_difficulty_score=time_difficulty_score,
                is_problematic=is_problematic
            ))
        
        return analysis

    # Continue in next part...
    async def _analyze_answer_patterns(self, exam_session: Dict) -> Dict[str, Any]:
        """Analyze answer patterns (streaks, clustering, etc.)"""
        answers = exam_session.get("answers", [])
        if not isinstance(answers, list):
            answers = []
        
        # Filter and sort by position or timestamp - only process valid dictionaries
        valid_answers = [a for a in answers if isinstance(a, dict)]
        sorted_answers = sorted(valid_answers, key=lambda x: x.get("position", 0))
        
        # Calculate streaks
        current_correct_streak = 0
        current_wrong_streak = 0
        max_correct_streak = 0
        max_wrong_streak = 0
        
        for answer in sorted_answers:
            if answer.get("is_correct", False):
                current_correct_streak += 1
                current_wrong_streak = 0
                max_correct_streak = max(max_correct_streak, current_correct_streak)
            else:
                current_wrong_streak += 1
                current_correct_streak = 0
                max_wrong_streak = max(max_wrong_streak, current_wrong_streak)
        
        # Analyze question order vs accuracy
        early_accuracy = 0  # First 25%
        mid_accuracy = 0    # Middle 50%
        late_accuracy = 0   # Last 25%
        
        total_questions = len(sorted_answers)
        if total_questions > 0:
            early_count = max(1, total_questions // 4)
            late_start = total_questions - early_count
            
            early_correct = sum(1 for a in sorted_answers[:early_count] if a.get("is_correct"))
            late_correct = sum(1 for a in sorted_answers[late_start:] if a.get("is_correct"))
            mid_correct = sum(1 for a in sorted_answers[early_count:late_start] if a.get("is_correct"))
            
            early_accuracy = early_correct / early_count if early_count > 0 else 0
            late_accuracy = late_correct / early_count if early_count > 0 else 0
            mid_count = late_start - early_count
            mid_accuracy = mid_correct / mid_count if mid_count > 0 else 0
        
        return {
            "max_correct_streak": max_correct_streak,
            "max_wrong_streak": max_wrong_streak,
            "early_performance": early_accuracy,
            "mid_performance": mid_accuracy,
            "late_performance": late_accuracy,
            "performance_trend": "improving" if late_accuracy > early_accuracy else 
                               "declining" if late_accuracy < early_accuracy else "stable",
            "consistency_score": 1.0 - abs(early_accuracy - late_accuracy)  # Higher = more consistent
        }

    async def _analyze_time_allocation(self, exam_session: Dict, exam: Dict) -> Dict[str, Any]:
        """Analyze time allocation patterns"""
        answers = exam_session.get("answers", [])
        if not isinstance(answers, list):
            answers = []
            
        total_duration = exam.get("duration", exam.get("duration_minutes", 60)) * 60  # Convert to seconds
        
        # Calculate time spent per question
        time_per_question = []
        total_time_accounted = 0
        
        for answer in answers:
            if not isinstance(answer, dict):
                continue
                
            time_spent = answer.get("time_spent", 0)
            if isinstance(time_spent, (int, float)) and time_spent > 0:
                time_per_question.append(time_spent)
                total_time_accounted += time_spent
        
        if not time_per_question:
            return {"error": "No timing data available"}
        
        avg_time = sum(time_per_question) / len(time_per_question)
        
        # Categorize questions by time spent
        quick_answers = len([t for t in time_per_question if t < avg_time * 0.5])
        normal_answers = len([t for t in time_per_question if avg_time * 0.5 <= t <= avg_time * 1.5])
        slow_answers = len([t for t in time_per_question if t > avg_time * 1.5])
        
        # Time efficiency
        time_efficiency = total_time_accounted / total_duration if total_duration > 0 else 1.0
        
        return {
            "average_time_per_question": avg_time,
            "total_time_accounted": total_time_accounted,
            "time_efficiency": min(time_efficiency, 1.0),
            "quick_answers_count": quick_answers,
            "normal_answers_count": normal_answers,
            "slow_answers_count": slow_answers,
            "time_distribution": {
                "quick_percentage": quick_answers / len(time_per_question) * 100,
                "normal_percentage": normal_answers / len(time_per_question) * 100,
                "slow_percentage": slow_answers / len(time_per_question) * 100
            }
        }

    async def _generate_behavioral_insights(
        self, 
        exam_session: Dict, 
        performance: PerformanceMetrics,
        violations: ViolationAnalytics
    ) -> List[str]:
        """Generate behavioral insights based on exam data"""
        insights = []
        
        # Performance insights
        if performance.accuracy_percentage >= 90:
            insights.append("Excellent mastery of the subject matter")
        elif performance.accuracy_percentage >= 70:
            insights.append("Good understanding with room for improvement")
        elif performance.accuracy_percentage >= 50:
            insights.append("Average performance - focus on weak areas")
        else:
            insights.append("Significant improvement needed in subject mastery")
        
        # Time management insights
        if performance.average_time_per_question < 30:  # 30 seconds
            insights.append("Very fast response times - consider reviewing answers carefully")
        elif performance.average_time_per_question > 180:  # 3 minutes
            insights.append("Slow response times - practice time management techniques")
        
        # Completion insights
        if performance.completion_percentage < 100:
            insights.append(f"Incomplete exam - {performance.unanswered_questions} questions unanswered")
        
        # Violation insights
        if violations.total_violations == 0:
            insights.append("Excellent exam conduct with no violations")
        elif violations.total_violations <= 2:
            insights.append("Minor violations detected - maintain focus during exams")
        else:
            insights.append("Multiple violations detected - review exam conduct guidelines")
        
        # Pattern-based insights
        answers = exam_session.get("answers", [])
        if not isinstance(answers, list):
            answers = []
            
        valid_answers = [a for a in answers if isinstance(a, dict)]
        if valid_answers:
            change_counts = [a.get("change_count", 0) for a in valid_answers if isinstance(a.get("change_count", 0), (int, float))]
            avg_changes = sum(change_counts) / len(change_counts) if change_counts else 0
            
            if avg_changes > 2:
                insights.append("High answer revision rate - indicates uncertainty or second-guessing")
            elif avg_changes < 0.5:
                insights.append("Low answer revision rate - shows confidence in initial responses")
        
        return insights[:5]  # Limit to top 5 insights

    async def _generate_recommendations(
        self, 
        performance: PerformanceMetrics,
        violations: ViolationAnalytics,
        class_comparison: ClassComparison
    ) -> List[str]:
        """Generate recommendations for the student"""
        recommendations = []
        
        # Performance-based recommendations
        if performance.accuracy_percentage < 70:
            recommendations.append("Focus on reviewing fundamental concepts in this subject")
            recommendations.append("Consider forming study groups or seeking additional help")
        
        if performance.completion_percentage < 100:
            recommendations.append("Practice time management to complete all questions")
            recommendations.append("Take practice tests to improve exam pacing")
        
        # Comparison-based recommendations
        if not class_comparison.above_average:
            recommendations.append("Review class materials and compare with top performers")
            recommendations.append("Analyze your mistakes to identify knowledge gaps")
        
        # Violation-based recommendations
        if violations.total_violations > 0:
            recommendations.append("Review exam conduct guidelines to avoid future violations")
            if "tab_switch" in violations.violations_by_type:
                recommendations.append("Avoid switching browser tabs during exams")
            if "text_selection" in violations.violations_by_type:
                recommendations.append("Avoid selecting/copying text during exams")
        
        # Time management recommendations
        if performance.average_time_per_question > 120:  # 2 minutes
            recommendations.append("Practice answering questions more quickly")
            recommendations.append("Learn to identify easy questions and answer them first")
        
        return recommendations[:5]  # Limit to top 5 recommendations

    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================

    async def _save_analytics(self, analytics: ExamSessionAnalytics) -> bool:
        """Save analytics to database"""
        db = await self._get_db()
        
        analytics_dict = analytics.dict()
        analytics_dict["_id"] = analytics_dict["exam_session_id"]
        
        try:
            await db.exam_analytics.replace_one(
                {"exam_session_id": analytics.exam_session_id},
                analytics_dict,
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")
            return False

    async def get_cached_analytics(self, exam_session_id: str) -> Optional[ExamSessionAnalytics]:
        """Get cached analytics if available and not expired"""
        db = await self._get_db()
        
        try:
            cached = await db.exam_analytics.find_one({
                "exam_session_id": ObjectId(exam_session_id),
                "cache_expires_at": {"$gt": datetime.utcnow()}
            })
            
            if cached:
                return ExamSessionAnalytics(**cached)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached analytics: {e}")
            return None

    async def get_analytics_summary(self, exam_session_id: str) -> Optional[ExamAnalyticsSummary]:
        """Get analytics summary for quick access"""
        db = await self._get_db()
        
        try:
            analytics = await db.exam_analytics.find_one({
                "exam_session_id": ObjectId(exam_session_id)
            })
            
            if not analytics:
                return None
                
            # Get student name
            student = await db.users.find_one({"_id": analytics["student_id"]})
            student_name = f"{student.get('first_name', '')} {student.get('last_name', '')}" if student else "Unknown"
            
            # Validate the nested fields existence and types before accessing them
            performance_metrics = analytics.get("performance_metrics", {})
            if not isinstance(performance_metrics, dict):
                performance_metrics = {}
                
            class_comparison = analytics.get("class_comparison", {})
            if not isinstance(class_comparison, dict):
                class_comparison = {}
                
            violation_analytics = analytics.get("violation_analytics", {})
            if not isinstance(violation_analytics, dict):
                violation_analytics = {}
            
            return ExamAnalyticsSummary(
                exam_session_id=analytics["exam_session_id"],
                student_name=student_name,
                exam_title=analytics.get("exam_title", "Unknown Exam"),
                score=performance_metrics.get("score", 0),
                accuracy=performance_metrics.get("accuracy_percentage", 0),
                completion=performance_metrics.get("completion_percentage", 0),
                rank_in_class=class_comparison.get("student_rank", 0),
                total_violations=violation_analytics.get("total_violations", 0),
                risk_level=violation_analytics.get("risk_level", "low"),
                duration_taken=analytics.get("duration_taken", 0),
                is_flagged=violation_analytics.get("is_flagged", False),
                generated_at=analytics.get("generated_at", datetime.utcnow())
            )
            
        except Exception as e:
            logger.error(f"Error in get_analytics_summary: {e}")
            return None

    async def delete_analytics(self, exam_session_id: str) -> bool:
        """Delete analytics data"""
        db = await self._get_db()
        
        try:
            result = await db.exam_analytics.delete_one({
                "exam_session_id": ObjectId(exam_session_id)
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete analytics: {e}")
            return False

# Global instance
exam_analytics_crud = ExamAnalyticsCRUD()
