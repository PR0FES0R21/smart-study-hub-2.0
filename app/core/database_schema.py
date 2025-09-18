# ==============================================================================
# File: app/core/database_schema.py
# Deskripsi: Complete database schema and relationships mapping
# ==============================================================================
from typing import Dict, List, Set, Optional, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseSchemaManager:
    """Complete database schema and relationship manager"""
    
    def __init__(self):
        # Complete collection definitions with all fields
        self.collection_schemas = {
            "users": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "User ID"},
                    "login_id": {"type": "string", "description": "NIS/NIP"},
                    "email": {"type": "string", "description": "Email address"},
                    "hashed_password": {"type": "string", "description": "Hashed password", "sensitive": True},
                    "roles": {"type": "array", "description": "User roles"},
                    "is_active": {"type": "boolean", "description": "Active status"},
                    "profile_id": {"type": "ObjectId", "description": "Profile reference"},
                    "created_at": {"type": "datetime", "description": "Creation date"},
                    "updated_at": {"type": "datetime", "description": "Last update date"},
                    "onboarding_completed": {"type": "boolean", "description": "Onboarding status"},
                    "password_last_changed_at": {"type": "datetime", "description": "Password change date"}
                },
                "relationships": {
                    "profiles": {"local_field": "profile_id", "foreign_field": "_id", "type": "one_to_one"},
                    "teaching_assignments": {"local_field": "_id", "foreign_field": "teacher_id", "type": "one_to_many"},
                    "classes": {"local_field": "_id", "foreign_field": "homeroom_teacher_id", "type": "one_to_many"},
                    "question_banks": {"local_field": "_id", "foreign_field": "created_by_teacher_id", "type": "one_to_many"},
                    "question_submissions": {"local_field": "_id", "foreign_field": "submitted_by_teacher_id", "type": "one_to_many"},
                    "question_sets": {"local_field": "_id", "foreign_field": "created_by_coordinator_id", "type": "one_to_many"},
                    "exam_sessions": {"local_field": "_id", "foreign_field": "student_id", "type": "one_to_many"},
                    "expertise_programs": {"local_field": "_id", "foreign_field": "head_of_department_id", "type": "one_to_many"}
                }
            },
            "profiles": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Profile ID"},
                    "full_name": {"type": "string", "description": "Full name"},
                    "gender": {"type": "string", "description": "Gender"},
                    "birth_date": {"type": "datetime", "description": "Birth date"},
                    "birth_place": {"type": "string", "description": "Birth place"},
                    "address": {"type": "string", "description": "Address"},
                    "phone_number": {"type": "string", "description": "Phone number"},
                    "department_id": {"type": "ObjectId", "description": "Department reference"},
                    "user_id": {"type": "ObjectId", "description": "User reference"},
                    "profile_picture_url": {"type": "string", "description": "Profile picture URL"},
                    "profile_picture_key": {"type": "string", "description": "Profile picture key"},
                    "start_year": {"type": "number", "description": "Start year"},
                    "end_year": {"type": "number", "description": "End year"},
                    "created_at": {"type": "datetime", "description": "Creation date"},
                    "updated_at": {"type": "datetime", "description": "Last update date"}
                },
                "relationships": {
                    "users": {"local_field": "user_id", "foreign_field": "_id", "type": "one_to_one"},
                    "expertise_programs": {"local_field": "department_id", "foreign_field": "_id", "type": "many_to_one"}
                }
            },
            "classes": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Class ID"},
                    "name": {"type": "string", "description": "Class name"},
                    "grade_level": {"type": "number", "description": "Grade level"},
                    "academic_year": {"type": "string", "description": "Academic year"},
                    "expertise_id": {"type": "ObjectId", "description": "Expertise program reference"},
                    "homeroom_teacher_id": {"type": "ObjectId", "description": "Homeroom teacher reference"}
                },
                "relationships": {
                    "expertise_programs": {"local_field": "expertise_id", "foreign_field": "_id", "type": "many_to_one"},
                    "users": {"local_field": "homeroom_teacher_id", "foreign_field": "_id", "type": "many_to_one"},
                    "teaching_assignments": {"local_field": "_id", "foreign_field": "class_id", "type": "one_to_many"}
                }
            },
            "expertise_programs": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Expertise program ID"},
                    "name": {"type": "string", "description": "Program name"},
                    "abbreviation": {"type": "string", "description": "Program abbreviation"},
                    "description": {"type": "string", "description": "Program description"},
                    "head_of_department_id": {"type": "ObjectId", "description": "Department head reference"}
                },
                "relationships": {
                    "users": {"local_field": "head_of_department_id", "foreign_field": "_id", "type": "many_to_one"},
                    "profiles": {"local_field": "_id", "foreign_field": "department_id", "type": "one_to_many"},
                    "classes": {"local_field": "_id", "foreign_field": "expertise_id", "type": "one_to_many"}
                }
            },
            "subjects": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Subject ID"},
                    "name": {"type": "string", "description": "Subject name"},
                    "code": {"type": "string", "description": "Subject code"},
                    "description": {"type": "string", "description": "Subject description"},
                    "created_at": {"type": "datetime", "description": "Creation date"},
                    "updated_at": {"type": "datetime", "description": "Last update date"}
                },
                "relationships": {
                    "teaching_assignments": {"local_field": "_id", "foreign_field": "subject_id", "type": "one_to_many"},
                    "question_banks": {"local_field": "_id", "foreign_field": "subject_id", "type": "one_to_many"},
                    "question_sets": {"local_field": "_id", "foreign_field": "subject_id", "type": "one_to_many"}
                }
            },
            "teaching_assignments": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Teaching assignment ID"},
                    "class_id": {"type": "ObjectId", "description": "Class reference"},
                    "subject_id": {"type": "ObjectId", "description": "Subject reference"},
                    "teacher_id": {"type": "ObjectId", "description": "Teacher reference"},
                    "academic_period_id": {"type": "ObjectId", "description": "Academic period reference"}
                },
                "relationships": {
                    "classes": {"local_field": "class_id", "foreign_field": "_id", "type": "many_to_one"},
                    "subjects": {"local_field": "subject_id", "foreign_field": "_id", "type": "many_to_one"},
                    "users": {"local_field": "teacher_id", "foreign_field": "_id", "type": "many_to_one"},
                    "academic_periods": {"local_field": "academic_period_id", "foreign_field": "_id", "type": "many_to_one"},
                    "exams": {"local_field": "_id", "foreign_field": "teaching_assignment_id", "type": "one_to_many"}
                }
            },
            "academic_periods": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Academic period ID"},
                    "year": {"type": "string", "description": "Academic year"},
                    "semester": {"type": "string", "description": "Semester"},
                    "status": {"type": "string", "description": "Period status"},
                    "start_date": {"type": "datetime", "description": "Start date"},
                    "end_date": {"type": "datetime", "description": "End date"},
                    "created_at": {"type": "datetime", "description": "Creation date"},
                    "updated_at": {"type": "datetime", "description": "Last update date"}
                },
                "relationships": {
                    "teaching_assignments": {"local_field": "_id", "foreign_field": "academic_period_id", "type": "one_to_many"},
                    "question_submissions": {"local_field": "_id", "foreign_field": "academic_period_id", "type": "one_to_many"},
                    "exams": {"local_field": "_id", "foreign_field": "academic_period_id", "type": "one_to_many"}
                }
            },
            "question_banks": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Question ID"},
                    "subject_id": {"type": "ObjectId", "description": "Subject reference"},
                    "created_by_teacher_id": {"type": "ObjectId", "description": "Creator teacher reference"},
                    "question_type": {"type": "string", "description": "Question type"},
                    "difficulty": {"type": "string", "description": "Difficulty level"},
                    "question_text": {"type": "string", "description": "Question text"},
                    "options": {"type": "array", "description": "Answer options"},
                    "points": {"type": "number", "description": "Points value"},
                    "tags": {"type": "array", "description": "Question tags"}
                },
                "relationships": {
                    "subjects": {"local_field": "subject_id", "foreign_field": "_id", "type": "many_to_one"},
                    "users": {"local_field": "created_by_teacher_id", "foreign_field": "_id", "type": "many_to_one"},
                    "question_submissions": {"local_field": "_id", "foreign_field": "question_id", "type": "one_to_many"}
                }
            },
            "question_submissions": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Submission ID"},
                    "question_id": {"type": "ObjectId", "description": "Question reference"},
                    "submitted_by_teacher_id": {"type": "ObjectId", "description": "Submitter teacher reference"},
                    "coordination_assignment_id": {"type": "ObjectId", "description": "Coordination assignment reference"},
                    "academic_period_id": {"type": "ObjectId", "description": "Academic period reference"},
                    "purpose": {"type": "string", "description": "Submission purpose"},
                    "status": {"type": "string", "description": "Submission status"},
                    "created_at": {"type": "datetime", "description": "Creation date"},
                    "updated_at": {"type": "datetime", "description": "Last update date"}
                },
                "relationships": {
                    "question_banks": {"local_field": "question_id", "foreign_field": "_id", "type": "many_to_one"},
                    "users": {"local_field": "submitted_by_teacher_id", "foreign_field": "_id", "type": "many_to_one"},
                    "academic_periods": {"local_field": "academic_period_id", "foreign_field": "_id", "type": "many_to_one"}
                }
            },
            "question_sets": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Question set ID"},
                    "name": {"type": "string", "description": "Set name"},
                    "subject_id": {"type": "ObjectId", "description": "Subject reference"},
                    "grade_level": {"type": "number", "description": "Grade level"},
                    "created_by_coordinator_id": {"type": "ObjectId", "description": "Creator coordinator reference"},
                    "question_ids": {"type": "array", "description": "Question references"},
                    "status": {"type": "string", "description": "Set status"},
                    "is_public": {"type": "boolean", "description": "Public visibility"},
                    "access_permissions": {"type": "object", "description": "Access permissions"},
                    "metadata": {"type": "object", "description": "Set metadata"},
                    "description": {"type": "string", "description": "Set description"},
                    "version": {"type": "number", "description": "Version number"},
                    "published_date": {"type": "datetime", "description": "Publication date"},
                    "tags": {"type": "array", "description": "Set tags"},
                    "created_at": {"type": "datetime", "description": "Creation date"},
                    "updated_at": {"type": "datetime", "description": "Last update date"}
                },
                "relationships": {
                    "subjects": {"local_field": "subject_id", "foreign_field": "_id", "type": "many_to_one"},
                    "users": {"local_field": "created_by_coordinator_id", "foreign_field": "_id", "type": "many_to_one"}
                }
            },
            "exams": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Exam ID"},
                    "title": {"type": "string", "description": "Exam title"},
                    "exam_type": {"type": "string", "description": "Exam type"},
                    "duration_minutes": {"type": "number", "description": "Duration in minutes"},
                    "availability_start_time": {"type": "datetime", "description": "Start availability"},
                    "availability_end_time": {"type": "datetime", "description": "End availability"},
                    "status": {"type": "string", "description": "Exam status"},
                    "settings": {"type": "object", "description": "Exam settings"},
                    "academic_period_id": {"type": "ObjectId", "description": "Academic period reference"},
                    "teaching_assignment_id": {"type": "ObjectId", "description": "Teaching assignment reference"},
                    "question_ids": {"type": "array", "description": "Question references"},
                    "proctor_ids": {"type": "array", "description": "Proctor references"},
                    "updated_at": {"type": "datetime", "description": "Last update date"},
                    "completed_at": {"type": "datetime", "description": "Completion date"},
                    "completed_by": {"type": "ObjectId", "description": "Completed by reference"}
                },
                "relationships": {
                    "academic_periods": {"local_field": "academic_period_id", "foreign_field": "_id", "type": "many_to_one"},
                    "teaching_assignments": {"local_field": "teaching_assignment_id", "foreign_field": "_id", "type": "many_to_one"},
                    "exam_sessions": {"local_field": "_id", "foreign_field": "exam_id", "type": "one_to_many"}
                }
            },
            "exam_sessions": {
                "fields": {
                    "_id": {"type": "ObjectId", "description": "Session ID"},
                    "exam_id": {"type": "ObjectId", "description": "Exam reference"},
                    "student_id": {"type": "ObjectId", "description": "Student reference"},
                    "status": {"type": "string", "description": "Session status"},
                    "started_at": {"type": "datetime", "description": "Start time"},
                    "submitted_at": {"type": "datetime", "description": "Submission time"},
                    "score": {"type": "number", "description": "Session score"},
                    "answers": {"type": "object", "description": "Student answers"},
                    "question_map": {"type": "array", "description": "Question mapping"},
                    "interaction_logs": {"type": "array", "description": "Interaction logs"},
                    "client_metadata": {"type": "object", "description": "Client metadata"},
                    "completion_stats": {"type": "object", "description": "Completion statistics"},
                    "fraud_score": {"type": "number", "description": "Fraud detection score"},
                    "is_flagged_for_review": {"type": "boolean", "description": "Review flag"},
                    "violations": {"type": "array", "description": "Violation records"}
                },
                "relationships": {
                    "exams": {"local_field": "exam_id", "foreign_field": "_id", "type": "many_to_one"},
                    "users": {"local_field": "student_id", "foreign_field": "_id", "type": "many_to_one"}
                }
            }
        }
    
    def get_collection_fields(self, collection: str) -> Dict[str, Any]:
        """Get all fields for a specific collection"""
        return self.collection_schemas.get(collection, {}).get("fields", {})
    
    def get_collection_relationships(self, collection: str) -> Dict[str, Any]:
        """Get all relationships for a specific collection"""
        return self.collection_schemas.get(collection, {}).get("relationships", {})
    
    def get_all_collections(self) -> List[str]:
        """Get list of all available collections"""
        return list(self.collection_schemas.keys())
    
    def get_possible_joins(self, collection: str) -> List[Dict[str, Any]]:
        """Get all possible joins from a collection"""
        relationships = self.get_collection_relationships(collection)
        joins = []
        
        for target_collection, rel_info in relationships.items():
            joins.append({
                "collection": target_collection,
                "suggested_local_field": rel_info["local_field"],
                "suggested_foreign_field": rel_info["foreign_field"],
                "relationship_type": rel_info["type"],
                "description": f"Join {collection} to {target_collection} via {rel_info['local_field']}"
            })
        
        return joins
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """Check if field contains sensitive data"""
        sensitive_patterns = [
            "password", "token", "secret", "private", "internal", 
            "hashed_password", "reset_token", "api_key", "hash"
        ]
        return any(pattern in field_name.lower() for pattern in sensitive_patterns)

# Global instance
database_schema = DatabaseSchemaManager()
