# ==============================================================================
# File: app/crud/lesson.py
# Deskripsi: CRUD operations untuk Lesson management (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

from app.models.lesson import Lesson, LessonPage, LessonMetadata, MediaReference, EmbeddedComponent
from app.schemas.lesson import LessonCreateRequest, LessonUpdateRequest, LessonFilters, LessonSortBy
from app.schemas.base import PyObjectId
import re

class LessonCRUD:
    """CRUD operations untuk Lesson management"""
    
    def __init__(self):
        self.collection = "lessons"
        self.progress_collection = "lesson_progress"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def create_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_data: LessonCreateRequest,
        creator_id: str
    ) -> Lesson:
        """Create new lesson"""
        
        # Validate subject exists
        subject = await db["subjects"].find_one({"_id": ObjectId(lesson_data.subject_id)})
        if not subject:
            raise HTTPException(status_code=400, detail="Subject not found")
        
        # Generate slug from title
        slug = self._generate_slug(lesson_data.title)
        
        # Create lesson object (without pages - they're stored separately)
        lesson = Lesson(
            title=lesson_data.title,
            description=lesson_data.description,
            slug=slug,
            subject_id=lesson_data.subject_id,
            grade_level=lesson_data.grade_level,
            topic_tags=lesson_data.topic_tags,
            difficulty_level=lesson_data.difficulty_level,
            learning_objectives=lesson_data.learning_objectives,
            prerequisites=lesson_data.prerequisites,
            visibility=lesson_data.visibility,
            created_by=PyObjectId(creator_id)
        )
        
        # Insert lesson to database
        result = await db[self.collection].insert_one(lesson.to_mongo())
        lesson.id = str(result.inserted_id)
        
        # Note: Pages are NOT created here.
        # Frontend should use POST /lessons/{id}/pages to add pages after lesson creation.
        # This ensures clean separation: lessons collection = metadata, lesson_pages collection = content.
        
        return lesson
    
    async def add_page_to_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_data: Dict[str, Any],
        user_id: str
    ):
        """Add new page to existing lesson - DEPRECATED: Use lesson_page_crud.create_page() instead"""
        from app.crud.lesson_page import lesson_page_crud
        
        # Get lesson and verify permissions
        lesson = await self.get_lesson_by_id(db, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        if not lesson.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this lesson")
        
        # Delegate to lesson_page_crud
        return await lesson_page_crud.create_page(db, lesson_id, page_data, user_id)
    
    # ==================== READ OPERATIONS ====================
    
    async def get_lesson_by_id(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        user_id: Optional[str] = None,
        include_usage: bool = False
    ):
        """Get lesson by ID with optional user context
        
        Returns:
            If include_usage=False: Lesson object
            If include_usage=True: Tuple of (Lesson object, usage_details dict)
        """
        
        try:
            lesson_data = await db[self.collection].find_one({"_id": ObjectId(lesson_id)})
            if not lesson_data:
                return None if not include_usage else (None, None)
            
            # Populate subject_name
            if "subject_id" in lesson_data and lesson_data["subject_id"]:
                subject = await db["subjects"].find_one(
                    {"_id": ObjectId(lesson_data["subject_id"])},
                    {"name": 1}
                )
                lesson_data["subject_name"] = subject["name"] if subject else None
            else:
                lesson_data["subject_name"] = None
            
            # Populate created_by_name
            if "created_by" in lesson_data and lesson_data["created_by"]:
                creator = await db["users"].find_one(
                    {"_id": ObjectId(lesson_data["created_by"])},
                    {"profile_id": 1}
                )
                if creator and creator.get("profile_id"):
                    profile = await db["profiles"].find_one(
                        {"_id": ObjectId(creator["profile_id"])},
                        {"full_name": 1}
                    )
                    if profile:
                        lesson_data["created_by_name"] = profile.get("full_name", "Unknown")
                    else:
                        lesson_data["created_by_name"] = None
                else:
                    lesson_data["created_by_name"] = None
            else:
                lesson_data["created_by_name"] = None
            
            usage_details = None
            
            # Add usage information if requested
            if include_usage:
                # Find modules using this lesson
                module_usage = await db["modules"].find({
                    "lesson_refs.lesson_id": ObjectId(lesson_id)
                }, {
                    "title": 1,
                    "status": 1,
                    "created_by": 1
                }).to_list(100)
                
                # Find courses using these modules
                module_ids = [str(m["_id"]) for m in module_usage]
                course_usage = []
                if module_ids:
                    course_usage = await db["courses"].find({
                        "module_refs.module_id": {"$in": module_ids}
                    }, {
                        "title": 1,
                        "status": 1,
                        "coordinator_id": 1
                    }).to_list(100)
                
                # Update metadata in lesson_data before converting to model
                if "metadata" not in lesson_data:
                    lesson_data["metadata"] = {}
                lesson_data["metadata"]["usage_count"] = len(module_usage)
                
                # Build usage details dict
                usage_details = {
                    "modules": [
                        {
                            "id": str(m["_id"]),
                            "title": m["title"],
                            "status": m.get("status", "draft")
                        }
                        for m in module_usage
                    ],
                    "courses": [
                        {
                            "id": str(c["_id"]),
                            "title": c["title"],
                            "status": c.get("status", "draft")
                        }
                        for c in course_usage
                    ]
                }
            
            lesson = Lesson.from_mongo(lesson_data)
            
            # Return lesson only or tuple with usage details
            if include_usage:
                return (lesson, usage_details)
            else:
                return lesson
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving lesson: {str(e)}")
    
    async def list_lessons(
        self,
        db: AsyncIOMotorDatabase,
        filters: LessonFilters,
        sort_by: LessonSortBy,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List lessons dengan filtering, sorting, dan pagination"""
        
        # Build query filter
        query_filter = {}
        
        if filters.subject_id:
            query_filter["subject_id"] = ObjectId(filters.subject_id)
        if filters.grade_level:
            query_filter["grade_level"] = filters.grade_level
        if filters.created_by:
            query_filter["created_by"] = ObjectId(filters.created_by)
        if filters.visibility:
            query_filter["visibility"] = filters.visibility
        if filters.status:
            query_filter["status"] = filters.status
        if filters.difficulty_level:
            query_filter["difficulty_level"] = filters.difficulty_level
        if filters.topic_tags:
            query_filter["topic_tags"] = {"$in": filters.topic_tags}
        if filters.has_components is not None:
            if filters.has_components:
                query_filter["metadata.total_components"] = {"$gt": 0}
            else:
                query_filter["metadata.total_components"] = 0
        if filters.min_duration:
            query_filter["metadata.total_duration"] = {"$gte": filters.min_duration}
        if filters.max_duration:
            if "metadata.total_duration" in query_filter:
                query_filter["metadata.total_duration"]["$lte"] = filters.max_duration
            else:
                query_filter["metadata.total_duration"] = {"$lte": filters.max_duration}
        if filters.created_after:
            query_filter["created_at"] = {"$gte": filters.created_after}
        if filters.created_before:
            if "created_at" in query_filter:
                query_filter["created_at"]["$lte"] = filters.created_before
            else:
                query_filter["created_at"] = {"$lte": filters.created_before}
        
        # Text search
        if filters.search:
            query_filter["$or"] = [
                {"title": {"$regex": filters.search, "$options": "i"}},
                {"description": {"$regex": filters.search, "$options": "i"}},
                {"topic_tags": {"$regex": filters.search, "$options": "i"}}
            ]
        
        # Apply user-specific filters
        if user_id and "created_by" not in query_filter:
            # If not admin/coordinator, only show public lessons or own lessons
            user = await db["users"].find_one({"_id": ObjectId(user_id)})
            if user and "admin" not in user.get("roles", []) and "coordinator" not in user.get("roles", []):
                query_filter["$or"] = [
                    {"visibility": "public"},
                    {"created_by": ObjectId(user_id)},
                    {"collaborators": ObjectId(user_id)}
                ]
        
        # Get total count
        total_count = await db[self.collection].count_documents(query_filter)
        
        # Build sort
        sort_direction = DESCENDING if sort_by.direction == "desc" else ASCENDING
        sort_field = sort_by.field
        
        # Execute query dengan aggregation untuk better performance
        pipeline = [
            {"$match": query_filter},
            
            # Lookup subject name
            {
                "$lookup": {
                    "from": "subjects",
                    "localField": "subject_id",
                    "foreignField": "_id",
                    "as": "subject_info"
                }
            },
            {"$unwind": {"path": "$subject_info", "preserveNullAndEmptyArrays": True}},
            
            # Lookup creator name
            {
                "$lookup": {
                    "from": "users",
                    "localField": "created_by",
                    "foreignField": "_id",
                    "as": "creator_info"
                }
            },
            {"$unwind": {"path": "$creator_info", "preserveNullAndEmptyArrays": True}},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "subject_name": "$subject_info.name",
                    "created_by_name": {
                        "$concat": [
                            {"$ifNull": ["$creator_info.profile.first_name", ""]},
                            " ",
                            {"$ifNull": ["$creator_info.profile.last_name", ""]}
                        ]
                    },
                    "total_pages": "$metadata.total_pages",
                    "total_duration": "$metadata.total_duration"
                }
            },
            
            # Sort and paginate
            {"$sort": {sort_field: sort_direction}},
            {"$skip": skip},
            {"$limit": limit},
            
            # Project only needed fields for summary
            {
                "$project": {
                    "id": 1,
                    "title": 1,
                    "description": 1,
                    "slug": 1,
                    "subject_id": {"$toString": "$subject_id"},
                    "subject_name": 1,
                    "grade_level": 1,
                    "topic_tags": 1,
                    "total_pages": 1,
                    "total_duration": 1,
                    "difficulty_level": 1,
                    "created_by": {"$toString": "$created_by"},
                    "created_by_name": 1,
                    "collaborators": {
                        "$map": {
                            "input": {"$ifNull": ["$collaborators", []]},
                            "as": "collab",
                            "in": {"$toString": "$$collab"}
                        }
                    },
                    "visibility": 1,
                    "status": 1,
                    "created_at": 1,
                    "updated_at": 1
                }
            }
        ]
        
        lessons = await db[self.collection].aggregate(pipeline).to_list(limit)
        
        # Calculate pagination info
        has_next = skip + limit < total_count
        has_prev = skip > 0
        total_pages = (total_count + limit - 1) // limit
        current_page = (skip // limit) + 1
        
        return {
            "items": lessons,
            "total": total_count,
            "page": current_page,
            "per_page": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    
    async def get_lesson_library(
        self,
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get lesson library dengan featured, popular, recent lessons"""
        
        # Featured lessons (high rating, many uses)
        featured_pipeline = [
            {"$match": {"visibility": "public", "status": "published"}},
            {"$match": {"metadata.rating": {"$gte": 4.0}}},
            {"$sort": {"metadata.usage_count": -1}},
            {"$limit": 6}
        ]
        
        # Recent lessons
        recent_pipeline = [
            {"$match": {"visibility": "public", "status": "published"}},
            {"$sort": {"created_at": -1}},
            {"$limit": 8}
        ]
        
        # Popular lessons (by usage)
        popular_pipeline = [
            {"$match": {"visibility": "public", "status": "published"}},
            {"$sort": {"metadata.usage_count": -1}},
            {"$limit": 8}
        ]
        
        # Execute all queries in parallel
        featured_lessons = await db[self.collection].aggregate(featured_pipeline).to_list(6)
        recent_lessons = await db[self.collection].aggregate(recent_pipeline).to_list(8)
        popular_lessons = await db[self.collection].aggregate(popular_pipeline).to_list(8)
        
        # My lessons (if user provided)
        my_lessons = []
        if user_id:
            my_pipeline = [
                {"$match": {"created_by": ObjectId(user_id)}},
                {"$sort": {"updated_at": -1}},
                {"$limit": 6}
            ]
            my_lessons = await db[self.collection].aggregate(my_pipeline).to_list(6)
        
        # Get browse categories
        subjects = await db["subjects"].find({"is_active": True}).to_list(100)
        
        # Get statistics
        total_lessons = await db[self.collection].count_documents({"status": "published"})
        total_creators = await db[self.collection].distinct("created_by", {"status": "published"})
        
        return {
            "featured_lessons": [self._format_lesson_summary(lesson) for lesson in featured_lessons],
            "recent_lessons": [self._format_lesson_summary(lesson) for lesson in recent_lessons],
            "popular_lessons": [self._format_lesson_summary(lesson) for lesson in popular_lessons],
            "my_lessons": [self._format_lesson_summary(lesson) for lesson in my_lessons],
            "subjects": [{"id": str(s["_id"]), "name": s["name"]} for s in subjects],
            "grade_levels": list(range(1, 13)),
            "total_lessons": total_lessons,
            "total_creators": len(total_creators)
        }
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        updates: LessonUpdateRequest,
        user_id: str
    ) -> Lesson:
        """Update lesson"""
        
        # Get lesson and verify permissions
        lesson = await self.get_lesson_by_id(db, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        if not lesson.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this lesson")
        
        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        
        if updates.title is not None:
            update_doc["title"] = updates.title
            update_doc["slug"] = self._generate_slug(updates.title)
        if updates.description is not None:
            update_doc["description"] = updates.description
        if updates.topic_tags is not None:
            update_doc["topic_tags"] = updates.topic_tags
        if updates.difficulty_level is not None:
            update_doc["difficulty_level"] = updates.difficulty_level
        if updates.learning_objectives is not None:
            update_doc["learning_objectives"] = updates.learning_objectives
        if updates.prerequisites is not None:
            update_doc["prerequisites"] = updates.prerequisites
        if updates.visibility is not None:
            update_doc["visibility"] = updates.visibility
        if updates.status is not None:
            update_doc["status"] = updates.status
            if updates.status == "published":
                update_doc["published_at"] = datetime.utcnow()
            elif updates.status == "archived":
                update_doc["archived_at"] = datetime.utcnow()
        
        # NOTE: Pages are managed via separate endpoints (/lessons/{id}/pages)
        # LessonUpdateRequest schema does not include 'pages' field (strict separation)
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(lesson_id)},
            {"$set": update_doc}
        )
        
        # Return updated lesson
        return await self.get_lesson_by_id(db, lesson_id)
    
    async def update_lesson_page(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_number: int,
        page_updates: Dict[str, Any],
        user_id: str
    ):
        """Update specific page dalam lesson - DEPRECATED: Use lesson_page_crud.update_page() instead"""
        from app.crud.lesson_page import lesson_page_crud
        
        # Get lesson and verify permissions
        lesson = await self.get_lesson_by_id(db, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        if not lesson.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this lesson")
        
        # Delegate to lesson_page_crud
        return await lesson_page_crud.update_page(db, lesson_id, page_number, page_updates, user_id)
    
    # ==================== DELETE OPERATIONS ====================
    
    async def delete_lesson(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        user_id: str
    ) -> bool:
        """Delete lesson (with safety checks and cascade delete)"""
        
        # Get lesson and verify permissions
        lesson = await self.get_lesson_by_id(db, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        if not lesson.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to delete this lesson")
        
        # Check if lesson is being used in modules
        usage_count = await db["modules"].count_documents({
            "lesson_refs.lesson_id": ObjectId(lesson_id)
        })
        
        if usage_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete lesson. It is being used in {usage_count} modules. Remove from modules first."
            )
        
        # CASCADE DELETE: Delete all lesson pages first
        from app.crud.lesson_page import lesson_page_crud
        await lesson_page_crud.delete_all_pages(db, lesson_id)
        
        # Delete related progress data
        await db[self.progress_collection].delete_many({"lesson_id": ObjectId(lesson_id)})
        
        # Delete lesson
        result = await db[self.collection].delete_one({"_id": ObjectId(lesson_id)})
        
        return result.deleted_count > 0
    
    # ==================== HELPER METHODS ====================
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug dari title"""
        # Convert to lowercase, replace spaces with hyphens, remove special chars
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # Add timestamp untuk uniqueness
        timestamp = int(datetime.utcnow().timestamp())
        return f"{slug}-{timestamp}"
    
    def _format_lesson_summary(self, lesson_data: dict) -> dict:
        """Format lesson data untuk summary response"""
        return {
            "id": str(lesson_data.get("_id", "")),
            "title": lesson_data.get("title", ""),
            "description": lesson_data.get("description", ""),
            "slug": lesson_data.get("slug"),
            "subject_id": str(lesson_data.get("subject_id", "")),
            "grade_level": lesson_data.get("grade_level", 0),
            "topic_tags": lesson_data.get("topic_tags", []),
            "total_pages": lesson_data.get("metadata", {}).get("total_pages", 0),
            "total_duration": lesson_data.get("metadata", {}).get("total_duration", 0),
            "difficulty_level": lesson_data.get("difficulty_level", "medium"),
            "created_by": str(lesson_data.get("created_by", "")),  # Required field
            "visibility": lesson_data.get("visibility", "public"),
            "status": lesson_data.get("status", "draft"),
            "created_at": lesson_data.get("created_at"),
            "updated_at": lesson_data.get("updated_at")
        }

# Create singleton instance
lesson_crud = LessonCRUD()
