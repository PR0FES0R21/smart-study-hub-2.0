# ==============================================================================
# File: app/core/course_workflow.py
# Deskripsi: Git-like Workflow Engine untuk Course Management
# ==============================================================================
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status
import copy
import asyncio

from app.models.course import Course, TeacherFork, PullRequest, PullRequestChange
from app.core.course_permissions import course_permissions

class CourseWorkflowEngine:
    """Git-like workflow engine untuk course management"""
    
    def __init__(self):
        self.collection_courses = "courses"
        self.collection_forks = "teacher_forks"
        self.collection_prs = "pull_requests"
        self.collection_modules = "course_modules"
        self.collection_lessons = "course_lessons"
    
    # ==================== FORK OPERATIONS ====================
    
    async def create_fork(
        self,
        db: AsyncIOMotorDatabase,
        course_id: str,
        teacher_id: str,
        teaching_assignment_id: str,
        fork_title: Optional[str] = None,
        customization_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create teacher fork from standard course"""
        
        # Permission check
        if not await course_permissions.can_fork_course(db, teacher_id, course_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Cannot fork this course"
            )
        
        # Get master course
        master_course = await db[self.collection_courses].find_one({"_id": ObjectId(course_id)})
        if not master_course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Check if fork already exists for this teaching assignment
        existing_fork = await db[self.collection_forks].find_one({
            "master_course_id": ObjectId(course_id),
            "teaching_assignment_id": ObjectId(teaching_assignment_id)
        })
        
        if existing_fork:
            raise HTTPException(
                status_code=400, 
                detail="Fork already exists for this teaching assignment"
            )
        
        # Get teaching assignment details
        assignment = await db["teaching_assignments"].find_one({"_id": ObjectId(teaching_assignment_id)})
        if not assignment:
            raise HTTPException(status_code=404, detail="Teaching assignment not found")
        
        # Create fork
        fork_data = {
            "title": fork_title or f"{master_course['title']} - Fork",
            "description": f"Customized version of {master_course['title']}",
            "master_course_id": ObjectId(course_id),
            "teacher_id": ObjectId(teacher_id),
            "teaching_assignment_id": ObjectId(teaching_assignment_id),
            "customization_notes": customization_notes,
            "modifications": [],
            "custom_structure": None,  # Initially use master structure
            "custom_metadata": {},
            "last_sync_at": datetime.utcnow(),
            "is_behind": False,
            "conflicts_count": 0,
            "auto_sync_enabled": True,
            "enrolled_classes": [assignment["class_id"]],  # Auto-enroll the class
            "is_active": True,
            "pull_requests_submitted": 0,
            "forked_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db[self.collection_forks].insert_one(fork_data)
        
        # Update fork count in master course
        await db[self.collection_courses].update_one(
            {"_id": ObjectId(course_id)},
            {"$inc": {"fork_count": 1}}
        )
        
        # Copy course content to fork
        await self._copy_course_content_to_fork(db, course_id, str(result.inserted_id))
        
        return await self._get_fork_with_details(db, str(result.inserted_id))
    
    async def _copy_course_content_to_fork(
        self,
        db: AsyncIOMotorDatabase,
        master_course_id: str,
        fork_id: str
    ):
        """Copy course modules and lessons to fork"""
        
        # Copy modules
        modules = await db[self.collection_modules].find({
            "course_id": ObjectId(master_course_id)
        }).to_list(None)
        
        if modules:
            fork_modules = []
            for module in modules:
                fork_module = module.copy()
                fork_module.pop("_id", None)  # Remove original ID
                fork_module["course_id"] = ObjectId(fork_id)
                fork_module["is_fork_content"] = True
                fork_module["original_module_id"] = module["_id"]
                fork_module["forked_at"] = datetime.utcnow()
                fork_modules.append(fork_module)
            
            await db[self.collection_modules].insert_many(fork_modules)
        
        # Copy lessons
        lessons = await db[self.collection_lessons].find({
            "course_id": ObjectId(master_course_id)
        }).to_list(None)
        
        if lessons:
            fork_lessons = []
            for lesson in lessons:
                fork_lesson = lesson.copy()
                fork_lesson.pop("_id", None)
                fork_lesson["course_id"] = ObjectId(fork_id)
                fork_lesson["is_fork_content"] = True
                fork_lesson["original_lesson_id"] = lesson["_id"]
                fork_lesson["forked_at"] = datetime.utcnow()
                fork_lessons.append(fork_lesson)
            
            await db[self.collection_lessons].insert_many(fork_lessons)
    
    async def customize_fork(
        self,
        db: AsyncIOMotorDatabase,
        fork_id: str,
        teacher_id: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply customizations to teacher fork"""
        
        # Permission check
        if not await course_permissions.can_modify_fork(db, teacher_id, fork_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Cannot modify this fork"
            )
        
        fork = await db[self.collection_forks].find_one({"_id": ObjectId(fork_id)})
        if not fork:
            raise HTTPException(status_code=404, detail="Fork not found")
        
        # Track modifications
        modifications = fork.get("modifications", [])
        
        for change in changes:
            change_record = {
                "timestamp": datetime.utcnow(),
                "change_type": change["change_type"],  # add, modify, delete, reorder
                "target_type": change["target_type"],  # module, lesson, metadata
                "target_id": change.get("target_id"),
                "before_data": change.get("before_data"),
                "after_data": change.get("after_data"),
                "rationale": change.get("rationale", "")
            }
            
            # Apply the change
            await self._apply_fork_change(db, fork_id, change)
            modifications.append(change_record)
        
        # Update fork
        await db[self.collection_forks].update_one(
            {"_id": ObjectId(fork_id)},
            {
                "$set": {
                    "modifications": modifications,
                    "updated_at": datetime.utcnow(),
                    "is_behind": False  # Fork has new changes
                }
            }
        )
        
        return await self._get_fork_with_details(db, fork_id)
    
    async def _apply_fork_change(
        self,
        db: AsyncIOMotorDatabase,
        fork_id: str,
        change: Dict[str, Any]
    ):
        """Apply specific change to fork content"""
        
        target_type = change["target_type"]
        change_type = change["change_type"]
        
        if target_type == "module":
            collection = self.collection_modules
        elif target_type == "lesson":
            collection = self.collection_lessons
        else:
            return  # Skip unknown types
        
        if change_type == "add":
            # Add new content
            new_item = change["after_data"]
            new_item["course_id"] = ObjectId(fork_id)
            new_item["is_fork_content"] = True
            new_item["created_at"] = datetime.utcnow()
            await db[collection].insert_one(new_item)
            
        elif change_type == "modify":
            # Update existing content
            target_id = change["target_id"]
            update_data = change["after_data"]
            update_data["updated_at"] = datetime.utcnow()
            
            await db[collection].update_one(
                {"_id": ObjectId(target_id), "course_id": ObjectId(fork_id)},
                {"$set": update_data}
            )
            
        elif change_type == "delete":
            # Delete content
            target_id = change["target_id"]
            await db[collection].delete_one({
                "_id": ObjectId(target_id), 
                "course_id": ObjectId(fork_id)
            })
            
        elif change_type == "reorder":
            # Reorder content
            target_id = change["target_id"]
            new_order = change["after_data"]["order"]
            
            await db[collection].update_one(
                {"_id": ObjectId(target_id), "course_id": ObjectId(fork_id)},
                {"$set": {"order": new_order, "updated_at": datetime.utcnow()}}
            )
    
    # ==================== PULL REQUEST OPERATIONS ====================
    
    async def create_pull_request(
        self,
        db: AsyncIOMotorDatabase,
        fork_id: str,
        teacher_id: str,
        title: str,
        description: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create pull request to propose changes to master course"""
        
        # Permission check
        if not await course_permissions.can_create_pull_request(db, teacher_id, fork_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Cannot create pull request"
            )
        
        fork = await db[self.collection_forks].find_one({"_id": ObjectId(fork_id)})
        if not fork:
            raise HTTPException(status_code=404, detail="Fork not found")
        
        # Get next PR number
        pr_count = await db[self.collection_prs].count_documents({
            "master_course_id": fork["master_course_id"]
        })
        pr_number = pr_count + 1
        
        # Create PR changes
        pr_changes = []
        for change in changes:
            pr_change = PullRequestChange(
                change_type=change["change_type"],
                target_type=change["target_type"],
                target_id=change.get("target_id"),
                before_data=change.get("before_data"),
                after_data=change.get("after_data"),
                position_change=change.get("position_change"),
                rationale=change.get("rationale"),
                impact_assessment=change.get("impact_assessment")
            )
            pr_changes.append(pr_change.dict())
        
        # Create PR
        pr_data = {
            "title": title,
            "description": description,
            "pr_number": pr_number,
            "master_course_id": fork["master_course_id"],
            "fork_id": ObjectId(fork_id),
            "teacher_id": ObjectId(teacher_id),
            "changes": pr_changes,
            "files_changed": len(changes),
            "additions": len([c for c in changes if c["change_type"] == "add"]),
            "deletions": len([c for c in changes if c["change_type"] == "delete"]),
            "status": "open",
            "review_checklist": [],
            "comments": [],
            "requested_changes": [],
            "is_mergeable": True,
            "conflicts": [],
            "merge_strategy": "merge",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db[self.collection_prs].insert_one(pr_data)
        
        # Update fork PR count
        await db[self.collection_forks].update_one(
            {"_id": ObjectId(fork_id)},
            {
                "$inc": {"pull_requests_submitted": 1},
                "$set": {"last_pr_at": datetime.utcnow()}
            }
        )
        
        # Update master course PR count
        await db[self.collection_courses].update_one(
            {"_id": fork["master_course_id"]},
            {"$inc": {"total_pull_requests": 1}}
        )
        
        return await self._get_pr_with_details(db, str(result.inserted_id))
    
    async def review_pull_request(
        self,
        db: AsyncIOMotorDatabase,
        pr_id: str,
        coordinator_id: str,
        action: str,  # approve, request_changes, reject
        review_notes: Optional[str] = None,
        requested_changes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Review pull request"""
        
        # Permission check
        if not await course_permissions.can_review_pull_request(db, coordinator_id, pr_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Cannot review this pull request"
            )
        
        pr = await db[self.collection_prs].find_one({"_id": ObjectId(pr_id)})
        if not pr:
            raise HTTPException(status_code=404, detail="Pull request not found")
        
        if pr["status"] != "open":
            raise HTTPException(status_code=400, detail="Pull request is not open")
        
        # Update PR based on action
        update_data = {
            "reviewer_id": ObjectId(coordinator_id),
            "review_notes": review_notes,
            "reviewed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if action == "approve":
            update_data["status"] = "approved"
        elif action == "request_changes":
            update_data["status"] = "under_review"
            update_data["requested_changes"] = requested_changes or []
        elif action == "reject":
            update_data["status"] = "rejected"
            update_data["closed_at"] = datetime.utcnow()
        
        await db[self.collection_prs].update_one(
            {"_id": ObjectId(pr_id)},
            {"$set": update_data}
        )
        
        return await self._get_pr_with_details(db, pr_id)
    
    async def merge_pull_request(
        self,
        db: AsyncIOMotorDatabase,
        pr_id: str,
        coordinator_id: str,
        merge_strategy: str = "merge"
    ) -> Dict[str, Any]:
        """Merge approved pull request into master course"""
        
        # Permission check
        if not await course_permissions.can_review_pull_request(db, coordinator_id, pr_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Cannot merge this pull request"
            )
        
        pr = await db[self.collection_prs].find_one({"_id": ObjectId(pr_id)})
        if not pr:
            raise HTTPException(status_code=404, detail="Pull request not found")
        
        if pr["status"] != "approved":
            raise HTTPException(status_code=400, detail="Pull request is not approved")
        
        if not pr["is_mergeable"]:
            raise HTTPException(status_code=400, detail="Pull request has conflicts")
        
        # Apply changes to master course
        await self._apply_pr_changes_to_master(db, pr)
        
        # Update PR status
        await db[self.collection_prs].update_one(
            {"_id": ObjectId(pr_id)},
            {
                "$set": {
                    "status": "merged",
                    "merged_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "merge_strategy": merge_strategy
                }
            }
        )
        
        # Update master course
        await db[self.collection_courses].update_one(
            {"_id": pr["master_course_id"]},
            {
                "$set": {
                    "last_updated_by": pr["teacher_id"],
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"total_contributors": 1}
            }
        )
        
        # Mark other forks as behind
        await self._mark_forks_as_behind(db, str(pr["master_course_id"]), str(pr["fork_id"]))
        
        return await self._get_pr_with_details(db, pr_id)
    
    async def _apply_pr_changes_to_master(
        self,
        db: AsyncIOMotorDatabase,
        pr: Dict[str, Any]
    ):
        """Apply PR changes to master course"""
        
        master_course_id = str(pr["master_course_id"])
        
        for change in pr["changes"]:
            change_type = change["change_type"]
            target_type = change["target_type"]
            
            if target_type == "module":
                collection = self.collection_modules
            elif target_type == "lesson":
                collection = self.collection_lessons
            else:
                continue
            
            if change_type == "add":
                # Add new content to master
                new_item = change["after_data"].copy()
                new_item["course_id"] = ObjectId(master_course_id)
                new_item["is_fork_content"] = False
                new_item["created_at"] = datetime.utcnow()
                new_item["contributed_by"] = pr["teacher_id"]
                await db[collection].insert_one(new_item)
                
            elif change_type == "modify":
                # Update existing content in master
                target_id = change["target_id"]
                update_data = change["after_data"].copy()
                update_data["updated_at"] = datetime.utcnow()
                update_data["last_modified_by"] = pr["teacher_id"]
                
                await db[collection].update_one(
                    {"_id": ObjectId(target_id), "course_id": ObjectId(master_course_id)},
                    {"$set": update_data}
                )
                
            elif change_type == "delete":
                # Delete content from master
                target_id = change["target_id"]
                await db[collection].update_one(
                    {"_id": ObjectId(target_id), "course_id": ObjectId(master_course_id)},
                    {"$set": {"is_deleted": True, "deleted_by": pr["teacher_id"], "deleted_at": datetime.utcnow()}}
                )
    
    async def _mark_forks_as_behind(
        self,
        db: AsyncIOMotorDatabase,
        master_course_id: str,
        exclude_fork_id: str
    ):
        """Mark all other forks as behind after master is updated"""
        
        await db[self.collection_forks].update_many(
            {
                "master_course_id": ObjectId(master_course_id),
                "_id": {"$ne": ObjectId(exclude_fork_id)},
                "is_active": True
            },
            {
                "$set": {
                    "is_behind": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    # ==================== SYNC OPERATIONS ====================
    
    async def sync_fork_with_master(
        self,
        db: AsyncIOMotorDatabase,
        fork_id: str,
        teacher_id: str,
        auto_resolve_conflicts: bool = True
    ) -> Dict[str, Any]:
        """Sync teacher fork with latest master course changes"""
        
        # Permission check
        if not await course_permissions.can_modify_fork(db, teacher_id, fork_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Cannot sync this fork"
            )
        
        fork = await db[self.collection_forks].find_one({"_id": ObjectId(fork_id)})
        if not fork:
            raise HTTPException(status_code=404, detail="Fork not found")
        
        if not fork["is_behind"]:
            return {"message": "Fork is already up to date", "conflicts": []}
        
        # Get master course changes since last sync
        master_course = await db[self.collection_courses].find_one({"_id": fork["master_course_id"]})
        if not master_course:
            raise HTTPException(status_code=404, detail="Master course not found")
        
        # Detect conflicts and apply non-conflicting changes
        sync_result = await self._perform_fork_sync(db, fork, master_course, auto_resolve_conflicts)
        
        # Update fork sync status
        await db[self.collection_forks].update_one(
            {"_id": ObjectId(fork_id)},
            {
                "$set": {
                    "last_sync_at": datetime.utcnow(),
                    "is_behind": len(sync_result["conflicts"]) > 0,
                    "conflicts_count": len(sync_result["conflicts"]),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return sync_result
    
    async def _perform_fork_sync(
        self,
        db: AsyncIOMotorDatabase,
        fork: Dict[str, Any],
        master_course: Dict[str, Any],
        auto_resolve_conflicts: bool
    ) -> Dict[str, Any]:
        """Perform actual sync operation"""
        
        # This is a simplified version - in reality, you'd need sophisticated
        # conflict detection and resolution algorithms
        
        conflicts = []
        applied_changes = []
        
        # Get master content since last sync
        last_sync = fork.get("last_sync_at", fork["forked_at"])
        
        # Get modified modules in master since last sync
        master_modules = await db[self.collection_modules].find({
            "course_id": master_course["_id"],
            "updated_at": {"$gt": last_sync}
        }).to_list(None)
        
        for master_module in master_modules:
            # Check if this module has been modified in fork
            fork_module = await db[self.collection_modules].find_one({
                "course_id": fork["_id"],
                "original_module_id": master_module["_id"]
            })
            
            if fork_module and fork_module["updated_at"] > last_sync:
                # Conflict detected
                conflict = {
                    "type": "module_conflict",
                    "target_id": str(master_module["_id"]),
                    "master_version": master_module,
                    "fork_version": fork_module,
                    "auto_resolvable": False
                }
                conflicts.append(conflict)
            else:
                # No conflict, apply master changes
                if fork_module:
                    await db[self.collection_modules].update_one(
                        {"_id": fork_module["_id"]},
                        {"$set": master_module}
                    )
                else:
                    # New module in master, add to fork
                    new_module = master_module.copy()
                    new_module.pop("_id")
                    new_module["course_id"] = fork["_id"]
                    new_module["original_module_id"] = master_module["_id"]
                    new_module["is_fork_content"] = True
                    await db[self.collection_modules].insert_one(new_module)
                
                applied_changes.append({
                    "type": "module_updated",
                    "target_id": str(master_module["_id"])
                })
        
        return {
            "conflicts": conflicts,
            "applied_changes": applied_changes,
            "total_conflicts": len(conflicts),
            "total_applied": len(applied_changes)
        }
    
    # ==================== HELPER METHODS ====================
    
    async def _get_fork_with_details(
        self,
        db: AsyncIOMotorDatabase,
        fork_id: str
    ) -> Dict[str, Any]:
        """Get fork with populated details"""
        
        pipeline = [
            {"$match": {"_id": ObjectId(fork_id)}},
            
            # Populate master course
            {
                "$lookup": {
                    "from": self.collection_courses,
                    "localField": "master_course_id",
                    "foreignField": "_id",
                    "as": "master_course"
                }
            },
            {"$unwind": "$master_course"},
            
            # Populate teacher
            {
                "$lookup": {
                    "from": "users",
                    "localField": "teacher_id",
                    "foreignField": "_id",
                    "as": "teacher"
                }
            },
            {"$unwind": "$teacher"},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "master_course_title": "$master_course.title",
                    "teacher_name": "$teacher.full_name"
                }
            }
        ]
        
        result = await db[self.collection_forks].aggregate(pipeline).to_list(1)
        return result[0] if result else {}
    
    async def _get_pr_with_details(
        self,
        db: AsyncIOMotorDatabase,
        pr_id: str
    ) -> Dict[str, Any]:
        """Get pull request with populated details"""
        
        pipeline = [
            {"$match": {"_id": ObjectId(pr_id)}},
            
            # Populate master course
            {
                "$lookup": {
                    "from": self.collection_courses,
                    "localField": "master_course_id",
                    "foreignField": "_id",
                    "as": "master_course"
                }
            },
            {"$unwind": "$master_course"},
            
            # Populate fork
            {
                "$lookup": {
                    "from": self.collection_forks,
                    "localField": "fork_id",
                    "foreignField": "_id",
                    "as": "fork"
                }
            },
            {"$unwind": "$fork"},
            
            # Populate teacher
            {
                "$lookup": {
                    "from": "users",
                    "localField": "teacher_id",
                    "foreignField": "_id",
                    "as": "teacher"
                }
            },
            {"$unwind": "$teacher"},
            
            # Add computed fields
            {
                "$addFields": {
                    "id": {"$toString": "$_id"},
                    "master_course_title": "$master_course.title",
                    "fork_title": "$fork.title",
                    "teacher_name": "$teacher.full_name"
                }
            }
        ]
        
        result = await db[self.collection_prs].aggregate(pipeline).to_list(1)
        return result[0] if result else {}

# Create singleton instance
course_workflow = CourseWorkflowEngine()