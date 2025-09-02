# ==============================================================================
# File: app/crud/crud_question_sets.py (FIXED VERSION)
# Deskripsi: Fixed permission calculation bugs in aggregation pipeline
# ==============================================================================

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClientSession
from typing import List, Optional, Dict, Any, Union
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, status
import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from app.schemas.question_set import (
    QuestionSetCreate, 
    QuestionSetUpdate, 
    QuestionSetStatus
)
from app.schemas.pagination import PaginatedResponse
from app.core.cache import get_cache, set_cache, invalidate_cache

# ==============================================================================
# CACHE CONFIGURATION
# ==============================================================================

class CacheConfig:
    """Centralized cache configuration"""
    
    # TTL in seconds
    QUESTION_SETS_TTL = 300  # 5 minutes
    QUESTION_SET_DETAIL_TTL = 600  # 10 minutes
    TEACHING_ASSIGNMENTS_TTL = 1800  # 30 minutes
    
    # Cache patterns
    QUESTION_SETS_PATTERN = "question_sets:*"
    QUESTION_SET_DETAIL_PATTERN = "question_set:detail:*"
    USER_TEACHING_PATTERN = "user:teaching:*"

@dataclass
class CacheKeys:
    """Cache key generator with consistent patterns"""
    
    @staticmethod
    def question_sets_list(user_id: ObjectId, filters: Dict[str, Any], page: int, limit: int) -> str:
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]
        return f"question_sets:user:{user_id}:filters:{filter_hash}:page:{page}:limit:{limit}"
    
    @staticmethod
    def question_set_detail(question_set_id: ObjectId, user_id: ObjectId) -> str:
        return f"question_set:detail:{question_set_id}:user:{user_id}"
    
    @staticmethod
    def user_teaching(user_id: ObjectId) -> str:
        return f"user:teaching:{user_id}"

# ==============================================================================
# PERMISSION SYSTEM
# ==============================================================================

class Permission(Enum):
    """Standardized permission types"""
    VIEW = "can_view"
    EDIT = "can_edit"
    MANAGE_QUESTIONS = "can_manage_questions"
    PUBLISH = "can_publish"

class PermissionChecker:
    """Centralized permission checking logic"""
    
    def __init__(self, question_set: Dict[str, Any], user_id: ObjectId):
        self.question_set = question_set
        self.user_id = user_id
        self.creator_id = question_set.get("created_by_coordinator_id")
        self.permissions = question_set.get("access_permissions", {})
    
    def is_creator(self) -> bool:
        return self.creator_id == self.user_id
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        if self.is_creator():
            return True
        
        return self.user_id in self.permissions.get(permission.value, [])
    
    def can_view(self) -> bool:
        """Check view permission including public access"""
        if self.question_set.get("is_public", False):
            return True
        
        # Check any explicit permission (any permission includes view)
        return any(
            self.has_permission(perm) for perm in Permission
        )
    
    def can_edit(self) -> bool:
        return self.has_permission(Permission.EDIT)
    
    def can_manage_questions(self) -> bool:
        return self.has_permission(Permission.MANAGE_QUESTIONS)
    
    def can_publish(self) -> bool:
        return self.has_permission(Permission.PUBLISH)

# ==============================================================================
# DATABASE OPERATIONS
# ==============================================================================

class QuestionSetRepository:
    """Repository pattern for question set operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def find_by_id(self, question_set_id: ObjectId, session: Optional[AsyncIOMotorClientSession] = None) -> Optional[Dict[str, Any]]:
        """Find question set by ID"""
        return await self.db["question_sets"].find_one(
            {"_id": question_set_id}, session=session
        )
    
    async def find_by_id_or_raise(self, question_set_id: ObjectId, session: Optional[AsyncIOMotorClientSession] = None) -> Dict[str, Any]:
        """Find question set by ID or raise 404"""
        question_set = await self.find_by_id(question_set_id, session)
        if not question_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question set not found"
            )
        return question_set
    
    async def update_atomic(
        self, 
        question_set_id: ObjectId, 
        update_data: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> Dict[str, Any]:
        """Atomic update with timestamp"""
        update_data["updated_at"] = datetime.utcnow()
        
        await self.db["question_sets"].update_one(
            {"_id": question_set_id},
            {"$set": update_data},
            session=session
        )
        
        return await self.find_by_id(question_set_id, session)
    
    async def create(self, question_set_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new question set"""
        now = datetime.utcnow()
        question_set_data.update({
            "created_at": now,
            "updated_at": now
        })
        
        result = await self.db["question_sets"].insert_one(question_set_data)
        return await self.find_by_id(result.inserted_id)

