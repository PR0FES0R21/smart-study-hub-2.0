# ==============================================================================
# File: app/core/export_query_builder.py
# Deskripsi: Core query builder untuk flexible export system
# ==============================================================================
from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime
import re
import logging

from app.schemas.export import (
    ExportConfig, FilterCondition, JoinConfig, FilterOperator
)

logger = logging.getLogger(__name__)

class ExportQueryBuilder:
    """Builder untuk membuat MongoDB aggregation pipeline dari ExportConfig"""
    
    def __init__(self):
        self.pipeline = []
        
    def _convert_filter_value(self, value: Any, operator: FilterOperator) -> Any:
        """Convert filter value to appropriate MongoDB type"""
        if value is None:
            return None
            
        # Handle ObjectId conversion for _id fields
        if isinstance(value, str):
            # Try to convert string to ObjectId if it looks like one
            if re.match(r'^[0-9a-fA-F]{24}$', value):
                try:
                    return ObjectId(value)
                except Exception:
                    pass
            
            # Handle date string conversion
            if operator in [FilterOperator.GT, FilterOperator.GTE, FilterOperator.LT, FilterOperator.LTE]:
                try:
                    # Try to parse as ISO date
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except Exception:
                    pass
        
        # Handle array values for IN/NIN operators
        if operator in [FilterOperator.IN, FilterOperator.NIN]:
            if not isinstance(value, list):
                value = [value]
            
            # Convert each item in array
            converted_array = []
            for item in value:
                if isinstance(item, str) and re.match(r'^[0-9a-fA-F]{24}$', item):
                    try:
                        converted_array.append(ObjectId(item))
                    except Exception:
                        converted_array.append(item)
                else:
                    converted_array.append(item)
            return converted_array
        
        return value
    
    def _build_filter_condition(self, filter_cond: FilterCondition, field_prefix: str = "") -> Dict[str, Any]:
        """Build MongoDB filter condition from FilterCondition"""
        field_name = f"{field_prefix}.{filter_cond.field}" if field_prefix else filter_cond.field
        value = self._convert_filter_value(filter_cond.value, filter_cond.operator)
        
        operator_map = {
            FilterOperator.EQ: lambda v: {field_name: v},
            FilterOperator.NE: lambda v: {field_name: {"$ne": v}},
            FilterOperator.GT: lambda v: {field_name: {"$gt": v}},
            FilterOperator.GTE: lambda v: {field_name: {"$gte": v}},
            FilterOperator.LT: lambda v: {field_name: {"$lt": v}},
            FilterOperator.LTE: lambda v: {field_name: {"$lte": v}},
            FilterOperator.IN: lambda v: {field_name: {"$in": v}},
            FilterOperator.NIN: lambda v: {field_name: {"$nin": v}},
            FilterOperator.EXISTS: lambda v: {field_name: {"$exists": bool(v)}},
            FilterOperator.REGEX: lambda v: {field_name: {"$regex": v, "$options": filter_cond.options or "i"}}
        }
        
        if filter_cond.operator in operator_map:
            return operator_map[filter_cond.operator](value)
        else:
            logger.warning(f"Unknown filter operator: {filter_cond.operator}")
            return {field_name: value}  # Default to equality
    
    def _build_match_stage(self, filters: List[FilterCondition], field_prefix: str = "") -> Dict[str, Any]:
        """Build $match stage from list of filter conditions"""
        if not filters:
            return {}
        
        conditions = []
        for filter_cond in filters:
            condition = self._build_filter_condition(filter_cond, field_prefix)
            conditions.append(condition)
        
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def _build_lookup_stage(self, join: JoinConfig) -> List[Dict[str, Any]]:
        """Build $lookup and optional $unwind stages for a join"""
        stages = []
        
        # Basic lookup stage
        lookup_stage = {
            "$lookup": {
                "from": join.collection,
                "localField": join.local_field,
                "foreignField": join.foreign_field,
                "as": join.alias or join.collection
            }
        }
        stages.append(lookup_stage)
        
        # Add filters to lookup if specified
        if join.filters:
            lookup_stage["$lookup"]["pipeline"] = [
                {"$match": self._build_match_stage(join.filters)}
            ]
        
        # Add unwind if specified
        if join.join_type == "unwind":
            unwind_stage = {
                "$unwind": {
                    "path": f"${join.alias or join.collection}",
                    "preserveNullAndEmptyArrays": True
                }
            }
            stages.append(unwind_stage)
        
        return stages
    
    def _build_projection_stage(self, config: ExportConfig) -> Dict[str, Any]:
        """Build $project stage to select only required fields"""
        projection = {"_id": 1}  # Always include _id
        
        # Add fields from main collection
        for field in config.fields:
            projection[field] = 1
        
        # Add fields from joins
        for join in config.joins:
            alias = join.alias or join.collection
            
            if join.fields:
                # Specific fields from join
                for field in join.fields:
                    projection[f"{alias}.{field}"] = 1
            else:
                # All fields from join
                projection[alias] = 1
        
        return {"$project": projection} if len(projection) > 1 else {}
    
    def _build_sort_stage(self, sort_config: Dict[str, int]) -> Dict[str, Any]:
        """Build $sort stage from sort configuration"""
        if not sort_config:
            return {}
        
        return {"$sort": sort_config}
    
    def build_pipeline(self, config: ExportConfig) -> List[Dict[str, Any]]:
        """Build complete aggregation pipeline from ExportConfig"""
        pipeline = []
        
        # 1. Initial match stage for main collection filters
        if config.filters:
            match_stage = {"$match": self._build_match_stage(config.filters)}
            pipeline.append(match_stage)
        
        # 2. Add lookup stages for joins
        for join in config.joins:
            lookup_stages = self._build_lookup_stage(join)
            pipeline.extend(lookup_stages)
        
        # 3. Add projection stage if fields are specified
        projection_stage = self._build_projection_stage(config)
        if projection_stage:
            pipeline.append(projection_stage)
        
        # 4. Add sort stage
        sort_stage = self._build_sort_stage(config.sort)
        if sort_stage:
            pipeline.append(sort_stage)
        
        # 5. Add skip stage
        if config.skip and config.skip > 0:
            pipeline.append({"$skip": config.skip})
        
        # 6. Add limit stage
        if config.limit:
            pipeline.append({"$limit": config.limit})
        
        logger.info(f"Generated pipeline with {len(pipeline)} stages for collection '{config.main_collection}'")
        return pipeline
    
    def estimate_result_count(self, db, config: ExportConfig) -> Optional[int]:
        """Estimate the number of results that would be returned"""
        try:
            # Build pipeline without limit and skip for counting
            count_pipeline = []
            
            # Add initial match stage
            if config.filters:
                match_stage = {"$match": self._build_match_stage(config.filters)}
                count_pipeline.append(match_stage)
            
            # Add joins (they might filter results)
            for join in config.joins:
                lookup_stages = self._build_lookup_stage(join)
                count_pipeline.extend(lookup_stages)
            
            # Add count stage
            count_pipeline.append({"$count": "total"})
            
            # Execute count pipeline
            result = db[config.main_collection].aggregate(count_pipeline).to_list(1)
            
            if result and len(result) > 0:
                estimated_count = result[0]["total"]
                
                # Apply limit if specified
                if config.limit:
                    estimated_count = min(estimated_count, config.limit)
                
                return estimated_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error estimating result count: {e}")
            return None
    
    def validate_pipeline(self, pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the generated pipeline for common issues"""
        issues = []
        warnings = []
        
        # Check for too many stages
        if len(pipeline) > 10:
            warnings.append(f"Pipeline has many stages ({len(pipeline)}), may impact performance")
        
        # Check for multiple lookups
        lookup_count = sum(1 for stage in pipeline if "$lookup" in stage)
        if lookup_count > 3:
            warnings.append(f"Multiple lookups ({lookup_count}) may impact performance")
        
        # Check for missing indexes (basic heuristic)
        match_stages = [stage for stage in pipeline if "$match" in stage]
        if len(match_stages) > 1:
            warnings.append("Multiple $match stages - consider combining or adding indexes")
        
        # Check for large limits
        for stage in pipeline:
            if "$limit" in stage and stage["$limit"] > 10000:
                warnings.append(f"Large limit ({stage['$limit']}) may cause memory issues")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

# Utility functions for common use cases
def build_student_grades_pipeline(class_id: str = None, grade_level: int = None) -> List[Dict[str, Any]]:
    """Pre-built pipeline for student grades export"""
    config = ExportConfig(
        main_collection="users",
        fields=["_id", "username"],
        filters=[
            FilterCondition(field="roles", operator=FilterOperator.EQ, value="student")
        ],
        joins=[
            JoinConfig(
                collection="profiles",
                local_field="profile_id",
                foreign_field="_id",
                fields=["full_name", "class_id"],
                join_type="unwind"
            ),
            JoinConfig(
                collection="classes", 
                local_field="profiles.class_id",
                foreign_field="_id",
                fields=["name", "grade_level"],
                join_type="unwind",
                filters=[
                    FilterCondition(field="grade_level", operator=FilterOperator.EQ, value=grade_level)
                ] if grade_level else []
            ),
            JoinConfig(
                collection="exam_sessions",
                local_field="_id", 
                foreign_field="student_id",
                fields=["score", "exam_id", "status"],
                filters=[
                    FilterCondition(field="status", operator=FilterOperator.EQ, value="graded")
                ]
            )
        ],
        sort={"profiles.full_name": 1}
    )
    
    builder = ExportQueryBuilder()
    return builder.build_pipeline(config)

def build_teacher_assignments_pipeline(academic_period_id: str = None) -> List[Dict[str, Any]]:
    """Pre-built pipeline for teacher assignments export"""
    config = ExportConfig(
        main_collection="users",
        fields=["_id", "username", "email"],
        filters=[
            FilterCondition(field="roles", operator=FilterOperator.EQ, value="teacher")
        ],
        joins=[
            JoinConfig(
                collection="profiles",
                local_field="profile_id",
                foreign_field="_id", 
                fields=["full_name"],
                join_type="unwind"
            ),
            JoinConfig(
                collection="teaching_assignments",
                local_field="_id",
                foreign_field="teacher_id",
                fields=["subject_id", "class_id"],
                filters=[
                    FilterCondition(field="academic_period_id", operator=FilterOperator.EQ, value=academic_period_id)
                ] if academic_period_id else []
            ),
            JoinConfig(
                collection="subjects",
                local_field="teaching_assignments.subject_id",
                foreign_field="_id",
                fields=["name", "code"],
                join_type="unwind"
            ),
            JoinConfig(
                collection="classes",
                local_field="teaching_assignments.class_id", 
                foreign_field="_id",
                fields=["name", "grade_level"],
                join_type="unwind"
            )
        ],
        sort={"profiles.full_name": 1}
    )
    
    builder = ExportQueryBuilder()
    return builder.build_pipeline(config)
