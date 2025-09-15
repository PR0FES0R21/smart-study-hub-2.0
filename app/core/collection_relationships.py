# ==============================================================================
# File: app/core/collection_relationships.py
# Deskripsi: Enhanced collection relationships untuk smart join discovery
# ==============================================================================
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RelationshipType(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"  
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

@dataclass
class JoinRelationship:
    target_collection: str
    local_field: str
    foreign_field: str
    relationship_type: RelationshipType
    description: str = ""
    is_reverse_join: bool = False

@dataclass
class CollectionMetadata:
    name: str
    display_name: str
    description: str
    allowed_fields: List[str]
    sensitive_fields: List[str] = None
    relationships: Dict[str, JoinRelationship] = None
    required_roles: List[str] = None
    common_filters: List[str] = None

# Enhanced collection relationships dengan join discovery
COLLECTION_RELATIONSHIPS: Dict[str, CollectionMetadata] = {
    "users": CollectionMetadata(
        name="users",
        display_name="Users",
        description="System users (students, teachers, admins)",
        allowed_fields=[
            "_id", "username", "email", "roles", "is_active", "created_at", "updated_at"
        ],
        sensitive_fields=["hashed_password", "reset_token"],
        relationships={
            "profiles": JoinRelationship(
                target_collection="profiles",
                local_field="profile_id", 
                foreign_field="_id",
                relationship_type=RelationshipType.ONE_TO_ONE,
                description="User profile and personal information"
            ),
            "exam_sessions": JoinRelationship(
                target_collection="exam_sessions",
                local_field="_id",
                foreign_field="student_id", 
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Student's exam sessions and scores"
            ),
            "teaching_assignments": JoinRelationship(
                target_collection="teaching_assignments",
                local_field="_id",
                foreign_field="teacher_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Teacher's subject assignments"
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["roles", "is_active", "created_at", "updated_at"]
    ),
    
    "profiles": CollectionMetadata(
        name="profiles",
        display_name="User Profiles", 
        description="Detailed user profile information",
        allowed_fields=[
            "_id", "user_id", "full_name", "birth_date", "gender", "phone",
            "address", "class_id", "start_year", "end_year", "created_at"
        ],
        sensitive_fields=["phone", "address"],
        relationships={
            "users": JoinRelationship(
                target_collection="users",
                local_field="user_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Associated user account",
                is_reverse_join=True
            ),
            "classes": JoinRelationship(
                target_collection="classes",
                local_field="class_id",
                foreign_field="_id", 
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Student's assigned class"
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["gender", "class_id", "start_year", "end_year"]
    ),
    
    "classes": CollectionMetadata(
        name="classes",
        display_name="Classes",
        description="School classes and academic groups",
        allowed_fields=[
            "_id", "name", "grade_level", "expertise_id", "academic_period_id", 
            "homeroom_teacher_id", "created_at"
        ],
        relationships={
            "expertise_programs": JoinRelationship(
                target_collection="expertise_programs",
                local_field="expertise_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Class specialization program"
            ),
            "academic_periods": JoinRelationship(
                target_collection="academic_periods", 
                local_field="academic_period_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Academic period/semester"
            ),
            "profiles": JoinRelationship(
                target_collection="profiles",
                local_field="_id",
                foreign_field="class_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Students in this class",
                is_reverse_join=True
            ),
            "homeroom_teacher": JoinRelationship(
                target_collection="users",
                local_field="homeroom_teacher_id", 
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Class homeroom teacher"
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["grade_level", "expertise_id", "academic_period_id"]
    ),
    
    "expertise_programs": CollectionMetadata(
        name="expertise_programs",
        display_name="Expertise Programs",
        description="Vocational specialization programs",
        allowed_fields=[
            "_id", "name", "abbreviation", "description", "department_id", "created_at"
        ],
        relationships={
            "classes": JoinRelationship(
                target_collection="classes",
                local_field="_id", 
                foreign_field="expertise_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Classes in this program",
                is_reverse_join=True
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["name", "abbreviation"]
    ),
    
    "exam_sessions": CollectionMetadata(
        name="exam_sessions",
        display_name="Exam Sessions", 
        description="Individual student exam attempts",
        allowed_fields=[
            "_id", "exam_id", "student_id", "score", "status", "started_at",
            "submitted_at", "graded_at", "answers", "time_spent_minutes"
        ],
        sensitive_fields=["answers"],
        relationships={
            "users": JoinRelationship(
                target_collection="users",
                local_field="student_id",
                foreign_field="_id", 
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Student who took the exam",
                is_reverse_join=True
            ),
            "exams": JoinRelationship(
                target_collection="exams",
                local_field="exam_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="The exam that was taken"
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["status", "score", "started_at", "submitted_at"]
    ),
    
    "exams": CollectionMetadata(
        name="exams",
        display_name="Exams",
        description="Exam configurations and questions", 
        allowed_fields=[
            "_id", "title", "exam_type", "duration_minutes", "status",
            "availability_start_time", "availability_end_time", "created_at",
            "teaching_assignment_id", "academic_period_id"
        ],
        sensitive_fields=["questions"],
        relationships={
            "teaching_assignments": JoinRelationship(
                target_collection="teaching_assignments",
                local_field="teaching_assignment_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Subject and teacher assignment"
            ),
            "exam_sessions": JoinRelationship(
                target_collection="exam_sessions", 
                local_field="_id",
                foreign_field="exam_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Student sessions for this exam",
                is_reverse_join=True
            ),
            "academic_periods": JoinRelationship(
                target_collection="academic_periods",
                local_field="academic_period_id", 
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Academic period when exam is held"
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["exam_type", "status", "availability_start_time", "availability_end_time"]
    ),
    
    "teaching_assignments": CollectionMetadata(
        name="teaching_assignments", 
        display_name="Teaching Assignments",
        description="Teacher-subject-class assignments",
        allowed_fields=[
            "_id", "teacher_id", "subject_id", "class_id", "academic_period_id", "created_at"
        ],
        relationships={
            "users": JoinRelationship(
                target_collection="users",
                local_field="teacher_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Assigned teacher",
                is_reverse_join=True
            ),
            "subjects": JoinRelationship(
                target_collection="subjects",
                local_field="subject_id", 
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Subject being taught"
            ),
            "classes": JoinRelationship(
                target_collection="classes",
                local_field="class_id",
                foreign_field="_id",
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Class being taught"
            ),
            "academic_periods": JoinRelationship(
                target_collection="academic_periods",
                local_field="academic_period_id",
                foreign_field="_id", 
                relationship_type=RelationshipType.MANY_TO_ONE,
                description="Academic period"
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["teacher_id", "subject_id", "class_id", "academic_period_id"]
    ),
    
    "subjects": CollectionMetadata(
        name="subjects",
        display_name="Subjects",
        description="Academic subjects and courses",
        allowed_fields=[
            "_id", "name", "code", "description", "created_at"
        ],
        relationships={
            "teaching_assignments": JoinRelationship(
                target_collection="teaching_assignments",
                local_field="_id",
                foreign_field="subject_id", 
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Teaching assignments for this subject",
                is_reverse_join=True
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["name", "code"]
    ),
    
    "academic_periods": CollectionMetadata(
        name="academic_periods",
        display_name="Academic Periods",
        description="Semesters and academic terms",
        allowed_fields=[
            "_id", "name", "start_date", "end_date", "is_active", "semester", "academic_year"
        ],
        relationships={
            "classes": JoinRelationship(
                target_collection="classes",
                local_field="_id",
                foreign_field="academic_period_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Classes in this period",
                is_reverse_join=True
            ),
            "teaching_assignments": JoinRelationship(
                target_collection="teaching_assignments", 
                local_field="_id",
                foreign_field="academic_period_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Teaching assignments in this period",
                is_reverse_join=True
            ),
            "exams": JoinRelationship(
                target_collection="exams",
                local_field="_id",
                foreign_field="academic_period_id",
                relationship_type=RelationshipType.ONE_TO_MANY,
                description="Exams in this period", 
                is_reverse_join=True
            )
        },
        required_roles=["admin", "teacher"],
        common_filters=["is_active", "semester", "academic_year", "start_date", "end_date"]
    )
}

class JoinPathFinder:
    """Smart join path discovery and optimization"""
    
    def __init__(self):
        self.relationships = COLLECTION_RELATIONSHIPS
    
    def find_join_paths(self, from_collection: str, to_collection: str, 
                       max_depth: int = 3, visited: Set[str] = None) -> List[List[str]]:
        """Find all possible join paths between two collections"""
        if visited is None:
            visited = set()
        
        if from_collection == to_collection:
            return [[from_collection]]
        
        if from_collection in visited or max_depth <= 0:
            return []
        
        if from_collection not in self.relationships:
            return []
        
        visited = visited.copy()
        visited.add(from_collection)
        
        paths = []
        for target, relationship in self.relationships[from_collection].relationships.items():
            if target not in visited:
                sub_paths = self.find_join_paths(target, to_collection, max_depth - 1, visited)
                for sub_path in sub_paths:
                    paths.append([from_collection] + sub_path)
        
        return paths
    
    def get_optimal_main_collection(self, required_collections: List[str]) -> str:
        """Suggest the best main collection for joining to multiple collections"""
        collection_scores = {}
        
        for candidate in required_collections:
            if candidate not in self.relationships:
                continue
                
            score = 0
            for target in required_collections:
                if candidate != target:
                    paths = self.find_join_paths(candidate, target, max_depth=2)
                    if paths:
                        # Shorter paths get higher scores
                        score += max(0, 3 - len(min(paths, key=len)))
            
            collection_scores[candidate] = score
        
        if collection_scores:
            return max(collection_scores.keys(), key=lambda x: collection_scores[x])
        
        return required_collections[0] if required_collections else None
    
    def build_join_suggestion(self, main_collection: str, target_collections: List[str]) -> Dict[str, Any]:
        """Build join configuration suggestions for UI"""
        suggestions = {
            "main_collection": main_collection,
            "suggested_joins": [],
            "alternative_approaches": []
        }
        
        if main_collection not in self.relationships:
            return suggestions
        
        main_meta = self.relationships[main_collection]
        
        # Direct joins
        for target in target_collections:
            if target in main_meta.relationships:
                rel = main_meta.relationships[target]
                suggestions["suggested_joins"].append({
                    "collection": target,
                    "local_field": rel.local_field,
                    "foreign_field": rel.foreign_field,
                    "relationship_type": rel.relationship_type.value,
                    "description": rel.description,
                    "suggested_fields": self.relationships[target].allowed_fields[:5]  # Top 5 fields
                })
        
        # Alternative main collections
        for alt_main in target_collections:
            if alt_main != main_collection:
                alt_score = len([t for t in target_collections 
                               if t in self.relationships.get(alt_main, CollectionMetadata("", "", "", [])).relationships])
                if alt_score > 0:
                    suggestions["alternative_approaches"].append({
                        "main_collection": alt_main, 
                        "can_join_to": alt_score,
                        "description": f"Use {alt_main} as main collection to access {alt_score} other collections directly"
                    })
        
        return suggestions
    
    def get_collection_discovery_info(self, collection: str, user_roles: List[str] = None) -> Dict[str, Any]:
        """Get comprehensive collection info for UI discovery"""
        if collection not in self.relationships:
            return {}
        
        meta = self.relationships[collection]
        
        # Check user permissions
        has_access = True
        if meta.required_roles and user_roles:
            has_access = any(role in user_roles for role in meta.required_roles)
        
        if not has_access:
            return {"name": collection, "accessible": False}
        
        # Get available joins with next-level possibilities
        available_joins = []
        for target, rel in meta.relationships.items():
            target_meta = self.relationships.get(target)
            if target_meta:
                join_info = {
                    "target_collection": target,
                    "display_name": target_meta.display_name,
                    "local_field": rel.local_field,
                    "foreign_field": rel.foreign_field,
                    "relationship": rel.relationship_type.value,
                    "description": rel.description,
                    "next_possible_joins": [
                        {
                            "collection": next_target,
                            "display_name": self.relationships[next_target].display_name,
                            "relationship": next_rel.relationship_type.value
                        }
                        for next_target, next_rel in target_meta.relationships.items()
                        if next_target != collection  # Avoid circular references
                    ][:3]  # Limit to 3 for UI
                }
                available_joins.append(join_info)
        
        return {
            "name": collection,
            "display_name": meta.display_name,
            "description": meta.description,
            "accessible": True,
            "available_fields": meta.allowed_fields,
            "sensitive_fields": meta.sensitive_fields or [],
            "common_filters": meta.common_filters or [],
            "available_joins": available_joins,
            "total_joinable_collections": len(available_joins)
        }

# Global instances
join_path_finder = JoinPathFinder()

def get_collection_relationships() -> Dict[str, CollectionMetadata]:
    """Get all collection relationships"""
    return COLLECTION_RELATIONSHIPS

def get_smart_join_suggestions(collections: List[str]) -> Dict[str, Any]:
    """Get smart join suggestions for multiple collections"""
    optimal_main = join_path_finder.get_optimal_main_collection(collections)
    return join_path_finder.build_join_suggestion(optimal_main, collections)