class QuestionRepository:
    """Repository for question operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def validate_existence(
        self, 
        question_ids: List[ObjectId],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> None:
        """Validate that all question IDs exist"""
        if not question_ids:
            return
        
        existing_count = await self.db["question_banks"].count_documents(
            {"_id": {"$in": question_ids}}, session=session
        )
        
        if existing_count != len(question_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some question IDs do not exist"
            )
    
    async def calculate_metadata(
        self, 
        question_ids: List[ObjectId],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> Dict[str, Any]:
        """Calculate metadata using optimized aggregation"""
        if not question_ids:
            return {
                "total_questions": 0,
                "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
                "total_points": 0,
                "tags": []
            }
        
        pipeline = [
            {"$match": {"_id": {"$in": question_ids}}},
            {
                "$group": {
                    "_id": None,
                    "total_questions": {"$sum": 1},
                    "total_points": {"$sum": {"$ifNull": ["$points", 0]}},
                    "difficulties": {"$push": "$difficulty"},
                    "all_tags": {"$push": {"$ifNull": ["$tags", []]}}
                }
            },
            {
                "$project": {
                    "total_questions": 1,
                    "total_points": 1,
                    "difficulty_distribution": {
                        "easy": {
                            "$size": {
                                "$filter": {
                                    "input": "$difficulties",
                                    "cond": {"$eq": ["$$this", "easy"]}
                                }
                            }
                        },
                        "medium": {
                            "$size": {
                                "$filter": {
                                    "input": "$difficulties",
                                    "cond": {"$eq": ["$$this", "medium"]}
                                }
                            }
                        },
                        "hard": {
                            "$size": {
                                "$filter": {
                                    "input": "$difficulties",
                                    "cond": {"$eq": ["$$this", "hard"]}
                                }
                            }
                        }
                    },
                    "tags": {
                        "$reduce": {
                            "input": "$all_tags",
                            "initialValue": [],
                            "in": {"$setUnion": ["$$value", "$$this"]}
                        }
                    }
                }
            }
        ]
        
        result = await self.db["question_banks"].aggregate(
            pipeline, session=session
        ).to_list(1)
        
        if not result:
            return {
                "total_questions": 0,
                "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
                "total_points": 0,
                "tags": []
            }
        
        return result[0]

# ==============================================================================
# BUSINESS LOGIC SERVICES
# ==============================================================================

class QuestionSetService:
    """Business logic for question set operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.qset_repo = QuestionSetRepository(db)
        self.question_repo = QuestionRepository(db)
    
    async def get_accessible_question_sets_paginated(
        self,
        user_id: ObjectId,
        page: int = 1,
        limit: int = 20,
        subject_id: Optional[ObjectId] = None,
        grade_level: Optional[int] = None,
        status: Optional[QuestionSetStatus] = None,
        search: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> PaginatedResponse:
        """Get paginated accessible question sets with caching"""
        
        # Prepare filters for cache key
        filters = self._prepare_filters(subject_id, grade_level, status, search, is_public)
        
        # Try cache first
        cache_key = CacheKeys.question_sets_list(user_id, filters, page, limit)
        cached_result = await get_cache(cache_key)
        if cached_result:
            return PaginatedResponse(**cached_result)
        
        # Get user teaching assignments
        user_subjects_grades = await self._get_user_teaching_cached(user_id)
        
        # Build and execute query
        pipeline = self._build_question_sets_pipeline(
            user_id, user_subjects_grades, filters, page, limit
        )
        
        result = await self._execute_paginated_query(pipeline, page, limit, user_id)
        
        # Cache result
        await set_cache(cache_key, result.dict(), ttl=CacheConfig.QUESTION_SETS_TTL)
        
        return result
    
    async def get_question_set_detail(
        self, 
        question_set_id: ObjectId, 
        user_id: ObjectId
    ) -> Dict[str, Any]:
        """Get detailed question set with permissions"""
        
        # Try cache first
        cache_key = CacheKeys.question_set_detail(question_set_id, user_id)
        cached_result = await get_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Build and execute detailed query
        pipeline = self._build_detail_pipeline(question_set_id, user_id)
        results = await self.db["question_sets"].aggregate(pipeline).to_list(1)
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question set not found"
            )
        
        question_set = results[0]
        
        # Validate access permissions
        await self._validate_access_permission(question_set, user_id)
        
        # Cache result
        await set_cache(cache_key, question_set, ttl=CacheConfig.QUESTION_SET_DETAIL_TTL)
        
        return question_set
    
    async def create_question_set(
        self, 
        qset: QuestionSetCreate, 
        coordinator_id: ObjectId
    ) -> Dict[str, Any]:
        """Create new question set"""
        
        qset_data = {
            "name": qset.name,
            "subject_id": qset.subject_id,
            "grade_level": qset.grade_level,
            "created_by_coordinator_id": coordinator_id,
            "question_ids": [],
            "status": QuestionSetStatus.DRAFT,
            "is_public": qset.is_public,
            "access_permissions": {
                "can_view": [coordinator_id],
                "can_edit": [coordinator_id],
                "can_manage_questions": [coordinator_id],
                "can_publish": [coordinator_id]
            },
            "metadata": {
                "total_questions": 0,
                "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
                "total_points": 0,
                "tags": qset.tags or []
            },
            "description": qset.description,
            "version": 1,
            "published_date": None
        }
        
        created_qset = await self.qset_repo.create(qset_data)
        
        # Invalidate caches
        await self._invalidate_user_caches(coordinator_id)
        
        return created_qset
    
    async def update_question_set(
        self,
        question_set_id: ObjectId,
        qset_update: QuestionSetUpdate,
        user_id: ObjectId
    ) -> Dict[str, Any]:
        """Update question set with permission validation"""
        
        question_set = await self.qset_repo.find_by_id_or_raise(question_set_id)
        
        # Check permissions
        checker = PermissionChecker(question_set, user_id)
        if not checker.can_edit():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this question set"
            )
        
        update_data = qset_update.model_dump(exclude_unset=True)
        
        # Handle status change to published
        if (qset_update.status == QuestionSetStatus.PUBLISHED and 
            question_set["status"] != QuestionSetStatus.PUBLISHED):
            
            if not checker.can_publish():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to publish this question set"
                )
            
            update_data.update({
                "published_date": datetime.utcnow(),
                "version": question_set.get("version", 1) + 1
            })
        
        updated_qset = await self.qset_repo.update_atomic(question_set_id, update_data)
        
        # Invalidate caches
        await self._invalidate_question_set_caches(user_id, question_set_id)
        
        return updated_qset
    
    async def manage_questions(
        self,
        question_set_id: ObjectId,
        question_ids: List[ObjectId],
        user_id: ObjectId,
        operation: str  # "add" or "remove"
    ) -> Dict[str, Any]:
        """Manage questions in question set with transaction support"""
        
        if not question_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question IDs cannot be empty"
            )
        
        async with await self.db.client.start_session() as session:
            async with session.start_transaction():
                # Get and validate question set
                question_set = await self.qset_repo.find_by_id_or_raise(question_set_id, session)
                
                # Check permissions
                checker = PermissionChecker(question_set, user_id)
                if not checker.can_manage_questions():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to manage questions in this set"
                    )
                
                # Validate questions exist
                await self.question_repo.validate_existence(question_ids, session)
                
                # Calculate new question IDs
                current_ids = set(question_set.get("question_ids", []))
                new_question_ids = self._calculate_new_question_ids(
                    current_ids, question_ids, operation
                )
                
                # Check if changes are needed
                if new_question_ids == current_ids:
                    error_msg = (
                        "All questions are already in the set" if operation == "add"
                        else "Questions are not in the set"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )
                
                # Calculate metadata and update
                metadata = await self.question_repo.calculate_metadata(
                    list(new_question_ids), session
                )
                
                updated_qset = await self.qset_repo.update_atomic(
                    question_set_id,
                    {
                        "question_ids": list(new_question_ids),
                        "metadata": metadata
                    },
                    session
                )
                
                # Invalidate caches (outside transaction for better performance)
                await self._invalidate_question_set_caches(user_id, question_set_id)
                
                return updated_qset
    
    async def soft_delete_question_set(
        self,
        question_set_id: ObjectId,
        user_id: ObjectId,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Soft delete question set with validation"""
        
        question_set = await self.qset_repo.find_by_id_or_raise(question_set_id)
        
        # Check permissions - only creator can delete
        checker = PermissionChecker(question_set, user_id)
        if not checker.is_creator():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creator can delete question set"
            )
        
        # Soft delete by updating status to archived
        update_data = {
            "status": QuestionSetStatus.ARCHIVED,
            "archived_at": datetime.utcnow(),
            "archived_by": user_id,
            "archive_reason": reason or "Deleted by creator"
        }
        
        updated_qset = await self.qset_repo.update_atomic(question_set_id, update_data)
        
        # Invalidate caches
        await self._invalidate_question_set_caches(user_id, question_set_id)
        
        return updated_qset
    
    async def get_usage_info(
        self,
        question_set_id: ObjectId
    ) -> Dict[str, Any]:
        """Get usage information for question set"""
        
        # Get exam usage statistics
        pipeline = [
            {"$match": {"question_set_id": question_set_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        usage_stats = await self.db["exams"].aggregate(pipeline).to_list(None)
        usage_by_status = {stat["_id"]: stat["count"] for stat in usage_stats}
        
        total_exams = sum(usage_by_status.values())
        active_exams = usage_by_status.get("active", 0) + usage_by_status.get("scheduled", 0)
        
        return {
            "total_exams": total_exams,
            "active_exams": active_exams,
            "completed_exams": usage_by_status.get("completed", 0),
            "scheduled_exams": usage_by_status.get("scheduled", 0),
            "can_delete": active_exams == 0,
            "usage_by_status": usage_by_status
        }
    
    # Helper methods
    
    def _prepare_filters(self, subject_id, grade_level, status, search, is_public) -> Dict[str, Any]:
        """Prepare filters for caching and querying"""
        return {k: v for k, v in {
            "subject_id": str(subject_id) if subject_id else None,
            "grade_level": grade_level,
            "status": status,
            "search": search,
            "is_public": is_public
        }.items() if v is not None}
    
    def _calculate_new_question_ids(
        self, 
        current_ids: set, 
        question_ids: List[ObjectId], 
        operation: str
    ) -> set:
        """Calculate new question IDs based on operation"""
        question_ids_set = set(question_ids)
        
        if operation == "add":
            return current_ids | question_ids_set
        elif operation == "remove":
            return current_ids - question_ids_set
        else:
            raise ValueError(f"Invalid operation: {operation}")
    
    async def _get_user_group_access_with_coordinator(self, user_id: ObjectId) -> List[Dict[str, Any]]:
        """
        Get user group access berdasarkan koordinator yang sama.
        Ini adalah CORE FIX untuk konsep "satu grup".
        """
        cache_key = CacheKeys.user_teaching(user_id)
        cached_result = await get_cache(cache_key)
        if cached_result:
            return cached_result
        
        pipeline = [
            # 1. Match teaching assignments user
            {"$match": {"teacher_id": user_id}},
            
            # 2. Get class info untuk grade_level
            {
                "$lookup": {
                    "from": "classes",
                    "localField": "class_id",
                    "foreignField": "_id",
                    "as": "class_info"
                }
            },
            {"$unwind": "$class_info"},
            
            # 3. CRITICAL: Get coordination info untuk validasi grup
            {
                "$lookup": {
                    "from": "coordination_assignments",
                    "let": {
                        "subject_id": "$subject_id",
                        "grade_level": "$class_info.grade_level",
                        "academic_period": "$academic_period_id"
                    },
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$subject_id", "$$subject_id"]},
                                        {"$eq": ["$grade_level", "$$grade_level"]},
                                        {"$eq": ["$academic_period_id", "$$academic_period"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "coordinator_info"
                }
            },
            {"$unwind": {"path": "$coordinator_info", "preserveNullAndEmptyArrays": True}},
            
            # 4. Project dengan coordinator_id sebagai grup identifier
            {
                "$project": {
                    "subject_id": 1,
                    "grade_level": "$class_info.grade_level",
                    "coordinator_id": "$coordinator_info.coordinator_id",  # KEY ADDITION
                    "academic_period_id": 1,
                    "has_coordinator": {"$cond": [{"$ifNull": ["$coordinator_info.coordinator_id", False]}, True, False]}
                }
            },
            
            # 5. Only include assignments that have coordinators
            {"$match": {"has_coordinator": True}}
        ]
        
        assignments = await self.db["teaching_assignments"].aggregate(pipeline).to_list(None)
        
        # Cache dengan coordinator info
        await set_cache(cache_key, assignments, ttl=CacheConfig.TEACHING_ASSIGNMENTS_TTL)
        
        return assignments

    # Keep backward compatibility
    async def _get_user_teaching_cached(self, user_id: ObjectId) -> List[Dict[str, Any]]:
        """Backward compatibility wrapper"""
        return await self._get_user_group_access_with_coordinator(user_id)
    
    def _build_question_sets_pipeline(
        self,
        user_id: ObjectId,
        user_groups: List[Dict[str, Any]],  # RENAMED from user_subjects_grades
        filters: Dict[str, Any],
        page: int,
        limit: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Build pipeline dengan GROUP-BASED access control"""
        
        # Build match conditions
        match_conditions = {}
        
        if filters.get("subject_id"):
            match_conditions["subject_id"] = ObjectId(filters["subject_id"])
        if filters.get("grade_level"):
            match_conditions["grade_level"] = filters["grade_level"]
        if filters.get("status"):
            match_conditions["status"] = filters["status"]
        if filters.get("is_public") is not None:
            match_conditions["is_public"] = filters["is_public"]
        if filters.get("search"):
            match_conditions["name"] = {"$regex": filters["search"], "$options": "i"}
        
        # ENHANCED: Group-based access conditions
        access_conditions = [
            {"is_public": True},
            {"created_by_coordinator_id": user_id}
        ]
        
        # GROUP ACCESS: Hanya yang satu koordinator
        if user_groups:
            group_conditions = []
            for group in user_groups:
                if group.get("coordinator_id"):  # Only if has coordinator
                    group_conditions.append({
                        "$and": [
                            {"is_public": False},
                            {"subject_id": group["subject_id"]},
                            {"grade_level": group["grade_level"]},
                            {"created_by_coordinator_id": group["coordinator_id"]}  # KEY VALIDATION
                        ]
                    })
            
            if group_conditions:
                access_conditions.append({"$or": group_conditions})
        
        # Explicit permissions (tetap ada untuk backward compatibility)
        access_conditions.extend([
            {"access_permissions.can_view": user_id},
            {"access_permissions.can_edit": user_id},
            {"access_permissions.can_manage_questions": user_id},
            {"access_permissions.can_publish": user_id}
        ])
        
        # Combine conditions
        if match_conditions:
            final_match = {
                "$and": [
                    match_conditions,
                    {"$or": access_conditions}
                ]
            }
        else:
            final_match = {"$or": access_conditions}
        
        return {
            "match": final_match,
            "sort": {"created_at": -1}
        }
    
    def _build_detail_pipeline(self, question_set_id: ObjectId, user_id: ObjectId) -> List[Dict[str, Any]]:
        """Build detailed aggregation pipeline with all lookups - FIXED VERSION with permission_holders"""
        return [
            {"$match": {"_id": question_set_id}},
            
            # Lookup subject
            {
                "$lookup": {
                    "from": "subjects",
                    "localField": "subject_id",
                    "foreignField": "_id",
                    "as": "subject_info"
                }
            },
            {"$unwind": {"path": "$subject_info", "preserveNullAndEmptyArrays": True}},
            
            # Lookup creator profile
            {
                "$lookup": {
                    "from": "profiles",
                    "localField": "created_by_coordinator_id",
                    "foreignField": "user_id",
                    "as": "creator_profile"
                }
            },
            {"$unwind": {"path": "$creator_profile", "preserveNullAndEmptyArrays": True}},
            
            # NEW: Lookup permission holders for can_view
            {
                "$lookup": {
                    "from": "profiles",
                    "localField": "access_permissions.can_view",
                    "foreignField": "user_id",
                    "as": "can_view_profiles"
                }
            },
            
            # NEW: Lookup permission holders for can_edit
            {
                "$lookup": {
                    "from": "profiles",
                    "localField": "access_permissions.can_edit",
                    "foreignField": "user_id",
                    "as": "can_edit_profiles"
                }
            },
            
            # NEW: Lookup permission holders for can_manage_questions
            {
                "$lookup": {
                    "from": "profiles",
                    "localField": "access_permissions.can_manage_questions",
                    "foreignField": "user_id",
                    "as": "can_manage_questions_profiles"
                }
            },
            
            # NEW: Lookup permission holders for can_publish
            {
                "$lookup": {
                    "from": "profiles",
                    "localField": "access_permissions.can_publish",
                    "foreignField": "user_id",
                    "as": "can_publish_profiles"
                }
            },
            
            # FIXED: Add variables to hold these values for reuse in projection
            {
                "$addFields": {
                    "_current_user_id": user_id,
                    "_is_creator": {"$eq": ["$created_by_coordinator_id", user_id]}
                }
            },
            
            # Project with FIXED permissions calculation AND permission_holders
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "description": 1,
                    "grade_level": 1,
                    "status": 1,
                    "is_public": 1,
                    "metadata": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "published_date": 1,
                    "version": 1,
                    "question_ids": 1,
                    "access_permissions": 1,
                    "created_by_coordinator_id": 1,
                    
                    "subject": {
                        "_id": "$subject_info._id",
                        "name": "$subject_info.name",
                        "code": "$subject_info.code",
                        "description": "$subject_info.description"
                    },
                    
                    "created_by": {
                        "_id": "$created_by_coordinator_id",
                        "full_name": "$creator_profile.full_name",
                        "profile_picture_url": "$creator_profile.profile_picture_url"
                    },
                    
                    # NEW: Permission holders with user details
                    "permission_holders": {
                        "can_view": {
                            "$map": {
                                "input": "$can_view_profiles",
                                "as": "profile",
                                "in": {
                                    "_id": "$$profile.user_id",
                                    "full_name": "$$profile.full_name",
                                    "profile_picture_url": "$$profile.profile_picture_url"
                                }
                            }
                        },
                        "can_edit": {
                            "$map": {
                                "input": "$can_edit_profiles",
                                "as": "profile",
                                "in": {
                                    "_id": "$$profile.user_id",
                                    "full_name": "$$profile.full_name",
                                    "profile_picture_url": "$$profile.profile_picture_url"
                                }
                            }
                        },
                        "can_manage_questions": {
                            "$map": {
                                "input": "$can_manage_questions_profiles",
                                "as": "profile",
                                "in": {
                                    "_id": "$$profile.user_id",
                                    "full_name": "$$profile.full_name",
                                    "profile_picture_url": "$$profile.profile_picture_url"
                                }
                            }
                        },
                        "can_publish": {
                            "$map": {
                                "input": "$can_publish_profiles",
                                "as": "profile",
                                "in": {
                                    "_id": "$$profile.user_id",
                                    "full_name": "$$profile.full_name",
                                    "profile_picture_url": "$$profile.profile_picture_url"
                                }
                            }
                        }
                    },
                    
                    "current_user_permissions": {
                        "can_view": {
                            "$or": [
                                {"$eq": ["$is_public", True]},
                                "$_is_creator",
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_view", []]}]},
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_edit", []]}]},
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_manage_questions", []]}]},
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_publish", []]}]}
                            ]
                        },
                        "can_edit": {
                            "$or": [
                                "$_is_creator",
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_edit", []]}]}
                            ]
                        },
                        "can_manage_questions": {
                            "$or": [
                                "$_is_creator",
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_manage_questions", []]}]}
                            ]
                        },
                        "can_publish": {
                            "$or": [
                                "$_is_creator",
                                {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_publish", []]}]}
                            ]
                        },
                        "is_creator": "$_is_creator"
                    }
                }
            }
        ]
    
    async def _execute_paginated_query(
        self, 
        pipeline: Dict[str, Any], 
        page: int, 
        limit: int,
        user_id: ObjectId  # Added user_id parameter for permission calculation
    ) -> PaginatedResponse:
        """Execute paginated query with facet - FIXED VERSION"""
        
        facet_pipeline = [
            {"$match": pipeline["match"]},
            {
                "$facet": {
                    "total_count": [{"$count": "count"}],
                    "data": [
                        {
                            "$lookup": {
                                "from": "subjects",
                                "localField": "subject_id",
                                "foreignField": "_id",
                                "as": "subject_info"
                            }
                        },
                        {"$unwind": {"path": "$subject_info", "preserveNullAndEmptyArrays": True}},
                        {
                            "$lookup": {
                                "from": "profiles",
                                "localField": "created_by_coordinator_id",
                                "foreignField": "user_id",
                                "as": "creator_profile"
                            }
                        },
                        {"$unwind": {"path": "$creator_profile", "preserveNullAndEmptyArrays": True}},
                        
                        # FIXED: Add user ID and creator check
                        {
                            "$addFields": {
                                "_current_user_id": user_id,
                                "_is_creator": {"$eq": ["$created_by_coordinator_id", user_id]}
                            }
                        },
                        
                        {
                            "$project": {
                                "_id": 1,
                                "name": 1,
                                "description": 1,
                                "grade_level": 1,
                                "status": 1,
                                "is_public": 1,
                                "metadata": 1,
                                "created_at": 1,
                                "updated_at": 1,
                                
                                "subject": {
                                    "_id": "$subject_info._id",
                                    "name": "$subject_info.name",
                                    "code": "$subject_info.code"
                                },
                                
                                "created_by": {
                                    "_id": "$created_by_coordinator_id",
                                    "full_name": "$creator_profile.full_name",
                                    "profile_picture_url": "$creator_profile.profile_picture_url"
                                },
                                
                                # FIXED: Proper permission calculation
                                "can_edit": {
                                    "$or": [
                                        "$_is_creator",
                                        {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_edit", []]}]}
                                    ]
                                },
                                "can_manage_questions": {
                                    "$or": [
                                        "$_is_creator",
                                        {"$in": ["$_current_user_id", {"$ifNull": ["$access_permissions.can_manage_questions", []]}]}
                                    ]
                                },
                                "is_creator": "$_is_creator"
                            }
                        },
                        {"$sort": pipeline["sort"]},
                        {"$skip": (page - 1) * limit},
                        {"$limit": limit}
                    ]
                }
            }
        ]
        
        results = await self.db["question_sets"].aggregate(facet_pipeline).to_list(1)
        
        if not results:
            total_items = 0
            data = []
        else:
            total_items = results[0]["total_count"][0]["count"] if results[0]["total_count"] else 0
            data = results[0]["data"]
        
        total_pages = (total_items + limit - 1) // limit
        
        return PaginatedResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            limit=limit,
            data=data
        )
    
    async def _validate_access_permission(self, question_set: Dict[str, Any], user_id: ObjectId) -> None:
        """Validate user has access to view question set - FIXED VERSION"""
        # Use the calculated permissions from the aggregation pipeline
        current_user_permissions = question_set.get("current_user_permissions", {})
        
        if not current_user_permissions.get("can_view", False):
            # Check teaching assignment for private question sets as fallback
            if not question_set.get("is_public", False):
                user_subjects_grades = await self._get_user_teaching_cached(user_id)
                has_teaching_access = any(
                    sg["subject_id"] == question_set["subject"]["_id"] and 
                    sg["grade_level"] == question_set["grade_level"]
                    for sg in user_subjects_grades
                )
                if not has_teaching_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this question set"
                    )
    
    async def _invalidate_user_caches(self, user_id: ObjectId) -> None:
        """Invalidate user-specific caches"""
        await invalidate_cache(f"question_sets:user:{user_id}:*")
        await invalidate_cache(f"user:teaching:{user_id}")
    
    async def _invalidate_question_set_caches(self, user_id: ObjectId, question_set_id: ObjectId) -> None:
        """Invalidate question set specific caches"""
        await self._invalidate_user_caches(user_id)
        await invalidate_cache(f"question_set:detail:{question_set_id}:*")
    
    async def _invalidate_permission_change_caches(
        self, 
        question_set_id: ObjectId, 
        target_user_id: ObjectId,
        requester_user_id: ObjectId
    ) -> None:
        """
        Invalidate ALL related caches when permissions change.
        
        This is critical for ensuring permission changes take effect immediately
        without requiring manual cache clearing.
        
        Args:
            question_set_id: The question set whose permissions changed
            target_user_id: The user whose permissions were granted/revoked
            requester_user_id: The user who made the permission change
        """
        
        # Get the question set to find all affected users
        question_set = await self.qset_repo.find_by_id(question_set_id)
        if not question_set:
            print(f"⚠️  CACHE INVALIDATION: Question set {question_set_id} not found")
            return
            
        # Collect all user IDs that need cache invalidation
        users_to_invalidate = set()
        users_to_invalidate.add(requester_user_id)
        users_to_invalidate.add(target_user_id)
        
        # Add all users with explicit permissions to ensure consistency
        access_permissions = question_set.get("access_permissions", {})
        for permission_type, permission_list in access_permissions.items():
            if isinstance(permission_list, list):
                users_to_invalidate.update(permission_list)
        
        # Add the creator as they might have cached data too
        creator_id = question_set.get("created_by_coordinator_id")
        if creator_id:
            users_to_invalidate.add(creator_id)
        
        print(f"🔄 CACHE INVALIDATION START: question_set:{question_set_id}")
        print(f"   Target user: {target_user_id}")
        print(f"   Affected users: {len(users_to_invalidate)}")
        
        # Invalidate user-specific caches for all affected users
        for user_id in users_to_invalidate:
            await self._invalidate_user_caches(user_id)
            print(f"   ✅ Invalidated caches for user: {user_id}")
        
        # Invalidate question set detail caches for ALL users
        await invalidate_cache(f"question_set:detail:{question_set_id}:*")
        print(f"   ✅ Invalidated detail caches for question_set: {question_set_id}")
        
        # Invalidate ALL list caches to ensure immediate visibility changes
        # This is aggressive but necessary for permission changes
        await invalidate_cache("question_sets:user:*")
        print(f"   ✅ Invalidated ALL question sets list caches")
        
        # Invalidate teaching assignments cache for target user
        await invalidate_cache(f"user:teaching:{target_user_id}")
        print(f"   ✅ Invalidated teaching cache for target user")
        
        print(f"🔄 CACHE INVALIDATION COMPLETE: {len(users_to_invalidate)} users affected")

