# ==============================================================================
# File: app/crud/module.py
# Deskripsi: CRUD operations untuk Module management (Modular Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException

from app.models.lesson_assignment import Module, ModuleMetadata, LessonReference
from app.schemas.base import PyObjectId
import re

class ModuleCRUD:
    """CRUD operations untuk Module management"""
    
    def __init__(self):
        self.collection = "modules"
        self.lesson_collection = "lessons"
        self.progress_collection = "module_progress"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def create_module(
        self,
        db: AsyncIOMotorDatabase,
        module_data: Dict[str, Any],
        creator_id: str
    ) -> Module:
        """Create new module"""
        
        # Generate slug
        slug = self._generate_slug(module_data["title"])
        
        # Create module object
        module = Module(
            title=module_data["title"],
            description=module_data["description"],
            slug=slug,
            subject_id=PyObjectId(module_data["subject_id"]),
            grade_level=module_data["grade_level"],
            topic_tags=module_data.get("topic_tags", []),
            difficulty_level=module_data.get("difficulty_level", "medium"),
            learning_objectives=module_data.get("learning_objectives", []),
            prerequisites=module_data.get("prerequisites", []),
            visibility=module_data.get("visibility", "public"),
            created_by=PyObjectId(creator_id)
        )
        
        # Insert to database
        result = await db[self.collection].insert_one(module.to_mongo())
        module.id = str(result.inserted_id)
        
        return module
    
    async def add_lesson_to_module(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        lesson_id: str,
        user_id: str,
        lesson_config: Optional[Dict[str, Any]] = None
    ) -> Module:
        """Add lesson reference to module"""
        
        # Get module and verify permissions
        module = await self.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        if not module.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this module")
        
        # Verify lesson exists
        lesson = await db[self.lesson_collection].find_one({"_id": ObjectId(lesson_id)})
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Check if lesson already in module
        if module.get_lesson_reference(PyObjectId(lesson_id)):
            raise HTTPException(status_code=400, detail="Lesson already in this module")
        
        # Create lesson reference
        config = lesson_config or {}
        lesson_ref = LessonReference(
            lesson_id=PyObjectId(lesson_id),
            order=len(module.lesson_refs) + 1,
            required=config.get("required", True),
            custom_title=config.get("custom_title"),
            custom_description=config.get("custom_description"),
            weight=config.get("weight", 1.0),
            unlock_condition=config.get("unlock_condition", "sequential")
        )
        
        # Add to module
        module.lesson_refs.append(lesson_ref)
        module.updated_at = datetime.utcnow()
        
        # Recalculate metadata
        lesson_data = await self._get_lessons_for_module(db, module)
        await module.calculate_metadata(lesson_data)
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(module_id)},
            {
                "$set": {
                    "lesson_refs": [ref.dict() for ref in module.lesson_refs],
                    "metadata": module.metadata.dict(),
                    "updated_at": module.updated_at
                }
            }
        )
        
        return module
    
    # ==================== READ OPERATIONS ====================
    
    async def get_module_by_id(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        include_lessons: bool = False,
        user_id: Optional[str] = None
    ) -> Optional[Module]:
        """Get module by ID dengan optional lesson data"""
        
        try:
            module_data = await db[self.collection].find_one({"_id": ObjectId(module_id)})
            if not module_data:
                return None
            
            # Populate subject_name from database
            if module_data.get("subject_id"):
                subject = await db["subjects"].find_one({"_id": ObjectId(module_data["subject_id"])})
                if subject:
                    module_data["subject_name"] = subject.get("name")
            
            # Populate created_by_name from database
            if module_data.get("created_by"):
                creator = await db["users"].find_one({"_id": ObjectId(module_data["created_by"])})
                if creator:
                    module_data["created_by_name"] = creator.get("full_name") or creator.get("username")
            
            module = Module.from_mongo(module_data)
            
            # Include lesson details if requested
            if include_lessons and module.lesson_refs:
                lesson_ids = [ref.lesson_id for ref in module.lesson_refs]
                lessons = await db[self.lesson_collection].find({
                    "_id": {"$in": [ObjectId(lid) for lid in lesson_ids]}
                }).to_list(1000)
                
                # Add lesson details to response (can be used by API layer)
                # This would be added to a richer response schema
                
            return module
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving module: {str(e)}")
    
    async def list_modules(
        self,
        db: AsyncIOMotorDatabase,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        sort_field: str = "updated_at",
        sort_direction: str = "desc",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List modules dengan filtering dan pagination"""
        
        # Build query filter
        query_filter = {}
        
        if filters.get("subject_id"):
            query_filter["subject_id"] = ObjectId(filters["subject_id"])
        if filters.get("grade_level"):
            query_filter["grade_level"] = filters["grade_level"]
        if filters.get("created_by"):
            query_filter["created_by"] = ObjectId(filters["created_by"])
        if filters.get("visibility"):
            query_filter["visibility"] = filters["visibility"]
        if filters.get("status"):
            query_filter["status"] = filters["status"]
        if filters.get("difficulty_level"):
            query_filter["difficulty_level"] = filters["difficulty_level"]
        if filters.get("topic_tags"):
            query_filter["topic_tags"] = {"$in": filters["topic_tags"]}
        if filters.get("search"):
            query_filter["$or"] = [
                {"title": {"$regex": filters["search"], "$options": "i"}},
                {"description": {"$regex": filters["search"], "$options": "i"}},
                {"topic_tags": {"$regex": filters["search"], "$options": "i"}}
            ]
        
        # Apply user-specific filters
        if user_id and "created_by" not in query_filter:
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
        sort_direction_val = DESCENDING if sort_direction == "desc" else ASCENDING
        
        # Execute query dengan aggregation
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
                    "total_lessons": "$metadata.total_lessons",
                    "total_duration": "$metadata.total_duration"
                }
            },
            
            # Sort and paginate
            {"$sort": {sort_field: sort_direction_val}},
            {"$skip": skip},
            {"$limit": limit},
            
            # Project needed fields
            {
                "$project": {
                    "_id": 0,  # Exclude original ObjectId _id field
                    "id": 1,
                    "title": 1,
                    "description": 1,
                    "slug": 1,
                    "subject_id": {"$toString": "$subject_id"},
                    "subject_name": 1,
                    "grade_level": 1,
                    "topic_tags": 1,
                    "total_lessons": 1,
                    "total_duration": 1,
                    "difficulty_level": 1,
                    "created_by": {"$toString": "$created_by"},
                    "created_by_name": 1,
                    "visibility": 1,
                    "status": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "lesson_count": {
                        "$cond": {
                            "if": {"$isArray": "$lesson_refs"},
                            "then": {"$size": "$lesson_refs"},
                            "else": 0
                        }
                    }
                }
            }
        ]
        
        modules = await db[self.collection].aggregate(pipeline).to_list(limit)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        current_page = (skip // limit) + 1
        
        return {
            "items": modules,
            "total": total_count,
            "page": current_page,
            "per_page": limit,
            "total_pages": total_pages,
            "has_next": skip + limit < total_count,
            "has_prev": skip > 0
        }
    
    async def get_module_with_lessons(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get module dengan detailed lesson information"""
        
        module = await self.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Get lesson details
        lesson_details = []
        if module.lesson_refs:
            lesson_ids = [ObjectId(ref.lesson_id) for ref in module.lesson_refs]
            lessons = await db[self.lesson_collection].find({
                "_id": {"$in": lesson_ids}
            }).to_list(1000)
            
            # Create lookup dict
            lesson_lookup = {str(lesson["_id"]): lesson for lesson in lessons}
            
            # Combine lesson data dengan references
            for ref in sorted(module.lesson_refs, key=lambda x: x.order):
                lesson_data = lesson_lookup.get(str(ref.lesson_id))
                if lesson_data:
                    lesson_info = {
                        "lesson_id": str(ref.lesson_id),
                        "order": ref.order,
                        "required": ref.required,
                        "custom_title": ref.custom_title,
                        "weight": ref.weight,
                        "unlock_condition": ref.unlock_condition,
                        
                        # Lesson details
                        "title": lesson_data.get("title"),
                        "description": lesson_data.get("description"),
                        "total_pages": lesson_data.get("metadata", {}).get("total_pages", 0),
                        "total_duration": lesson_data.get("metadata", {}).get("total_duration", 0),
                        "difficulty_level": lesson_data.get("difficulty_level"),
                        "status": lesson_data.get("status")
                    }
                    lesson_details.append(lesson_info)
        
        # Convert module to dict with all ObjectIds as strings
        module_dict = module.dict(by_alias=False)
        
        # Ensure all ObjectId fields are strings
        if "_id" in module_dict:
            module_dict["id"] = str(module_dict["_id"])
            del module_dict["_id"]
        if "subject_id" in module_dict:
            module_dict["subject_id"] = str(module_dict["subject_id"])
        if "created_by" in module_dict:
            module_dict["created_by"] = str(module_dict["created_by"])
        if "collaborators" in module_dict:
            module_dict["collaborators"] = [str(c) for c in module_dict["collaborators"]]
        
        # Convert lesson_refs ObjectIds to strings
        if "lesson_refs" in module_dict:
            for ref in module_dict["lesson_refs"]:
                if "lesson_id" in ref:
                    ref["lesson_id"] = str(ref["lesson_id"])
        
        return {
            "module": module_dict,
            "lessons": lesson_details,
            "total_lessons": len(lesson_details),
            "total_duration": sum(lesson.get("total_duration", 0) for lesson in lesson_details)
        }
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_module(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        updates: Dict[str, Any],
        user_id: str
    ) -> Module:
        """Update module"""
        
        # Get module and verify permissions
        module = await self.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        if not module.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this module")
        
        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        
        if "title" in updates:
            update_doc["title"] = updates["title"]
            update_doc["slug"] = self._generate_slug(updates["title"])
        if "description" in updates:
            update_doc["description"] = updates["description"]
        if "topic_tags" in updates:
            update_doc["topic_tags"] = updates["topic_tags"]
        if "difficulty_level" in updates:
            update_doc["difficulty_level"] = updates["difficulty_level"]
        if "learning_objectives" in updates:
            update_doc["learning_objectives"] = updates["learning_objectives"]
        if "prerequisites" in updates:
            update_doc["prerequisites"] = updates["prerequisites"]
        if "visibility" in updates:
            update_doc["visibility"] = updates["visibility"]
        if "status" in updates:
            update_doc["status"] = updates["status"]
            if updates["status"] == "published":
                update_doc["published_at"] = datetime.utcnow()
            elif updates["status"] == "archived":
                update_doc["archived_at"] = datetime.utcnow()
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(module_id)},
            {"$set": update_doc}
        )
        
        # Return updated module
        return await self.get_module_by_id(db, module_id)
    
    async def reorder_module_lessons(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        lesson_order: List[str],
        user_id: str
    ) -> Module:
        """Reorder lessons dalam module"""
        
        # Get module and verify permissions
        module = await self.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        if not module.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this module")
        
        # Reorder lessons
        module.reorder_lessons(lesson_order)
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(module_id)},
            {
                "$set": {
                    "lesson_refs": [ref.dict() for ref in module.lesson_refs],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return module
    
    async def remove_lesson_from_module(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        lesson_id: str,
        user_id: str
    ) -> bool:
        """Remove lesson reference from module"""
        
        # Get module and verify permissions
        module = await self.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        if not module.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to edit this module")
        
        # Remove lesson reference
        removed = module.remove_lesson_reference(PyObjectId(lesson_id))
        if not removed:
            raise HTTPException(status_code=404, detail="Lesson not found in this module")
        
        # Recalculate metadata
        lesson_data = await self._get_lessons_for_module(db, module)
        await module.calculate_metadata(lesson_data)
        
        # Update in database
        await db[self.collection].update_one(
            {"_id": ObjectId(module_id)},
            {
                "$set": {
                    "lesson_refs": [ref.dict() for ref in module.lesson_refs],
                    "metadata": module.metadata.dict(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return True
    
    # ==================== DELETE OPERATIONS ====================
    
    async def delete_module(
        self,
        db: AsyncIOMotorDatabase,
        module_id: str,
        user_id: str
    ) -> bool:
        """Delete module (with safety checks)"""
        
        # Get module and verify permissions
        module = await self.get_module_by_id(db, module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        if not module.is_editable_by(PyObjectId(user_id)):
            raise HTTPException(status_code=403, detail="Not authorized to delete this module")
        
        # Check if module is being used in courses
        usage_count = await db["courses"].count_documents({
            "module_refs.module_id": ObjectId(module_id)
        })
        
        if usage_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete module. It is being used in {usage_count} courses. Remove from courses first."
            )
        
        # Delete related progress data
        await db[self.progress_collection].delete_many({"module_id": ObjectId(module_id)})
        
        # Delete module
        result = await db[self.collection].delete_one({"_id": ObjectId(module_id)})
        
        return result.deleted_count > 0
    
    # ==================== HELPER METHODS ====================
    
    async def _get_lessons_for_module(self, db: AsyncIOMotorDatabase, module: Module) -> List[dict]:
        """Get lesson data untuk metadata calculation"""
        if not module.lesson_refs:
            return []
        
        lesson_ids = [ObjectId(ref.lesson_id) for ref in module.lesson_refs]
        lessons = await db[self.lesson_collection].find({
            "_id": {"$in": lesson_ids}
        }).to_list(1000)
        
        return lessons
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug"""
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        timestamp = int(datetime.utcnow().timestamp())
        return f"{slug}-{timestamp}"

# Create singleton instance
module_crud = ModuleCRUD()
