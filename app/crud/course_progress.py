# ==============================================================================
# File: app/crud/course_progress.py
# Deskripsi: CRUD operations untuk Course Progress tracking (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

from app.models.lesson_progress import CourseProgress
from app.schemas.base import PyObjectId
from app.crud.module_progress import module_progress_crud
from app.crud.lesson_progress import lesson_progress_crud

class CourseProgressCRUD:
    """CRUD operations untuk Course Progress tracking"""
    
    def __init__(self):
        self.collection = "course_progress"
        self.course_collection = "courses"
        self.module_progress_collection = "module_progress"
        self.lesson_progress_collection = "lesson_progress"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def enroll_student_in_course(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str,
        enrollment_metadata: Optional[Dict[str, Any]] = None
    ) -> CourseProgress:
        """Enroll student in course dan create progress tracking"""
        
        # Check if already enrolled
        existing_progress = await self.get_course_progress(db, student_id, course_id)
        if existing_progress:
            return existing_progress
        
        # Get course data
        course = await db[self.course_collection].find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Check if course allows enrollment
        from app.models.course import Course
        course_obj = Course.from_mongo(course)
        if not course_obj.can_enroll():
            raise HTTPException(status_code=400, detail="Course is not accepting enrollments")
        
        # Create course progress
        progress = CourseProgress(
            student_id=PyObjectId(student_id),
            course_id=PyObjectId(course_id),
            enrollment_id=PyObjectId(enrollment_metadata.get("enrollment_id")) if enrollment_metadata and enrollment_metadata.get("enrollment_id") else None,
            status="not_started",
            total_modules=len(course.get("module_refs", [])),
            enrolled_at=datetime.utcnow()
        )
        
        # Insert to database
        result = await db[self.collection].insert_one(progress.to_mongo())
        progress.id = str(result.inserted_id)
        
        # Initialize module progress untuk semua modules
        module_refs = course.get("module_refs", [])
        for module_ref in module_refs:
            await module_progress_crud.start_module_progress(
                db, student_id, str(module_ref["module_id"]), course_id
            )
        
        return progress
    
    async def update_course_progress_from_modules(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> CourseProgress:
        """Update course progress berdasarkan module progress"""
        
        # Get or create course progress
        progress = await self.get_course_progress(db, student_id, course_id)
        if not progress:
            progress = await self.enroll_student_in_course(db, student_id, course_id)
        
        # Get course data
        course = await db[self.course_collection].find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        module_refs = course.get("module_refs", [])
        module_ids = [str(ref["module_id"]) for ref in module_refs]
        
        # Get module progress data
        module_progress_data = await db[self.module_progress_collection].find({
            "student_id": ObjectId(student_id),
            "module_id": {"$in": [ObjectId(mid) for mid in module_ids]}
        }).to_list(len(module_ids))
        
        # Get lesson progress data
        lesson_progress_data = await db[self.lesson_progress_collection].find({
            "student_id": ObjectId(student_id),
            "course_id": ObjectId(course_id)
        }).to_list(10000)
        
        # Update course progress
        await progress.calculate_from_module_progress(module_progress_data, lesson_progress_data)
        
        # Update current position
        in_progress_modules = [mp for mp in module_progress_data if mp.get("status") == "in_progress"]
        if in_progress_modules:
            current_module = max(in_progress_modules, key=lambda x: x.get("last_activity", datetime.min))
            progress.current_module_id = PyObjectId(current_module["module_id"])
            
            # Get current lesson from module
            if current_module.get("current_lesson_id"):
                progress.current_lesson_id = PyObjectId(current_module["current_lesson_id"])
        
        # Update engagement metrics
        await self._update_engagement_metrics(db, progress, lesson_progress_data)
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return progress
    
    # ==================== READ OPERATIONS ====================
    
    async def get_course_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> Optional[CourseProgress]:
        """Get course progress untuk specific student"""
        
        progress_data = await db[self.collection].find_one({
            "student_id": ObjectId(student_id),
            "course_id": ObjectId(course_id)
        })
        
        if not progress_data:
            return None
        
        return CourseProgress.from_mongo(progress_data)
    
    async def get_student_course_progress_list(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get list of course progress untuk student"""
        
        # Build query
        query = {"student_id": ObjectId(student_id)}
        
        if filters:
            if filters.get("status"):
                query["status"] = filters["status"]
            if filters.get("grade_level"):
                # This would require joining dengan course data
                pass
        
        # Get total count
        total_count = await db[self.collection].count_documents(query)
        
        # Execute query dengan course details
        pipeline = [
            {"$match": query},
            
            # Lookup course details
            {
                "$lookup": {
                    "from": "courses",
                    "localField": "course_id",
                    "foreignField": "_id",
                    "as": "course_info"
                }
            },
            {"$unwind": {"path": "$course_info", "preserveNullAndEmptyArrays": True}},
            
            # Lookup subject info
            {
                "$lookup": {
                    "from": "subjects",
                    "localField": "course_info.subject_id",
                    "foreignField": "_id",
                    "as": "subject_info"
                }
            },
            {"$unwind": {"path": "$subject_info", "preserveNullAndEmptyArrays": True}},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "course_title": "$course_info.title",
                    "course_description": "$course_info.description",
                    "subject_name": "$subject_info.name",
                    "grade_level": "$course_info.grade_level"
                }
            },
            
            # Sort by last activity
            {"$sort": {"last_activity": -1}},
            {"$skip": skip},
            {"$limit": limit},
            
            # Project needed fields
            {
                "$project": {
                    "id": 1,
                    "course_id": {"$toString": "$course_id"},
                    "course_title": 1,
                    "course_description": 1,
                    "subject_name": 1,
                    "grade_level": 1,
                    "status": 1,
                    "completion_percentage": 1,
                    "score": 1,
                    "grade": 1,
                    "total_modules": 1,
                    "completed_modules": 1,
                    "total_lessons": 1,
                    "completed_lessons": 1,
                    "total_time_spent": 1,
                    "enrolled_at": 1,
                    "started_at": 1,
                    "completed_at": 1,
                    "last_activity": 1
                }
            }
        ]
        
        progress_list = await db[self.collection].aggregate(pipeline).to_list(limit)
        
        return {
            "items": progress_list,
            "total": total_count,
            "page": (skip // limit) + 1,
            "per_page": limit,
            "has_next": skip + limit < total_count,
            "has_prev": skip > 0
        }
    
    async def get_course_progress_analytics(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        coordinator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive analytics untuk course progress"""
        
        # Get all progress untuk this course
        pipeline = [
            {"$match": {"course_id": ObjectId(course_id)}},
            
            # Lookup student info
            {
                "$lookup": {
                    "from": "users",
                    "localField": "student_id",
                    "foreignField": "_id",
                    "as": "student_info"
                }
            },
            {"$unwind": {"path": "$student_info", "preserveNullAndEmptyArrays": True}},
            
            # Lookup course info
            {
                "$lookup": {
                    "from": "courses",
                    "localField": "course_id",
                    "foreignField": "_id",
                    "as": "course_info"
                }
            },
            {"$unwind": {"path": "$course_info", "preserveNullAndEmptyArrays": True}}
        ]
        
        progress_data = await db[self.collection].aggregate(pipeline).to_list(1000)
        
        if not progress_data:
            return {
                "course_id": course_id,
                "enrollment_stats": {},
                "performance_stats": {},
                "module_analytics": {},
                "engagement_analytics": {}
            }
        
        # Calculate enrollment stats
        total_enrolled = len(progress_data)
        completed = sum(1 for p in progress_data if p.get("status") == "completed")
        in_progress = sum(1 for p in progress_data if p.get("status") == "in_progress")
        withdrawn = sum(1 for p in progress_data if p.get("status") == "withdrawn")
        active_students = sum(1 for p in progress_data 
                            if p.get("last_activity") and 
                            (datetime.utcnow() - p["last_activity"]).days < 7)
        
        # Performance stats
        scores = [p.get("score") for p in progress_data if p.get("score") is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Time stats
        completion_times = []
        for p in progress_data:
            if p.get("enrolled_at") and p.get("completed_at"):
                time_diff = p["completed_at"] - p["enrolled_at"]
                completion_times.append(time_diff.total_seconds() / 3600)  # hours
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Grade distribution
        grades = [p.get("grade") for p in progress_data if p.get("grade")]
        grade_distribution = {}
        for grade in ["A", "B", "C", "D", "F", "I"]:
            grade_distribution[grade] = grades.count(grade)
        
        # Module analytics
        course_info = progress_data[0].get("course_info", {}) if progress_data else {}
        module_refs = course_info.get("module_refs", [])
        
        module_analytics = {}
        for ref in module_refs:
            module_id = str(ref["module_id"])
            module_analytics[module_id] = await self._get_module_analytics_for_course(
                db, course_id, module_id
            )
        
        # Engagement analytics
        engagement_stats = await self._calculate_engagement_analytics(db, course_id, progress_data)
        
        return {
            "course_id": course_id,
            "enrollment_stats": {
                "total_enrolled": total_enrolled,
                "active_students": active_students,
                "completed_students": completed,
                "in_progress_students": in_progress,
                "withdrawn_students": withdrawn,
                "completion_rate": (completed / total_enrolled * 100) if total_enrolled > 0 else 0,
                "dropout_rate": (withdrawn / total_enrolled * 100) if total_enrolled > 0 else 0
            },
            "performance_stats": {
                "average_score": round(avg_score, 2),
                "grade_distribution": grade_distribution,
                "average_completion_time": round(avg_completion_time, 2),  # hours
                "total_completions": len(completion_times)
            },
            "module_analytics": module_analytics,
            "engagement_analytics": engagement_stats,
            "trends": await self._calculate_progress_trends(db, course_id)
        }
    
    async def get_course_progress_dashboard(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard untuk student course progress"""
        
        # Get course progress
        course_progress = await self.get_course_progress(db, student_id, course_id)
        if not course_progress:
            course_progress = await self.enroll_student_in_course(db, student_id, course_id)
        
        # Get course data
        course = await db[self.course_collection].find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Get module progress dengan details
        module_progress_list = []
        module_refs = course.get("module_refs", [])
        
        for ref in sorted(module_refs, key=lambda x: x.get("order", 0)):
            module_id = str(ref["module_id"])
            module_progress_detail = await module_progress_crud.get_module_progress_with_lessons(
                db, student_id, module_id
            )
            
            module_info = {
                "module_id": module_id,
                "order": ref.get("order", 0),
                "required": ref.get("required", True),
                "custom_title": ref.get("custom_title"),
                "weight": ref.get("weight", 1.0),
                "progress": module_progress_detail["module_progress"],
                "lesson_summary": {
                    "total_lessons": len(module_progress_detail["lesson_details"]),
                    "completed_lessons": sum(1 for l in module_progress_detail["lesson_details"] 
                                           if l["progress"] and l["progress"]["status"] == "completed"),
                    "next_lesson": module_progress_detail["next_lesson"]
                },
                "is_unlocked": self._is_module_unlocked(ref, module_progress_list),
                "can_start": self._can_start_module(ref, module_progress_list)
            }
            module_progress_list.append(module_info)
        
        # Get recent activity
        recent_activity = await self._get_recent_activity(db, student_id, course_id, limit=10)
        
        # Get recommendations
        recommendations = await self._get_learning_recommendations(db, student_id, course_id)
        
        return {
            "course_progress": course_progress.dict(),
            "course_info": {
                "title": course.get("title"),
                "description": course.get("description"),
                "coordinator": course.get("coordinator_id"),
                "start_date": course.get("course_start"),
                "end_date": course.get("course_end")
            },
            "module_progress": module_progress_list,
            "learning_path": self._generate_course_learning_path(module_progress_list),
            "next_steps": self._get_next_steps(module_progress_list),
            "recent_activity": recent_activity,
            "recommendations": recommendations,
            "statistics": {
                "time_spent_today": await self._get_time_spent_today(db, student_id, course_id),
                "streak_days": course_progress.streak_days,
                "completion_prediction": await self._predict_completion_time(db, student_id, course_id)
            }
        }
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_course_progress_status(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CourseProgress:
        """Update course progress status"""
        
        progress = await self.get_course_progress(db, student_id, course_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Course progress not found")
        
        old_status = progress.status
        progress.status = status
        progress.last_activity = datetime.utcnow()
        
        if status == "completed" and not progress.completed_at:
            progress.completed_at = datetime.utcnow()
            progress.grade = progress.calculate_grade()
        elif status == "in_progress" and not progress.started_at:
            progress.started_at = datetime.utcnow()
        elif status == "withdrawn":
            progress.withdrawn_at = datetime.utcnow()
        
        # Update engagement metrics
        if old_status != status:
            if status == "in_progress":
                progress.login_count += 1
            
            # Update streak
            await self._update_learning_streak(db, progress)
        
        # Update metadata if provided
        if metadata:
            if "grade" in metadata:
                progress.grade = metadata["grade"]
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return progress
    
    async def record_course_activity(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str,
        activity_data: Dict[str, Any]
    ) -> bool:
        """Record student activity dalam course"""
        
        progress = await self.get_course_progress(db, student_id, course_id)
        if not progress:
            return False
        
        # Update activity timestamp
        progress.last_activity = datetime.utcnow()
        progress.login_count += 1
        
        # Update time spent
        time_spent = activity_data.get("time_spent", 0)
        if time_spent > 0:
            progress.total_time_spent += time_spent
        
        # Update streak
        await self._update_learning_streak(db, progress)
        
        # Update active days
        today = datetime.utcnow().date()
        if not hasattr(progress, "_last_active_date") or progress._last_active_date != today:
            progress.active_days += 1
            progress._last_active_date = today
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return True
    
    # ==================== DELETE OPERATIONS ====================
    
    async def withdraw_from_course(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Withdraw student from course"""
        
        progress = await self.update_course_progress_status(
            db, student_id, course_id, "withdrawn", {"reason": reason}
        )
        
        return progress is not None
    
    async def delete_course_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str,
        delete_related: bool = True
    ) -> bool:
        """Delete course progress completely"""
        
        if delete_related:
            # Delete related module and lesson progress
            await db[self.module_progress_collection].delete_many({
                "student_id": ObjectId(student_id),
                "course_id": ObjectId(course_id)
            })
            
            await db[self.lesson_progress_collection].delete_many({
                "student_id": ObjectId(student_id),
                "course_id": ObjectId(course_id)
            })
        
        # Delete course progress
        result = await db[self.collection].delete_one({
            "student_id": ObjectId(student_id),
            "course_id": ObjectId(course_id)
        })
        
        return result.deleted_count > 0
    
    # ==================== HELPER METHODS ====================
    
    async def _update_engagement_metrics(
        self,
        db: AsyncIOMotorDatabase,
        progress: CourseProgress,
        lesson_progress_data: List[Dict[str, Any]]
    ) -> None:
        """Update engagement metrics"""
        
        # Calculate quiz and assignment scores
        quiz_scores = []
        assignment_scores = []
        
        for lp in lesson_progress_data:
            for page in lp.get("page_progress", []):
                for comp in page.get("component_progress", []):
                    if comp.get("score") is not None:
                        if comp.get("component_type") == "quiz":
                            quiz_scores.append(comp["score"])
                        elif comp.get("component_type") == "assignment":
                            assignment_scores.append(comp["score"])
        
        progress.quiz_scores = quiz_scores
        progress.assignment_scores = assignment_scores
        progress.average_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0.0
        progress.average_assignment_score = sum(assignment_scores) / len(assignment_scores) if assignment_scores else 0.0
    
    async def _update_learning_streak(
        self,
        db: AsyncIOMotorDatabase,
        progress: CourseProgress
    ) -> None:
        """Update learning streak"""
        
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        # Check if active yesterday untuk streak calculation
        was_active_yesterday = await db[self.collection].find_one({
            "_id": ObjectId(progress.id),
            "last_activity": {
                "$gte": datetime.combine(yesterday, datetime.min.time()),
                "$lt": datetime.combine(today, datetime.min.time())
            }
        })
        
        if was_active_yesterday:
            progress.streak_days += 1
        else:
            progress.streak_days = 1  # Reset streak
        
        if progress.streak_days > progress.longest_streak:
            progress.longest_streak = progress.streak_days
    
    def _is_module_unlocked(
        self,
        module_ref: Dict[str, Any],
        completed_modules: List[Dict[str, Any]]
    ) -> bool:
        """Check if module is unlocked"""
        
        unlock_condition = module_ref.get("unlock_condition", "sequential")
        
        if unlock_condition == "immediate":
            return True
        
        if unlock_condition == "sequential":
            current_order = module_ref.get("order", 0)
            for mod in completed_modules:
                if mod.get("order", 0) < current_order and mod.get("required", True):
                    if not mod["progress"] or mod["progress"]["status"] != "completed":
                        return False
            return True
        
        return True
    
    def _can_start_module(
        self,
        module_ref: Dict[str, Any],
        module_progress_list: List[Dict[str, Any]]
    ) -> bool:
        """Check if module can be started"""
        
        # Already started or completed
        current_progress = next((mod for mod in module_progress_list 
                               if mod["module_id"] == str(module_ref["module_id"])), None)
        
        if current_progress and current_progress["progress"]["status"] in ["in_progress", "completed"]:
            return True
        
        return self._is_module_unlocked(module_ref, module_progress_list)
    
    def _generate_course_learning_path(
        self,
        module_progress_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate recommended learning path untuk course"""
        
        path = []
        for module in sorted(module_progress_list, key=lambda x: x["order"]):
            path_item = {
                "module_id": module["module_id"],
                "order": module["order"],
                "status": module["progress"]["status"],
                "completion_percentage": module["progress"]["completion_percentage"],
                "is_unlocked": module["is_unlocked"],
                "is_next": False,
                "estimated_time": module["progress"].get("estimated_time_remaining", 0)
            }
            path.append(path_item)
        
        # Mark next module to take
        for item in path:
            if item["status"] == "not_started" and item["is_unlocked"]:
                item["is_next"] = True
                break
        
        return path
    
    def _get_next_steps(
        self,
        module_progress_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get recommended next steps"""
        
        next_steps = []
        
        # Find next module/lesson to work on
        for module in sorted(module_progress_list, key=lambda x: x["order"]):
            if module["can_start"]:
                if module["progress"]["status"] == "not_started":
                    next_steps.append({
                        "type": "start_module",
                        "module_id": module["module_id"],
                        "title": f"Start module: {module.get('custom_title', 'Module')}",
                        "priority": "high"
                    })
                    break
                elif module["progress"]["status"] == "in_progress":
                    if module["lesson_summary"]["next_lesson"]:
                        next_lesson = module["lesson_summary"]["next_lesson"]
                        next_steps.append({
                            "type": "continue_lesson",
                            "lesson_id": next_lesson["lesson_id"],
                            "title": f"Continue: {next_lesson['title']}",
                            "priority": "high"
                        })
                        break
        
        return next_steps
    
    async def _get_recent_activity(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent activity untuk student dalam course"""
        
        # Get recent lesson progress updates
        recent_lesson_activity = await db[self.lesson_progress_collection].find({
            "student_id": ObjectId(student_id),
            "course_id": ObjectId(course_id)
        }).sort("last_activity", -1).limit(limit).to_list(limit)
        
        activity = []
        for lp in recent_lesson_activity:
            # Get lesson info
            lesson = await db["lessons"].find_one(
                {"_id": lp["lesson_id"]},
                {"title": 1}
            )
            
            activity.append({
                "type": "lesson_progress",
                "timestamp": lp.get("last_activity"),
                "description": f"Worked on: {lesson.get('title', 'Unknown Lesson') if lesson else 'Unknown Lesson'}",
                "status": lp.get("status"),
                "completion_percentage": lp.get("completion_percentage", 0)
            })
        
        return sorted(activity, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    async def _get_learning_recommendations(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> List[Dict[str, Any]]:
        """Get personalized learning recommendations"""
        
        recommendations = []
        
        # Analyze progress patterns
        progress = await self.get_course_progress(db, student_id, course_id)
        if not progress:
            return recommendations
        
        # Time-based recommendations
        if progress.streak_days == 0:
            recommendations.append({
                "type": "engagement",
                "title": "Start your learning streak",
                "description": "Begin studying today to start building a learning habit",
                "priority": "medium"
            })
        elif progress.streak_days >= 7:
            recommendations.append({
                "type": "achievement",
                "title": "Great job on your learning streak!",
                "description": f"You've been consistent for {progress.streak_days} days",
                "priority": "low"
            })
        
        # Performance-based recommendations
        if progress.average_quiz_score < 70 and len(progress.quiz_scores) > 0:
            recommendations.append({
                "type": "improvement",
                "title": "Review quiz topics",
                "description": "Your average quiz score could use improvement",
                "priority": "high"
            })
        
        return recommendations
    
    async def _get_time_spent_today(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> int:
        """Get time spent today dalam course (seconds)"""
        
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        
        # Get today's lesson progress updates
        today_progress = await db[self.lesson_progress_collection].find({
            "student_id": ObjectId(student_id),
            "course_id": ObjectId(course_id),
            "last_activity": {"$gte": today_start}
        }).to_list(1000)
        
        total_time = sum(lp.get("total_time_spent", 0) for lp in today_progress)
        return total_time
    
    async def _predict_completion_time(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        course_id: str
    ) -> Optional[datetime]:
        """Predict course completion time berdasarkan current progress"""
        
        progress = await self.get_course_progress(db, student_id, course_id)
        if not progress or progress.completion_percentage == 0:
            return None
        
        # Calculate average daily progress
        if progress.started_at:
            days_since_start = (datetime.utcnow() - progress.started_at).days
            if days_since_start > 0:
                daily_progress = progress.completion_percentage / days_since_start
                remaining_progress = 100 - progress.completion_percentage
                
                if daily_progress > 0:
                    days_to_completion = remaining_progress / daily_progress
                    return datetime.utcnow() + timedelta(days=days_to_completion)
        
        return None
    
    async def _get_module_analytics_for_course(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        module_id: str
    ) -> Dict[str, Any]:
        """Get module analytics within course context"""
        
        module_progress_docs = await db[self.module_progress_collection].find({
            "course_id": ObjectId(course_id),
            "module_id": ObjectId(module_id)
        }).to_list(1000)
        
        if not module_progress_docs:
            return {
                "students_enrolled": 0,
                "completion_rate": 0,
                "average_score": 0,
                "average_time": 0
            }
        
        total_students = len(module_progress_docs)
        completed = sum(1 for mp in module_progress_docs if mp.get("status") == "completed")
        scores = [mp.get("score") for mp in module_progress_docs if mp.get("score") is not None]
        times = [mp.get("total_time_spent", 0) for mp in module_progress_docs]
        
        return {
            "students_enrolled": total_students,
            "completion_rate": (completed / total_students * 100) if total_students > 0 else 0,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "average_time": sum(times) / len(times) if times else 0
        }
    
    async def _calculate_engagement_analytics(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        progress_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate engagement analytics"""
        
        # Daily active users over time
        daily_activity = {}
        for p in progress_data:
            if p.get("last_activity"):
                date_key = p["last_activity"].date().isoformat()
                daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
        
        # Peak activity hours
        hourly_activity = {}
        for p in progress_data:
            if p.get("last_activity"):
                hour = p["last_activity"].hour
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "daily_active_users": daily_activity,
            "peak_activity_hours": [hour for hour, count in peak_hours],
            "engagement_trend": "increasing",  # This would be calculated from historical data
            "average_session_time": sum(p.get("total_time_spent", 0) for p in progress_data) / len(progress_data) if progress_data else 0
        }
    
    async def _calculate_progress_trends(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str
    ) -> Dict[str, Any]:
        """Calculate progress trends over time"""
        
        # Get historical progress data
        # This would typically involve tracking progress snapshots over time
        # For now, return placeholder data
        
        return {
            "enrollment_trend": "stable",
            "completion_trend": "improving",
            "performance_trend": "stable",
            "engagement_trend": "increasing"
        }

# Create singleton instance
course_progress_crud = CourseProgressCRUD()