# ==============================================================================
# PUBLIC API FUNCTIONS (for backward compatibility)
# ==============================================================================

_service_instance = None

def get_question_set_service(db: AsyncIOMotorDatabase) -> QuestionSetService:
    """Get or create service instance"""
    global _service_instance
    if _service_instance is None or _service_instance.db != db:
        _service_instance = QuestionSetService(db)
    return _service_instance

async def get_accessible_question_sets_paginated(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    page: int = 1,
    limit: int = 20,
    subject_id: Optional[ObjectId] = None,
    grade_level: Optional[int] = None,
    status: Optional[QuestionSetStatus] = None,
    search: Optional[str] = None,
    is_public: Optional[bool] = None
) -> PaginatedResponse:
    """Get paginated accessible question sets - backward compatible wrapper"""
    service = get_question_set_service(db)
    return await service.get_accessible_question_sets_paginated(
        user_id, page, limit, subject_id, grade_level, status, search, is_public
    )

async def get_question_set_detail_with_permissions(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    user_id: ObjectId
) -> Optional[Dict[str, Any]]:
    """Get detailed question set - backward compatible wrapper"""
    service = get_question_set_service(db)
    return await service.get_question_set_detail(question_set_id, user_id)

async def create_question_set(
    db: AsyncIOMotorDatabase, 
    qset: QuestionSetCreate, 
    coordinator_id: ObjectId
) -> Dict[str, Any]:
    """Create question set - backward compatible wrapper"""
    service = get_question_set_service(db)
    return await service.create_question_set(qset, coordinator_id)

