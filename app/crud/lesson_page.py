# ==============================================================================
# File: app/crud/lesson_page.py
# Deskripsi: CRUD operations for lesson pages (separate from lessons)
# ==============================================================================
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException

from app.models.lesson_page import LessonPage, LessonPageSummary
from app.schemas.base import PyObjectId

class LessonPageCRUD:
    def __init__(self):
        self.collection = "lesson_pages"
    
    # ==================== CREATE OPERATIONS ====================
    
    async def create_page(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_data: Dict[str, Any],
        user_id: str
    ) -> LessonPage:
        """Create new page for lesson"""
        
        # Check if page number already exists
        existing = await db[self.collection].find_one({
            "lesson_id": ObjectId(lesson_id),
            "page_number": page_data["page_number"]
        })
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Page {page_data['page_number']} already exists for this lesson"
            )
        
        # Create page document
        page_doc = {
            "lesson_id": ObjectId(lesson_id),
            "page_number": page_data["page_number"],
            "title": page_data["title"],
            "content_markdown": page_data.get("content_markdown", ""),
            "media_references": page_data.get("media_references", []),
            "embedded_components": page_data.get("embedded_components", []),
            "estimated_duration": page_data.get("estimated_duration", 10),
            "difficulty_level": page_data.get("difficulty_level", "medium"),
            "learning_objectives": page_data.get("learning_objectives", []),
            "status": page_data.get("status", "published"),
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": ObjectId(user_id),
            "updated_by": None
        }
        
        result = await db[self.collection].insert_one(page_doc)
        page_doc["_id"] = result.inserted_id
        
        # Update lesson metadata
        await self._update_lesson_metadata(db, lesson_id)
        
        return LessonPage.from_mongo(page_doc)
    
    # ==================== READ OPERATIONS ====================
    
    async def get_page(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_number: int
    ) -> Optional[LessonPage]:
        """Get single page by page number"""
        
        page_doc = await db[self.collection].find_one({
            "lesson_id": ObjectId(lesson_id),
            "page_number": page_number
        })
        
        if not page_doc:
            return None
        
        return LessonPage.from_mongo(page_doc)
    
    async def list_pages(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        status_filter: Optional[str] = None,
        summary_only: bool = False
    ) -> List[Any]:
        """List all pages for a lesson"""
        
        query = {"lesson_id": ObjectId(lesson_id)}
        
        if status_filter:
            query["status"] = status_filter
        
        cursor = db[self.collection].find(query).sort("page_number", 1)
        pages = await cursor.to_list(None)
        
        if summary_only:
            # Return summary only (no content)
            return [
                LessonPageSummary(
                    page_number=p["page_number"],
                    title=p["title"],
                    estimated_duration=p.get("estimated_duration", 10),
                    difficulty_level=p.get("difficulty_level", "medium"),
                    status=p.get("status", "published"),
                    has_media=len(p.get("media_references", [])) > 0,
                    has_components=len(p.get("embedded_components", [])) > 0,
                    media_count=len(p.get("media_references", [])),
                    component_count=len(p.get("embedded_components", [])),
                    created_at=p.get("created_at", datetime.utcnow()),
                    updated_at=p.get("updated_at", datetime.utcnow())
                )
                for p in pages
            ]
        
        # Return full page objects
        return [LessonPage.from_mongo(p) for p in pages]
    
    async def get_pages_batch(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_numbers: List[int]
    ) -> List[LessonPage]:
        """Get multiple pages at once (for prefetching)"""
        
        cursor = db[self.collection].find({
            "lesson_id": ObjectId(lesson_id),
            "page_number": {"$in": page_numbers}
        }).sort("page_number", 1)
        
        pages = await cursor.to_list(None)
        
        return [LessonPage.from_mongo(p) for p in pages]
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_page(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_number: int,
        updates: Dict[str, Any],
        user_id: str
    ) -> Optional[LessonPage]:
        """Update page content"""
        
        # Build update document
        update_doc = {
            "updated_at": datetime.utcnow(),
            "updated_by": ObjectId(user_id)
        }
        
        # Allowed fields to update
        allowed_fields = [
            "title", "content_markdown", "media_references",
            "embedded_components", "estimated_duration",
            "difficulty_level", "learning_objectives", "status"
        ]
        
        for field in allowed_fields:
            if field in updates:
                update_doc[field] = updates[field]
        
        # If content changed, increment version
        if "content_markdown" in updates:
            update_doc["$inc"] = {"version": 1}
        
        result = await db[self.collection].find_one_and_update(
            {
                "lesson_id": ObjectId(lesson_id),
                "page_number": page_number
            },
            {"$set": update_doc},
            return_document=True
        )
        
        if not result:
            return None
        
        # Update lesson metadata
        await self._update_lesson_metadata(db, lesson_id)
        
        return LessonPage.from_mongo(result)
    
    async def reorder_pages(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        new_order: List[int]
    ) -> bool:
        """Reorder pages (change page numbers) - TRANSACTION-SAFE"""
        
        # Get all pages
        pages = await db[self.collection].find({
            "lesson_id": ObjectId(lesson_id)
        }).sort("page_number", 1).to_list(None)
        
        if len(pages) != len(new_order):
            raise HTTPException(
                status_code=400,
                detail=f"New order must include all {len(pages)} pages, but got {len(new_order)}"
            )
        
        # Validate new_order contains valid page numbers
        if set(new_order) != set(range(1, len(pages) + 1)):
            raise HTTPException(
                status_code=400,
                detail="New order must be a permutation of page numbers 1 to N"
            )
        
        # Use transaction to prevent race conditions
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                # Step 1: Temporarily set all page numbers to negative (to avoid collisions)
                for i, page in enumerate(pages):
                    await db[self.collection].update_one(
                        {"_id": page["_id"]},
                        {"$set": {"page_number": -(i + 1)}},
                        session=session
                    )
                
                # Step 2: Set new page numbers according to new_order
                for new_pos, old_pos in enumerate(new_order, 1):
                    # Find the page that was at old_pos (now at -old_pos)
                    page_to_move = pages[old_pos - 1]
                    
                    await db[self.collection].update_one(
                        {"_id": page_to_move["_id"]},
                        {"$set": {
                            "page_number": new_pos,
                            "updated_at": datetime.utcnow()
                        }},
                        session=session
                    )
        
        return True
    
    # ==================== DELETE OPERATIONS ====================
    
    async def delete_page(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str,
        page_number: int
    ) -> bool:
        """Delete a page (and reorder remaining pages)"""
        
        # Delete the page
        result = await db[self.collection].delete_one({
            "lesson_id": ObjectId(lesson_id),
            "page_number": page_number
        })
        
        if result.deleted_count == 0:
            return False
        
        # Reorder remaining pages (shift down)
        await db[self.collection].update_many(
            {
                "lesson_id": ObjectId(lesson_id),
                "page_number": {"$gt": page_number}
            },
            {
                "$inc": {"page_number": -1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Update lesson metadata
        await self._update_lesson_metadata(db, lesson_id)
        
        return True
    
    async def delete_all_pages(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str
    ) -> int:
        """Delete all pages for a lesson (when lesson is deleted)"""
        
        result = await db[self.collection].delete_many({
            "lesson_id": ObjectId(lesson_id)
        })
        
        return result.deleted_count
    
    # ==================== HELPER METHODS ====================
    
    async def _update_lesson_metadata(
        self,
        db: AsyncIOMotorDatabase,
        lesson_id: str
    ):
        """Update lesson metadata after page changes"""
        
        # Aggregate page statistics
        pipeline = [
            {"$match": {"lesson_id": ObjectId(lesson_id)}},
            {"$group": {
                "_id": None,
                "total_pages": {"$sum": 1},
                "total_duration": {"$sum": "$estimated_duration"},
                "total_media": {"$sum": {"$size": {"$ifNull": ["$media_references", []]}}},
                "total_components": {"$sum": {"$size": {"$ifNull": ["$embedded_components", []]}}}
            }}
        ]
        
        result = await db[self.collection].aggregate(pipeline).to_list(1)
        
        if result:
            stats = result[0]
            await db["lessons"].update_one(
                {"_id": ObjectId(lesson_id)},
                {"$set": {
                    "metadata.total_pages": stats["total_pages"],
                    "metadata.total_duration": stats["total_duration"],
                    "metadata.total_media": stats["total_media"],
                    "metadata.total_components": stats["total_components"],
                    "metadata.calculated_at": datetime.utcnow()
                }}
            )
        else:
            # No pages, reset metadata
            await db["lessons"].update_one(
                {"_id": ObjectId(lesson_id)},
                {"$set": {
                    "metadata.total_pages": 0,
                    "metadata.total_duration": 0,
                    "metadata.total_media": 0,
                    "metadata.total_components": 0,
                    "metadata.calculated_at": datetime.utcnow()
                }}
            )

# Create instance
lesson_page_crud = LessonPageCRUD()
