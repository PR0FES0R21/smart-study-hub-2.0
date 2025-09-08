# ==============================================================================
# File: app/crud/score_trend_analytics.py
# Deskripsi: CRUD operations untuk analytics trend nilai ujian
# ==============================================================================

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..api.v1.deps import get_database
from ..schemas.score_trend_analytics import (
    ScoreTrendAnalytics, ScoreTrendSeries, ScoreDataPoint, ScoreTrendRequest
)
import logging

logger = logging.getLogger(__name__)

class ScoreTrendAnalyticsCRUD:
    def __init__(self):
        pass

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        return get_database()

    async def get_score_trend_analytics(
        self,
        request: ScoreTrendRequest,
        current_user: Dict[str, Any]
    ) -> ScoreTrendAnalytics:
        """
        Generate score trend analytics berdasarkan role dan filter
        """
        db = await self._get_db()
        user_roles = current_user.get("roles", [])
        
        # Determine role-based access restrictions
        filters = await self._build_role_based_filters(request, current_user, db)
        
        # Build aggregation pipeline
        pipeline = await self._build_aggregation_pipeline(filters, request)
        
        # Execute aggregation
        cursor = db.exam_sessions.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        # Process results into chart format
        series_data = await self._process_results_to_series(results, request, db)
        
        # Build metadata
        metadata = await self._build_metadata(filters, request, current_user)
        
        return ScoreTrendAnalytics(
            series=series_data,
            metadata=metadata
        )

    async def _build_role_based_filters(
        self, 
        request: ScoreTrendRequest, 
        current_user: Dict[str, Any],
        db: AsyncIOMotorDatabase
    ) -> Dict[str, Any]:
        """Build filters based on user role and permissions"""
        base_filters = {
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None}
        }
        
        user_roles = current_user.get("roles", [])
        user_id = current_user.get("_id")
        
        # Date range filter
        if request.start_date or request.end_date:
            date_filter = {}
            if request.start_date:
                date_filter["$gte"] = request.start_date
            if request.end_date:
                date_filter["$lte"] = request.end_date
            base_filters["submitted_at"] = date_filter
        else:
            # Default: last 3 months
            three_months_ago = datetime.utcnow() - timedelta(days=90)
            base_filters["submitted_at"] = {"$gte": three_months_ago}
        
        if "admin" in user_roles:
            # Admin dapat melihat semua data, tapi bisa difilter
            if request.class_id:
                base_filters["class_id"] = ObjectId(request.class_id)
            if request.grade_level:
                base_filters["grade_level"] = request.grade_level
            if request.student_id:
                base_filters["student_id"] = ObjectId(request.student_id)
            if request.teacher_id:
                base_filters["teacher_id"] = ObjectId(request.teacher_id)
                
        elif "teacher" in user_roles:
            # Teacher hanya bisa lihat kelas yang dia ajar
            teaching_assignments = await db.teaching_assignments.find({
                "teacher_id": ObjectId(user_id)
            }).to_list(length=None)
            
            if not teaching_assignments:
                # Tidak ada teaching assignment, return empty filter
                base_filters["exam_id"] = {"$in": []}
                return base_filters
            
            # Get exam IDs from teaching assignments
            assignment_ids = [ta["_id"] for ta in teaching_assignments]
            exams_cursor = db.exams.find({"teaching_assignment_id": {"$in": assignment_ids}})
            teacher_exams = await exams_cursor.to_list(length=None)
            exam_ids = [exam["_id"] for exam in teacher_exams]
            
            base_filters["exam_id"] = {"$in": exam_ids}
            
            # Apply additional filters if specified
            if request.class_id:
                # Check if teacher teaches this class
                class_assignments = [ta for ta in teaching_assignments 
                                   if str(ta.get("class_id")) == str(request.class_id)]
                if class_assignments:
                    class_exam_ids = []
                    for ta in class_assignments:
                        class_exams = [e for e in teacher_exams 
                                     if str(e.get("teaching_assignment_id")) == str(ta["_id"])]
                        class_exam_ids.extend([e["_id"] for e in class_exams])
                    base_filters["exam_id"] = {"$in": class_exam_ids}
                else:
                    # Teacher doesn't teach this class
                    base_filters["exam_id"] = {"$in": []}
                    
            if request.subject_id:
                # Filter by subject
                subject_assignments = [ta for ta in teaching_assignments 
                                     if str(ta.get("subject_id")) == str(request.subject_id)]
                if subject_assignments:
                    subject_exam_ids = []
                    for ta in subject_assignments:
                        subject_exams = [e for e in teacher_exams 
                                       if str(e.get("teaching_assignment_id")) == str(ta["_id"])]
                        subject_exam_ids.extend([e["_id"] for e in subject_exams])
                    base_filters["exam_id"] = {"$in": subject_exam_ids}
                else:
                    base_filters["exam_id"] = {"$in": []}
                    
        elif "student" in user_roles:
            # Student hanya bisa lihat data pribadi
            base_filters["student_id"] = ObjectId(user_id)
            
            # Ignore most filters for students, only allow date range
            for key in ["class_id", "teacher_id", "subject_id", "expertise_id"]:
                if hasattr(request, key) and getattr(request, key):
                    logger.warning(f"Student tried to access {key} filter - ignored")
                    
        else:
            # Unknown role, deny access
            base_filters["exam_id"] = {"$in": []}
            
        return base_filters

    async def _build_aggregation_pipeline(
        self, 
        filters: Dict[str, Any], 
        request: ScoreTrendRequest
    ) -> List[Dict[str, Any]]:
        """Build MongoDB aggregation pipeline with proper grouping"""
        pipeline = []
        
        # Match stage with filters
        pipeline.append({"$match": filters})
        
        # Lookup exam details
        pipeline.append({
            "$lookup": {
                "from": "exams",
                "localField": "exam_id",
                "foreignField": "_id",
                "as": "exam"
            }
        })
        
        # Unwind exam
        pipeline.append({"$unwind": "$exam"})
        
        # Lookup teaching assignment
        pipeline.append({
            "$lookup": {
                "from": "teaching_assignments",
                "localField": "exam.teaching_assignment_id",
                "foreignField": "_id",
                "as": "teaching_assignment"
            }
        })
        
        # Unwind teaching assignment (might not exist for old exams)
        pipeline.append({
            "$unwind": {
                "path": "$teaching_assignment",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Lookup class info
        pipeline.append({
            "$lookup": {
                "from": "classes",
                "localField": "teaching_assignment.class_id",
                "foreignField": "_id",
                "as": "class"
            }
        })
        
        # Unwind class
        pipeline.append({
            "$unwind": {
                "path": "$class",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Lookup subject info
        pipeline.append({
            "$lookup": {
                "from": "subjects",
                "localField": "teaching_assignment.subject_id",
                "foreignField": "_id",
                "as": "subject"
            }
        })
        
        # Unwind subject
        pipeline.append({
            "$unwind": {
                "path": "$subject",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Lookup teacher profile
        pipeline.append({
            "$lookup": {
                "from": "users",
                "localField": "teaching_assignment.teacher_id",
                "foreignField": "_id",
                "as": "teacher"
            }
        })
        
        pipeline.append({
            "$unwind": {
                "path": "$teacher",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Lookup teacher profile details
        pipeline.append({
            "$lookup": {
                "from": "profiles",
                "localField": "teacher.profile_id",
                "foreignField": "_id",
                "as": "teacher_profile"
            }
        })
        
        pipeline.append({
            "$unwind": {
                "path": "$teacher_profile",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Lookup expertise program details
        pipeline.append({
            "$lookup": {
                "from": "expertise_programs",
                "localField": "class.expertise_id",
                "foreignField": "_id",
                "as": "expertise_program"
            }
        })
        
        pipeline.append({
            "$unwind": {
                "path": "$expertise_program",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Add date formatting for grouping
        pipeline.append({
            "$addFields": {
                "exam_date": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$submitted_at"
                    }
                }
            }
        })
        
        # Group stage - this is the key difference!
        group_stage = self._build_group_stage(request)
        pipeline.append(group_stage)
        
        # Sort by date
        pipeline.append({"$sort": {"exam_date": 1}})
        
        return pipeline
    
    def _build_group_stage(self, request: ScoreTrendRequest) -> Dict[str, Any]:
        """Build the group stage based on group_by parameter"""
        
        group_id = {"exam_date": "$exam_date", "exam_id": "$exam._id"}
        
        # Add grouping field based on request
        if request.group_by == "class":
            group_id["class_id"] = "$class._id"
        elif request.group_by == "grade":
            group_id["grade_level"] = "$class.grade_level"
        elif request.group_by == "subject":
            group_id["subject_id"] = "$subject._id"
        elif request.group_by == "teacher":
            group_id["teacher_id"] = "$teacher._id"
        elif request.group_by == "student":
            group_id["student_id"] = "$student_id"
        
        return {
            "$group": {
                "_id": group_id,
                "avg_score": {"$avg": "$score"},
                "student_count": {"$sum": 1},
                "exam_title": {"$first": "$exam.title"},
                "exam_date": {"$first": "$submitted_at"},
                "class_id": {"$first": "$class._id"},
                "class_name": {"$first": "$class.name"},
                "grade_level": {"$first": "$class.grade_level"},
                "subject_id": {"$first": "$subject._id"},
                "subject_name": {"$first": "$subject.name"},
                "subject_code": {"$first": "$subject.code"},
                "teacher_id": {"$first": "$teacher._id"},
                "teacher_name": {"$first": "$teacher_profile.full_name"},
                "expertise_id": {"$first": "$class.expertise_id"},
                "expertise_name": {"$first": "$expertise_program.name"},
                "expertise_abbreviation": {"$first": "$expertise_program.abbreviation"}
            }
        }

    async def _process_results_to_series(
        self, 
        results: List[Dict], 
        request: ScoreTrendRequest,
        db: AsyncIOMotorDatabase
    ) -> List[ScoreTrendSeries]:
        """Process aggregated results into chart series format"""
        if not results:
            logger.warning("No results found for score trend analytics - empty data")
            return []
        
        logger.info(f"Processing {len(results)} results for score trend series")
        series_dict = {}
        
        for result in results:
            try:
                # Extract aggregated data
                group_key = await self._get_group_key_from_aggregated(result, request)
                
                if group_key not in series_dict:
                    series_dict[group_key] = {
                        "label": group_key,
                        "data": [],
                        "metadata": await self._get_group_metadata_from_aggregated(result, request)
                    }
                
                # Handle date field - check multiple possible formats
                exam_date = result.get("exam_date")
                if exam_date is None:
                    # Try alternative date fields
                    exam_date = result.get("_id", {}).get("exam_date")
                    if exam_date is None:
                        # Use submitted_at or current datetime as fallback
                        exam_date = result.get("submitted_at") or datetime.utcnow()
                
                # Ensure exam_date is datetime object
                if isinstance(exam_date, str):
                    try:
                        exam_date = datetime.fromisoformat(exam_date.replace('Z', '+00:00'))
                    except:
                        exam_date = datetime.utcnow()
                
                # Create data point from aggregated result
                score_value = result.get("avg_score") or result.get("score", 0)
                
                data_point = ScoreDataPoint(
                    date=exam_date,
                    score=float(score_value),
                    exam_id=result["_id"]["exam_id"] if "exam_id" in result["_id"] else result.get("exam_id", ObjectId()),
                    exam_title=result.get("exam_title", "Unknown"),
                    subject_name=result.get("subject_name"),
                    subject_code=result.get("subject_code")
                )
                
                series_dict[group_key]["data"].append(data_point)
                
            except Exception as e:
                logger.warning(f"Error processing result item: {e}. Skipping this result.")
                continue
        
        # Convert to list of series and sort data points by date
        series_list = []
        for key, series_data in series_dict.items():
            # Sort data points by date
            series_data["data"].sort(key=lambda x: x.date)
            
            series_list.append(ScoreTrendSeries(
                label=series_data["label"],
                data=series_data["data"],
                metadata=series_data["metadata"]
            ))
        
        logger.info(f"Generated {len(series_list)} series for score trend chart")
        return series_list

    async def _get_group_key_from_aggregated(self, result: Dict, request: ScoreTrendRequest) -> str:
        """Get the grouping key from aggregated data based on group_by parameter"""
        group_by = request.group_by
        
        if group_by == "class":
            class_name = result.get("class_name", "Unknown")
            grade_level = result.get("grade_level", "")
            expertise_abbr = result.get("expertise_abbreviation", "")
            
            if grade_level and expertise_abbr and class_name:
                return f"Kelas {grade_level} {expertise_abbr} {class_name}"
            elif grade_level and class_name:
                return f"Kelas {grade_level}-{class_name}"  # Fallback jika expertise tidak ada
            else:
                return class_name or "Unknown Class"
            
        elif group_by == "subject":
            return result.get("subject_name", "Unknown Subject")
            
        elif group_by == "grade":
            grade_level = result.get("grade_level", "Unknown")
            return f"Kelas {grade_level}"
            
        elif group_by == "teacher":
            return result.get("teacher_name", "Unknown Teacher")
            
        elif group_by == "student":
            # For student grouping, we'd need to lookup student name from _id
            student_id = result["_id"].get("student_id", "Unknown")
            return f"Student {student_id}"
            
        else:
            return "Data"

    async def _get_group_metadata_from_aggregated(self, result: Dict, request: ScoreTrendRequest) -> Dict[str, Any]:
        """Get metadata for the group from aggregated data"""
        metadata = {
            "student_count": result.get("student_count", 0)  # Number of students in this group
        }
        
        if request.group_by == "class":
            metadata.update({
                "class_id": str(result.get("class_id", "")),
                "grade_level": result.get("grade_level"),
                "expertise_id": str(result.get("expertise_id", "")),
                "expertise_name": result.get("expertise_name"),
                "expertise_abbreviation": result.get("expertise_abbreviation")
            })
        elif request.group_by == "subject":
            metadata.update({
                "subject_id": str(result.get("subject_id", "")),
                "subject_code": result.get("subject_code")
            })
        elif request.group_by == "teacher":
            metadata.update({
                "teacher_id": str(result.get("teacher_id", ""))
            })
        elif request.group_by == "student":
            student_id = result["_id"].get("student_id", "")
            metadata.update({
                "student_id": str(student_id)
            })
        elif request.group_by == "grade":
            metadata.update({
                "grade_level": result.get("grade_level"),
                "total_classes": 1  # Could be enhanced to count unique classes
            })
        
        return metadata
        
    # Keep old functions for backward compatibility if needed
    async def _get_group_key(self, result: Dict, request: ScoreTrendRequest) -> str:
        """Get the grouping key based on group_by parameter (legacy)"""
        return await self._get_group_key_from_aggregated(result, request)

    async def _get_group_metadata(self, result: Dict, request: ScoreTrendRequest) -> Dict[str, Any]:
        """Get metadata for the group (legacy)"""
        return await self._get_group_metadata_from_aggregated(result, request)

    async def _build_metadata(
        self, 
        filters: Dict[str, Any], 
        request: ScoreTrendRequest, 
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build response metadata"""
        metadata = {
            "user_role": current_user.get("roles", []),
            "group_by": request.group_by,
            "filters_applied": {}
        }
        
        # Add applied filters to metadata
        if "submitted_at" in filters:
            date_filter = filters["submitted_at"]
            metadata["filters_applied"]["date_range"] = {
                "start": date_filter.get("$gte"),
                "end": date_filter.get("$lte")
            }
        
        if request.class_id:
            metadata["filters_applied"]["class_id"] = str(request.class_id)
        if request.grade_level:
            metadata["filters_applied"]["grade_level"] = request.grade_level
        if request.subject_id:
            metadata["filters_applied"]["subject_id"] = str(request.subject_id)
        if request.teacher_id:
            metadata["filters_applied"]["teacher_id"] = str(request.teacher_id)
        if request.student_id:
            metadata["filters_applied"]["student_id"] = str(request.student_id)
        
        metadata["generated_at"] = datetime.utcnow()
        
        return metadata

# Create instance
score_trend_crud = ScoreTrendAnalyticsCRUD()