async def update_question_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    qset_update: QuestionSetUpdate,
    user_id: ObjectId
) -> Optional[Dict[str, Any]]:
    """Update question set - backward compatible wrapper"""
    service = get_question_set_service(db)
    return await service.update_question_set(question_set_id, qset_update, user_id)

async def add_questions_to_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    question_ids: List[ObjectId],
    user_id: ObjectId
) -> Dict[str, Any]:
    """Add questions to question set - backward compatible wrapper"""
    service = get_question_set_service(db)
    return await service.manage_questions(question_set_id, question_ids, user_id, "add")

async def remove_questions_from_set(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    question_ids: List[ObjectId],
    user_id: ObjectId
) -> Dict[str, Any]:
    """Remove questions from question set - backward compatible wrapper"""
    service = get_question_set_service(db)
    return await service.manage_questions(question_set_id, question_ids, user_id, "remove")

async def manage_permissions(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    target_user_id: ObjectId,
    permissions: List[str],
    action: str,
    requester_user_id: ObjectId
) -> Dict[str, Any]:
    """Manage user permissions for question set"""
    
    service = get_question_set_service(db)
    question_set = await service.qset_repo.find_by_id_or_raise(question_set_id)

    # Only creator can manage permissions
    checker = PermissionChecker(question_set, requester_user_id)
    if not checker.is_creator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator can manage permissions"
        )
    
    access_permissions = question_set.get("access_permissions", {
        "can_view": [],
        "can_edit": [],
        "can_manage_questions": [],
        "can_publish": []
    })
    
    # Apply permissions based on action
    for permission in permissions:
        if permission in access_permissions:
            current_list = access_permissions[permission]
            
            if action == "grant" and target_user_id not in current_list:
                current_list.append(target_user_id)
            elif action == "revoke" and target_user_id in current_list:
                current_list.remove(target_user_id)
    
    # Update database
    updated_qset = await service.qset_repo.update_atomic(
        question_set_id,
        {"access_permissions": access_permissions}
    )
    
    # 🔄 FIXED: Use comprehensive cache invalidation for permission changes
    await service._invalidate_permission_change_caches(
        question_set_id, 
        target_user_id, 
        requester_user_id
    )
    
    return updated_qset

