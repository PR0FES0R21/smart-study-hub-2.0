# ==============================================================================
# File: app/crud/course_version.py
# Deskripsi: CRUD operations untuk Course Version System (New Architecture)
# ==============================================================================
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from fastapi import HTTPException, status

from app.models.course_version import (
    CourseVersion, CourseFamilyMetadata, CourseModule, LessonContent,
    CourseChangeRecord, UsageStatistics
)
from app.models.course_pull_request import CoursePullRequest, ChangeProposal
from app.models.course_change_history import CourseChangeHistory, ChangeContext, ChangeDetail
from app.schemas.base import PyObjectId

class CourseVersionCRUD:
    """CRUD operations untuk Course Version System"""
    
    def __init__(self):
        self.course_versions_collection = "course_versions"
        self.course_families_collection = "course_families"
        self.pull_requests_collection = "course_pull_requests"
        self.change_history_collection = "course_change_history"
    
    # ==================== COURSE FAMILY OPERATIONS ====================
    
    async def create_course_family(
        self,
        db: AsyncIOMotorDatabase,
        base_title: str,
        subject_id: PyObjectId,
        grade_level: int,
        coordinator_id: PyObjectId,
        initial_course_data: Dict[str, Any]
    ) -> Tuple[CourseFamilyMetadata, CourseVersion]:
        """Create new course family dengan initial master version"""
        
        # Validate coordinator has access
        await self._validate_coordinator_access(db, coordinator_id, subject_id, grade_level)
        
        # Create course family
        family_id = PyObjectId(ObjectId())
        family_data = CourseFamilyMetadata(
            course_family_id=family_id,
            base_title=base_title,
            subject_id=subject_id,
            grade_level=grade_level,
            coordinator_id=coordinator_id,
            current_version="1.0.0",
            total_versions=1
        )
        
        # Create initial master version
        master_version = CourseVersion(
            course_family_id=family_id,
            version="1.0.0",
            version_number=1.0,
            title=f"{base_title} v1.0",
            description=initial_course_data.get("description", ""),
            subject_id=subject_id,
            grade_level=grade_level,
            coordinator_id=coordinator_id,
            is_master=True,
            is_active=True,
            fork_type="master",
            modules=initial_course_data.get("modules", []),
            created_by=coordinator_id
        )
        
        # Insert to database
        await db[self.course_families_collection].insert_one(family_data.to_mongo())
        result = await db[self.course_versions_collection].insert_one(master_version.to_mongo())
        
        # Update family with master version ID
        family_data.current_master_version_id = PyObjectId(result.inserted_id)
        await db[self.course_families_collection].update_one(
            {"_id": family_data.course_family_id},
            {"$set": {"current_master_version_id": family_data.current_master_version_id}}
        )
        
        # Log creation
        await self._log_change(
            db, family_id, None, "course_family_created", 
            f"Created course family: {base_title}",
            coordinator_id, "coordinator"
        )
        
        return family_data, master_version
    
    async def get_course_family(
        self,
        db: AsyncIOMotorDatabase,
        family_id: PyObjectId
    ) -> Optional[CourseFamilyMetadata]:
        """Get course family metadata"""
        data = await db[self.course_families_collection].find_one({"course_family_id": family_id})
        return CourseFamilyMetadata.from_mongo(data) if data else None
    
    # ==================== COURSE VERSION OPERATIONS ====================
    
    async def create_teacher_fork(
        self,
        db: AsyncIOMotorDatabase,
        master_version_id: PyObjectId,
        teacher_id: PyObjectId,
        class_ids: List[PyObjectId],
        fork_title_suffix: str = ""
    ) -> CourseVersion:
        """Create teacher fork dari master version"""
        
        # Get master version
        master = await self.get_version_by_id(db, master_version_id)
        if not master:
            raise HTTPException(status_code=404, detail="Master version not found")
        
        # Validate teacher access
        await self._validate_teacher_access(db, teacher_id, master.subject_id, class_ids)
        
        # Generate fork version number
        fork_count = await db[self.course_versions_collection].count_documents({
            "course_family_id": master.course_family_id,
            "teacher_id": teacher_id,
            "fork_type": "teacher_fork"
        })
        
        fork_version = f"{master.version}-teacher-{teacher_id}-v{fork_count + 1}"
        
        # Create fork
        fork = CourseVersion(
            course_family_id=master.course_family_id,
            version=fork_version,
            version_number=master.version_number + 0.001 * (fork_count + 1),
            title=f"{master.title}{' - ' + fork_title_suffix if fork_title_suffix else ''} (Fork)",
            description=f"Teacher fork of {master.title}",
            subject_id=master.subject_id,
            grade_level=master.grade_level,
            coordinator_id=master.coordinator_id,
            is_master=False,
            is_active=True,
            parent_version_id=master_version_id,
            teacher_id=teacher_id,
            class_ids=class_ids,
            fork_type="teacher_fork",
            modules=master.modules.copy(),  # Deep copy modules
            created_by=teacher_id
        )
        
        # Insert to database
        result = await db[self.course_versions_collection].insert_one(fork.to_mongo())
        fork.id = str(result.inserted_id)
        
        # Update family statistics
        await db[self.course_families_collection].update_one(
            {"course_family_id": master.course_family_id},
            {"$inc": {"total_forks": 1}}
        )
        
        # Log fork creation
        await self._log_change(
            db, master.course_family_id, PyObjectId(result.inserted_id),
            "fork_created", f"Teacher fork created from {master.version}",
            teacher_id, "teacher"
        )
        
        # Auto-enroll students dari classes
        await self._auto_enroll_students_to_fork(db, PyObjectId(result.inserted_id), class_ids)
        
        return fork
    
    async def get_version_by_id(
        self,
        db: AsyncIOMotorDatabase,
        version_id: PyObjectId,
        include_usage_stats: bool = False
    ) -> Optional[CourseVersion]:
        """Get course version by ID"""
        
        pipeline = [
            {"$match": {"_id": version_id}},
        ]
        
        if include_usage_stats:
            # Add usage statistics calculation
            pipeline.extend([
                {
                    "$lookup": {
                        "from": "lesson_progress",
                        "localField": "_id",
                        "foreignField": "course_version_id",
                        "as": "progress_data"
                    }
                },
                {
                    "$addFields": {
                        "usage_stats.enrolled_students": {"$size": "$progress_data"},
                        "usage_stats.active_students": {
                            "$size": {
                                "$filter": {
                                    "input": "$progress_data",
                                    "cond": {
                                        "$gte": [
                                            "$progress_data.updated_at",
                                            {"$dateSubtract": {"startDate": "$$NOW", "unit": "day", "amount": 30}}
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            ])
        
        result = await db[self.course_versions_collection].aggregate(pipeline).to_list(1)
        return CourseVersion.from_mongo(result[0]) if result else None
    
    async def update_course_content(
        self,
        db: AsyncIOMotorDatabase,
        version_id: PyObjectId,
        updates: Dict[str, Any],
        updated_by: PyObjectId
    ) -> CourseVersion:
        """Update course content (modules, lessons)"""
        
        # Get current version
        current_version = await self.get_version_by_id(db, version_id)
        if not current_version:
            raise HTTPException(status_code=404, detail="Course version not found")
        
        # Validate permissions
        await self._validate_edit_permission(db, current_version, updated_by)
        
        # Track changes
        changes_made = []
        
        # Apply updates
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        if "modules" in updates:
            # Compare modules to track changes
            old_modules = {str(m.module_id): m for m in current_version.modules}
            new_modules = updates["modules"]
            
            for new_module in new_modules:
                module_id = str(new_module.get("module_id"))
                if module_id in old_modules:
                    # Check for modifications
                    if new_module != old_modules[module_id].dict():
                        changes_made.append(
                            CourseChangeRecord(
                                action="modify_module",
                                target_type="module",
                                target_id=PyObjectId(module_id),
                                description=f"Modified module: {new_module.get('title', 'Unknown')}",
                                old_data=old_modules[module_id].dict(),
                                new_data=new_module
                            )
                        )
                else:
                    # New module
                    changes_made.append(
                        CourseChangeRecord(
                            action="add_module",
                            target_type="module",
                            target_id=PyObjectId(module_id),
                            description=f"Added module: {new_module.get('title', 'Unknown')}",
                            new_data=new_module
                        )
                    )
            
            update_data["modules"] = new_modules
            update_data["changes_from_parent"] = current_version.changes_from_parent + changes_made
        
        # Apply other updates
        for key, value in updates.items():
            if key not in ["modules"]:  # modules handled above
                update_data[key] = value
        
        # Update in database
        await db[self.course_versions_collection].update_one(
            {"_id": version_id},
            {"$set": update_data}
        )
        
        # Log changes
        if changes_made:
            await self._log_change(
                db, current_version.course_family_id, version_id,
                "content_updated", f"Updated course content - {len(changes_made)} changes",
                updated_by, self._get_user_type(current_version, updated_by),
                changes_applied=[
                    ChangeDetail(
                        action=change.action,
                        target_type=change.target_type,
                        target_id=change.target_id,
                        summary=change.description
                    ) for change in changes_made
                ]
            )
        
        return await self.get_version_by_id(db, version_id)
    
    async def archive_version(
        self,
        db: AsyncIOMotorDatabase,
        version_id: PyObjectId,
        archived_by: PyObjectId,
        archive_reason: str = "Replaced by newer version"
    ) -> bool:
        """Archive course version"""
        
        # Update version status
        result = await db[self.course_versions_collection].update_one(
            {"_id": version_id},
            {
                "$set": {
                    "status": "archived",
                    "is_active": False,
                    "archived_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Get version for logging
            version = await self.get_version_by_id(db, version_id)
            if version:
                await self._log_change(
                    db, version.course_family_id, version_id,
                    "version_archived", f"Archived version {version.version}: {archive_reason}",
                    archived_by, "system"
                )
            return True
        
        return False
    
    # ==================== PULL REQUEST OPERATIONS ====================
    
    async def create_pull_request(
        self,
        db: AsyncIOMotorDatabase,
        source_version_id: PyObjectId,
        target_version_id: PyObjectId,
        title: str,
        description: str,
        changes: List[Dict[str, Any]],
        requested_by: PyObjectId
    ) -> CoursePullRequest:
        """Create pull request"""
        
        # Get source and target versions
        source = await self.get_version_by_id(db, source_version_id)
        target = await self.get_version_by_id(db, target_version_id)
        
        if not source or not target:
            raise HTTPException(status_code=404, detail="Source or target version not found")
        
        if source.course_family_id != target.course_family_id:
            raise HTTPException(status_code=400, detail="Source and target must be from same course family")
        
        # Generate PR number
        pr_count = await db[self.pull_requests_collection].count_documents({
            "course_family_id": source.course_family_id
        })
        
        # Create change proposals
        change_proposals = []
        for change_data in changes:
            proposal = ChangeProposal(
                action=change_data["action"],
                target_type=change_data["target_type"],
                target_id=change_data.get("target_id"),
                title=change_data["title"],
                description=change_data["description"],
                rationale=change_data.get("rationale", ""),
                insertion_data=change_data.get("insertion_data"),
                old_data=change_data.get("old_data"),
                new_data=change_data.get("new_data")
            )
            change_proposals.append(proposal)
        
        # Create PR
        pr = CoursePullRequest(
            pr_number=pr_count + 1,
            course_family_id=source.course_family_id,
            title=title,
            description=description,
            source_version_id=source_version_id,
            target_version_id=target_version_id,
            requested_by=requested_by,
            changes=change_proposals
        )
        
        # Add initial workflow step
        pr.add_workflow_step("submitted", requested_by, "Pull request submitted for review")
        
        # Insert to database
        result = await db[self.pull_requests_collection].insert_one(pr.to_mongo())
        pr.id = str(result.inserted_id)
        
        # Update family statistics
        await db[self.course_families_collection].update_one(
            {"course_family_id": source.course_family_id},
            {"$inc": {"total_pull_requests": 1}}
        )
        
        # Log PR creation
        await self._log_change(
            db, source.course_family_id, None,
            "pr_submitted", f"PR #{pr.pr_number} submitted: {title}",
            requested_by, "teacher"
        )
        
        # Notify coordinator
        await self._notify_coordinator_new_pr(db, pr)
        
        return pr
    
    async def approve_pull_request(
        self,
        db: AsyncIOMotorDatabase,
        pr_id: PyObjectId,
        approved_by: PyObjectId,
        approval_comment: str = ""
    ) -> Tuple[CoursePullRequest, CourseVersion]:
        """Approve and merge pull request"""
        
        # Get PR
        pr_data = await db[self.pull_requests_collection].find_one({"_id": pr_id})
        if not pr_data:
            raise HTTPException(status_code=404, detail="Pull request not found")
        
        pr = CoursePullRequest.from_mongo(pr_data)
        
        # Validate approval permission
        target_version = await self.get_version_by_id(db, pr.target_version_id)
        if not target_version:
            raise HTTPException(status_code=404, detail="Target version not found")
        
        await self._validate_coordinator_permission(db, approved_by, target_version.coordinator_id)
        
        # Archive current master
        await self.archive_version(
            db, pr.target_version_id, approved_by, 
            f"Replaced by merge from PR #{pr.pr_number}"
        )
        
        # Create new master version dengan changes applied
        new_master = await self._apply_pr_changes(db, pr, approved_by)
        
        # Update PR status
        pr.status = "merged"
        pr.merged_at = datetime.utcnow()
        pr.merged_version_id = PyObjectId(new_master.id)
        pr.add_workflow_step("approved", approved_by, approval_comment)
        pr.add_workflow_step("merged", approved_by, "Changes merged to master")
        
        await db[self.pull_requests_collection].update_one(
            {"_id": pr_id},
            {"$set": pr.dict(exclude={"id"})}
        )
        
        # Update course family
        await db[self.course_families_collection].update_one(
            {"course_family_id": pr.course_family_id},
            {
                "$set": {
                    "current_master_version_id": PyObjectId(new_master.id),
                    "current_version": new_master.version,
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"total_versions": 1}
            }
        )
        
        # Log merge
        await self._log_change(
            db, pr.course_family_id, PyObjectId(new_master.id),
            "pr_merged", f"PR #{pr.pr_number} merged - created version {new_master.version}",
            approved_by, "coordinator"
        )
        
        # Notify teachers about update
        await self._notify_teachers_master_update(db, new_master)
        
        return pr, new_master
    
    # ==================== HELPER METHODS ====================
    
    async def _validate_coordinator_access(
        self,
        db: AsyncIOMotorDatabase,
        coordinator_id: PyObjectId,
        subject_id: PyObjectId,
        grade_level: int
    ):
        """Validate coordinator has access to subject/grade"""
        assignment = await db["coordination_assignments"].find_one({
            "coordinator_id": coordinator_id,
            "subject_id": subject_id,
            "grade_level": grade_level
        })
        if not assignment:
            raise HTTPException(
                status_code=403,
                detail="Coordinator does not have access to this subject/grade"
            )
    
    async def _validate_teacher_access(
        self,
        db: AsyncIOMotorDatabase,
        teacher_id: PyObjectId,
        subject_id: PyObjectId,
        class_ids: List[PyObjectId]
    ):
        """Validate teacher has access to subject/classes"""
        for class_id in class_ids:
            assignment = await db["teaching_assignments"].find_one({
                "teacher_id": teacher_id,
                "subject_id": subject_id,
                "class_id": class_id
            })
            if not assignment:
                raise HTTPException(
                    status_code=403,
                    detail=f"Teacher does not have access to subject/class {class_id}"
                )
    
    async def _validate_edit_permission(
        self,
        db: AsyncIOMotorDatabase,
        version: CourseVersion,
        user_id: PyObjectId
    ):
        """Validate user can edit this version"""
        if version.is_master:
            # Only coordinator can edit master
            if version.coordinator_id != user_id:
                raise HTTPException(status_code=403, detail="Only coordinator can edit master course")
        else:
            # Only teacher owner can edit fork
            if version.teacher_id != user_id:
                raise HTTPException(status_code=403, detail="Only fork owner can edit teacher fork")
    
    def _get_user_type(self, version: CourseVersion, user_id: PyObjectId) -> str:
        """Determine user type for logging"""
        if version.coordinator_id == user_id:
            return "coordinator"
        elif version.teacher_id == user_id:
            return "teacher"
        else:
            return "admin"  # Default fallback
    
    async def _log_change(
        self,
        db: AsyncIOMotorDatabase,
        course_family_id: PyObjectId,
        version_id: Optional[PyObjectId],
        change_type: str,
        description: str,
        actor_id: PyObjectId,
        actor_type: str,
        changes_applied: Optional[List[ChangeDetail]] = None
    ):
        """Log change to history"""
        history = CourseChangeHistory(
            course_family_id=course_family_id,
            version_id=version_id,
            change_type=change_type,
            title=change_type.replace("_", " ").title(),
            description=description,
            actor_id=actor_id,
            actor_type=actor_type,
            changes_applied=changes_applied or []
        )
        
        await db[self.change_history_collection].insert_one(history.to_mongo())
    
    async def _auto_enroll_students_to_fork(
        self,
        db: AsyncIOMotorDatabase,
        fork_version_id: PyObjectId,
        class_ids: List[PyObjectId]
    ):
        """Auto-enroll students to fork version"""
        # This would integrate dengan existing enrollment system
        # For now, placeholder
        pass
    
    async def _apply_pr_changes(
        self,
        db: AsyncIOMotorDatabase,
        pr: CoursePullRequest,
        applied_by: PyObjectId
    ) -> CourseVersion:
        """Apply PR changes and create new master version"""
        # Get target version
        target = await self.get_version_by_id(db, pr.target_version_id)
        
        # Calculate new version number
        current_version_parts = target.version.split(".")
        major, minor, patch = map(int, current_version_parts)
        new_version = f"{major}.{minor + 1}.0"
        
        # Apply changes (simplified - dalam implementasi real akan lebih complex)
        new_modules = target.modules.copy()
        
        # Create new master version
        new_master = CourseVersion(
            course_family_id=target.course_family_id,
            version=new_version,
            version_number=float(f"{major}.{minor + 1}"),
            title=target.title.replace(f"v{target.version}", f"v{new_version}"),
            description=target.description,
            subject_id=target.subject_id,
            grade_level=target.grade_level,
            coordinator_id=target.coordinator_id,
            is_master=True,
            is_active=True,
            parent_version_id=pr.target_version_id,
            created_from_pr_id=PyObjectId(pr.id),
            fork_type="master",
            modules=new_modules,
            created_by=applied_by,
            changes_from_parent=[
                CourseChangeRecord(
                    action=change.action,
                    target_type=change.target_type,
                    description=change.description
                ) for change in pr.changes
            ]
        )
        
        # Insert new master
        result = await db[self.course_versions_collection].insert_one(new_master.to_mongo())
        new_master.id = str(result.inserted_id)
        
        return new_master
    
    async def _notify_coordinator_new_pr(self, db: AsyncIOMotorDatabase, pr: CoursePullRequest):
        """Notify coordinator about new PR"""
        # Placeholder untuk notification system
        pass
    
    async def _notify_teachers_master_update(self, db: AsyncIOMotorDatabase, new_master: CourseVersion):
        """Notify teachers about master update"""
        # Placeholder untuk notification system
        pass
    
    async def _validate_coordinator_permission(
        self,
        db: AsyncIOMotorDatabase,
        user_id: PyObjectId,
        coordinator_id: PyObjectId
    ):
        """Validate user is coordinator or admin"""
        if user_id != coordinator_id:
            # Check if user is admin
            user = await db["users"].find_one({"_id": user_id})
            if not user or "admin" not in user.get("roles", []):
                raise HTTPException(status_code=403, detail="Only coordinator or admin can perform this action")

# Create singleton instance
course_version_crud = CourseVersionCRUD()
