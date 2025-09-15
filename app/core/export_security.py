# ==============================================================================
# File: app/core/export_security.py
# Deskripsi: Security layer dan configuration untuk flexible export system
# ==============================================================================
from typing import Dict, List, Set, Optional
from app.schemas.export import CollectionPermission, ExportConfig, FilterCondition, JoinConfig
import logging

logger = logging.getLogger(__name__)

# Configuration untuk collection permissions
COLLECTION_PERMISSIONS: Dict[str, CollectionPermission] = {
    "users": CollectionPermission(
        name="users",
        allowed_fields=[
            "_id", "username", "email", "roles", "is_active", "created_at", "updated_at"
        ],
        sensitive_fields=["hashed_password", "reset_token"],
        allowed_joins=["profiles", "exam_sessions"],
        allowed_filters=["roles", "is_active", "created_at", "updated_at"],
        required_roles=["admin", "teacher"]
    ),
    
    "profiles": CollectionPermission(
        name="profiles",
        allowed_fields=[
            "_id", "user_id", "full_name", "birth_date", "gender", "phone", 
            "address", "class_id", "start_year", "end_year", "created_at"
        ],
        sensitive_fields=["phone", "address"],
        allowed_joins=["users", "classes"],
        allowed_filters=["gender", "class_id", "start_year", "end_year", "created_at"],
        required_roles=["admin", "teacher"]
    ),
    
    "classes": CollectionPermission(
        name="classes",
        allowed_fields=[
            "_id", "name", "grade_level", "expertise_id", "academic_period_id", "created_at"
        ],
        sensitive_fields=[],
        allowed_joins=["expertise_programs", "academic_periods", "profiles"],
        allowed_filters=["grade_level", "expertise_id", "academic_period_id"],
        required_roles=["admin", "teacher"]
    ),
    
    "expertise_programs": CollectionPermission(
        name="expertise_programs", 
        allowed_fields=[
            "_id", "name", "abbreviation", "description", "created_at"
        ],
        sensitive_fields=[],
        allowed_joins=["classes"],
        allowed_filters=["name", "abbreviation"],
        required_roles=["admin", "teacher"]
    ),
    
    "subjects": CollectionPermission(
        name="subjects",
        allowed_fields=[
            "_id", "name", "code", "description", "created_at"
        ],
        sensitive_fields=[],
        allowed_joins=["teaching_assignments"],
        allowed_filters=["name", "code"],
        required_roles=["admin", "teacher"]
    ),
    
    "exam_sessions": CollectionPermission(
        name="exam_sessions",
        allowed_fields=[
            "_id", "exam_id", "student_id", "score", "status", "started_at", 
            "submitted_at", "graded_at", "answers", "time_spent_minutes"
        ],
        sensitive_fields=["answers"],  # Detail jawaban siswa sensitif
        allowed_joins=["exams", "users"],
        allowed_filters=["status", "score", "started_at", "submitted_at", "graded_at"],
        required_roles=["admin", "teacher"]
    ),
    
    "exams": CollectionPermission(
        name="exams",
        allowed_fields=[
            "_id", "title", "exam_type", "duration_minutes", "status",
            "availability_start_time", "availability_end_time", "created_at",
            "teaching_assignment_id", "academic_period_id"
        ],
        sensitive_fields=["questions"],  # Soal ujian sensitif
        allowed_joins=["teaching_assignments", "exam_sessions", "academic_periods"],
        allowed_filters=["exam_type", "status", "availability_start_time", "availability_end_time", "created_at"],
        required_roles=["admin", "teacher"]
    ),
    
    "teaching_assignments": CollectionPermission(
        name="teaching_assignments",
        allowed_fields=[
            "_id", "teacher_id", "subject_id", "class_id", "academic_period_id", "created_at"
        ],
        sensitive_fields=[],
        allowed_joins=["users", "subjects", "classes", "academic_periods"],
        allowed_filters=["teacher_id", "subject_id", "class_id", "academic_period_id"],
        required_roles=["admin", "teacher"]
    ),
    
    "academic_periods": CollectionPermission(
        name="academic_periods",
        allowed_fields=[
            "_id", "name", "start_date", "end_date", "is_active", "semester", "academic_year"
        ],
        sensitive_fields=[],
        allowed_joins=["classes", "teaching_assignments", "exams"],
        allowed_filters=["is_active", "semester", "academic_year", "start_date", "end_date"],
        required_roles=["admin", "teacher"]
    )
}

