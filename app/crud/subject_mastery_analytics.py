# ==============================================================================
# File: app/crud/subject_mastery_analytics.py
# Deskripsi: High-performance CRUD untuk Subject Mastery Analytics
# Focus: Minimal queries, optimal aggregation, smart caching
# ==============================================================================

from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
import logging
import hashlib
import json

from ..api.v1.deps import get_database
from ..core.cache import get_cache, set_cache
from ..schemas.subject_mastery_analytics import (
    SubjectMasteryAnalytics, MultiEntityMasteryAnalytics, SubjectMasteryRequest,
    SubjectMasteryData, StudentMasteryResponse, ClassMasteryResponse, SchoolMasteryResponse
)

logger = logging.getLogger(__name__)

class SubjectMasteryAnalyticsCRUD:
    def __init__(self):
        self.cache_ttl = 900  # 15 minutes cache
        
    async def _get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        return get_database()

    def _generate_cache_key(self, request: SubjectMasteryRequest, user_role: List[str], user_id: str) -> str:
        """Generate unique cache key untuk request"""
        # Create deterministic hash dari request parameters
        cache_data = {
            "user_id": user_id,
            "user_role": sorted(user_role),
            "student_id": str(request.student_id) if request.student_id else None,
            "class_id": str(request.class_id) if request.class_id else None,
            "grade_level": request.grade_level,
            "expertise_id": str(request.expertise_id) if request.expertise_id else None,
            "start_date": request.start_date.isoformat() if request.start_date else None,
            "end_date": request.end_date.isoformat() if request.end_date else None,
            "academic_period_id": str(request.academic_period_id) if request.academic_period_id else None,
            "min_exams": request.min_exams_per_subject,
            "include_zero": request.include_zero_scores
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_str.encode()).hexdigest()
        return f"subject_mastery:{cache_hash}"

    async def get_subject_mastery_analytics(
        self,
        request: SubjectMasteryRequest,
        current_user: Dict[str, Any]
    ) -> Union[StudentMasteryResponse, ClassMasteryResponse, SchoolMasteryResponse]:
        """
        Main entry point - performance optimized dengan smart caching
        """
        user_roles = current_user.get("roles", [])
        user_id = str(current_user.get("_id", ""))
        
        # Try cache first (if enabled)
        if request.use_cache:
            cache_key = self._generate_cache_key(request, user_roles, user_id)
            cached_result = await get_cache(cache_key)
            if cached_result:
                logger.info(f"Cache HIT untuk subject mastery analytics: {cache_key[:12]}...")
                return self._deserialize_cached_result(cached_result)
        
        # Apply role-based restrictions
        filters = await self._build_role_based_filters(request, current_user)
        
        # Route to appropriate handler based on role and request
        if "student" in user_roles:
            result = await self._get_student_mastery(filters, current_user)
        elif "teacher" in user_roles:
            result = await self._get_teacher_mastery(filters, request, current_user)
        elif "admin" in user_roles:
            result = await self._get_admin_mastery(filters, request, current_user)
        else:
            raise PermissionError("Invalid user role for analytics access")
        
        # Cache result if enabled
        if request.use_cache:
            cache_key = self._generate_cache_key(request, user_roles, user_id)
            await set_cache(cache_key, self._serialize_for_cache(result), ttl=self.cache_ttl)
            logger.info(f"Cache SET untuk subject mastery analytics: {cache_key[:12]}...")
        
        return result

    async def _build_role_based_filters(
        self, 
        request: SubjectMasteryRequest, 
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build optimized filters berdasarkan role dengan early filtering"""
        base_filters = {
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        }
        
        user_roles = current_user.get("roles", [])
        user_id = current_user.get("_id")
        
        # Date filtering (apply early untuk performance)
        if request.start_date or request.end_date:
            date_filter = {}
            if request.start_date:
                date_filter["$gte"] = request.start_date
            if request.end_date:
                date_filter["$lte"] = request.end_date
            base_filters["submitted_at"] = date_filter
        else:
            # Default: current academic year (performance optimization)
            current_year = datetime.now().year
            academic_start = datetime(current_year, 7, 1)  # July start
            base_filters["submitted_at"] = {"$gte": academic_start}
        
        # Role-specific filtering (most restrictive first)
        if "student" in user_roles:
            # Most restrictive - only own data
            base_filters["student_id"] = ObjectId(user_id)
            logger.debug(f"Student filter applied: {user_id}")
            
        elif "teacher" in user_roles:
            # Get teaching assignments efficiently (single query)
            db = await self._get_db()
            teaching_assignments = await db.teaching_assignments.find(
                {"teacher_id": ObjectId(user_id)},
                {"_id": 1}  # Projection - only get IDs
            ).to_list(length=None)
            
            if not teaching_assignments:
                # No assignments = no data
                base_filters["exam_id"] = {"$in": []}
                return base_filters
            
            # Get exam IDs efficiently
            assignment_ids = [ta["_id"] for ta in teaching_assignments]
            exam_cursor = db.exams.find(
                {"teaching_assignment_id": {"$in": assignment_ids}},
                {"_id": 1}  # Projection
            )
            teacher_exams = await exam_cursor.to_list(length=None)
            exam_ids = [exam["_id"] for exam in teacher_exams]
            
            base_filters["exam_id"] = {"$in": exam_ids}
            
            # Apply additional filters if specified
            if request.class_id:
                # Validate teacher has access to this class
                class_assignments = await db.teaching_assignments.find({
                    "teacher_id": ObjectId(user_id),
                    "class_id": ObjectId(request.class_id)
                }).to_list(length=1)
                
                if not class_assignments:
                    base_filters["exam_id"] = {"$in": []}  # No access
                
        elif "admin" in user_roles:
            # Admin filters (applied if specified)
            if request.student_id:
                base_filters["student_id"] = ObjectId(request.student_id)
            if request.class_id:
                base_filters["class_id"] = ObjectId(request.class_id)
            if request.grade_level:
                base_filters["grade_level"] = request.grade_level
        
        return base_filters

    async def _get_student_mastery(
        self, 
        filters: Dict[str, Any], 
        current_user: Dict[str, Any]
    ) -> StudentMasteryResponse:
        """Optimized student mastery - single aggregation pipeline"""
        db = await self._get_db()
        
        # Single optimized pipeline untuk student
        pipeline = [
            {"$match": filters},
            
            # Essential lookups only
            {
                "$lookup": {
                    "from": "exams",
                    "localField": "exam_id",
                    "foreignField": "_id",
                    "as": "exam",
                    "pipeline": [
                        {"$project": {"teaching_assignment_id": 1}}  # Minimal projection
                    ]
                }
            },
            {"$unwind": "$exam"},
            
            {
                "$lookup": {
                    "from": "teaching_assignments",
                    "localField": "exam.teaching_assignment_id", 
                    "foreignField": "_id",
                    "as": "teaching_assignment",
                    "pipeline": [
                        {"$project": {"subject_id": 1}}  # Minimal projection
                    ]
                }
            },
            {"$unwind": "$teaching_assignment"},
            
            {
                "$lookup": {
                    "from": "subjects",
                    "localField": "teaching_assignment.subject_id",
                    "foreignField": "_id", 
                    "as": "subject",
                    "pipeline": [
                        {"$project": {"name": 1}}  # Only name needed
                    ]
                }
            },
            {"$unwind": "$subject"},
            
            # Group by subject untuk calculate averages
            {
                "$group": {
                    "_id": "$subject.name",
                    "avg_score": {"$avg": "$score"},
                    "exam_count": {"$sum": 1},
                    "total_score": {"$sum": "$score"}
                }
            },
            
            # Filter by minimum exams threshold
            {
                "$match": {
                    "exam_count": {"$gte": 1}  # At least 1 exam per subject
                }
            },
            
            # Sort untuk consistent output
            {"$sort": {"_id": 1}}
        ]
        
        cursor = db.exam_sessions.aggregate(pipeline, allowDiskUse=False)  # Force memory usage for speed
        results = await cursor.to_list(length=None)
        
        # Process results into response format
        subject_scores = {}
        total_score = 0
        total_exams = 0
        
        for result in results:
            subject_name = result["_id"]
            avg_score = round(result["avg_score"], 1)
            exam_count = result["exam_count"]
            
            subject_scores[subject_name] = avg_score
            total_score += result["total_score"]
            total_exams += exam_count
        
        overall_average = round(total_score / total_exams, 1) if total_exams > 0 else 0
        
        # Get student profile for display name
        profile = await db.profiles.find_one(
            {"user_id": current_user["_id"]},
            {"full_name": 1}
        )
        student_name = profile.get("full_name", "Student") if profile else "Student"
        
        mastery_data = SubjectMasteryData(
            subject_scores=subject_scores,
            overall_average=overall_average,
            total_exams=total_exams
        )
        
        return StudentMasteryResponse(
            entity_id=str(current_user["_id"]),
            entity_type="student",
            entity_name=student_name,
            mastery_data=mastery_data,
            metadata={
                "generated_at": datetime.utcnow(),
                "cache_duration": "15min",
                "user_role": current_user.get("roles", []),
                "total_subjects": len(subject_scores)
            }
        )

    async def _get_teacher_mastery(
        self,
        filters: Dict[str, Any],
        request: SubjectMasteryRequest,
        current_user: Dict[str, Any]
    ) -> ClassMasteryResponse:
        """Optimized teacher mastery - class averages"""
        db = await self._get_db()
        
        # If specific student requested, return single student
        if request.student_id:
            student_filters = filters.copy()
            student_filters["student_id"] = ObjectId(request.student_id)
            return await self._get_single_student_mastery(student_filters, request.student_id, db)
        
        # Otherwise return class-level aggregation
        pipeline = await self._build_class_aggregation_pipeline(filters)
        
        cursor = db.exam_sessions.aggregate(pipeline, allowDiskUse=False)
        results = await cursor.to_list(length=None)
        
        # Process results ke multiple entities
        entities = await self._process_class_results(results, db)
        
        # Calculate comparison metadata
        comparison_metadata = self._calculate_comparison_metadata(entities)
        
        return ClassMasteryResponse(
            entities=entities,
            comparison_metadata=comparison_metadata
        )

    async def _get_admin_mastery(
        self,
        filters: Dict[str, Any],
        request: SubjectMasteryRequest, 
        current_user: Dict[str, Any]
    ) -> SchoolMasteryResponse:
        """Optimized admin mastery - school-wide analysis"""
        db = await self._get_db()
        
        # Route berdasarkan request specificity
        if request.student_id:
            return await self._get_single_student_mastery(filters, request.student_id, db)
        elif request.class_id:
            return await self._get_single_class_mastery(filters, request.class_id, db)
        elif request.grade_level:
            return await self._get_grade_mastery(filters, request.grade_level, db)
        else:
            return await self._get_school_wide_mastery(filters, db)

    async def _build_class_aggregation_pipeline(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build efficient pipeline untuk class-level aggregation"""
        return [
            {"$match": filters},
            
            # Lookup dengan projection untuk minimize data transfer
            {
                "$lookup": {
                    "from": "exams",
                    "localField": "exam_id",
                    "foreignField": "_id",
                    "as": "exam",
                    "pipeline": [{"$project": {"teaching_assignment_id": 1}}]
                }
            },
            {"$unwind": "$exam"},
            
            {
                "$lookup": {
                    "from": "teaching_assignments",
                    "localField": "exam.teaching_assignment_id",
                    "foreignField": "_id",
                    "as": "ta",
                    "pipeline": [{"$project": {"subject_id": 1, "class_id": 1}}]
                }
            },
            {"$unwind": "$ta"},
            
            {
                "$lookup": {
                    "from": "subjects",
                    "localField": "ta.subject_id",
                    "foreignField": "_id",
                    "as": "subject",
                    "pipeline": [{"$project": {"name": 1}}]
                }
            },
            {"$unwind": "$subject"},
            
            {
                "$lookup": {
                    "from": "classes",
                    "localField": "ta.class_id",
                    "foreignField": "_id",
                    "as": "class",
                    "pipeline": [{"$project": {"name": 1, "grade_level": 1, "expertise_id": 1}}]
                }
            },
            {"$unwind": "$class"},
            
            # Group by class dan subject
            {
                "$group": {
                    "_id": {
                        "class_id": "$ta.class_id",
                        "subject_name": "$subject.name"
                    },
                    "avg_score": {"$avg": "$score"},
                    "exam_count": {"$sum": 1},
                    "class_name": {"$first": "$class.name"},
                    "grade_level": {"$first": "$class.grade_level"},
                    "expertise_id": {"$first": "$class.expertise_id"}
                }
            },
            
            {"$sort": {"_id.class_id": 1, "_id.subject_name": 1}}
        ]

    async def _process_class_results(self, results: List[Dict], db: AsyncIOMotorDatabase) -> List[SubjectMasteryAnalytics]:
        """Process aggregation results into entities"""
        class_data = {}
        
        # Group by class
        for result in results:
            class_id = str(result["_id"]["class_id"])
            subject_name = result["_id"]["subject_name"]
            avg_score = round(result["avg_score"], 1)
            
            if class_id not in class_data:
                class_data[class_id] = {
                    "subjects": {},
                    "total_score": 0,
                    "total_exams": 0,
                    "class_name": result["class_name"],
                    "grade_level": result["grade_level"],
                    "expertise_id": result.get("expertise_id")
                }
            
            class_data[class_id]["subjects"][subject_name] = avg_score
            class_data[class_id]["total_score"] += result["avg_score"] * result["exam_count"]
            class_data[class_id]["total_exams"] += result["exam_count"]
        
        # Convert to entities
        entities = []
        for class_id, data in class_data.items():
            overall_avg = round(data["total_score"] / data["total_exams"], 1) if data["total_exams"] > 0 else 0
            
            # Get expertise abbreviation if available
            class_name = f"Kelas {data['grade_level']}"
            if data.get("expertise_id"):
                expertise = await db.expertise_programs.find_one(
                    {"_id": data["expertise_id"]},
                    {"abbreviation": 1}
                )
                if expertise:
                    class_name = f"Kelas {data['grade_level']} {expertise['abbreviation']} {data['class_name']}"
                else:
                    class_name = f"Kelas {data['grade_level']}-{data['class_name']}"
            else:
                class_name = f"Kelas {data['grade_level']}-{data['class_name']}"
            
            mastery_data = SubjectMasteryData(
                subject_scores=data["subjects"],
                overall_average=overall_avg,
                total_exams=data["total_exams"]
            )
            
            entity = SubjectMasteryAnalytics(
                entity_id=class_id,
                entity_type="class",
                entity_name=class_name,
                mastery_data=mastery_data
            )
            
            entities.append(entity)
        
        return entities

    def _calculate_comparison_metadata(self, entities: List[SubjectMasteryAnalytics]) -> Dict[str, Any]:
        """Calculate comparison metadata untuk entities"""
        if not entities:
            return {}
        
        all_averages = [e.mastery_data.overall_average for e in entities]
        all_subjects = set()
        subject_totals = {}
        
        for entity in entities:
            for subject, score in entity.mastery_data.subject_scores.items():
                all_subjects.add(subject)
                if subject not in subject_totals:
                    subject_totals[subject] = {"total": 0, "count": 0}
                subject_totals[subject]["total"] += score
                subject_totals[subject]["count"] += 1
        
        # Find best and worst subjects
        subject_averages = {
            subj: data["total"] / data["count"] 
            for subj, data in subject_totals.items() if data["count"] > 0
        }
        
        best_subject = max(subject_averages.items(), key=lambda x: x[1])[0] if subject_averages else "N/A"
        worst_subject = min(subject_averages.items(), key=lambda x: x[1])[0] if subject_averages else "N/A"
        
        return {
            "total_entities": len(entities),
            "school_average": round(sum(all_averages) / len(all_averages), 1),
            "highest_average": round(max(all_averages), 1),
            "lowest_average": round(min(all_averages), 1),
            "total_subjects": len(all_subjects),
            "best_subject": best_subject,
            "weakest_subject": worst_subject,
            "subject_averages": {k: round(v, 1) for k, v in subject_averages.items()}
        }

    async def _get_single_student_mastery(self, filters: Dict[str, Any], student_id: ObjectId, db: AsyncIOMotorDatabase) -> StudentMasteryResponse:
        """Get mastery untuk single student (helper)"""
        # Implementation similar to _get_student_mastery but dengan student_id override
        pass

    def _serialize_for_cache(self, result: Any) -> Dict[str, Any]:
        """Serialize result untuk caching"""
        if hasattr(result, 'dict'):
            return result.dict()
        return result

    def _deserialize_cached_result(self, cached_data: Dict[str, Any]) -> Any:
        """Deserialize cached result"""
        # Determine type dari cached data dan return appropriate response type
        if "entities" in cached_data:
            if cached_data.get("comparison_metadata", {}).get("total_entities", 0) <= 5:
                return ClassMasteryResponse(**cached_data)
            else:
                return SchoolMasteryResponse(**cached_data)
        else:
            return StudentMasteryResponse(**cached_data)

# Create singleton instance
subject_mastery_crud = SubjectMasteryAnalyticsCRUD()