async def get_question_set_questions(
    db: AsyncIOMotorDatabase,
    question_set_id: ObjectId,
    user_id: ObjectId
) -> Optional[Dict[str, Any]]:
    """Get question IDs from a question set for exam purposes"""
    
    # First, get the question set and validate access
    service = get_question_set_service(db)
    question_set = await service.get_question_set_detail(question_set_id, user_id)
    
    if not question_set:
        return None
    
    # Check if user has view permission
    if not question_set["current_user_permissions"]["can_view"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this question set"
        )
    
    # Get question IDs from the question set (already in the correct order)
    question_ids = question_set.get("question_ids", [])
    
    return {
        "question_set_id": question_set_id,
        "question_set_name": question_set["name"],
        "total_questions": len(question_ids),
        "question_ids": question_ids
    }

# ==============================================================================
# CACHE MANAGEMENT FUNCTIONS
# ==============================================================================

async def invalidate_question_sets_cache(
    user_id: Optional[ObjectId] = None,
    question_set_id: Optional[ObjectId] = None
):
    """Invalidate related caches when question sets change"""
    
    if user_id:
        # Invalidate user-specific caches
        await invalidate_cache(f"question_sets:user:{user_id}:*")
        await invalidate_cache(f"user:teaching:{user_id}")
    
    if question_set_id:
        # Invalidate question set detail caches
        await invalidate_cache(f"question_set:detail:{question_set_id}:*")
    
    # Invalidate all question sets caches if major change
    if not user_id and not question_set_id:
        await invalidate_cache(CacheConfig.QUESTION_SETS_PATTERN)
        await invalidate_cache(CacheConfig.USER_TEACHING_PATTERN)

# ==============================================================================
# LEGACY HELPER FUNCTIONS (deprecated, use PermissionChecker instead)
# ==============================================================================

async def _check_edit_permission(question_set: Dict[str, Any], user_id: ObjectId) -> bool:
    """DEPRECATED: Use PermissionChecker.can_edit() instead"""
    checker = PermissionChecker(question_set, user_id)
    return checker.can_edit()

async def _check_publish_permission(question_set: Dict[str, Any], user_id: ObjectId) -> bool:
    """DEPRECATED: Use PermissionChecker.can_publish() instead"""
    checker = PermissionChecker(question_set, user_id)
    return checker.can_publish()

async def _check_manage_questions_permission(question_set: Dict[str, Any], user_id: ObjectId) -> bool:
    """DEPRECATED: Use PermissionChecker.can_manage_questions() instead"""
    checker = PermissionChecker(question_set, user_id)
    return checker.can_manage_questions()

async def _calculate_metadata(db: AsyncIOMotorDatabase, question_ids: List[ObjectId]) -> Dict[str, Any]:
    """DEPRECATED: Use QuestionRepository.calculate_metadata() instead"""
    question_repo = QuestionRepository(db)
    return await question_repo.calculate_metadata(question_ids)