class ExportSecurityManager:
    """Manager untuk validasi keamanan export operations"""
    
    def __init__(self):
        self.permissions = COLLECTION_PERMISSIONS
    
    def validate_user_access(self, user_roles: List[str], collection: str) -> bool:
        """Validasi apakah user memiliki akses ke collection"""
        if not collection in self.permissions:
            return False
        
        required_roles = self.permissions[collection].required_roles
        if not required_roles:  # Jika tidak ada requirement, allow
            return True
            
        return any(role in user_roles for role in required_roles)
    
    def validate_collection_access(self, user_roles: List[str], collections: List[str]) -> Dict[str, bool]:
        """Validasi akses ke multiple collections"""
        access_map = {}
        for collection in collections:
            access_map[collection] = self.validate_user_access(user_roles, collection)
        return access_map
    
    def get_allowed_fields(self, collection: str, include_sensitive: bool = False) -> List[str]:
        """Get daftar field yang diizinkan untuk collection"""
        if collection not in self.permissions:
            return []
        
        perm = self.permissions[collection]
        fields = perm.allowed_fields.copy()
        
        if include_sensitive:
            fields.extend(perm.sensitive_fields)
            
        return fields
    
    def validate_fields(self, collection: str, requested_fields: List[str], 
                       user_roles: List[str]) -> Dict[str, any]:
        """Validasi field yang diminta user"""
        if collection not in self.permissions:
            return {"valid": False, "errors": [f"Collection '{collection}' not allowed"]}
        
        perm = self.permissions[collection]
        allowed_fields = set(perm.allowed_fields)
        sensitive_fields = set(perm.sensitive_fields)
        requested_set = set(requested_fields)
        
        # Check basic field access
        invalid_fields = requested_set - allowed_fields - sensitive_fields
        if invalid_fields:
            return {
                "valid": False, 
                "errors": [f"Invalid fields for {collection}: {list(invalid_fields)}"]
            }
        
        # Check sensitive field access
        requested_sensitive = requested_set & sensitive_fields
        has_admin = "admin" in user_roles
        
        if requested_sensitive and not has_admin:
            return {
                "valid": False,
                "errors": [f"Sensitive fields require admin role: {list(requested_sensitive)}"]
            }
        
        return {"valid": True, "errors": []}
    
    def validate_joins(self, main_collection: str, joins: List[JoinConfig], 
                      user_roles: List[str]) -> Dict[str, any]:
        """Validasi join operations"""
        if main_collection not in self.permissions:
            return {"valid": False, "errors": [f"Main collection '{main_collection}' not allowed"]}
        
        main_perm = self.permissions[main_collection]
        allowed_joins = set(main_perm.allowed_joins)
        
        errors = []
        
        for join in joins:
            # Validate join collection is allowed
            if join.collection not in allowed_joins:
                errors.append(f"Join to '{join.collection}' not allowed from '{main_collection}'")
                continue
            
            # Validate join collection exists in permissions
            if join.collection not in self.permissions:
                errors.append(f"Join collection '{join.collection}' not configured")
                continue
            
            # Validate user has access to join collection
            if not self.validate_user_access(user_roles, join.collection):
                errors.append(f"No access to join collection '{join.collection}'")
                continue
            
            # Validate fields in join
            if join.fields:
                field_validation = self.validate_fields(join.collection, join.fields, user_roles)
                if not field_validation["valid"]:
                    errors.extend([f"Join {join.collection}: {err}" for err in field_validation["errors"]])
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def validate_filters(self, collection: str, filters: List[FilterCondition]) -> Dict[str, any]:
        """Validasi filter conditions"""
        if collection not in self.permissions:
            return {"valid": False, "errors": [f"Collection '{collection}' not allowed"]}
        
        perm = self.permissions[collection]
        allowed_filter_fields = set(perm.allowed_filters + perm.allowed_fields)
        
        errors = []
        for filter_cond in filters:
            if filter_cond.field not in allowed_filter_fields:
                errors.append(f"Filter on field '{filter_cond.field}' not allowed in {collection}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def validate_export_config(self, config: ExportConfig, user_roles: List[str]) -> Dict[str, any]:
        """Comprehensive validation of export configuration"""
        all_errors = []
        all_warnings = []
        
        # Validate main collection access
        if not self.validate_user_access(user_roles, config.main_collection):
            return {
                "valid": False,
                "errors": [f"No access to main collection '{config.main_collection}'"],
                "warnings": []
            }
        
        # Validate main collection fields
        if config.fields:
            field_validation = self.validate_fields(config.main_collection, config.fields, user_roles)
            if not field_validation["valid"]:
                all_errors.extend(field_validation["errors"])
        
        # Validate main collection filters
        if config.filters:
            filter_validation = self.validate_filters(config.main_collection, config.filters)
            if not filter_validation["valid"]:
                all_errors.extend(filter_validation["errors"])
        
        # Validate joins
        if config.joins:
            join_validation = self.validate_joins(config.main_collection, config.joins, user_roles)
            if not join_validation["valid"]:
                all_errors.extend(join_validation["errors"])
            
            # Validate join filters
            for join in config.joins:
                if join.filters:
                    join_filter_validation = self.validate_filters(join.collection, join.filters)
                    if not join_filter_validation["valid"]:
                        all_errors.extend([f"Join {join.collection}: {err}" for err in join_filter_validation["errors"]])
        
        # Performance warnings
        if config.limit and config.limit > 5000:
            all_warnings.append("Large export (>5000 records) may impact performance")
        
        if len(config.joins) > 3:
            all_warnings.append("Multiple joins (>3) may impact performance")
        
        return {
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings
        }
    
    def get_available_collections(self, user_roles: List[str]) -> List[Dict[str, any]]:
        """Get list of collections available to user"""
        available = []
        
        for collection_name, perm in self.permissions.items():
            if self.validate_user_access(user_roles, collection_name):
                # Determine which fields to show based on role
                has_admin = "admin" in user_roles
                available_fields = perm.allowed_fields.copy()
                sensitive_fields = perm.sensitive_fields if has_admin else []
                
                available.append({
                    "name": collection_name,
                    "display_name": collection_name.replace("_", " ").title(),
                    "description": f"Data from {collection_name} collection",
                    "available_fields": available_fields,
                    "sensitive_fields": sensitive_fields,
                    "joinable_collections": perm.allowed_joins,
                    "common_filters": perm.allowed_filters
                })
        
        return available

# Global instance
export_security = ExportSecurityManager()
