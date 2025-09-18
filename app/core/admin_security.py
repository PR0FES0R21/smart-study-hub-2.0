# ==============================================================================
# File: app/core/admin_security.py
# Deskripsi: Admin security validator dengan enhanced permissions
# ==============================================================================
from typing import Dict, List, Set, Optional, Any
from app.schemas.admin_export import AdvancedExportConfig, AdvancedJoinConfig, AdvancedFilterCondition
from app.core.database_schema import database_schema
import logging

logger = logging.getLogger(__name__)

class AdminExportSecurityManager:
    """Enhanced security manager untuk admin export dengan flexible validation"""
    
    def __init__(self):
        # Admin mendapat akses ke semua collections dari database schema
        self.admin_collections = set(database_schema.get_all_collections())
    
    def validate_admin_access(self, user_roles: List[str]) -> bool:
        """Validate if user has admin access"""
        return "admin" in user_roles
    
    def validate_collection_exists(self, collection: str) -> bool:
        """Validate if collection exists in system"""
        return collection in self.admin_collections
    
    def validate_field_reference(self, collection: str, field: str) -> Dict[str, Any]:
        """Validate field reference dengan flexible approach untuk admin"""
        # Admin bisa akses field apapun, tapi beri warning untuk field sensitif
        warnings = []
        
        sensitive_field_patterns = [
            "password", "token", "secret", "private", "internal", 
            "hashed_password", "reset_token", "api_key"
        ]
        
        if any(pattern in field.lower() for pattern in sensitive_field_patterns):
            warnings.append(f"Accessing sensitive field '{field}' in collection '{collection}'")
        
        return {
            "valid": True,
            "warnings": warnings
        }
    
    def validate_join_relationship(self, from_collection: str, to_collection: str, 
                                  local_field: str, foreign_field: str) -> Dict[str, Any]:
        """Validate join relationship dengan enhanced logic"""
        warnings = []
        errors = []
        
        # Check if collections exist
        if not self.validate_collection_exists(from_collection):
            errors.append(f"Source collection '{from_collection}' not found")
        
        if not self.validate_collection_exists(to_collection):
            errors.append(f"Target collection '{to_collection}' not found")
        
        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Get relationships from database schema
        relationships = database_schema.get_collection_relationships(from_collection)
        
        # Check if this is a known relationship
        if to_collection in relationships:
            expected_local_field = relationships[to_collection]["local_field"]
            if local_field != expected_local_field:
                warnings.append(
                    f"Non-standard join: expected '{expected_local_field}' but got '{local_field}' "
                    f"for join from '{from_collection}' to '{to_collection}'"
                )
        else:
            # This is a custom join - check if fields make sense
            from_fields = database_schema.get_collection_fields(from_collection)
            if local_field not in from_fields and not local_field.endswith("_id") and local_field != "_id":
                warnings.append(
                    f"Unusual local field '{local_field}' for join from '{from_collection}'. "
                    f"Field not found in collection schema."
                )
        
        # Check foreign field (usually _id)
        to_fields = database_schema.get_collection_fields(to_collection)
        if foreign_field not in to_fields and foreign_field != "_id":
            warnings.append(
                f"Foreign field '{foreign_field}' not found in collection '{to_collection}'. "
                f"Most joins use '_id' as foreign field."
            )
        
        return {
            "valid": True,
            "warnings": warnings,
            "relationship_type": "known" if to_collection in relationships else "custom"
        }
    
    def validate_nested_joins(self, joins: List[AdvancedJoinConfig], 
                             parent_collection: str, depth: int = 0) -> Dict[str, Any]:
        """Validate nested joins recursively"""
        if depth > 5:  # Prevent infinite recursion
            return {
                "valid": False,
                "errors": [f"Join depth too deep (>{5}). This may cause performance issues."]
            }
        
        all_warnings = []
        all_errors = []
        
        for join in joins:
            # Validate this join
            join_validation = self.validate_join_relationship(
                parent_collection, join.collection, 
                join.local_field, join.foreign_field
            )
            
            if not join_validation["valid"]:
                all_errors.extend(join_validation["errors"])
            else:
                all_warnings.extend(join_validation["warnings"])
            
            # Validate fields in this join
            if join.fields:
                for field in join.fields:
                    field_validation = self.validate_field_reference(join.collection, field)
                    all_warnings.extend(field_validation["warnings"])
            
            # Validate filters in this join
            if join.filters:
                filter_validation = self.validate_filters(join.collection, join.filters)
                if not filter_validation["valid"]:
                    all_errors.extend(filter_validation["errors"])
                all_warnings.extend(filter_validation["warnings"])
            
            # Recursively validate nested joins
            if join.joins:
                nested_validation = self.validate_nested_joins(
                    join.joins, join.collection, depth + 1
                )
                if not nested_validation["valid"]:
                    all_errors.extend(nested_validation["errors"])
                all_warnings.extend(nested_validation["warnings"])
        
        return {
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings
        }
    
    def validate_filters(self, collection: str, filters: List[AdvancedFilterCondition]) -> Dict[str, Any]:
        """Validate filter conditions untuk collection"""
        warnings = []
        errors = []
        
        for filter_cond in filters:
            # Validate field access
            field_validation = self.validate_field_reference(collection, filter_cond.field)
            warnings.extend(field_validation["warnings"])
            
            # Validate operator and value compatibility
            if filter_cond.operator.value in ["in", "nin"] and not isinstance(filter_cond.value, list):
                warnings.append(
                    f"Operator '{filter_cond.operator.value}' typically expects array value, "
                    f"got {type(filter_cond.value).__name__}"
                )
            
            if filter_cond.operator.value == "regex" and not isinstance(filter_cond.value, str):
                errors.append(
                    f"Regex operator requires string value, got {type(filter_cond.value).__name__}"
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def validate_advanced_export_config(self, config: AdvancedExportConfig, 
                                       user_roles: List[str]) -> Dict[str, Any]:
        """Comprehensive validation of advanced export configuration"""
        if not self.validate_admin_access(user_roles):
            return {
                "valid": False,
                "errors": ["Admin access required for advanced export functionality"],
                "warnings": []
            }
        
        all_errors = []
        all_warnings = []
        
        # Validate main collection
        if not self.validate_collection_exists(config.main_collection):
            all_errors.append(f"Main collection '{config.main_collection}' not found")
            return {"valid": False, "errors": all_errors, "warnings": all_warnings}
        
        # Validate main collection fields
        if config.fields:
            for field in config.fields:
                field_validation = self.validate_field_reference(config.main_collection, field)
                all_warnings.extend(field_validation["warnings"])
        
        # Validate main collection filters
        if config.filters:
            filter_validation = self.validate_filters(config.main_collection, config.filters)
            if not filter_validation["valid"]:
                all_errors.extend(filter_validation["errors"])
            all_warnings.extend(filter_validation["warnings"])
        
        # Validate joins
        if config.joins:
            join_validation = self.validate_nested_joins(config.joins, config.main_collection)
            if not join_validation["valid"]:
                all_errors.extend(join_validation["errors"])
            all_warnings.extend(join_validation["warnings"])
        
        # Performance warnings
        if config.limit and config.limit > 50000:
            all_warnings.append(f"Very large limit ({config.limit}) may cause memory issues")
        
        if config.joins and len(config.joins) > 5:
            all_warnings.append(f"Many joins ({len(config.joins)}) may impact performance significantly")
        
        # Validate group by fields
        if config.group_by:
            for field in config.group_by:
                # Group by fields should typically be from main collection or joined collections
                if "." not in field:  # Main collection field
                    field_validation = self.validate_field_reference(config.main_collection, field)
                    all_warnings.extend(field_validation["warnings"])
        
        # Validate having conditions
        if config.having:
            having_validation = self.validate_filters(config.main_collection, config.having)
            if not having_validation["valid"]:
                all_errors.extend([f"Having condition error: {err}" for err in having_validation["errors"]])
            all_warnings.extend([f"Having condition warning: {warn}" for warn in having_validation["warnings"]])
        
        return {
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings
        }
    
    def get_collection_suggestions(self, current_collection: str) -> List[Dict[str, Any]]:
        """Get suggested collections that can be joined from current collection"""
        return database_schema.get_possible_joins(current_collection)
    
    def analyze_query_performance(self, config: AdvancedExportConfig) -> Dict[str, Any]:
        """Analyze query for potential performance issues"""
        issues = []
        recommendations = []
        
        # Count total collections involved
        collections_involved = {config.main_collection}
        
        def count_collections(joins):
            if not joins:
                return
            for join in joins:
                collections_involved.add(join.collection)
                if join.joins:
                    count_collections(join.joins)
        
        if config.joins:
            count_collections(config.joins)
        
        # Performance analysis
        if len(collections_involved) > 5:
            issues.append(f"Query involves {len(collections_involved)} collections - very complex")
            recommendations.append("Consider breaking into multiple simpler queries")
        
        if config.limit and config.limit > 10000:
            issues.append(f"Large result set ({config.limit} records)")
            recommendations.append("Consider using pagination or smaller limits")
        
        if not config.limit:
            issues.append("No limit specified - could return entire collection")
            recommendations.append("Always specify a reasonable limit for safety")
        
        return {
            "collections_involved": list(collections_involved),
            "complexity_level": "high" if len(collections_involved) > 3 else "medium" if len(collections_involved) > 1 else "low",
            "potential_issues": issues,
            "recommendations": recommendations
        }

# Global instance
admin_export_security = AdminExportSecurityManager()
