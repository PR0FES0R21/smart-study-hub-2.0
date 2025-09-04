# ==============================================================================
# File: app/crud/crud_teacher_analytics.py  
# Deskripsi: CRUD functions untuk Teacher Analytics (Exam-level Analytics)
# ==============================================================================
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from statistics import median, stdev
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.teacher_analytics import (
    ExamAnalytics, ExamMetadata, ClassStatistics, QuestionAnalysis,
    StudentPerformance, TimeAnalysis, ViolationAnalysis, ComparisonAnalysis,
    AnalyticsTask, AnalyticsListItem
)
from app.api.v1.deps import get_database

logger = logging.getLogger(__name__)


class TeacherAnalyticsCRUD:
    def __init__(self):
        self.db = None
    
    async def _get_db(self) -> AsyncIOMotorDatabase:
        """Get database connection"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    async def generate_exam_analytics(
        self, 
        exam_id: str, 
        teacher_id: ObjectId,
        force_regenerate: bool = False,
        include_comparison: bool = True
    ) -> ExamAnalytics:
        """
        Generate comprehensive exam analytics untuk guru
        Fungsi ini akan dijalankan di background task
        """
        db = await self._get_db()
        start_time = datetime.utcnow()
        
        logger.info(f"Starting analytics generation for exam {exam_id}")
        
        try:
            # 1. Validasi dan ambil data exam
            exam_data = await self._get_exam_data(db, exam_id, teacher_id)
            
            # 2. Ambil semua exam sessions untuk ujian ini
            exam_sessions = await self._get_exam_sessions(db, exam_id)
            
            if not exam_sessions:
                raise ValueError("No exam sessions found for this exam")
            
            # 3. Generate berbagai komponen analytics
            exam_metadata = await self._generate_exam_metadata(db, exam_data)
            class_statistics = await self._generate_class_statistics(db, exam_sessions, exam_data)
            questions_analysis = await self._generate_questions_analysis(db, exam_sessions, exam_data)
            student_performances = await self._generate_student_performances(db, exam_sessions, exam_data)
            time_analysis = await self._generate_time_analysis(exam_sessions, exam_data)
            violation_analysis = await self._generate_violation_analysis(exam_sessions)
            comparison_analysis = None
            
            if include_comparison:
                comparison_analysis = await self._generate_comparison_analysis(db, exam_data, class_statistics)
            
            # 4. Hitung generation time
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 5. Buat analytics object
            analytics = ExamAnalytics(
                status="completed",
                exam_metadata=exam_metadata,
                class_statistics=class_statistics,
                questions_analysis=questions_analysis,
                student_performances=student_performances,
                time_analysis=time_analysis,
                violation_analysis=violation_analysis,
                comparison_analysis=comparison_analysis,
                generated_at=datetime.utcnow(),
                generation_time=generation_time,
                cache_expires_at=datetime.utcnow() + timedelta(hours=24),
                data_version="1.0"
            )
            
            # 6. Simpan ke database
            await self._save_analytics(db, analytics)
            
            logger.info(f"Analytics generation completed for exam {exam_id} in {generation_time:.2f}s")
            return analytics
            
        except Exception as e:
            logger.error(f"Error generating analytics for exam {exam_id}: {str(e)}")
            raise
    
    async def _get_exam_data(self, db: AsyncIOMotorDatabase, exam_id: str, teacher_id: ObjectId) -> Dict:
        """Ambil dan validasi data exam"""
        if not ObjectId.is_valid(exam_id):
            raise ValueError("Invalid exam ID")
        
        pipeline = [
            {"$match": {"_id": ObjectId(exam_id)}},
            {"$lookup": {
                "from": "teaching_assignments",
                "localField": "teaching_assignment_id",
                "foreignField": "_id",
                "as": "assignment"
            }},
            {"$unwind": "$assignment"},
            {"$lookup": {
                "from": "subjects",
                "localField": "assignment.subject_id", 
                "foreignField": "_id",
                "as": "subject"
            }},
            {"$unwind": "$subject"},
            {"$lookup": {
                "from": "classes",
                "localField": "assignment.class_id",
                "foreignField": "_id", 
                "as": "class"
            }},
            {"$unwind": "$class"},
            {"$lookup": {
                "from": "users",
                "localField": "assignment.teacher_id",
                "foreignField": "_id",
                "as": "teacher"
            }},
            {"$unwind": "$teacher"}
        ]
        
        result = await db.exams.aggregate(pipeline).to_list(1)
        if not result:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        exam_data = result[0]
        
        # Validasi ownership
        if exam_data["assignment"]["teacher_id"] != teacher_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this exam analytics")
        
        return exam_data
    
    async def _get_exam_sessions(self, db: AsyncIOMotorDatabase, exam_id: str) -> List[Dict]:
        """Ambil semua exam sessions dengan data lengkap"""
        pipeline = [
            {"$match": {
                "exam_id": ObjectId(exam_id),
                "status": {"$in": ["submitted", "graded"]}
            }},
            {"$lookup": {
                "from": "users",
                "localField": "student_id",
                "foreignField": "_id",
                "as": "student"
            }},
            {"$unwind": "$student"},
            {"$lookup": {
                "from": "profiles",
                "localField": "student_id",
                "foreignField": "user_id",
                "as": "profile"
            }},
            {"$unwind": "$profile"},
            {"$sort": {"score": -1}}  # Sort by score descending untuk ranking
        ]
        
        return await db.exam_sessions.aggregate(pipeline).to_list(None)
    
    async def _generate_exam_metadata(self, db: AsyncIOMotorDatabase, exam_data: Dict) -> ExamMetadata:
        """Generate exam metadata"""
        # Get academic period info
        academic_period = await db.academic_periods.find_one({"_id": exam_data.get("academic_period_id")})
        academic_period_name = academic_period.get("name", "Unknown") if academic_period else "Unknown"
        
        return ExamMetadata(
            exam_id=exam_data["_id"],
            exam_title=exam_data.get("title", ""),
            exam_type=exam_data.get("exam_type", ""),
            subject_name=exam_data["subject"]["name"],
            class_name=exam_data["class"]["name"],
            teacher_name=exam_data["teacher"].get("full_name", f"{exam_data['teacher'].get('first_name', '')} {exam_data['teacher'].get('last_name', '')}".strip()),
            total_questions=len(exam_data.get("question_ids", [])),
            max_score=100,  # Default, bisa dihitung dari total points
            duration_minutes=exam_data.get("duration_minutes", 60),
            availability_start_time=exam_data.get("availability_start_time"),
            availability_end_time=exam_data.get("availability_end_time"),
            academic_period=academic_period_name
        )
    
    async def _generate_class_statistics(self, db: AsyncIOMotorDatabase, sessions: List[Dict], exam_data: Dict) -> ClassStatistics:
        """Generate class statistics"""
        # Hitung jumlah siswa yang seharusnya mengikuti ujian
        class_id = exam_data["assignment"]["class_id"]
        total_students_result = await db.profiles.count_documents({"class_id": class_id})
        
        # Statistics from sessions
        completed_sessions = [s for s in sessions if s["status"] == "graded"]
        scores = [s.get("score", 0) for s in completed_sessions]
        
        if not scores:
            scores = [0]  # Prevent division by zero
        
        # Calculate statistics
        class_average = sum(scores) / len(scores) if scores else 0
        median_score = median(scores) if len(scores) > 0 else 0
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0
        std_dev = stdev(scores) if len(scores) > 1 else 0
        passing_rate = len([s for s in scores if s >= 60]) / len(scores) * 100 if scores else 0
        
        # Grade distribution
        grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for score in scores:
            if score >= 90:
                grade_distribution["A"] += 1
            elif score >= 80:
                grade_distribution["B"] += 1
            elif score >= 70:
                grade_distribution["C"] += 1
            elif score >= 60:
                grade_distribution["D"] += 1
            else:
                grade_distribution["E"] += 1
        
        # Score ranges
        score_ranges = {
            "0-20": len([s for s in scores if 0 <= s <= 20]),
            "21-40": len([s for s in scores if 21 <= s <= 40]),
            "41-60": len([s for s in scores if 41 <= s <= 60]),
            "61-80": len([s for s in scores if 61 <= s <= 80]),
            "81-100": len([s for s in scores if 81 <= s <= 100])
        }
        
        return ClassStatistics(
            total_students=total_students_result,
            students_completed=len(completed_sessions),
            students_in_progress=len([s for s in sessions if s["status"] == "submitted"]),
            students_not_started=total_students_result - len(sessions),
            completion_rate=len(completed_sessions) / total_students_result * 100 if total_students_result > 0 else 0,
            class_average=class_average,
            median_score=median_score,
            highest_score=highest_score,
            lowest_score=lowest_score,
            standard_deviation=std_dev,
            passing_rate=passing_rate,
            grade_distribution=grade_distribution,
            score_ranges=score_ranges
        )
    
    async def _generate_questions_analysis(self, db: AsyncIOMotorDatabase, sessions: List[Dict], exam_data: Dict) -> List[QuestionAnalysis]:
        """Generate per-question analysis"""
        questions_analysis = []
        question_ids = exam_data.get("question_ids", [])
        
        # Get question details
        questions_cursor = db.question_banks.find({"_id": {"$in": question_ids}})
        questions_dict = {q["_id"]: q for q in await questions_cursor.to_list(None)}
        
        for i, question_id in enumerate(question_ids):
            question = questions_dict.get(question_id, {})
            question_id_str = str(question_id)
            
            # Analyze answers for this question
            correct_count = 0
            wrong_count = 0
            unanswered_count = 0
            response_times = []
            answer_distribution = {}
            
            for session in sessions:
                answers = session.get("answers", {})
                interaction_logs = session.get("interaction_logs", [])
                
                # Check answer correctness
                student_answer = answers.get(question_id_str)
                if student_answer:
                    if question.get("type") == "multiple_choice":
                        correct_option = next((opt for opt in question.get("options", []) if opt.get("is_correct")), None)
                        if correct_option and str(correct_option.get("id", "")) == str(student_answer):
                            correct_count += 1
                        else:
                            wrong_count += 1
                        
                        # Answer distribution for MC
                        option_text = self._get_option_text(question.get("options", []), student_answer)
                        answer_distribution[option_text] = answer_distribution.get(option_text, 0) + 1
                    else:
                        # Essay - assume correct if answered
                        if str(student_answer).strip():
                            correct_count += 1
                        else:
                            wrong_count += 1
                else:
                    unanswered_count += 1
                
                # Calculate response time
                question_interactions = [log for log in interaction_logs if str(log.get("question_id", "")) == question_id_str]
                if len(question_interactions) >= 2:
                    first_interaction = min(question_interactions, key=lambda x: x.get("timestamp", datetime.min))
                    last_interaction = max(question_interactions, key=lambda x: x.get("timestamp", datetime.min))
                    if first_interaction.get("timestamp") and last_interaction.get("timestamp"):
                        time_spent = (last_interaction["timestamp"] - first_interaction["timestamp"]).total_seconds()
                        if 0 < time_spent < 3600:  # Reasonable time range
                            response_times.append(time_spent)
            
            # Calculate metrics
            total_responses = correct_count + wrong_count + unanswered_count
            class_accuracy = correct_count / total_responses if total_responses > 0 else 0
            
            # Time statistics
            avg_time = sum(response_times) / len(response_times) if response_times else 0
            median_time = median(response_times) if response_times else 0
            fastest_time = min(response_times) if response_times else 0
            slowest_time = max(response_times) if response_times else 0
            
            # Quality indicators
            is_problematic = class_accuracy < 0.5
            discrimination_index = self._calculate_discrimination_index(sessions, question_id_str, question)
            
            questions_analysis.append(QuestionAnalysis(
                question_id=question_id,
                question_number=i + 1,
                question_text=question.get("question_text", f"Question {i+1}"),
                question_type=question.get("type", "unknown"),
                difficulty=question.get("difficulty", "medium"),
                points=question.get("points", 1),
                class_accuracy=class_accuracy,
                correct_count=correct_count,
                wrong_count=wrong_count,
                unanswered_count=unanswered_count,
                average_time=avg_time,
                median_time=median_time,
                fastest_time=fastest_time,
                slowest_time=slowest_time,
                is_problematic=is_problematic,
                discrimination_index=discrimination_index,
                answer_distribution=answer_distribution if question.get("type") == "multiple_choice" else None,
                correct_option=self._get_correct_option_text(question) if question.get("type") == "multiple_choice" else None
            ))
        
        return questions_analysis
    
    def _get_option_text(self, options: List[Dict], option_id: str) -> str:
        """Get option text from option ID"""
        for opt in options:
            if str(opt.get("id", "")) == str(option_id):
                return opt.get("text", f"Option {option_id}")
        return f"Option {option_id}"
    
    def _get_correct_option_text(self, question: Dict) -> Optional[str]:
        """Get correct option text"""
        options = question.get("options", [])
        correct_option = next((opt for opt in options if opt.get("is_correct")), None)
        return correct_option.get("text", "") if correct_option else None
    
    def _calculate_discrimination_index(self, sessions: List[Dict], question_id_str: str, question: Dict) -> float:
        """Calculate discrimination index untuk question"""
        # Simplified discrimination index calculation
        # Bandingkan performa top 27% vs bottom 27% students
        sessions_with_scores = [s for s in sessions if s.get("score") is not None]
        if len(sessions_with_scores) < 6:  # Need minimum data
            return 0.0
        
        # Sort by total score
        sessions_sorted = sorted(sessions_with_scores, key=lambda x: x.get("score", 0), reverse=True)
        
        # Get top and bottom 27%
        top_count = max(1, int(len(sessions_sorted) * 0.27))
        bottom_count = max(1, int(len(sessions_sorted) * 0.27))
        
        top_group = sessions_sorted[:top_count]
        bottom_group = sessions_sorted[-bottom_count:]
        
        # Calculate correct rate for each group
        top_correct = 0
        bottom_correct = 0
        
        for session in top_group:
            if self._is_question_correct(session, question_id_str, question):
                top_correct += 1
        
        for session in bottom_group:
            if self._is_question_correct(session, question_id_str, question):
                bottom_correct += 1
        
        top_rate = top_correct / len(top_group) if top_group else 0
        bottom_rate = bottom_correct / len(bottom_group) if bottom_group else 0
        
        return top_rate - bottom_rate
    
    def _is_question_correct(self, session: Dict, question_id_str: str, question: Dict) -> bool:
        """Check if question is answered correctly in session"""
        answers = session.get("answers", {})
        student_answer = answers.get(question_id_str)
        
        if not student_answer:
            return False
        
        if question.get("type") == "multiple_choice":
            correct_option = next((opt for opt in question.get("options", []) if opt.get("is_correct")), None)
            return correct_option and str(correct_option.get("id", "")) == str(student_answer)
        else:
            # Essay - assume correct if has content
            return bool(str(student_answer).strip())
    
    async def _generate_student_performances(self, db: AsyncIOMotorDatabase, sessions: List[Dict], exam_data: Dict) -> List[StudentPerformance]:
        """Generate student performance list"""
        performances = []
        total_questions = len(exam_data.get("question_ids", []))
        
        # Add ranking
        sessions_sorted = sorted([s for s in sessions if s.get("score") is not None], key=lambda x: x.get("score", 0), reverse=True)
        
        for rank, session in enumerate(sessions_sorted, 1):
            student = session.get("student", {})
            profile = session.get("profile", {})
            
            # Calculate metrics
            score = session.get("score", 0)
            percentage = score
            duration_minutes = 0
            
            if session.get("started_at") and session.get("submitted_at"):
                duration_minutes = (session["submitted_at"] - session["started_at"]).total_seconds() / 60
            
            # Count answers
            answers = session.get("answers", {})
            answered_questions = len([a for a in answers.values() if a is not None and str(a).strip()])
            
            # Calculate correct answers (simplified)
            correct_answers = int(score / 100 * total_questions) if total_questions > 0 else 0
            wrong_answers = answered_questions - correct_answers
            unanswered_questions = total_questions - answered_questions
            
            # Grade calculation
            grade = "E"
            if score >= 90:
                grade = "A"
            elif score >= 80:
                grade = "B"
            elif score >= 70:
                grade = "C"
            elif score >= 60:
                grade = "D"
            
            # Violations
            violations = session.get("violations", [])
            violations_count = len(violations) if isinstance(violations, list) else 0
            integrity_score = max(0, 1.0 - (violations_count * 0.1))  # Simple calculation
            
            # Percentile calculation
            scores_below = len([s for s in sessions_sorted if s.get("score", 0) < score])
            percentile = (scores_below / len(sessions_sorted)) * 100 if sessions_sorted else 0
            
            performances.append(StudentPerformance(
                student_id=session["student_id"],
                student_name=profile.get("full_name", f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()),
                exam_session_id=session["_id"],
                status=session.get("status", "completed"),
                score=score,
                percentage=percentage,
                rank=rank,
                percentile=percentile,
                grade=grade,
                duration_taken=duration_minutes,
                time_efficiency=score / duration_minutes if duration_minutes > 0 else 0,
                answered_questions=answered_questions,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                unanswered_questions=unanswered_questions,
                accuracy_rate=correct_answers / answered_questions if answered_questions > 0 else 0,
                violations_count=violations_count,
                integrity_score=integrity_score,
                started_at=session.get("started_at"),
                submitted_at=session.get("submitted_at")
            ))
        
        return performances
    
    async def _generate_time_analysis(self, sessions: List[Dict], exam_data: Dict) -> TimeAnalysis:
        """Generate time analysis"""
        durations = []
        overtime_count = 0
        early_submission_count = 0
        duration_limit = exam_data.get("duration_minutes", 60)
        
        for session in sessions:
            if session.get("started_at") and session.get("submitted_at"):
                duration_minutes = (session["submitted_at"] - session["started_at"]).total_seconds() / 60
                durations.append(duration_minutes)
                
                if duration_minutes > duration_limit:
                    overtime_count += 1
                elif duration_minutes < duration_limit * 0.5:
                    early_submission_count += 1
        
        if not durations:
            durations = [0]
        
        # Calculate statistics
        avg_completion = sum(durations) / len(durations)
        median_completion = median(durations)
        fastest = min(durations)
        slowest = max(durations)
        std_dev = stdev(durations) if len(durations) > 1 else 0
        
        # Time distribution
        time_distribution = {
            "0-30min": len([d for d in durations if d <= 30]),
            "31-60min": len([d for d in durations if 30 < d <= 60]),
            "61-90min": len([d for d in durations if 60 < d <= 90]),
            "90+min": len([d for d in durations if d > 90])
        }
        
        total_questions = len(exam_data.get("question_ids", []))
        avg_time_per_question = (avg_completion * 60) / total_questions if total_questions > 0 else 0  # seconds
        
        return TimeAnalysis(
            average_completion_time=avg_completion,
            median_completion_time=median_completion,
            fastest_completion=fastest,
            slowest_completion=slowest,
            standard_deviation=std_dev,
            time_distribution=time_distribution,
            overtime_count=overtime_count,
            early_submission_count=early_submission_count,
            average_time_per_question=avg_time_per_question,
            questions_with_long_response=[]  # Could be calculated based on question analytics
        )
    
    async def _generate_violation_analysis(self, sessions: List[Dict]) -> ViolationAnalysis:
        """Generate violation analysis"""
        total_violations = 0
        students_with_violations = 0
        violation_types = {}
        severity_distribution = {}
        flagged_students = []
        
        for session in sessions:
            violations = session.get("violations", [])
            if not isinstance(violations, list):
                continue
                
            student_violation_count = len(violations)
            if student_violation_count > 0:
                students_with_violations += 1
                total_violations += student_violation_count
                
                # Flag high-risk students (>5 violations)
                if student_violation_count >= 5:
                    flagged_students.append(session["student_id"])
                
                # Categorize violations
                for violation in violations:
                    v_type = violation.get("type", "unknown")
                    severity = violation.get("severity", "low")
                    
                    violation_types[v_type] = violation_types.get(v_type, 0) + 1
                    severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        # Calculate integrity metrics
        total_students = len(sessions)
        violation_percentage = (students_with_violations / total_students) * 100 if total_students > 0 else 0
        class_integrity_score = max(0, 1.0 - (violation_percentage / 100))
        
        # Integrity rating
        if class_integrity_score >= 0.9:
            integrity_rating = "excellent"
        elif class_integrity_score >= 0.7:
            integrity_rating = "good"
        elif class_integrity_score >= 0.5:
            integrity_rating = "fair"
        else:
            integrity_rating = "poor"
        
        return ViolationAnalysis(
            total_violations=total_violations,
            students_with_violations=students_with_violations,
            violation_percentage=violation_percentage,
            violation_types=violation_types,
            severity_distribution=severity_distribution,
            flagged_students=flagged_students,
            high_risk_count=len(flagged_students),
            class_integrity_score=class_integrity_score,
            integrity_rating=integrity_rating
        )
    
    async def _generate_comparison_analysis(self, db: AsyncIOMotorDatabase, exam_data: Dict, class_stats: ClassStatistics) -> Optional[ComparisonAnalysis]:
        """Generate comparison with similar exams (optional)"""
        # Simplified implementation - could be enhanced
        return ComparisonAnalysis(
            has_comparison=False,
            comparison_exams=[],
            score_improvement=None,
            difficulty_comparison=None,
            performance_trend=None
        )
    
    async def _save_analytics(self, db: AsyncIOMotorDatabase, analytics: ExamAnalytics):
        """Save analytics to database"""
        analytics_dict = analytics.model_dump(mode='python')
        
        # Update or insert
        await db.teacher_analytics.update_one(
            {"exam_metadata.exam_id": analytics.exam_metadata.exam_id},
            {"$set": analytics_dict},
            upsert=True
        )
    
    async def get_analytics(self, exam_id: str, teacher_id: ObjectId) -> Optional[ExamAnalytics]:
        """Retrieve existing analytics"""
        db = await self._get_db()
        
        result = await db.teacher_analytics.find_one({"exam_metadata.exam_id": ObjectId(exam_id)})
        if not result:
            return None
        
        # Validate teacher ownership
        exam = await db.exams.find_one({"_id": ObjectId(exam_id)})
        if exam:
            assignment = await db.teaching_assignments.find_one({"_id": exam["teaching_assignment_id"]})
            if not assignment or assignment["teacher_id"] != teacher_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this analytics")
        
        return ExamAnalytics(**result)
    
    async def delete_analytics(self, exam_id: str, teacher_id: ObjectId) -> bool:
        """Delete analytics"""
        db = await self._get_db()
        
        # Validate ownership first
        await self.get_analytics(exam_id, teacher_id)  # This will throw if not authorized
        
        result = await db.teacher_analytics.delete_one({"exam_metadata.exam_id": ObjectId(exam_id)})
        return result.deleted_count > 0
    
    async def list_analytics(self, teacher_id: ObjectId, skip: int = 0, limit: int = 20) -> List[AnalyticsListItem]:
        """List analytics untuk guru"""
        db = await self._get_db()
        
        # Get teacher's exams with analytics status
        pipeline = [
            {"$lookup": {
                "from": "teaching_assignments",
                "localField": "teaching_assignment_id",
                "foreignField": "_id",
                "as": "assignment"
            }},
            {"$unwind": "$assignment"},
            {"$match": {"assignment.teacher_id": teacher_id}},
            {"$lookup": {
                "from": "classes",
                "localField": "assignment.class_id",
                "foreignField": "_id",
                "as": "class_info"
            }},
            {"$unwind": "$class_info"},
            {"$lookup": {
                "from": "teacher_analytics",
                "localField": "_id",
                "foreignField": "exam_metadata.exam_id",
                "as": "analytics"
            }},
            {"$skip": skip},
            {"$limit": limit},
            {"$sort": {"availability_start_time": -1}}
        ]
        
        exams = await db.exams.aggregate(pipeline).to_list(None)
        
        items = []
        for exam in exams:
            # Get basic stats from exam sessions
            sessions = await db.exam_sessions.find({
                "exam_id": exam["_id"],
                "status": {"$in": ["submitted", "graded"]}
            }).to_list(None)
            
            total_students = await db.profiles.count_documents({"class_id": exam["assignment"]["class_id"]})
            completion_rate = len(sessions) / total_students * 100 if total_students > 0 else 0
            class_average = sum([s.get("score", 0) for s in sessions]) / len(sessions) if sessions else 0
            
            analytics_data = exam.get("analytics", [])
            has_analytics = len(analytics_data) > 0
            generated_at = analytics_data[0].get("generated_at") if analytics_data else None
            
            items.append(AnalyticsListItem(
                exam_id=exam["_id"],
                exam_title=exam.get("title", ""),
                class_name=exam["class_info"]["name"],
                total_students=total_students,
                completion_rate=completion_rate,
                class_average=class_average,
                status="completed" if has_analytics else "pending",
                generated_at=generated_at,
                has_analytics=has_analytics
            ))
        
        return items


# Create global instance
teacher_analytics_crud = TeacherAnalyticsCRUD()
