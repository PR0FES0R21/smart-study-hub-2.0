# ==============================================================================
# File: app/core/field_mapping.py
# Deskripsi: Field alias mapping system untuk export yang lebih user-friendly
# ==============================================================================
from typing import Dict, List, Optional, Any
from app.core.database_schema import database_schema
import logging

logger = logging.getLogger(__name__)

class FieldMappingSystem:
    """System untuk mapping field names ke aliases yang lebih user-friendly"""
    
    def __init__(self):
        # Collection-specific field aliases dalam bahasa Indonesia
        self.collection_fields = {
            "users": {
                "_id": "ID",
                "login_id": "NIS/NIP",
                "email": "Email",
                "roles": "Peran",
                "is_active": "Status Aktif",
                "profile_id": "ID Profil",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui",
                "onboarding_completed": "Onboarding Selesai",
                "password_last_changed_at": "Password Terakhir Diubah"
            },
            "profiles": {
                "_id": "ID",
                "full_name": "Nama Lengkap",
                "gender": "Jenis Kelamin",
                "birth_date": "Tanggal Lahir",
                "birth_place": "Tempat Lahir",
                "address": "Alamat",
                "phone_number": "Nomor Telepon",
                "start_year": "Tahun Masuk",
                "end_year": "Tahun Lulus",
                "user_id": "ID User",
                "class_id": "ID Kelas",
                "department_id": "ID Jurusan",
                "profile_picture_url": "URL Foto Profil",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui"
            },
            "classes": {
                "_id": "ID",
                "name": "Nama Kelas",
                "grade_level": "Tingkat Kelas",
                "academic_year": "Tahun Akademik",
                "expertise_id": "ID Jurusan",
                "homeroom_teacher_id": "ID Wali Kelas"
            },
            "expertise_programs": {
                "_id": "ID",
                "name": "Nama Jurusan",
                "abbreviation": "Singkatan",
                "description": "Deskripsi",
                "head_of_department_id": "ID Kepala Jurusan"
            },
            "subjects": {
                "_id": "ID",
                "name": "Nama Mata Pelajaran",
                "code": "Kode Mata Pelajaran",
                "description": "Deskripsi",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui"
            },
            "teaching_assignments": {
                "_id": "ID",
                "class_id": "ID Kelas",
                "subject_id": "ID Mata Pelajaran",
                "teacher_id": "ID Guru",
                "academic_period_id": "ID Periode Akademik"
            },
            "academic_periods": {
                "_id": "ID",
                "year": "Tahun Akademik",
                "semester": "Semester",
                "status": "Status",
                "start_date": "Tanggal Mulai",
                "end_date": "Tanggal Selesai",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui"
            },
            "question_banks": {
                "_id": "ID",
                "subject_id": "ID Mata Pelajaran",
                "created_by_teacher_id": "ID Pembuat",
                "question_type": "Jenis Soal",
                "difficulty": "Tingkat Kesulitan",
                "question_text": "Teks Soal",
                "options": "Pilihan Jawaban",
                "points": "Poin Soal",
                "tags": "Tag Soal"
            },
            "question_submissions": {
                "_id": "ID",
                "question_id": "ID Soal",
                "submitted_by_teacher_id": "ID Guru Pengirim",
                "coordination_assignment_id": "ID Tugas Koordinasi",
                "academic_period_id": "ID Periode Akademik",
                "purpose": "Tujuan",
                "status": "Status",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui"
            },
            "question_sets": {
                "_id": "ID",
                "name": "Nama Set Soal",
                "subject_id": "ID Mata Pelajaran",
                "grade_level": "Tingkat Kelas",
                "created_by_coordinator_id": "ID Pembuat",
                "question_ids": "ID Soal-soal",
                "status": "Status Set",
                "is_public": "Akses Publik",
                "access_permissions": "Izin Akses",
                "metadata": "Metadata",
                "description": "Deskripsi",
                "version": "Versi",
                "published_date": "Tanggal Publikasi",
                "tags": "Tag",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui"
            },
            "exams": {
                "_id": "ID",
                "title": "Judul Ujian",
                "exam_type": "Jenis Ujian",
                "duration_minutes": "Durasi (Menit)",
                "availability_start_time": "Mulai Tersedia",
                "availability_end_time": "Selesai Tersedia",
                "status": "Status Ujian",
                "academic_period_id": "ID Periode Akademik",
                "teaching_assignment_id": "ID Penugasan Mengajar",
                "question_ids": "ID Soal",
                "proctor_ids": "ID Pengawas",
                "updated_at": "Tanggal Diperbarui",
                "completed_at": "Tanggal Selesai"
            },
            "exam_sessions": {
                "_id": "ID",
                "exam_id": "ID Ujian",
                "student_id": "ID Siswa",
                "status": "Status",
                "started_at": "Waktu Mulai",
                "submitted_at": "Waktu Submit",
                "score": "Skor",
                "answers": "Jawaban",
                "question_map": "Peta Soal",
                "interaction_logs": "Log Interaksi",
                "client_metadata": "Metadata Klien",
                "completion_stats": "Statistik Penyelesaian",
                "fraud_score": "Skor Kecurangan",
                "is_flagged_for_review": "Ditandai untuk Review",
                "violations": "Pelanggaran"
            },
            "academic_periods": {
                "_id": "ID",
                "year": "Tahun Akademik",
                "semester": "Semester", 
                "status": "Status",
                "start_date": "Tanggal Mulai",
                "end_date": "Tanggal Selesai",
                "created_at": "Tanggal Dibuat",
                "updated_at": "Tanggal Diperbarui"
            }
        }
        
        # Legacy field aliases untuk joined data (digunakan saat export)
        self.field_aliases = {
            # Users collection
            "_id": "ID",
            "login_id": "NIS/NIP",
            "email": "Email",
            "roles": "Peran",
            "is_active": "Status Aktif",
            "created_at": "Tanggal Dibuat",
            "updated_at": "Tanggal Diperbarui",
            
            # Profiles collection (dengan prefix untuk joined data)
            "profile._id": "ID Profil",
            "profile.full_name": "Nama Lengkap",
            "profile.gender": "Jenis Kelamin",
            "profile.birth_date": "Tanggal Lahir",
            "profile.birth_place": "Tempat Lahir",
            "profile.address": "Alamat",
            "profile.phone_number": "Nomor Telepon",
            "profile.start_year": "Tahun Masuk",
            "profile.end_year": "Tahun Lulus",
            
            # Classes collection (dengan prefix untuk joined data)
            "profile.class_detail._id": "ID Kelas",
            "profile.class_detail.name": "Nama Kelas",
            "profile.class_detail.grade_level": "Tingkat Kelas",
            "profile.class_detail.academic_year": "Tahun Akademik",
            
            # Expertise Programs collection (dengan prefix untuk joined data)
            "profile.class_detail.expertise._id": "ID Jurusan",
            "profile.class_detail.expertise.name": "Nama Jurusan",
            "profile.class_detail.expertise.abbreviation": "Singkatan Jurusan",
            "profile.class_detail.expertise.description": "Deskripsi Jurusan",
            
            # Common fields
            "created_by": "Dibuat Oleh",
            "updated_by": "Diperbarui Oleh",
            "deleted_at": "Tanggal Dihapus",
            "archived_at": "Tanggal Diarsipkan"
        }
        
        # Field categories per collection
        self.collection_categories = {
            "users": {
                "identity": ["_id", "login_id", "email"],
                "access": ["roles", "is_active", "onboarding_completed"],
                "relationships": ["profile_id"],
                "timestamps": ["created_at", "updated_at", "password_last_changed_at"]
            },
            "profiles": {
                "identity": ["_id", "full_name", "gender"],
                "personal": ["birth_date", "birth_place", "address", "phone_number", "profile_picture_url"],
                "academic": ["start_year", "end_year"],
                "relationships": ["user_id", "class_id", "department_id"],
                "timestamps": ["created_at", "updated_at"]
            },
            "classes": {
                "identity": ["_id", "name", "grade_level"],
                "academic": ["academic_year"],
                "relationships": ["expertise_id", "homeroom_teacher_id"]
            },
            "expertise_programs": {
                "identity": ["_id", "name", "abbreviation"],
                "description": ["description"],
                "relationships": ["head_of_department_id"]
            }
        }
        
        # Fields yang biasanya tidak perlu di export (ObjectIds)
        self.id_fields = [
            "_id", "id", "profile._id", "profile.class_detail._id", 
            "profile.class_detail.expertise._id", "user_id", "profile_id",
            "class_id", "subject_id", "teacher_id", "academic_period_id",
            "created_by_teacher_id", "created_by_coordinator_id",
            "head_of_department_id", "homeroom_teacher_id",
            # Additional ID fields that might appear in joined data
            "profile.id", "class_detail.id", "class_detail._id",
            "expertise.id", "expertise._id", "department_id",
            "student_id", "exam_id", "question_id", "session_id",
            # Common ID patterns
            "Id", "ID", "profile.Id", "class_detail.Id", "expertise.Id"
        ]
        
        # Field categories untuk grouping
        self.field_categories = {
            "user_info": ["login_id", "email", "roles", "is_active"],
            "profile_info": ["profile.full_name", "profile.gender", "profile.birth_date", 
                           "profile.birth_place", "profile.address", "profile.phone_number"],
            "academic_info": ["profile.class_detail.name", "profile.class_detail.grade_level",
                            "profile.class_detail.expertise.name", "profile.class_detail.expertise.abbreviation"],
            "timestamps": ["created_at", "updated_at", "deleted_at", "archived_at"]
        }
    
    def get_field_alias(self, field_path: str) -> str:
        """Get user-friendly alias for field path"""
        return self.field_aliases.get(field_path, self._generate_fallback_alias(field_path))
    
    def _generate_fallback_alias(self, field_path: str) -> str:
        """Generate fallback alias for unmapped fields"""
        # Remove collection prefixes and convert to title case
        clean_path = field_path.split('.')[-1]  # Get last part
        clean_path = clean_path.replace('_', ' ')  # Replace underscores
        return clean_path.title()  # Convert to title case
    
    def should_exclude_field(self, field_path: str, exclude_ids: bool = True) -> bool:
        """Check if field should be excluded from export"""
        if exclude_ids and field_path in self.id_fields:
            return True
        return False
    
    def process_export_headers(self, field_paths: List[str], 
                              exclude_ids: bool = True, 
                              use_aliases: bool = True) -> Dict[str, str]:
        """Process field paths to create header mapping"""
        header_mapping = {}
        
        for field_path in field_paths:
            # Skip if should be excluded
            if self.should_exclude_field(field_path, exclude_ids):
                continue
                
            # Get alias or original name
            if use_aliases:
                header = self.get_field_alias(field_path)
            else:
                header = field_path
            
            header_mapping[field_path] = header
        
        return header_mapping
    
    def flatten_nested_data(self, data: List[Dict[str, Any]], 
                          header_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Flatten nested data and apply header mapping"""
        flattened_data = []
        
        for record in data:
            flat_record = {}
            flattened = self._flatten_dict(record)
            
            # Apply header mapping
            for original_key, alias in header_mapping.items():
                if original_key in flattened:
                    flat_record[alias] = flattened[original_key]
            
            flattened_data.append(flat_record)
        
        return flattened_data
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Recursively flatten nested dictionary"""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                # Handle array of objects (take first item for structure)
                items.extend(self._flatten_dict(v[0], new_key, sep=sep).items())
            else:
                # Handle special cases
                if isinstance(v, list):
                    # Convert lists to comma-separated strings
                    v = ', '.join(str(item) for item in v)
                elif hasattr(v, 'isoformat'):
                    # Convert datetime to string
                    v = v.isoformat()
                
                items.append((new_key, v))
        
        return dict(items)
    
    def get_available_fields_with_aliases(self, collection: str) -> List[Dict[str, str]]:
        """Get available fields for specific collection with their aliases - COLLECTION SPECIFIC ONLY"""
        available_fields = []
        
        # Get fields from database schema
        schema_fields = database_schema.get_collection_fields(collection)
        collection_aliases = self.collection_fields.get(collection, {})
        
        for field_name, field_info in schema_fields.items():
            # Skip sensitive fields unless explicitly requested
            if field_info.get("sensitive", False):
                continue
                
            alias = collection_aliases.get(field_name, field_name.replace("_", " ").title())
            
            available_fields.append({
                "field": field_name,
                "alias": alias,
                "type": field_info.get("type", "unknown"),
                "description": field_info.get("description", ""),
                "category": self._get_collection_field_category(collection, field_name),
                "sensitive": field_info.get("sensitive", False)
            })
        
        return available_fields
    
    def _get_collection_field_category(self, collection: str, field_name: str) -> str:
        """Get category for field within specific collection"""
        if collection in self.collection_categories:
            categories = self.collection_categories[collection]
            
            for category_name, fields in categories.items():
                if field_name in fields:
                    return category_name
        
        return "other"
    
    def _get_field_category(self, field_path: str) -> str:
        """Get category for field"""
        for category, fields in self.field_categories.items():
            if field_path in fields:
                return category
        return "other"
    
    def create_smart_field_suggestions(self, collection: str) -> Dict[str, List[Dict[str, Any]]]:
        """Create smart field suggestions based on collection - COLLECTION SPECIFIC ONLY"""
        suggestions = {
            "recommended": [],
            "optional": [],
            "advanced": []
        }
        
        # Get all fields from schema
        schema_fields = database_schema.get_collection_fields(collection)
        collection_aliases = self.collection_fields.get(collection, {})
        
        # Define field priority patterns
        recommended_patterns = ["name", "title", "email", "login_id", "full_name", "status", "score"]
        optional_patterns = ["date", "time", "level", "year", "type", "gender", "phone", "address"]
        advanced_patterns = ["_id", "created_at", "updated_at", "metadata", "settings", "permissions"]
        
        for field_name, field_info in schema_fields.items():
            # Skip sensitive fields
            if field_info.get("sensitive", False):
                continue
            
            alias = collection_aliases.get(field_name, field_name.replace("_", " ").title())
            
            field_suggestion = {
                "field": field_name,
                "alias": alias,
                "type": field_info.get("type", "unknown"),
                "description": field_info.get("description", "")
            }
            
            # Categorize based on field name patterns
            field_lower = field_name.lower()
            
            if any(pattern in field_lower for pattern in recommended_patterns):
                suggestions["recommended"].append(field_suggestion)
            elif any(pattern in field_lower for pattern in optional_patterns):
                suggestions["optional"].append(field_suggestion)
            elif any(pattern in field_lower for pattern in advanced_patterns):
                suggestions["advanced"].append(field_suggestion)
            else:
                # Default to optional for unknown patterns
                suggestions["optional"].append(field_suggestion)
        
        return suggestions

# Global instance
field_mapper = FieldMappingSystem()
