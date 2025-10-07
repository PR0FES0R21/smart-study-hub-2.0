# ==============================================================================
# File: app/crud/lesson_progress.py
# Deskripsi: CRUD operations untuk Lesson Progress tracking (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

from app.models.lesson_progress import (
    LessonProgress, PageProgress, ComponentProgress,
    ModuleProgress, CourseProgress
)
from app.schemas.base import PyObjectId
import asyncio

class LessonProgressCRUD:
    """CRUD operations untuk Lesson Progress tracking"""
    
    def __init__(self):
        self.collection = "lesson_progress"
        self.lesson_collection = "lessons"
        self.user_collection = "users"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def start_lesson_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_id: str,
        course_id: Optional[str] = None,
        module_id: Optional[str] = None,
        access_method: str = "direct"
    ) -> LessonProgress:
        """Start progress tracking untuk lesson"""
        
        # Check if progress already exists
        existing_progress = await self.get_lesson_progress(db, student_id, lesson_id)
        if existing_progress:
            return existing_progress
        
        # Get lesson data untuk setup progress
        lesson = await db[self.lesson_collection].find_one({"_id": ObjectId(lesson_id)})
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Create progress object
        progress = LessonProgress(
            student_id=PyObjectId(student_id),
            lesson_id=PyObjectId(lesson_id),
            course_id=PyObjectId(course_id) if course_id else None,
            module_id=PyObjectId(module_id) if module_id else None,
            access_method=access_method,
            status="not_started"
        )
        
        # Initialize page progress untuk semua pages dalam lesson
        lesson_pages = lesson.get("pages", [])
        for page in lesson_pages:
            page_progress = PageProgress(
                page_number=page.get("page_number", 1),
                status="not_started",
                component_progress=[
                    ComponentProgress(
                        component_id=comp.get("component_id"),
                        component_type=comp.get("type"),
                        status="not_started"
                    ) for comp in page.get("embedded_components", [])
                ]
            )
            progress.page_progress.append(page_progress)
        
        # Insert to database
        result = await db[self.collection].insert_one(progress.to_mongo())
        progress.id = str(result.inserted_id)
        
        return progress
    
    async def update_page_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_id: str,
        page_number: int,
        progress_data: Dict[str, Any]
    ) -> LessonProgress:
        """Update progress untuk specific page"""
        
        # Get existing progress
        progress = await self.get_lesson_progress(db, student_id, lesson_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Lesson progress not found")
        
        # Find and update page progress
        page_progress = None
        for page in progress.page_progress:
            if page.page_number == page_number:
                page_progress = page
                break
        
        if not page_progress:
            raise HTTPException(status_code=404, detail="Page not found in progress")
        
        # Update page progress
        if "status" in progress_data:
            page_progress.status = progress_data["status"]
        if "time_spent" in progress_data:
            page_progress.time_spent += progress_data["time_spent"]
        if "completion_percentage" in progress_data:
            page_progress.completion_percentage = progress_data["completion_percentage"]
        
        # Update timestamps
        now = datetime.utcnow()
        if page_progress.status == "reading" and not page_progress.started_at:
            page_progress.started_at = now
        elif page_progress.status == "completed":
            page_progress.completed_at = now
        
        page_progress.last_activity = now
        
        # Update component progress if provided
        if "component_progress" in progress_data:
            for comp_update in progress_data["component_progress"]:
                comp_id = comp_update.get("component_id")
                for comp in page_progress.component_progress:
                    if comp.component_id == comp_id:
                        comp.status = comp_update.get("status", comp.status)
                        comp.score = comp_update.get("score", comp.score)
                        comp.time_spent += comp_update.get("time_spent", 0)
                        comp.attempts += comp_update.get("attempts", 0)
                        comp.last_activity = now
                        
                        if comp.status == "in_progress" and not comp.started_at:
                            comp.started_at = now
                        elif comp.status == "completed":
                            comp.completed_at = now
                        break
        
        # Recalculate lesson progress
        progress.update_completion_status()
        progress.current_page = page_number
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return progress
    
    async def complete_component(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_id: str,
        page_number: int,
        component_id: str,
        completion_data: Dict[str, Any]
    ) -> LessonProgress:
        """Mark component as completed dengan score dan feedback"""
        
        progress_data = {
            "component_progress": [{
                "component_id": component_id,
                "status": "completed",
                "score": completion_data.get("score"),
                "time_spent": completion_data.get("time_spent", 0),
                "attempts": completion_data.get("attempts", 1),
                "responses": completion_data.get("responses", [])
            }]
        }
        
        return await self.update_page_progress(
            db, student_id, lesson_id, page_number, progress_data
        )
    
    # ==================== READ OPERATIONS ====================
    
    async def get_lesson_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_id: str
    ) -> Optional[LessonProgress]:
        """Get lesson progress untuk specific student"""
        
        progress_data = await db[self.collection].find_one({
            "student_id": ObjectId(student_id),
            "lesson_id": ObjectId(lesson_id)
        })
        
        if not progress_data:
            return None
        
        return LessonProgress.from_mongo(progress_data)
    
    async def get_student_lesson_progress_list(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get list of lesson progress untuk student"""
        
        # Build query
        query = {"student_id": ObjectId(student_id)}
        
        if filters:
            if filters.get("course_id"):
                query["course_id"] = ObjectId(filters["course_id"])
            if filters.get("module_id"):
                query["module_id"] = ObjectId(filters["module_id"])
            if filters.get("status"):
                query["status"] = filters["status"]
            if filters.get("access_method"):
                query["access_method"] = filters["access_method"]
        
        # Get total count
        total_count = await db[self.collection].count_documents(query)
        
        # Execute query dengan lesson details
        pipeline = [
            {"$match": query},
            
            # Lookup lesson details
            {
                "$lookup": {
                    "from": "lessons",
                    "localField": "lesson_id",
                    "foreignField": "_id",
                    "as": "lesson_info"
                }
            },
            {"$unwind": {"path": "$lesson_info", "preserveNullAndEmptyArrays": True}},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "lesson_title": "$lesson_info.title",
                    "lesson_description": "$lesson_info.description",
                    "total_pages": {"$size": "$page_progress"}
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
                    "lesson_id": {"$toString": "$lesson_id"},
                    "lesson_title": 1,
                    "lesson_description": 1,
                    "status": 1,
                    "completion_percentage": 1,
                    "score": 1,
                    "current_page": 1,
                    "total_pages": 1,
                    "total_time_spent": 1,
                    "access_method": 1,
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
    
    async def get_lesson_progress_analytics(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        teacher_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get analytics untuk lesson progress (untuk teachers)"""
        
        # Get all progress untuk this lesson
        pipeline = [
            {"$match": {"lesson_id": ObjectId(lesson_id)}},
            
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
            
            # Lookup lesson info
            {
                "$lookup": {
                    "from": "lessons",
                    "localField": "lesson_id",
                    "foreignField": "_id",
                    "as": "lesson_info"
                }
            },
            {"$unwind": {"path": "$lesson_info", "preserveNullAndEmptyArrays": True}}
        ]
        
        progress_data = await db[self.collection].aggregate(pipeline).to_list(1000)
        
        if not progress_data:
            return {
                "lesson_id": lesson_id,
                "total_students": 0,
                "completion_stats": {},
                "performance_stats": {},
                "engagement_stats": {}
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
        completion_times = []
        for p in progress_data:
            if p.get("started_at") and p.get("completed_at"):
                time_diff = p["completed_at"] - p["started_at"]
                completion_times.append(time_diff.total_seconds() / 60)  # minutes
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Page analytics
        page_analytics = {}
        for p in progress_data:
            for page in p.get("page_progress", []):
                page_num = page.get("page_number")
                if page_num not in page_analytics:
                    page_analytics[page_num] = {
                        "total_views": 0,
                        "completed": 0,
                        "avg_time": 0,
                        "drop_off_rate": 0
                    }
                
                page_analytics[page_num]["total_views"] += 1
                if page.get("status") == "completed":
                    page_analytics[page_num]["completed"] += 1
        
        # Calculate drop-off rates
        for page_num, stats in page_analytics.items():
            if stats["total_views"] > 0:
                stats["completion_rate"] = (stats["completed"] / stats["total_views"]) * 100
                stats["drop_off_rate"] = 100 - stats["completion_rate"]
        
        return {
            "lesson_id": lesson_id,
            "total_students": total_students,
            "completion_stats": {
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started,
                "completion_rate": (completed / total_students * 100) if total_students > 0 else 0
            },
            "performance_stats": {
                "average_score": round(avg_score, 2),
                "total_scores": len(scores),
                "score_distribution": self._calculate_score_distribution(scores)
            },
            "time_stats": {
                "average_completion_time": round(avg_completion_time, 2),  # minutes
                "total_completions": len(completion_times)
            },
            "page_analytics": page_analytics,
            "engagement_stats": {
                "active_in_last_week": sum(1 for p in progress_data 
                                         if p.get("last_activity") and 
                                         (datetime.utcnow() - p["last_activity"]).days < 7),
                "never_started": not_started
            }
        }
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_lesson_progress_status(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LessonProgress:
        """Update overall lesson progress status"""
        
        progress = await self.get_lesson_progress(db, student_id, lesson_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Lesson progress not found")
        
        progress.status = status
        progress.last_activity = datetime.utcnow()
        
        if status == "completed" and not progress.completed_at:
            progress.completed_at = datetime.utcnow()
        elif status == "in_progress" and not progress.started_at:
            progress.started_at = datetime.utcnow()
        
        # Update metadata if provided
        if metadata:
            if "device_type" in metadata:
                progress.device_type = metadata["device_type"]
            if "estimated_time_remaining" in metadata:
                progress.estimated_time_remaining = metadata["estimated_time_remaining"]
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(progress.id)},
            {"$set": progress.to_mongo()}
        )
        
        return progress
    
    # ==================== DELETE OPERATIONS ====================
    
    async def delete_lesson_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_id: str
    ) -> bool:
        """Delete lesson progress (reset progress)"""
        
        result = await db[self.collection].delete_one({
            "student_id": ObjectId(student_id),
            "lesson_id": ObjectId(lesson_id)
        })
        
        return result.deleted_count > 0
    
    async def delete_all_student_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str
    ) -> int:
        """Delete all progress untuk student (untuk cleanup)"""
        
        result = await db[self.collection].delete_many({
            "student_id": ObjectId(student_id)
        })
        
        return result.deleted_count
    
    # ==================== BATCH OPERATIONS ====================
    
    async def get_multiple_lesson_progress(
        self,
        db: AsyncIOMotorDatabase,
        student_id: str,
        lesson_ids: List[str]
    ) -> Dict[str, LessonProgress]:
        """Get progress untuk multiple lessons"""
        
        progress_docs = await db[self.collection].find({
            "student_id": ObjectId(student_id),
            "lesson_id": {"$in": [ObjectId(lid) for lid in lesson_ids]}
        }).to_list(len(lesson_ids))
        
        result = {}
        for doc in progress_docs:
            lesson_id = str(doc["lesson_id"])
            result[lesson_id] = LessonProgress.from_mongo(doc)
        
        return result
    
    async def bulk_update_activity_timestamps(
        self,
        db: AsyncIOMotorDatabase,
        updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update activity timestamps untuk multiple progress records"""
        
        operations = []
        for update in updates:
            operations.append({
                "update_one": {
                    "filter": {
                        "student_id": ObjectId(update["student_id"]),
                        "lesson_id": ObjectId(update["lesson_id"])
                    },
                    "update": {
                        "$set": {
                            "last_activity": datetime.utcnow(),
                            "total_time_spent": update.get("total_time_spent", 0)
                        }
                    }
                }
            })
        
        if operations:
            result = await db[self.collection].bulk_write(operations, ordered=False)
            return result.modified_count
        
        return 0
    
    # ==================== HELPER METHODS ====================
    
    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate score distribution"""
        if not scores:
            return {}
        
        distribution = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "below-60": 0
        }
        
        for score in scores:
            if score >= 90:
                distribution["90-100"] += 1
            elif score >= 80:
                distribution["80-89"] += 1
            elif score >= 70:
                distribution["70-79"] += 1
            elif score >= 60:
                distribution["60-69"] += 1
            else:
                distribution["below-60"] += 1
        
        return distribution
    
    async def _recalculate_lesson_metadata(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str
    ) -> None:
        """Recalculate lesson metadata based on all progress data"""
        
        # Get all progress untuk lesson
        progress_docs = await db[self.collection].find({
            "lesson_id": ObjectId(lesson_id)
        }).to_list(1000)
        
        if not progress_docs:
            return
        
        # Calculate aggregated stats
        total_students = len(progress_docs)
        completed = sum(1 for p in progress_docs if p.get("status") == "completed")
        completion_rate = (completed / total_students * 100) if total_students > 0 else 0
        
        # Calculate average completion time
        completion_times = []
        for p in progress_docs:
            if p.get("total_time_spent"):
                completion_times.append(p["total_time_spent"])
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else None
        
        # Update lesson metadata
        await db[self.lesson_collection].update_one(
            {"_id": ObjectId(lesson_id)},
            {
                "$set": {
                    "metadata.completion_rate": completion_rate,
                    "metadata.average_completion_time": avg_completion_time,
                    "updated_at": datetime.utcnow()
                }
            }
        )

# Create singleton instance
lesson_progress_crud = LessonProgressCRUD()
