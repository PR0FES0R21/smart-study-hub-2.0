# ==============================================================================
# File: app/core/lms_integration.py
# Deskripsi: Integration Bridge untuk Git-like LMS dengan existing systems
# ==============================================================================
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

class LMSIntegrationBridge:
    """Bridge untuk integrasi Git-like LMS dengan existing Smart Study Hub systems"""
    
    def __init__(self):
        pass
    
    # ==================== TEACHING ASSIGNMENTS INTEGRATION ====================
    
    async def auto_create_courses_from_assignments(
        self,
        db: AsyncIOMotorDatabase,
        academic_period_id: str
    ) -> List[Dict[str, Any]]:
        """Auto-create standard courses berdasarkan coordination assignments"""
        
        # Get coordination assignments untuk academic period
        coordinations = await db["coordination_assignments"].find({
            "academic_period_id": ObjectId(academic_period_id),
            "is_active": True
        }).to_list(None)
        
        created_courses = []
        
        for coordination in coordinations:
            # Check if course already exists
            existing_course = await db["courses"].find_one({
                "subject_id": coordination["subject_id"],
                "grade_level": coordination["grade_level"],  # Assuming this field exists
                "academic_period_id": ObjectId(academic_period_id),
                "is_master": True
            })
            
            if existing_course:
                continue  # Skip if already exists
            
            # Get subject and coordinator details
            subject = await db["subjects"].find_one({"_id": coordination["subject_id"]})
            coordinator = await db["users"].find_one({"_id": coordination["coordinator_id"]})
            
            if not subject or not coordinator:
                continue
            
            # Create standard course
            course_data = {
                "title": f"{subject['name']} - Grade {coordination.get('grade_level', 'N/A')}",
                "description": f"Standard course for {subject['name']} subject",
                "code": f"{subject['code']}-G{coordination.get('grade_level', 'X')}-{academic_period_id[:8]}",
                "subject_id": coordination["subject_id"],
                "expertise_program_id": coordination.get("expertise_program_id"),
                "grade_level": coordination.get("grade_level", 10),
                "academic_period_id": ObjectId(academic_period_id),
                "coordinator_id": coordination["coordinator_id"],
                "coordination_assignment_id": coordination["_id"],
                
                "metadata": {
                    "estimated_duration_hours": 40,
                    "difficulty_level": "intermediate",
                    "prerequisites": [],
                    "learning_objectives": [],
                    "tags": [subject["name"].lower(), f"grade-{coordination.get('grade_level', 10)}"],
                    "curriculum_standards": [],
                    "version": "1.0",
                    "changelog": [
                        {
                            "version": "1.0",
                            "date": datetime.utcnow(),
                            "changes": ["Initial course creation"],
                            "author": str(coordination["coordinator_id"])
                        }
                    ]
                },
                
                "structure": {
                    "modules": [],
                    "total_lessons": 0,
                    "total_assessments": 0,
                    "completion_criteria": {
                        "required_modules": "all",
                        "minimum_score": 70,
                        "time_limit_days": None,
                        "attendance_required": True
                    }
                },
                
                "is_master": True,
                "fork_count": 0,
                "status": "development",
                "is_published": False,
                "total_contributors": 1,
                "total_pull_requests": 0,
                "last_updated_by": coordination["coordinator_id"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db["courses"].insert_one(course_data)
            course_data["_id"] = result.inserted_id
            course_data["id"] = str(result.inserted_id)
            created_courses.append(course_data)
        
        return created_courses
    
    async def get_available_courses_for_teacher(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        academic_period_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get courses yang bisa di-fork oleh teacher berdasarkan teaching assignments"""
        
        # Get teacher's teaching assignments
        match_criteria = {
            "teacher_id": ObjectId(teacher_id),
            "is_active": True
        }
        
        if academic_period_id:
            match_criteria["academic_period_id"] = ObjectId(academic_period_id)
        
        assignments = await db["teaching_assignments"].find(match_criteria).to_list(None)
        
        if not assignments:
            return []
        
        # Get unique subject IDs from assignments
        subject_ids = list(set([assignment["subject_id"] for assignment in assignments]))
        
        # Get available courses for these subjects
        courses = await db["courses"].find({
            "subject_id": {"$in": subject_ids},
            "is_master": True,
            "is_published": True,
            "status": "active"
        }).to_list(None)
        
        # Enhance courses with fork information
        enhanced_courses = []
        for course in courses:
            # Check if teacher already has a fork for any of their teaching assignments
            existing_forks = await db["teacher_forks"].find({
                "master_course_id": course["_id"],
                "teacher_id": ObjectId(teacher_id),
                "is_active": True
            }).to_list(None)
            
            # Get applicable teaching assignments for this course
            applicable_assignments = [
                assignment for assignment in assignments
                if assignment["subject_id"] == course["subject_id"]
            ]
            
            course["id"] = str(course["_id"])
            course["existing_forks"] = [
                {
                    "fork_id": str(fork["_id"]),
                    "teaching_assignment_id": str(fork["teaching_assignment_id"]),
                    "title": fork["title"],
                    "is_active": fork["is_active"]
                } for fork in existing_forks
            ]
            course["applicable_assignments"] = [
                {
                    "assignment_id": str(assignment["_id"]),
                    "class_id": str(assignment["class_id"]),
                    "class_name": "Class Name",  # Would need to populate this
                    "can_fork": len(existing_forks) == 0 or not any(
                        fork["teaching_assignment_id"] == assignment["_id"] for fork in existing_forks
                    )
                } for assignment in applicable_assignments
            ]
            
            enhanced_courses.append(course)
        
        return enhanced_courses
    
    # ==================== EXAM SYSTEM INTEGRATION ====================
    
    async def create_exam_from_course_module(
        self,
        db: AsyncIOMotorDatabase,
        fork_id: str,
        module_id: str,
        teacher_id: str,
        exam_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create exam based on course module content"""
        
        # Get fork and module
        fork = await db["teacher_forks"].find_one({"_id": ObjectId(fork_id)})
        if not fork:
            raise HTTPException(status_code=404, detail="Fork not found")
        
        module = await db["course_modules"].find_one({
            "_id": ObjectId(module_id),
            "course_id": ObjectId(fork_id)
        })
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Get teaching assignment
        teaching_assignment = await db["teaching_assignments"].find_one({
            "_id": fork["teaching_assignment_id"]
        })
        if not teaching_assignment:
            raise HTTPException(status_code=404, detail="Teaching assignment not found")
        
        # Create exam using existing exam system
        exam_data = {
            "title": f"Exam: {module['title']}",
            "description": f"Exam based on course module: {module['title']}",
            "teaching_assignment_id": teaching_assignment["_id"],
            "course_module_id": ObjectId(module_id),  # Link to course module
            "course_fork_id": ObjectId(fork_id),      # Link to fork
            
            # Use existing exam fields
            "exam_type": exam_settings.get("exam_type", "quiz"),
            "total_questions": exam_settings.get("total_questions", 10),
            "duration_minutes": exam_settings.get("duration_minutes", 30),
            "max_score": exam_settings.get("max_score", 100),
            "passing_score": exam_settings.get("passing_score", 70),
            
            # Schedule
            "availability_start_time": exam_settings.get("start_time", datetime.utcnow()),
            "availability_end_time": exam_settings.get("end_time", datetime.utcnow()),
            
            # Settings
            "randomize_questions": exam_settings.get("randomize_questions", True),
            "show_results_immediately": exam_settings.get("show_results", False),
            "allow_review": exam_settings.get("allow_review", True),
            
            # Integration metadata
            "created_from_lms": True,
            "lms_metadata": {
                "source_type": "course_module",
                "source_id": str(module_id),
                "fork_id": str(fork_id),
                "module_title": module["title"]
            },
            
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db["exams"].insert_one(exam_data)
        
        # Link module to exam
        await db["course_modules"].update_one(
            {"_id": ObjectId(module_id)},
            {
                "$push": {
                    "linked_exams": {
                        "exam_id": result.inserted_id,
                        "exam_type": exam_data["exam_type"],
                        "created_at": datetime.utcnow()
                    }
                }
            }
        )
        
        return {
            "exam_id": str(result.inserted_id),
            "exam_title": exam_data["title"],
            "module_id": str(module_id),
            "fork_id": str(fork_id),
            "created_at": exam_data["created_at"]
        }
    
    async def sync_course_progress_with_exams(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        fork_id: str
    ) -> Dict[str, Any]:
        """Sync course progress dengan exam results"""
        
        # Get student's exam sessions untuk course-related exams
        pipeline = [
            {
                "$lookup": {
                    "from": "exams",
                    "localField": "exam_id",
                    "foreignField": "_id",
                    "as": "exam"
                }
            },
            {"$unwind": "$exam"},
            {
                "$match": {
                    "student_id": ObjectId(student_id),
                    "exam.course_fork_id": ObjectId(fork_id),
                    "status": "completed"
                }
            }
        ]
        
        exam_sessions = await db["exam_sessions"].aggregate(pipeline).to_list(None)
        
        if not exam_sessions:
            return {"message": "No completed exams found", "progress": 0}
        
        # Calculate progress based on exam results
        total_score = sum([session["final_score"] for session in exam_sessions])
        total_possible = sum([session["max_possible_score"] for session in exam_sessions])
        
        overall_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
        
        # Update or create course progress record
        progress_data = {
            "user_id": ObjectId(student_id),
            "fork_id": ObjectId(fork_id),
            "overall_progress": {
                "percentage": overall_percentage,
                "completed_exams": len(exam_sessions),
                "total_score": total_score,
                "max_possible_score": total_possible
            },
            "exam_results": [
                {
                    "exam_id": str(session["exam_id"]),
                    "module_id": str(session["exam"]["course_module_id"]),
                    "score": session["final_score"],
                    "max_score": session["max_possible_score"],
                    "completed_at": session["completed_at"]
                } for session in exam_sessions
            ],
            "last_updated": datetime.utcnow()
        }
        
        await db["course_progress"].update_one(
            {"user_id": ObjectId(student_id), "fork_id": ObjectId(fork_id)},
            {"$set": progress_data},
            upsert=True
        )
        
        return progress_data
    
    # ==================== USER MANAGEMENT INTEGRATION ====================
    
    async def auto_enroll_students_to_forks(
        self,
        db: AsyncIOMotorDatabase,
        academic_period_id: str
    ) -> Dict[str, Any]:
        """Auto-enroll students to teacher forks berdasarkan class assignments"""
        
        enrolled_count = 0
        errors = []
        
        # Get all active forks
        forks = await db["teacher_forks"].find({
            "is_active": True
        }).to_list(None)
        
        for fork in forks:
            try:
                # Get teaching assignment
                assignment = await db["teaching_assignments"].find_one({
                    "_id": fork["teaching_assignment_id"],
                    "academic_period_id": ObjectId(academic_period_id)
                })
                
                if not assignment:
                    continue
                
                # Get students in the class
                students = await db["profiles"].find({
                    "class_id": assignment["class_id"],
                    "is_active": True
                }).to_list(None)
                
                # Auto-enroll students who aren't already enrolled
                for student in students:
                    existing_enrollment = await db["course_enrollments"].find_one({
                        "user_id": student["user_id"],
                        "fork_id": fork["_id"],
                        "is_active": True
                    })
                    
                    if not existing_enrollment:
                        enrollment_data = {
                            "user_id": student["user_id"],
                            "fork_id": fork["_id"],
                            "enrollment_type": "automatic",
                            "enrolled_at": datetime.utcnow(),
                            "access_level": "student",
                            "is_active": True,
                            "progress": {
                                "completion_percentage": 0.0,
                                "modules_completed": 0,
                                "lessons_viewed": 0,
                                "assignments_submitted": 0
                            },
                            "auto_enrolled_from": {
                                "source": "class_assignment",
                                "class_id": assignment["class_id"],
                                "teaching_assignment_id": assignment["_id"]
                            }
                        }
                        
                        await db["course_enrollments"].insert_one(enrollment_data)
                        enrolled_count += 1
                        
            except Exception as e:
                errors.append({
                    "fork_id": str(fork["_id"]),
                    "error": str(e)
                })
        
        return {
            "enrolled_count": enrolled_count,
            "total_errors": len(errors),
            "errors": errors
        }
    
    # ==================== ANALYTICS INTEGRATION ====================
    
    async def generate_integrated_analytics(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: str,
        academic_period_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate analytics yang menggabungkan LMS dan exam data"""
        
        # Get teacher's forks
        match_criteria = {"teacher_id": ObjectId(teacher_id), "is_active": True}
        forks = await db["teacher_forks"].find(match_criteria).to_list(None)
        
        analytics = {
            "teacher_summary": {
                "total_forks": len(forks),
                "active_courses": 0,
                "total_students": 0,
                "avg_completion_rate": 0.0
            },
            "course_performance": [],
            "student_engagement": {
                "most_active_courses": [],
                "completion_trends": [],
                "challenge_areas": []
            },
            "content_analytics": {
                "most_accessed_modules": [],
                "popular_lesson_types": {},
                "exam_integration_stats": {}
            }
        }
        
        total_completion = 0.0
        total_students = 0
        
        for fork in forks:
            # Get fork statistics
            enrollments = await db["course_enrollments"].find({
                "fork_id": fork["_id"],
                "is_active": True
            }).to_list(None)
            
            # Get exam data for this fork
            exams = await db["exams"].find({
                "course_fork_id": fork["_id"]
            }).to_list(None)
            
            # Calculate completion rates
            completed_students = len([
                e for e in enrollments 
                if e["progress"]["completion_percentage"] >= 70
            ])
            
            completion_rate = (completed_students / len(enrollments) * 100) if enrollments else 0
            
            course_perf = {
                "fork_id": str(fork["_id"]),
                "course_title": fork["title"],
                "total_students": len(enrollments),
                "completion_rate": completion_rate,
                "avg_progress": sum([e["progress"]["completion_percentage"] for e in enrollments]) / len(enrollments) if enrollments else 0,
                "total_exams": len(exams),
                "last_activity": fork.get("updated_at")
            }
            
            analytics["course_performance"].append(course_perf)
            total_completion += completion_rate
            total_students += len(enrollments)
        
        # Update summary
        analytics["teacher_summary"]["active_courses"] = len([f for f in forks if f.get("is_active")])
        analytics["teacher_summary"]["total_students"] = total_students
        analytics["teacher_summary"]["avg_completion_rate"] = total_completion / len(forks) if forks else 0
        
        return analytics
    
    # ==================== NOTIFICATION INTEGRATION ====================
    
    async def create_lms_notifications(
        self,
        db: AsyncIOMotorDatabase,
        event_type: str,
        data: Dict[str, Any],
        target_users: Optional[List[str]] = None
    ) -> List[str]:
        """Create notifications untuk LMS events"""
        
        notification_templates = {
            "course_published": {
                "title": "New Course Available",
                "message": f"Course '{data.get('course_title')}' is now available for forking",
                "type": "course_update",
                "target_roles": ["teacher"]
            },
            "pull_request_created": {
                "title": "New Pull Request",
                "message": f"Pull request '{data.get('pr_title')}' needs review",
                "type": "pr_notification",
                "target_roles": ["coordinator"]
            },
            "pull_request_approved": {
                "title": "Pull Request Approved",
                "message": f"Your pull request '{data.get('pr_title')}' has been approved",
                "type": "pr_notification", 
                "target_roles": ["teacher"]
            },
            "course_updated": {
                "title": "Course Updated",
                "message": f"Course '{data.get('course_title')}' has been updated",
                "type": "course_update",
                "target_roles": ["student"]
            },
            "fork_behind": {
                "title": "Course Update Available",
                "message": f"Your course fork '{data.get('fork_title')}' has updates available",
                "type": "sync_notification",
                "target_roles": ["teacher"]
            }
        }
        
        template = notification_templates.get(event_type)
        if not template:
            return []
        
        # Create notifications (simplified version)
        notifications = []
        
        if target_users:
            for user_id in target_users:
                notification_data = {
                    "recipient_id": ObjectId(user_id),
                    "title": template["title"],
                    "message": template["message"],
                    "type": template["type"],
                    "data": data,
                    "is_read": False,
                    "created_at": datetime.utcnow(),
                    "event_source": "lms",
                    "event_type": event_type
                }
                
                result = await db["notifications"].insert_one(notification_data)
                notifications.append(str(result.inserted_id))
        
        return notifications

# Create singleton instance
lms_integration = LMSIntegrationBridge()