# ==============================================================================
# File: app/crud/module_progress.py
# Deskripsi: CRUD operations untuk Module Progress tracking (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

from app.models.lesson_progress import ModuleProgress
from app.schemas.base import PyObjectId
from app.crud.lesson_progress import lesson_progress_crud

class ModuleProgressCRUD:
    """CRUD operations untuk Module Progress tracking"""
    
    def __init__(self):
        self.collection = "module_progress"
        self.module_collection = "modules"
        self.lesson_progress_collection = "lesson_progress"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def start_module_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        module_id: str,
        course_id: Optional[str] = None
    ) -> ModuleProgress:
        """Start progress tracking untuk module"""
        
        # Check if progress already exists
        existing_progress = await self.get_module_progress(db, student_id, module_id)
        if existing_progress:
            return existing_progress
        
        # Get module data
        module = await db[self.module_collection].find_one({"_id": ObjectId(module_id)})
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Create progress object
        progress = ModuleProgress(
            student_id=PyObjectId(student_id),
            module_id=PyObjectId(module_id),
            course_id=PyObjectId(course_id) if course_id else None,
            status="not_started",
            total_lessons=len(module.get("lesson_refs", []))
        )
        
        # Insert to database
        result = await db[self.collection].insert_one(progress.to_mongo())
        progress.id = str(result.inserted_id)
        
        return progress
    
    async def update_module_progress_from_lessons(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        module_id: str
    ) -> ModuleProgress:
        """Update module progress berdasarkan lesson progress"""
        
        # Get or create module progress
        progress = await self.get_module_progress(db, student_id, module_id)
        if not progress:
            progress = await self.start_module_progress(db, student_id, module_id)
        
        # Get module data untuk lesson references
        module = await db[self.module_collection].find_one({"_id": ObjectId(module_id)})
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        lesson_refs = module.get("lesson_refs", [])
        lesson_ids = [str(ref["lesson_id"]) for ref in lesson_refs]
        
        # Get lesson progress data
        lesson_progress_data = await db[self.lesson_progress_collection].find({
            "student_id": ObjectId(student_id),
            "lesson_id": {"$in": [ObjectId(lid) for lid in lesson_ids]}
        }).to_list(len(lesson_ids))
        
        # Update module progress
        await progress.calculate_from_lesson_progress(lesson_progress_data)
        
        # Update current lesson
        in_progress_lessons = [lp for lp in lesson_progress_data if lp.get("status") == "in_progress"]
        if in_progress_lessons:
            # Get the most recent in-progress lesson
            current_lesson = max(in_progress_lessons, key=lambda x: x.get("last_activity", datetime.min))
            progress.current_lesson_id = PyObjectId(current_lesson["lesson_id"])
        
        # Update completion order
        completed_lessons = [lp for lp in lesson_progress_data if lp.get("status") == "completed"]
        completed_lessons.sort(key=lambda x: x.get("completed_at", datetime.min))
        progress.lesson_completion_order = [PyObjectId(lp["lesson_id"]) for lp in completed_lessons]
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return progress
    
    # ==================== READ OPERATIONS ====================
    
    async def get_module_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        module_id: str
    ) -> Optional[ModuleProgress]:
        """Get module progress untuk specific student"""
        
        progress_data = await db[self.collection].find_one({
            "student_id": ObjectId(student_id),
            "module_id": ObjectId(module_id)
        })
        
        if not progress_data:
            return None
        
        return ModuleProgress.from_mongo(progress_data)
    
    async def get_student_module_progress_list(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get list of module progress untuk student"""
        
        # Build query
        query = {"student_id": ObjectId(student_id)}
        
        if filters:
            if filters.get("course_id"):
                query["course_id"] = ObjectId(filters["course_id"])
            if filters.get("status"):
                query["status"] = filters["status"]
        
        # Get total count
        total_count = await db[self.collection].count_documents(query)
        
        # Execute query dengan module details
        pipeline = [
            {"$match": query},
            
            # Lookup module details
            {
                "$lookup": {
                    "from": "modules",
                    "localField": "module_id",
                    "foreignField": "_id",
                    "as": "module_info"
                }
            },
            {"$unwind": {"path": "$module_info", "preserveNullAndEmptyArrays": True}},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "module_title": "$module_info.title",
                    "module_description": "$module_info.description"
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
                    "module_id": {"$toString": "$module_id"},
                    "module_title": 1,
                    "module_description": 1,
                    "status": 1,
                    "completion_percentage": 1,
                    "score": 1,
                    "total_lessons": 1,
                    "completed_lessons": 1,
                    "in_progress_lessons": 1,
                    "total_time_spent": 1,
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
    
    async def get_module_progress_analytics(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        teacher_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get analytics untuk module progress"""
        
        # Get all progress untuk this module
        pipeline = [
            {"$match": {"module_id": ObjectId(module_id)}},
            
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
            
            # Lookup module info
            {
                "$lookup": {
                    "from": "modules",
                    "localField": "module_id",
                    "foreignField": "_id",
                    "as": "module_info"
                }
            },
            {"$unwind": {"path": "$module_info", "preserveNullAndEmptyArrays": True}}
        ]
        
        progress_data = await db[self.collection].aggregate(pipeline).to_list(1000)
        
        if not progress_data:
            return {
                "module_id": module_id,
                "total_students": 0,
                "completion_stats": {},
                "performance_stats": {},
                "lesson_analytics": {}
            }
        
        # Calculate analytics
        total_students = len(progress_data)
        completed = sum(1 for p in progress_data if p.get("status") == "completed")
        in_progress = sum(1 for p in progress_data if p.get("status") == "in_progress")
        not_started = sum(1 for p in progress_data if p.get("status") == "not_started")
        
        # Performance stats
        scores = [p.get("score") for p in progress_data if p.get("score") is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Time stats
        total_times = [p.get("total_time_spent", 0) for p in progress_data if p.get("total_time_spent")]
        avg_time = sum(total_times) / len(total_times) if total_times else 0
        
        # Lesson completion analytics
        module_info = progress_data[0].get("module_info", {}) if progress_data else {}
        lesson_refs = module_info.get("lesson_refs", [])
        
        lesson_analytics = {}
        for ref in lesson_refs:
            lesson_id = str(ref["lesson_id"])
            lesson_analytics[lesson_id] = {
                "order": ref.get("order", 0),
                "required": ref.get("required", True),
                "students_started": 0,
                "students_completed": 0,
                "average_score": 0,
                "completion_rate": 0
            }
        
        # Get lesson progress data untuk detailed analytics
        all_lesson_ids = [ObjectId(ref["lesson_id"]) for ref in lesson_refs]
        lesson_progress_docs = await db[self.lesson_progress_collection].find({
            "lesson_id": {"$in": all_lesson_ids}
        }).to_list(10000)
        
        # Calculate lesson-level analytics
        for lesson_id_str, analytics in lesson_analytics.items():
            lesson_id_obj = ObjectId(lesson_id_str)
            lesson_progresses = [lp for lp in lesson_progress_docs if lp.get("lesson_id") == lesson_id_obj]
            
            if lesson_progresses:
                started = sum(1 for lp in lesson_progresses if lp.get("status") != "not_started")
                completed = sum(1 for lp in lesson_progresses if lp.get("status") == "completed")
                scores = [lp.get("score") for lp in lesson_progresses if lp.get("score") is not None]
                
                analytics["students_started"] = started
                analytics["students_completed"] = completed
                analytics["completion_rate"] = (completed / started * 100) if started > 0 else 0
                analytics["average_score"] = sum(scores) / len(scores) if scores else 0
        
        return {
            "module_id": module_id,
            "total_students": total_students,
            "completion_stats": {
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started,
                "completion_rate": (completed / total_students * 100) if total_students > 0 else 0
            },
            "performance_stats": {
                "average_score": round(avg_score, 2),
                "average_time_spent": round(avg_time / 3600, 2),  # Convert to hours
                "total_scores": len(scores)
            },
            "lesson_analytics": lesson_analytics,
            "engagement_stats": {
                "active_in_last_week": sum(1 for p in progress_data 
                                         if p.get("last_activity") and 
                                         (datetime.utcnow() - p["last_activity"]).days < 7),
                "average_lessons_completed": sum(p.get("completed_lessons", 0) for p in progress_data) / total_students if total_students > 0 else 0
            }
        }
    
    async def get_module_progress_with_lessons(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        module_id: str
    ) -> Dict[str, Any]:
        """Get detailed module progress dengan lesson progress"""
        
        # Get module progress
        module_progress = await self.get_module_progress(db, student_id, module_id)
        if not module_progress:
            module_progress = await self.start_module_progress(db, student_id, module_id)
        
        # Get module data
        module = await db[self.module_collection].find_one({"_id": ObjectId(module_id)})
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Get lesson progress data
        lesson_refs = module.get("lesson_refs", [])
        lesson_ids = [str(ref["lesson_id"]) for ref in lesson_refs]
        
        lesson_progress_map = await lesson_progress_crud.get_multiple_lesson_progress(
            db, student_id, lesson_ids
        )
        
        # Combine data
        lesson_details = []
        for ref in sorted(lesson_refs, key=lambda x: x.get("order", 0)):
            lesson_id = str(ref["lesson_id"])
            lesson_progress = lesson_progress_map.get(lesson_id)
            
            # Get lesson basic info
            lesson_info = await db["lessons"].find_one(
                {"_id": ObjectId(lesson_id)},
                {"title": 1, "description": 1, "metadata": 1, "difficulty_level": 1}
            )
            
            lesson_detail = {
                "lesson_id": lesson_id,
                "order": ref.get("order", 0),
                "required": ref.get("required", True),
                "custom_title": ref.get("custom_title"),
                "weight": ref.get("weight", 1.0),
                "unlock_condition": ref.get("unlock_condition", "sequential"),
                
                # Lesson info
                "title": lesson_info.get("title", "") if lesson_info else "",
                "description": lesson_info.get("description", "") if lesson_info else "",
                "difficulty_level": lesson_info.get("difficulty_level", "medium") if lesson_info else "medium",
                "estimated_duration": lesson_info.get("metadata", {}).get("total_duration", 0) if lesson_info else 0,
                
                # Progress info
                "progress": lesson_progress.dict() if lesson_progress else None,
                "is_unlocked": self._is_lesson_unlocked(ref, lesson_progress_map, lesson_refs),
                "can_start": self._can_start_lesson(ref, lesson_progress_map, lesson_refs)
            }
            lesson_details.append(lesson_detail)
        
        return {
            "module_progress": module_progress.dict(),
            "lesson_details": lesson_details,
            "learning_path": self._generate_learning_path(lesson_details),
            "next_lesson": self._get_next_lesson(lesson_details),
            "completion_summary": self._get_completion_summary(lesson_details)
        }
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_module_progress_status(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        module_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModuleProgress:
        """Update module progress status"""
        
        progress = await self.get_module_progress(db, student_id, module_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Module progress not found")
        
        progress.status = status
        progress.last_activity = datetime.utcnow()
        
        if status == "completed" and not progress.completed_at:
            progress.completed_at = datetime.utcnow()
        elif status == "in_progress" and not progress.started_at:
            progress.started_at = datetime.utcnow()
        
        # Update metadata if provided
        if metadata:
            if "estimated_time_remaining" in metadata:
                progress.estimated_time_remaining = metadata["estimated_time_remaining"]
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return progress
    
    # ==================== DELETE OPERATIONS ====================
    
    async def delete_module_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        module_id: str
    ) -> bool:
        """Delete module progress"""
        
        result = await db[self.collection].delete_one({
            "student_id": ObjectId(student_id),
            "module_id": ObjectId(module_id)
        })
        
        return result.deleted_count > 0
    
    # ==================== HELPER METHODS ====================
    
    def _is_lesson_unlocked(
        self,
        lesson_ref: Dict[str, Any],
        lesson_progress_map: Dict[str, Any],
        all_lesson_refs: List[Dict[str, Any]]
    ) -> bool:
        """Check if lesson is unlocked berdasarkan unlock condition"""
        
        unlock_condition = lesson_ref.get("unlock_condition", "sequential")
        
        if unlock_condition == "immediate":
            return True
        
        if unlock_condition == "sequential":
            # Check if all previous required lessons are completed
            current_order = lesson_ref.get("order", 0)
            for ref in all_lesson_refs:
                if ref.get("order", 0) < current_order and ref.get("required", True):
                    lesson_id = str(ref["lesson_id"])
                    progress = lesson_progress_map.get(lesson_id)
                    if not progress or progress.status != "completed":
                        return False
            return True
        
        # Custom unlock conditions would be implemented here
        return True
    
    def _can_start_lesson(
        self,
        lesson_ref: Dict[str, Any],
        lesson_progress_map: Dict[str, Any],
        all_lesson_refs: List[Dict[str, Any]]
    ) -> bool:
        """Check if lesson dapat dimulai"""
        
        lesson_id = str(lesson_ref["lesson_id"])
        progress = lesson_progress_map.get(lesson_id)
        
        # Already started or completed
        if progress and progress.status in ["in_progress", "completed"]:
            return True
        
        # Check if unlocked
        return self._is_lesson_unlocked(lesson_ref, lesson_progress_map, all_lesson_refs)
    
    def _generate_learning_path(self, lesson_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate recommended learning path"""
        
        path = []
        for lesson in sorted(lesson_details, key=lambda x: x["order"]):
            path_item = {
                "lesson_id": lesson["lesson_id"],
                "title": lesson["title"],
                "order": lesson["order"],
                "status": lesson["progress"]["status"] if lesson["progress"] else "not_started",
                "is_unlocked": lesson["is_unlocked"],
                "is_next": False
            }
            path.append(path_item)
        
        # Mark next lesson to take
        for item in path:
            if item["status"] == "not_started" and item["is_unlocked"]:
                item["is_next"] = True
                break
        
        return path
    
    def _get_next_lesson(self, lesson_details: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get next lesson yang harus diambil"""
        
        for lesson in sorted(lesson_details, key=lambda x: x["order"]):
            if lesson["can_start"] and (not lesson["progress"] or lesson["progress"]["status"] == "not_started"):
                return {
                    "lesson_id": lesson["lesson_id"],
                    "title": lesson["title"],
                    "order": lesson["order"],
                    "estimated_duration": lesson["estimated_duration"]
                }
        
        return None
    
    def _get_completion_summary(self, lesson_details: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get completion summary"""
        
        total_lessons = len(lesson_details)
        completed = sum(1 for lesson in lesson_details 
                       if lesson["progress"] and lesson["progress"]["status"] == "completed")
        in_progress = sum(1 for lesson in lesson_details 
                         if lesson["progress"] and lesson["progress"]["status"] == "in_progress")
        
        total_time = sum(lesson["progress"]["total_time_spent"] for lesson in lesson_details 
                        if lesson["progress"] and lesson["progress"]["total_time_spent"])
        
        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed,
            "in_progress_lessons": in_progress,
            "completion_percentage": (completed / total_lessons * 100) if total_lessons > 0 else 0,
            "total_time_spent": total_time,
            "estimated_time_remaining": sum(lesson["estimated_duration"] for lesson in lesson_details 
                                          if not lesson["progress"] or lesson["progress"]["status"] != "completed")
        }

# Create singleton instance
module_progress_crud = ModuleProgressCRUD()
