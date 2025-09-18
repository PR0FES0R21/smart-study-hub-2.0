# ==============================================================================
# File: app/core/advanced_query_builder.py
# Deskripsi: Advanced query builder untuk nested joins dan complex filtering
# ==============================================================================
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
from datetime import datetime
import re
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.admin_export import (
    AdvancedExportConfig, AdvancedJoinConfig, AdvancedFilterCondition,
    QueryComplexity, JoinPath
)
from app.schemas.export import FilterOperator

logger = logging.getLogger(__name__)

class AdvancedExportQueryBuilder:
    """Advanced query builder dengan unlimited nested join capability"""
    
    def __init__(self):
        self.pipeline = []
        self.complexity_score = 0
        self.join_paths = []
        self.collections_used = set()
        
    def _convert_filter_value(self, value: Any, operator: FilterOperator) -> Any:
        """Convert filter value to appropriate MongoDB type dengan enhanced support"""
        if value is None:
            return None
            
        # Handle ObjectId conversion
        if isinstance(value, str) and re.match(r'^[0-9a-fA-F]{24}$', value):
            try:
                return ObjectId(value)
            except Exception:
                pass
        
        # Handle date string conversion dengan multiple formats
        if operator in [FilterOperator.GT, FilterOperator.GTE, FilterOperator.LT, FilterOperator.LTE]:
            if isinstance(value, str):
                try:
                    # Try ISO format first
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except Exception:
                    try:
                        # Try common date formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                            return datetime.strptime(value, fmt)
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
    
    def _build_advanced_filter_condition(self, filter_cond: AdvancedFilterCondition, 
                                        field_prefix: str = "") -> Dict[str, Any]:
        """Build MongoDB filter condition dengan advanced operator support"""
        field_name = f"{field_prefix}.{filter_cond.field}" if field_prefix else filter_cond.field
        value = self._convert_filter_value(filter_cond.value, filter_cond.operator)
        
        # Enhanced operator mapping
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
            FilterOperator.REGEX: lambda v: {
                field_name: {
                    "$regex": v, 
                    "$options": filter_cond.options or "i"
                }
            }
        }
        
        if filter_cond.operator in operator_map:
            return operator_map[filter_cond.operator](value)
        else:
            logger.warning(f"Unknown filter operator: {filter_cond.operator}")
            return {field_name: value}
    
    def _build_advanced_match_stage(self, filters: List[AdvancedFilterCondition], 
                                   field_prefix: str = "") -> Dict[str, Any]:
        """Build advanced $match stage dengan multiple filter support"""
        if not filters:
            return {}
        
        conditions = []
        for filter_cond in filters:
            condition = self._build_advanced_filter_condition(filter_cond, field_prefix)
            conditions.append(condition)
        
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def _build_nested_lookup_stages(self, join: AdvancedJoinConfig, 
                                   parent_prefix: str = "") -> List[Dict[str, Any]]:
        """Build nested lookup stages dengan recursive join support - FIXED VERSION"""
        stages = []
        alias = join.alias or join.collection
        
        # Build the lookup pipeline for nested operations
        lookup_pipeline = []
        
        # Add filters to lookup pipeline if specified
        if join.filters:
            match_stage = self._build_advanced_match_stage(join.filters)
            if match_stage:
                lookup_pipeline.append({"$match": match_stage})
        
        # Handle nested joins - CRITICAL FIX!
        if join.joins:
            for nested_join in join.joins:
                # Build nested lookup stage
                nested_alias = nested_join.alias or nested_join.collection
                
                nested_lookup = {
                    "$lookup": {
                        "from": nested_join.collection,
                        "localField": nested_join.local_field,
                        "foreignField": nested_join.foreign_field,
                        "as": nested_alias
                    }
                }
                
                # Build nested pipeline for the nested join
                nested_pipeline = []
                
                # Add filters for nested join
                if nested_join.filters:
                    nested_match = self._build_advanced_match_stage(nested_join.filters)
                    if nested_match:
                        nested_pipeline.append({"$match": nested_match})
                
                # Handle deeply nested joins (recursive)
                if nested_join.joins:
                    for deep_join in nested_join.joins:
                        deep_alias = deep_join.alias or deep_join.collection
                        deep_lookup = {
                            "$lookup": {
                                "from": deep_join.collection,
                                "localField": deep_join.local_field,
                                "foreignField": deep_join.foreign_field,
                                "as": deep_alias
                            }
                        }
                        
                        # Add pipeline for deep join if needed
                        deep_pipeline = []
                        if deep_join.filters:
                            deep_match = self._build_advanced_match_stage(deep_join.filters)
                            if deep_match:
                                deep_pipeline.append({"$match": deep_match})
                        
                        if deep_join.fields or deep_join.exclude_fields:
                            deep_projection = {}
                            if deep_join.fields:
                                deep_projection = {field: 1 for field in deep_join.fields}
                                deep_projection["_id"] = 1
                            if deep_join.exclude_fields:
                                for field in deep_join.exclude_fields:
                                    deep_projection[field] = 0
                            if deep_projection:
                                deep_pipeline.append({"$project": deep_projection})
                        
                        if deep_pipeline:
                            deep_lookup["$lookup"]["pipeline"] = deep_pipeline
                        
                        nested_pipeline.append(deep_lookup)
                        
                        # Add unwind for deep join if needed
                        if deep_join.join_type == "unwind":
                            deep_unwind = {
                                "$unwind": {
                                    "path": f"${deep_alias}",
                                    "preserveNullAndEmptyArrays": deep_join.preserve_null_and_empty_arrays
                                }
                            }
                            nested_pipeline.append(deep_unwind)
                        
                        self.collections_used.add(deep_join.collection)
                
                # Add projection for nested join fields
                if nested_join.fields or nested_join.exclude_fields:
                    nested_projection = {}
                    if nested_join.fields:
                        nested_projection = {field: 1 for field in nested_join.fields}
                        nested_projection["_id"] = 1
                        
                        # CRITICAL FIX: Include fields needed for deeply nested joins
                        if nested_join.joins:
                            for deep_join in nested_join.joins:
                                # Add local_field needed for deep join
                                nested_projection[deep_join.local_field] = 1
                                # CRITICAL FIX: Include the nested join result field
                                deep_alias = deep_join.alias or deep_join.collection
                                nested_projection[deep_alias] = 1
                                logger.debug(f"Added field for deep join: {deep_join.local_field}")
                                logger.debug(f"Added nested join result: {deep_alias}")
                    if nested_join.exclude_fields:
                        for field in nested_join.exclude_fields:
                            nested_projection[field] = 0
                    if nested_projection:
                        nested_pipeline.append({"$project": nested_projection})
                
                # Add nested pipeline to lookup if we have operations
                if nested_pipeline:
                    nested_lookup["$lookup"]["pipeline"] = nested_pipeline
                
                lookup_pipeline.append(nested_lookup)
                
                # Add unwind for nested join if specified
                if nested_join.join_type == "unwind":
                    nested_unwind = {
                        "$unwind": {
                            "path": f"${nested_alias}",
                            "preserveNullAndEmptyArrays": nested_join.preserve_null_and_empty_arrays
                        }
                    }
                    lookup_pipeline.append(nested_unwind)
                
                self.collections_used.add(nested_join.collection)
        
        # Add field projection for main join if specified
        if join.fields or join.exclude_fields:
            projection = {}
            
            if join.fields:
                # Include only specified fields
                projection = {field: 1 for field in join.fields}
                projection["_id"] = 1  # Always include _id for joins
                
                # CRITICAL FIX: Include fields needed for nested joins
                if join.joins:
                    for nested_join in join.joins:
                        # Add local_field needed for nested join
                        projection[nested_join.local_field] = 1
                        # CRITICAL FIX: Include the nested join result field
                        nested_alias = nested_join.alias or nested_join.collection
                        projection[nested_alias] = 1
                        logger.debug(f"Added field for nested join: {nested_join.local_field}")
                        logger.debug(f"Added nested join result: {nested_alias}")
            
            if join.exclude_fields:
                # Exclude specified fields
                for field in join.exclude_fields:
                    projection[field] = 0
            
            if projection:
                lookup_pipeline.append({"$project": projection})
        
        # Add sort if specified
        if join.sort:
            lookup_pipeline.append({"$sort": join.sort})
        
        # Add limit if specified
        if join.limit:
            lookup_pipeline.append({"$limit": join.limit})
        
        # Main lookup stage
        lookup_stage = {
            "$lookup": {
                "from": join.collection,
                "localField": join.local_field,
                "foreignField": join.foreign_field,
                "as": alias
            }
        }
        
        # Add pipeline to lookup if we have operations
        if lookup_pipeline:
            lookup_stage["$lookup"]["pipeline"] = lookup_pipeline
        
        stages.append(lookup_stage)
        
        # Add unwind if specified
        if join.join_type == "unwind":
            unwind_stage = {
                "$unwind": {
                    "path": f"${alias}",
                    "preserveNullAndEmptyArrays": join.preserve_null_and_empty_arrays
                }
            }
            stages.append(unwind_stage)
        
        # Update complexity tracking
        self.complexity_score += 1 + (len(join.joins) if join.joins else 0)
        self.collections_used.add(join.collection)
        
        return stages
    
    def _build_advanced_projection_stage(self, config: AdvancedExportConfig) -> Dict[str, Any]:
        """Build advanced projection stage dengan nested field support"""
        projection = {"_id": 1}  # Always include _id
        
        # Handle main collection fields
        if config.fields:
            for field in config.fields:
                projection[field] = 1
        elif config.exclude_fields:
            for field in config.exclude_fields:
                projection[field] = 0
        
        # CRITICAL FIX: Include joined collection fields
        if config.joins:
            for join in config.joins:
                alias = join.alias or join.collection
                projection[alias] = 1  # Include the entire joined collection
                logger.debug(f"Added joined collection to projection: {alias}")
        
        return {"$project": projection} if len(projection) > 1 or config.exclude_fields else {}
    
    def _analyze_complexity(self, config: AdvancedExportConfig) -> Tuple[QueryComplexity, List[str]]:
        """Analyze query complexity dan generate warnings"""
        warnings = []
        total_joins = 0
        max_depth = 0
        
        def count_joins(joins, depth=0):
            nonlocal total_joins, max_depth
            if not joins:
                return
            
            max_depth = max(max_depth, depth)
            for join in joins:
                total_joins += 1
                if join.joins:
                    count_joins(join.joins, depth + 1)
        
        if config.joins:
            count_joins(config.joins, 1)
        
        # Determine complexity
        complexity = QueryComplexity.LOW
        
        if total_joins > 5 or max_depth > 3:
            complexity = QueryComplexity.VERY_HIGH
            warnings.append(f"Very complex query: {total_joins} joins with max depth {max_depth}")
        elif total_joins > 3 or max_depth > 2:
            complexity = QueryComplexity.HIGH
            warnings.append(f"Complex query: {total_joins} joins with max depth {max_depth}")
        elif total_joins > 1 or max_depth > 1:
            complexity = QueryComplexity.MEDIUM
            warnings.append(f"Moderate complexity: {total_joins} joins with max depth {max_depth}")
        
        # Check for other complexity factors
        if config.limit and config.limit > 10000:
            warnings.append(f"Large limit ({config.limit}) may impact performance")
        
        if config.group_by:
            complexity = QueryComplexity.HIGH if complexity == QueryComplexity.MEDIUM else complexity
            warnings.append("Grouping operations increase query complexity")
        
        return complexity, warnings
    
    def build_advanced_pipeline(self, config: AdvancedExportConfig) -> List[Dict[str, Any]]:
        """Build complete advanced aggregation pipeline dengan nested joins"""
        pipeline = []
        self.collections_used.add(config.main_collection)
        
        # 1. Initial match stage for main collection filters
        if config.filters:
            match_stage = self._build_advanced_match_stage(config.filters)
            if match_stage:
                pipeline.append({"$match": match_stage})
        
        # 2. Add nested lookup stages for joins
        if config.joins:
            for join in config.joins:
                lookup_stages = self._build_nested_lookup_stages(join)
                pipeline.extend(lookup_stages)
        
        # 3. Add projection stage if needed
        projection_stage = self._build_advanced_projection_stage(config)
        if projection_stage:
            pipeline.append(projection_stage)
        
        # 4. Add grouping if specified
        if config.group_by:
            group_stage = {
                "$group": {
                    "_id": {field: f"${field}" for field in config.group_by}
                }
            }
            # Add other fields to group stage
            # This is simplified - in practice, you'd want more sophisticated grouping
            pipeline.append(group_stage)
            
            # Add having conditions
            if config.having:
                having_match = self._build_advanced_match_stage(config.having)
                if having_match:
                    pipeline.append({"$match": having_match})
        
        # 5. Add sort stage
        if config.sort:
            pipeline.append({"$sort": config.sort})
        
        # 6. Add skip stage
        if config.skip and config.skip > 0:
            pipeline.append({"$skip": config.skip})
        
        # 7. Add limit stage
        if config.limit:
            pipeline.append({"$limit": config.limit})
        
        # 8. Add performance options
        if config.allow_disk_use:
            # This would be handled at the aggregation execution level
            pass
        
        logger.info(f"Generated pipeline with {len(pipeline)} stages for collection '{config.main_collection}'")
        logger.info(f"DEBUG ADVANCED PIPELINE: {pipeline}")
        logger.info(f"Collections involved: {self.collections_used}")
        logger.info(f"Complexity score: {self.complexity_score}")
        
        return pipeline
    
    async def estimate_advanced_result_count(self, db: AsyncIOMotorDatabase, 
                                           config: AdvancedExportConfig) -> Optional[int]:
        """Estimate result count untuk advanced query"""
        try:
            # Build a count-only pipeline (without limit and skip)
            count_pipeline = []
            
            # Add initial match stage
            if config.filters:
                match_stage = self._build_advanced_match_stage(config.filters)
                if match_stage:
                    count_pipeline.append({"$match": match_stage})
            
            # Add joins (they might filter results)
            if config.joins:
                for join in config.joins:
                    lookup_stages = self._build_nested_lookup_stages(join)
                    count_pipeline.extend(lookup_stages)
            
            # Add grouping if specified
            if config.group_by:
                group_stage = {
                    "$group": {
                        "_id": {field: f"${field}" for field in config.group_by}
                    }
                }
                count_pipeline.append(group_stage)
                
                if config.having:
                    having_match = self._build_advanced_match_stage(config.having)
                    if having_match:
                        count_pipeline.append({"$match": having_match})
            
            # Add count stage
            count_pipeline.append({"$count": "total"})
            
            # Execute count pipeline with timeout
            options = {}
            if config.max_time_ms:
                options['maxTimeMS'] = config.max_time_ms
            
            cursor = db[config.main_collection].aggregate(count_pipeline, **options)
            result = await cursor.to_list(1)
            
            if result and len(result) > 0:
                estimated_count = result[0]["total"]
                
                # Apply limit if specified
                if config.limit:
                    estimated_count = min(estimated_count, config.limit)
                
                return estimated_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error estimating advanced result count: {e}")
            return None
    
    def get_query_analysis(self, config: AdvancedExportConfig) -> Dict[str, Any]:
        """Get comprehensive query analysis"""
        complexity, warnings = self._analyze_complexity(config)
        
        # Count total joins and max depth
        total_joins = 0
        max_depth = 0
        
        def analyze_joins(joins, depth=0):
            nonlocal total_joins, max_depth
            if not joins:
                return
            
            max_depth = max(max_depth, depth)
            for join in joins:
                total_joins += 1
                if join.joins:
                    analyze_joins(join.joins, depth + 1)
        
        if config.joins:
            analyze_joins(config.joins, 1)
        
        return {
            "complexity": complexity.value,
            "total_joins": total_joins,
            "max_join_depth": max_depth,
            "collections_involved": list(self.collections_used),
            "estimated_pipeline_stages": len(self.build_advanced_pipeline(config)),
            "warnings": warnings
        }
