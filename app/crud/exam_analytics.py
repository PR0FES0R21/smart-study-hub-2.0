# ==============================================================================
# File: app/crud/exam_analytics.py
# Deskripsi: CRUD operations untuk analytics hasil ujian
# ==============================================================================

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
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
                
                # Get teacher profile for full name
                teacher_profile = None
                if teacher and teacher.get("profile_id"):
                    teacher_profile = await db.profiles.find_one({"_id": teacher["profile_id"]})
                
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
            question_difficulty_analysis = await self._generate_question_difficulty_analysis(exam, exam_session)
            logger.debug("Question difficulty analysis generated successfully")
        except Exception as e:
            logger.error(f"Error generating question difficulty analysis: {e}")
            raise
        
        # Generate advanced analytics with error handling
        try:
            answer_pattern_analysis = await self._analyze_answer_patterns(exam_session, questions_analytics)
            logger.debug(f"Answer pattern analysis generated successfully: {answer_pattern_analysis}")
        except Exception as e:
            logger.error(f"Error generating answer pattern analysis: {e}")
            logger.exception("Full traceback for answer pattern analysis:")
            # Provide default values
            answer_pattern_analysis = {
                "max_correct_streak": 0,
                "max_wrong_streak": 0,
                "early_performance": 0,
                "mid_performance": 0,
                "late_performance": 0,
                "performance_trend": "stable",
                "consistency_score": 1.0,
                "error": f"Calculation error: {str(e)}"
            }
            
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
                teacher_name=teacher_profile.get('full_name', "Tidak Diketahui") if teacher_profile else "Tidak Diketahui",
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
        """Generate performance metrics for new data format"""
        # Use completion_stats if available (new format)
        completion_stats = exam_session.get("completion_stats", {})
        
        if completion_stats:
            # New format - use pre-calculated stats
            total_questions = completion_stats.get("total_questions", 0)
            answered_questions = completion_stats.get("answered_questions", 0)
            completion_percentage = completion_stats.get("completion_percentage", 0)
        else:
            # Fallback to old format calculation
            answers = exam_session.get("answers", {})
            if isinstance(answers, dict):
                # New format: answers is a dict {question_id: answer}
                answered_questions = len([v for v in answers.values() if v])
                total_questions = len(exam_session.get("question_map", []))
            else:
                # Old format: answers is a list
                answers = answers if isinstance(answers, list) else []
                answered_questions = len([a for a in answers if isinstance(a, dict) and (a.get("selected_option") or a.get("answer_text"))])
                total_questions = len(exam.get("question_ids", exam.get("questions", [])))
            
            completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
        
        unanswered_questions = total_questions - answered_questions
        
        # Calculate correct/wrong answers with fallback for missing questions DB
        correct_answers = await self._calculate_correct_answers(exam_session, exam)
        
        # Fallback: if questions DB is empty, estimate from score
        if correct_answers == 0 and exam_session.get("score", 0) > 0:
            # Estimate based on score - this is not perfect but better than 0
            max_possible = await self._calculate_max_possible_score(exam_session, exam)
            current_score = exam_session.get("score", 0)
            if max_possible > 0:
                estimated_accuracy = current_score / max_possible
                correct_answers = int(answered_questions * estimated_accuracy)
                logger.info(f"Using score-based estimation: {correct_answers} correct answers from score {current_score}/{max_possible}")
        
        wrong_answers = answered_questions - correct_answers
        
        # Calculate percentages
        accuracy_percentage = (correct_answers / answered_questions * 100) if answered_questions > 0 else 0
        
        # Calculate time metrics from interaction_logs (new format)
        interaction_logs = exam_session.get("interaction_logs", [])
        time_per_question = await self._calculate_time_per_question(interaction_logs)
        
        total_time = (exam_session["submitted_at"] - exam_session["started_at"]).total_seconds() if exam_session.get("submitted_at") and exam_session.get("started_at") else 0
        avg_time_per_question = sum(time_per_question) / len(time_per_question) if time_per_question else 0
        fastest_answer = min(time_per_question) if time_per_question else 0
        slowest_answer = max(time_per_question) if time_per_question else 0
        
        # Get scores
        score = exam_session.get("score", 0)
        max_possible_score = await self._calculate_max_possible_score(exam_session, exam)

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
        """Generate analytics untuk setiap soal - new format"""
        db = await self._get_db()
        questions_data = []
        
        # Get data from new format
        answers = exam_session.get("answers", {})  # Dict format: {question_id: answer}
        question_map = exam_session.get("question_map", [])  # Position mapping
        interaction_logs = exam_session.get("interaction_logs", [])  # Timing and changes
        
        if not isinstance(answers, dict) or not question_map:
            logger.warning("Invalid or missing question data in new format")
            return questions_data
        
        # Create lookup for interaction data
        interaction_lookup = {}
        change_count_lookup = {}
        
        for log in interaction_logs:
            q_id = str(log.get("question_id", ""))
            if q_id:
                if q_id not in interaction_lookup:
                    interaction_lookup[q_id] = []
                    change_count_lookup[q_id] = 0
                    
                interaction_lookup[q_id].append(log)
                if log.get("action") in ["answer_updated", "answer_submitted"]:
                    change_count_lookup[q_id] += 1
        
        # Process each question from question_map
        for q_map in question_map:
            if not isinstance(q_map, dict):
                continue
                
            question_id = q_map.get("question_id")
            if not question_id:
                continue
                
            question_id_str = str(question_id)
            
            try:
                # Get student's final answer from answers dict first
                student_answer = answers.get(question_id_str)
                
                # Get question details from database (fix: use question_banks collection)
                question_doc = await db.question_banks.find_one({"_id": question_id})
                if not question_doc:
                    logger.warning(f"Question {question_id} not found in database - using fallback")
                    
                    # Fallback: Create dummy question data
                    inferred_type = "essay" if isinstance(student_answer, str) and student_answer and not ObjectId.is_valid(str(student_answer)) else "multiple_choice"
                    question_doc = {
                        "_id": question_id,
                        "question_text": f"[Question {q_map.get('position', 'N/A')} - Data not found]",
                        "question_type": inferred_type,
                        "type": inferred_type,  # Backward compatibility
                        "difficulty": "medium",
                        "points": 10,
                        "options": []
                    }
                
                # Determine correct answer based on question type
                question_type = question_doc.get("question_type", question_doc.get("type", "unknown"))
                
                if question_type == "multiple_choice":
                    # Find the correct option (options use 'id' field, not '_id')
                    correct_option = next((opt for opt in question_doc.get("options", []) if opt.get("is_correct")), None)
                    correct_answer = str(correct_option["id"]) if correct_option else None
                    correct_answer_text = correct_option.get("text", "") if correct_option else ""
                    
                    # Get student answer text for multiple choice
                    if student_answer:
                        # Find selected option using 'id' field
                        selected_option = next((opt for opt in question_doc.get("options", []) 
                                              if str(opt["id"]) == str(student_answer)), None)
                        
                        student_answer_text = selected_option.get("text", "Jawaban tidak ditemukan") if selected_option else "Jawaban tidak valid"
                    else:
                        student_answer_text = "Tidak dijawab"
                        
                else:
                    # Essay question - no automatic scoring for essays!
                    correct_answer = ""
                    correct_answer_text = "Perlu dinilai manual"
                    student_answer_text = str(student_answer) if student_answer else "Tidak dijawab"
                
                # Check if answer is correct
                is_correct = False
                if student_answer:
                    if question_type == "multiple_choice" and correct_answer:
                        is_correct = str(student_answer) == correct_answer
                    elif question_type == "essay":
                        # For essay questions, we cannot determine correctness automatically
                        # Check if there's a manual grade/score for this question
                        # For now, we'll use the overall score to estimate
                        question_points = question_doc.get("points", 10)
                        total_score = exam_session.get("score", 0)
                        total_questions = len(exam_session.get("question_map", []))
                        
                        # If this is the only question contributing to score, estimate correctness
                        if total_questions > 0:
                            expected_score_per_question = total_score / total_questions
                            # If expected score per question >= 50% of max points, consider correct
                            is_correct = expected_score_per_question >= (question_points * 0.5)
                        else:
                            is_correct = False
                    else:
                        # Unknown question type - try to infer from answer format
                        if ObjectId.is_valid(str(student_answer)):
                            # Looks like MC option ID, check against options
                            if question_doc.get("options") and correct_answer:
                                is_correct = str(student_answer) == correct_answer
                        else:
                            # Text answer, assume essay-like
                            is_correct = False  # Cannot determine without manual grading
                
                # Calculate time spent from interaction logs
                question_interactions = interaction_lookup.get(question_id_str, [])
                time_spent = 0
                answer_timestamp = None
                
                if question_interactions:
                    # Sort interactions by timestamp
                    sorted_interactions = sorted(question_interactions, key=lambda x: x.get("timestamp", datetime.min))
                    
                    if len(sorted_interactions) >= 2:
                        # Time between first and last interaction for this question
                        first = sorted_interactions[0]
                        last = sorted_interactions[-1]
                        if first.get("timestamp") and last.get("timestamp"):
                            time_spent = (last["timestamp"] - first["timestamp"]).total_seconds()
                    
                    # Get last interaction timestamp
                    answer_timestamp = sorted_interactions[-1].get("timestamp")
                elif student_answer:
                    # If no interaction logs but has answer, use default time
                    time_spent = 30  # Default 30 seconds
                
                # Get points for this question
                question_points = question_doc.get("points", 10)
                points_earned = question_points if is_correct else 0
                
                questions_data.append(QuestionAnalytics(
                    question_id=question_id,
                    original_position=q_map.get("position", 0),
                    displayed_position=q_map.get("position", 0),
                    question_text=question_doc.get("question_text", ""),
                    question_type=question_type,
                    difficulty=question_doc.get("difficulty", "medium"),
                    points=question_points,
                    student_answer=str(student_answer) if student_answer else None,
                    correct_answer=correct_answer,
                    student_answer_text=student_answer_text,
                    correct_answer_text=correct_answer_text,
                    is_correct=is_correct,
                    points_earned=points_earned,
                    time_spent=time_spent,
                    answer_timestamp=answer_timestamp,
                    change_count=change_count_lookup.get(question_id_str, 0),
                    options=[{
                        "id": str(opt["id"]),
                        "text": opt["text"],
                        "is_correct": opt.get("is_correct", False)
                    } for opt in question_doc.get("options", [])]
                ))
                
                # Debug logging for options
                if question_doc.get("type") == "multiple_choice":
                    options_count = len(question_doc.get("options", []))
                    logger.debug(f"Question {question_id_str} ({question_doc.get('type')}) has {options_count} options")
                    if options_count == 0:
                        logger.warning(f"Question {question_id_str} is multiple_choice but has no options in database!")
                
                logger.debug(f"Processed question {question_id_str}: answered={bool(student_answer)}, correct={is_correct}")
                
            except Exception as e:
                logger.error(f"Error processing question {question_id}: {e}")
                continue
        
        return questions_data

    async def _generate_timeline_events(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> List[TimelineEvent]:
        """Generate timeline events dari exam session - new format"""
        events = []
        
        # Answer submission events from interaction_logs (new format)
        interaction_logs = exam_session.get("interaction_logs", [])
        if isinstance(interaction_logs, list):
            for log in interaction_logs:
                if not isinstance(log, dict) or not log.get("timestamp"):
                    continue
                    
                # Determine if answer is correct (need to check against correct answer)
                is_correct = await self._is_answer_correct_from_log(log, exam_session)
                
                events.append(TimelineEvent(
                    timestamp=log["timestamp"],
                    event_type=log.get("action", "answer_submitted"),
                    question_id=log.get("question_id"),
                    displayed_position=log.get("displayed_position"),
                    is_correct=is_correct,
                    details={
                        "answer": log.get("student_answer", ""),
                        "action": log.get("action", "")
                    }
                ))
        
        # Violation events (new format with better structure)
        violations = exam_session.get("violations", [])
        if isinstance(violations, list):
            for violation in violations:
                if not isinstance(violation, dict) or not violation.get("timestamp"):
                    continue
                    
                events.append(TimelineEvent(
                    timestamp=violation["timestamp"],
                    event_type="violation",
                    details={
                        "violation_type": violation.get("type", "unknown"),
                        "severity": violation.get("severity", "low"),
                        "description": violation.get("details", "")
                    }
                ))
        
        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp)
        
        # Add cumulative scores
        cumulative_score = 0
        for event in events:
            if event.event_type in ["answer_submitted", "answer_updated"] and event.is_correct:
                cumulative_score += 1
            event.cumulative_score = cumulative_score
        
        return events
    
    async def _is_answer_correct_from_log(self, log: Dict, exam_session: Dict) -> bool:
        """Check if answer in interaction log is correct"""
        try:
            question_id = log.get("question_id")
            student_answer = log.get("student_answer")
            
            if not question_id or not student_answer:
                return False
            
            # Get final answer from exam_session.answers (more reliable)
            final_answers = exam_session.get("answers", {})
            question_id_str = str(question_id)
            final_answer = final_answers.get(question_id_str)
            
            # Only check correctness if this interaction's answer matches the final answer
            if str(student_answer) != str(final_answer):
                return False  # This is not the final answer, so mark as incorrect for timeline
            
            db = await self._get_db()
            question = await db.question_banks.find_one({"_id": question_id})
            
            if not question:
                # Fallback: essay questions with text are considered correct
                if not ObjectId.is_valid(str(student_answer)):
                    return bool(str(student_answer).strip())
                return False
            
            question_type = question.get("question_type", question.get("type", "unknown"))
            if question_type == "multiple_choice":
                correct_option = next((opt for opt in question.get("options", []) if opt.get("is_correct")), None)
                return correct_option and str(correct_option["id"]) == str(student_answer)
            else:
                # For essay, assume correct if answered
                return bool(str(student_answer).strip())
                
        except Exception as e:
            logger.debug(f"Error checking answer correctness in timeline: {e}")
            return False

    async def _generate_score_timeline(
        self, 
        exam_session: Dict, 
        exam: Dict
    ) -> List[ScoreTimeline]:
        """Generate score timeline progresif from interaction logs - simplified"""
        timeline = []
        cumulative_correct = 0
        cumulative_wrong = 0
        cumulative_score = 0
        processed_questions = set()
        
        try:
            db = await self._get_db()
            
            # Get interaction logs and sort by timestamp
            interaction_logs = exam_session.get("interaction_logs", [])
            if not isinstance(interaction_logs, list):
                logger.warning("No interaction logs found for score timeline")
                return timeline
                
            # Filter for answer submissions/updates only and sort
            answer_interactions = [log for log in interaction_logs 
                                  if log.get("action") in ["answer_submitted", "answer_updated"]
                                  and log.get("timestamp")
                                  and log.get("question_id")]
            
            if not answer_interactions:
                logger.warning("No answer interactions found for score timeline")
                return timeline
            
            # Sort by timestamp
            sorted_interactions = sorted(answer_interactions, key=lambda x: x["timestamp"])
            logger.info(f"Processing {len(sorted_interactions)} interactions for score timeline")
            
            answers_dict = exam_session.get("answers", {})
            
            for interaction in sorted_interactions:
                try:
                    question_id = interaction.get("question_id")
                    question_id_str = str(question_id)
                    
                    # Skip if we've already processed this question's final answer
                    if question_id_str in processed_questions:
                        continue
                    
                    # Get the final answer for this question
                    final_answer = answers_dict.get(question_id_str)
                    if not final_answer:
                        continue
                    
                    # Check if this final answer is correct
                    question_doc = await db.question_banks.find_one({"_id": question_id})
                    if not question_doc:
                        logger.warning(f"Question {question_id} not found in database")
                        continue
                    
                    is_correct = False
                    points_for_question = question_doc.get("points", 10)
                    
                    question_type = question_doc.get("question_type", question_doc.get("type", "unknown"))
                    if question_type == "multiple_choice":
                        correct_option = next((opt for opt in question_doc.get("options", []) if opt.get("is_correct")), None)
                        is_correct = correct_option and str(correct_option.get("id", "")) == str(final_answer)
                    else:
                        # Essay - cannot determine correctness automatically
                        # Use score-based estimation instead
                        is_correct = False  # Conservative approach for essays
                    
                    # Update cumulative stats
                    if is_correct:
                        cumulative_correct += 1
                        score_change = points_for_question
                        cumulative_score += points_for_question
                    else:
                        cumulative_wrong += 1
                        score_change = 0
                    
                    # Find the timestamp when this question was last answered
                    question_interactions = [log for log in sorted_interactions if str(log.get("question_id", "")) == question_id_str]
                    latest_timestamp = max(q_int.get("timestamp") for q_int in question_interactions) if question_interactions else interaction["timestamp"]
                    
                    timeline.append(ScoreTimeline(
                        timestamp=latest_timestamp,
                        question_position=interaction.get("displayed_position", 0),
                        question_id=question_id,
                        is_correct=is_correct,
                        cumulative_correct=cumulative_correct,
                        cumulative_wrong=cumulative_wrong,
                        cumulative_score=cumulative_score,
                        score_change=score_change
                    ))
                    
                    processed_questions.add(question_id_str)
                    
                    logger.debug(f"Score timeline: Q{interaction.get('displayed_position')} - {'CORRECT' if is_correct else 'WRONG'}, score: +{score_change}, cumulative: {cumulative_score}")
                    
                except Exception as e:
                    logger.warning(f"Error processing interaction for score timeline: {e}")
                    continue
            
            logger.info(f"Generated score timeline with {len(timeline)} events")
            
        except Exception as e:
            logger.error(f"Error generating score timeline: {e}")
        
        return timeline

    async def _generate_violation_analytics(
        self, 
        exam_session: Dict
    ) -> ViolationAnalytics:
        """Generate analytics untuk violations - new format"""
        violations = exam_session.get("violations", [])
        if not isinstance(violations, list):
            violations = []
        
        # Count by severity and type (new format has different field names)
        violations_by_severity = {}
        violations_by_type = {}
        
        for v in violations:
            if not isinstance(v, dict):
                continue
                
            # New format uses 'severity' and 'type' fields
            severity = v.get("severity", "low")
            v_type = v.get("type", "unknown")
            
            violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1
            violations_by_type[v_type] = violations_by_type.get(v_type, 0) + 1
        
        # Use pre-calculated fraud score if available
        fraud_score = exam_session.get("fraud_score", self._calculate_fraud_score(violations))
        is_flagged = exam_session.get("is_flagged_for_review", fraud_score > 0.5)
        risk_level = self._determine_risk_level(fraud_score, len(violations))
        
        return ViolationAnalytics(
            total_violations=len(violations),
            violations_by_severity=violations_by_severity,
            violations_by_type=violations_by_type,
            violation_timeline=[{
                "timestamp": v["timestamp"].isoformat() if v.get("timestamp") else datetime.utcnow().isoformat(),
                "type": v.get("type", "unknown"),
                "severity": v.get("severity", "low"),
                "description": v.get("details", "")
            } for v in violations if isinstance(v, dict)],
            fraud_score=fraud_score,
            is_flagged=is_flagged,
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
        exam: Dict,
        exam_session: Dict = None
    ) -> List[QuestionDifficultyAnalysis]:
        """Analyze question difficulty based on class performance - new format"""
        db = await self._get_db()
        analysis = []
        
        # Get all sessions for this exam with status graded or submitted
        all_sessions = await db.exam_sessions.find({
            "exam_id": exam["_id"],
            "status": {"$in": ["submitted", "graded"]}
        }).to_list(length=None)
        
        if not all_sessions:
            logger.info("No exam sessions found for difficulty analysis - creating default analysis")
            # Create default difficulty analysis based on current session only
            current_answers = exam_session.get("answers", {})
            current_question_map = exam_session.get("question_map", [])
            
            for q_map in current_question_map:
                question_id = q_map.get("question_id")
                if not question_id:
                    continue
                    
                question_id_str = str(question_id)
                
                try:
                    question_doc = await db.question_banks.find_one({"_id": question_id})
                    if not question_doc:
                        continue
                    
                    # Single student analysis - basic difficulty
                    student_answer = current_answers.get(question_id_str)
                    is_correct = False
                    
                    question_type = question_doc.get("question_type", question_doc.get("type", "unknown"))
                    if student_answer and question_type == "multiple_choice":
                        correct_option = next((opt for opt in question_doc.get("options", []) if opt.get("is_correct")), None)
                        is_correct = correct_option and str(correct_option["id"]) == str(student_answer)
                    elif student_answer and question_type == "essay":
                        # Cannot determine essay correctness automatically
                        is_correct = False
                    
                    # Simple difficulty assessment
                    intended_difficulty = question_doc.get("difficulty", "medium")
                    actual_difficulty = "easy" if is_correct else "hard"
                    
                    analysis.append(QuestionDifficultyAnalysis(
                        question_id=question_id,
                        intended_difficulty=intended_difficulty,
                        actual_difficulty=actual_difficulty,
                        class_accuracy=1.0 if is_correct else 0.0,
                        time_difficulty_score=0.5,  # Default
                        is_problematic=intended_difficulty != actual_difficulty
                    ))
                    
                except Exception as e:
                    logger.warning(f"Error in default difficulty analysis for {question_id}: {e}")
                    continue
            
            logger.info(f"Created default difficulty analysis with {len(analysis)} questions")
            return analysis
        
        # Get list of questions from first session's question_map
        sample_session = all_sessions[0]
        question_map = sample_session.get("question_map", [])
        
        if not question_map:
            logger.warning("No question_map found for difficulty analysis")
            return analysis
        
        logger.info(f"Analyzing difficulty for {len(question_map)} questions across {len(all_sessions)} sessions")
        
        # Analyze each question
        for q_map in question_map:
            question_id = q_map.get("question_id")
            if not question_id:
                continue
                
            question_id_str = str(question_id)
            
            try:
                # Get question details
                question_doc = await db.question_banks.find_one({"_id": question_id})
                if not question_doc:
                    continue
                
                # Calculate class performance for this question
                correct_answers = 0
                total_answers = 0
                total_time = 0
                time_count = 0
                
                for session in all_sessions:
                    session_answers = session.get("answers", {})
                    if isinstance(session_answers, dict) and question_id_str in session_answers:
                        student_answer = session_answers[question_id_str]
                        
                        if student_answer:  # Only count answered questions
                            total_answers += 1
                            
                            # Check if correct (use proper 'id' field)
                            question_type = question_doc.get("question_type", question_doc.get("type", "unknown"))
                            if question_type == "multiple_choice":
                                correct_option = next((opt for opt in question_doc.get("options", []) if opt.get("is_correct")), None)
                                if correct_option and str(correct_option["id"]) == str(student_answer):
                                    correct_answers += 1
                            else:
                                # Essay - cannot determine correctness automatically
                                # Don't count essay answers as correct for difficulty analysis
                                pass
                            
                            # Calculate time (simplified - could be enhanced)
                            session_interaction_logs = session.get("interaction_logs", [])
                            question_interactions = [log for log in session_interaction_logs 
                                                   if str(log.get("question_id", "")) == question_id_str]
                            
                            if len(question_interactions) >= 2:
                                first = min(question_interactions, key=lambda x: x.get("timestamp", datetime.min))
                                last = max(question_interactions, key=lambda x: x.get("timestamp", datetime.min))
                                if first.get("timestamp") and last.get("timestamp"):
                                    q_time = (last["timestamp"] - first["timestamp"]).total_seconds()
                                    if 0 < q_time < 3600:  # Reasonable range
                                        total_time += q_time
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
                    difficulty_order.get(actual_difficulty, 2) - difficulty_order.get(intended_difficulty, 2)
                ) >= 2
                
                analysis.append(QuestionDifficultyAnalysis(
                    question_id=question_id,
                    intended_difficulty=intended_difficulty,
                    actual_difficulty=actual_difficulty,
                    class_accuracy=round(class_accuracy, 3),
                    time_difficulty_score=round(time_difficulty_score, 2),
                    is_problematic=is_problematic
                ))
                
                logger.debug(f"Difficulty analysis for question {question_id_str}: {class_accuracy:.2%} accuracy, {actual_difficulty} difficulty")
                
            except Exception as e:
                logger.warning(f"Error analyzing difficulty for question {question_id}: {e}")
                continue
        
        return analysis

    # Continue in next part...
    async def _analyze_answer_patterns(self, exam_session: Dict, questions_analytics: List = None) -> Dict[str, Any]:
        """Analyze answer patterns using questions analytics data"""
        
        # If questions_analytics is provided, use that (better approach)
        if questions_analytics:
            # Sort by displayed position
            sorted_questions = sorted(questions_analytics, key=lambda x: x.displayed_position if hasattr(x, 'displayed_position') else 0)
        else:
            # Fallback: create basic pattern from answers and question_map
            answers = exam_session.get("answers", {})
            question_map = exam_session.get("question_map", [])
            
            if not isinstance(answers, dict) or not question_map:
                return {
                    "max_correct_streak": 0,
                    "max_wrong_streak": 0,
                    "early_performance": 0,
                    "mid_performance": 0,
                    "late_performance": 0,
                    "performance_trend": "stable",
                    "consistency_score": 1.0,
                    "error": "Data tidak cukup untuk analisis pola"
                }
            
            # Create simplified analytics for pattern analysis
            db = await self._get_db()
            sorted_questions = []
            
            for q_map in sorted(question_map, key=lambda x: x.get("position", 0)):
                question_id = q_map.get("question_id")
                question_id_str = str(question_id)
                student_answer = answers.get(question_id_str)
                
                # Quick correctness check
                is_correct = False
                if student_answer:
                    try:
                        question_doc = await db.question_banks.find_one({"_id": question_id})
                        if question_doc:
                            question_type = question_doc.get("question_type", question_doc.get("type", "unknown"))
                            if question_type == "multiple_choice":
                                correct_option = next((opt for opt in question_doc.get("options", []) if opt.get("is_correct")), None)
                                is_correct = correct_option and str(correct_option["id"]) == str(student_answer)
                            else:
                                # Essay - cannot determine correctness automatically
                                is_correct = False
                    except Exception:
                        pass
                
                sorted_questions.append({
                    "displayed_position": q_map.get("position", 0),
                    "is_correct": is_correct
                })
        
        # Calculate streaks
        current_correct_streak = 0
        current_wrong_streak = 0
        max_correct_streak = 0
        max_wrong_streak = 0
        
        for question in sorted_questions:
            # Handle both dict and object types
            is_correct = False
            if hasattr(question, 'is_correct'):
                is_correct = question.is_correct
            elif isinstance(question, dict):
                is_correct = question.get("is_correct", False)
            
            if is_correct:
                current_correct_streak += 1
                current_wrong_streak = 0
                max_correct_streak = max(max_correct_streak, current_correct_streak)
            else:
                current_wrong_streak += 1
                current_correct_streak = 0
                max_wrong_streak = max(max_wrong_streak, current_wrong_streak)
        
        # Analyze performance by position (early, mid, late)
        total_questions = len(sorted_questions)
        early_accuracy = 0
        mid_accuracy = 0
        late_accuracy = 0
        
        if total_questions > 0:
            early_count = max(1, total_questions // 4)
            late_start = total_questions - early_count
            
            def get_is_correct(q):
                if hasattr(q, 'is_correct'):
                    return q.is_correct
                elif isinstance(q, dict):
                    return q.get("is_correct", False)
                return False
            
            early_correct = sum(1 for q in sorted_questions[:early_count] if get_is_correct(q))
            late_correct = sum(1 for q in sorted_questions[late_start:] if get_is_correct(q))
            mid_correct = sum(1 for q in sorted_questions[early_count:late_start] if get_is_correct(q))
            
            early_accuracy = early_correct / early_count if early_count > 0 else 0
            late_accuracy = late_correct / early_count if early_count > 0 else 0
            mid_count = late_start - early_count
            mid_accuracy = mid_correct / mid_count if mid_count > 0 else 0
        
        # Determine performance trend
        performance_trend = "stable"
        if total_questions > 2:  # Need minimum questions for trend analysis
            if late_accuracy > early_accuracy + 0.2:  # 20% improvement
                performance_trend = "meningkat"
            elif early_accuracy > late_accuracy + 0.2:  # 20% decline
                performance_trend = "menurun"
        
        return {
            "max_correct_streak": max_correct_streak,
            "max_wrong_streak": max_wrong_streak,
            "early_performance": round(early_accuracy, 3),
            "mid_performance": round(mid_accuracy, 3),
            "late_performance": round(late_accuracy, 3),
            "performance_trend": performance_trend,
            "consistency_score": round(1.0 - abs(early_accuracy - late_accuracy), 3),
            "total_analyzed_questions": total_questions
        }

    async def _analyze_time_allocation(self, exam_session: Dict, exam: Dict) -> Dict[str, Any]:
        """Analyze time allocation patterns from interaction logs"""
        interaction_logs = exam_session.get("interaction_logs", [])
        if not isinstance(interaction_logs, list) or not interaction_logs:
            return {"error": "Tidak ada data interaksi tersedia"}
            
        total_duration = exam.get("duration", exam.get("duration_minutes", 60)) * 60  # Convert to seconds
        
        # Group interactions by question to calculate time per question
        question_times = {}
        
        # Sort interactions by timestamp
        sorted_logs = sorted([log for log in interaction_logs if log.get("timestamp")], 
                           key=lambda x: x["timestamp"])
        
        # Calculate time between consecutive interactions
        time_per_question = []
        
        for i in range(len(sorted_logs) - 1):
            current_log = sorted_logs[i]
            next_log = sorted_logs[i + 1]
            
            current_qid = str(current_log.get("question_id", ""))
            next_qid = str(next_log.get("question_id", ""))
            
            # Calculate time spent on current question
            time_diff = (next_log["timestamp"] - current_log["timestamp"]).total_seconds()
            
            if 0 < time_diff < 3600:  # Reasonable time range (0-1 hour)
                if current_qid not in question_times:
                    question_times[current_qid] = []
                question_times[current_qid].append(time_diff)
                time_per_question.append(time_diff)
        
        if not time_per_question:
            return {"error": "Tidak dapat menghitung waktu dari data interaksi"}
        
        # Calculate statistics
        avg_time = sum(time_per_question) / len(time_per_question)
        total_time_accounted = sum(time_per_question)
        
        # Categorize questions by time spent
        quick_answers = len([t for t in time_per_question if t < avg_time * 0.5])
        normal_answers = len([t for t in time_per_question if avg_time * 0.5 <= t <= avg_time * 1.5])
        slow_answers = len([t for t in time_per_question if t > avg_time * 1.5])
        
        # Time efficiency
        time_efficiency = total_time_accounted / total_duration if total_duration > 0 else 1.0
        
        # Per-question time analysis
        question_time_stats = {}
        for qid, times in question_times.items():
            if times:
                question_time_stats[qid] = {
                    "total_time": sum(times),
                    "average_time": sum(times) / len(times),
                    "interaction_count": len(times)
                }
        
        return {
            "average_time_per_question": avg_time,
            "total_time_accounted": total_time_accounted,
            "time_efficiency": min(time_efficiency, 1.0),
            "quick_answers_count": quick_answers,
            "normal_answers_count": normal_answers,
            "slow_answers_count": slow_answers,
            "total_interactions": len(sorted_logs),
            "unique_questions_with_timing": len(question_times),
            "time_distribution": {
                "quick_percentage": quick_answers / len(time_per_question) * 100 if time_per_question else 0,
                "normal_percentage": normal_answers / len(time_per_question) * 100 if time_per_question else 0,
                "slow_percentage": slow_answers / len(time_per_question) * 100 if time_per_question else 0
            },
            "question_time_breakdown": question_time_stats
        }

    async def _generate_behavioral_insights(
        self, 
        exam_session: Dict, 
        performance: PerformanceMetrics,
        violations: ViolationAnalytics
    ) -> List[str]:
        """Generate behavioral insights based on exam data"""
        insights = []
        
        # Performance insights (Indonesian)
        if performance.accuracy_percentage >= 90:
            insights.append("Penguasaan materi sangat baik")
        elif performance.accuracy_percentage >= 70:
            insights.append("Pemahaman baik dengan ruang untuk perbaikan")
        elif performance.accuracy_percentage >= 50:
            insights.append("Performa rata-rata - fokus pada area yang lemah")
        else:
            insights.append("Perlu peningkatan signifikan dalam penguasaan materi")
        
        # Time management insights (Indonesian)
        if performance.average_time_per_question < 30:  # 30 seconds
            insights.append("Waktu respon sangat cepat - pertimbangkan untuk meninjau jawaban dengan teliti")
        elif performance.average_time_per_question > 180:  # 3 minutes
            insights.append("Waktu respon lambat - latih teknik manajemen waktu")
        
        # Completion insights (Indonesian)
        if performance.completion_percentage < 100:
            insights.append(f"Ujian tidak lengkap - {performance.unanswered_questions} soal tidak dijawab")
        
        # Violation insights (Indonesian)
        if violations.total_violations == 0:
            insights.append("Perilaku ujian sangat baik tanpa pelanggaran")
        elif violations.total_violations <= 2:
            insights.append("Pelanggaran ringan terdeteksi - jaga fokus selama ujian")
        else:
            insights.append("Beberapa pelanggaran terdeteksi - tinjau kembali pedoman perilaku ujian")
        
        # Pattern-based insights
        answers = exam_session.get("answers", [])
        if not isinstance(answers, list):
            answers = []
            
        valid_answers = [a for a in answers if isinstance(a, dict)]
        if valid_answers:
            change_counts = [a.get("change_count", 0) for a in valid_answers if isinstance(a.get("change_count", 0), (int, float))]
            avg_changes = sum(change_counts) / len(change_counts) if change_counts else 0
            
            if avg_changes > 2:
                insights.append("Tingkat revisi jawaban tinggi - menunjukkan ketidakpastian atau keraguan")
            elif avg_changes < 0.5:
                insights.append("Tingkat revisi jawaban rendah - menunjukkan kepercayaan diri pada jawaban awal")
        
        return insights[:5]  # Limit to top 5 insights

    async def _generate_recommendations(
        self, 
        performance: PerformanceMetrics,
        violations: ViolationAnalytics,
        class_comparison: ClassComparison
    ) -> List[str]:
        """Generate recommendations for the student"""
        recommendations = []
        
        # Performance-based recommendations (Indonesian)
        if performance.accuracy_percentage < 70:
            recommendations.append("Fokus pada peninjauan konsep dasar dalam mata pelajaran ini")
            recommendations.append("Pertimbangkan untuk membentuk kelompok belajar atau mencari bantuan tambahan")
        
        if performance.completion_percentage < 100:
            recommendations.append("Latih manajemen waktu untuk menyelesaikan semua soal")
            recommendations.append("Lakukan tes latihan untuk meningkatkan kecepatan pengerjaan ujian")
        
        # Comparison-based recommendations (Indonesian)
        if not class_comparison.above_average:
            recommendations.append("Tinjau materi kelas dan bandingkan dengan siswa terbaik")
            recommendations.append("Analisis kesalahan untuk mengidentifikasi kesenjangan pengetahuan")
        
        # Violation-based recommendations (Indonesian)
        if violations.total_violations > 0:
            recommendations.append("Tinjau pedoman perilaku ujian untuk menghindari pelanggaran di masa depan")
            if "tab_switch" in violations.violations_by_type:
                recommendations.append("Hindari beralih tab browser selama ujian")
            if "text_selection" in violations.violations_by_type:
                recommendations.append("Hindari memilih/menyalin teks selama ujian")
            if "text_selection_attempt" in violations.violations_by_type:
                recommendations.append("Hindari mencoba memilih teks selama ujian")
        
        # Time management recommendations (Indonesian)
        if performance.average_time_per_question > 120:  # 2 minutes
            recommendations.append("Latih menjawab soal dengan lebih cepat")
            recommendations.append("Pelajari cara mengidentifikasi soal mudah dan jawab terlebih dahulu")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    # ========================================================================
    # HELPER METHODS FOR NEW DATA FORMAT
    # ========================================================================
    
    async def _calculate_correct_answers(self, exam_session: Dict, exam: Dict) -> int:
        """Calculate number of correct answers from new format"""
        db = await self._get_db()
        
        answers = exam_session.get("answers", {})
        if not isinstance(answers, dict):
            return 0
        
        correct_count = 0
        
        for question_id_str, student_answer in answers.items():
            if not student_answer:  # Skip empty answers
                continue
                
            try:
                question_id = ObjectId(question_id_str)
                question = await db.question_banks.find_one({"_id": question_id})
                
                if not question:
                    logger.warning(f"Question {question_id_str} not found for correctness check")
                    continue
                
                # Check if answer is correct based on question type
                question_type = question.get("question_type", question.get("type", "unknown"))
                if question_type == "multiple_choice":
                    # Find correct option (use 'id' field)
                    correct_option = next((opt for opt in question.get("options", []) if opt.get("is_correct")), None)
                    if correct_option and str(correct_option["id"]) == str(student_answer):
                        correct_count += 1
                        logger.debug(f"Question {question_id_str}: CORRECT (MC)")
                    else:
                        logger.debug(f"Question {question_id_str}: WRONG (MC) - answered {student_answer}, correct {correct_option['id'] if correct_option else 'none'}")
                else:
                    # For essay questions, we cannot determine correctness automatically
                    # Only count if manually graded (this is a simplified approach)
                    # In the future, this should check for manual grading data
                    logger.debug(f"Question {question_id_str}: ESSAY - Cannot determine correctness automatically")
                        
            except Exception as e:
                logger.warning(f"Error checking answer for question {question_id_str}: {e}")
                continue
        
        logger.info(f"Calculated {correct_count} correct answers out of {len(answers)} total answers")
        return correct_count
    
    async def _calculate_time_per_question(self, interaction_logs: List[Dict]) -> List[float]:
        """Calculate time spent per question from interaction logs"""
        if not interaction_logs:
            return []
        
        # Sort by timestamp
        sorted_logs = sorted(interaction_logs, key=lambda x: x.get("timestamp", datetime.min))
        
        time_per_question = []
        last_timestamp = None
        
        for log in sorted_logs:
            current_timestamp = log.get("timestamp")
            if not current_timestamp:
                continue
                
            if last_timestamp:
                # Calculate time difference in seconds
                time_diff = (current_timestamp - last_timestamp).total_seconds()
                if 0 < time_diff < 3600:  # Reasonable time range (0-1 hour)
                    time_per_question.append(time_diff)
            
            last_timestamp = current_timestamp
        
        return time_per_question
    
    async def _calculate_max_possible_score(self, exam_session: Dict, exam: Dict) -> float:
        """Calculate maximum possible score for the exam"""
        db = await self._get_db()
        
        question_map = exam_session.get("question_map", [])
        if not question_map:
            return 100.0  # Default assumption
        
        total_points = 0
        
        for q_map in question_map:
            try:
                question_id = q_map.get("question_id")
                if question_id:
                    question = await db.question_banks.find_one({"_id": question_id})
                    if question:
                        points = question.get("points", 10)  # Default 10 points per question
                        total_points += points
            except Exception as e:
                logger.warning(f"Error getting question points: {e}")
                total_points += 10  # Default fallback
        
        return total_points if total_points > 0 else 100.0

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
