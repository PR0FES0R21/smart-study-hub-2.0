# ==============================================================================
# File: app/core/field_mapping.py
# Deskripsi: Field alias mapping system untuk export yang lebih user-friendly
# ==============================================================================
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FieldMappingSystem:
    """System untuk mapping field names ke aliases yang lebih user-friendly"""
    
    def __init__(self):
        # Field aliases dalam bahasa Indonesia
        self.field_aliases = {
            # Users collection
            "_id": "ID",
            "login_id": "NIS/NIP",
            "email": "Email",
            "roles": "Peran",
            "is_active": "Status Aktif",
            "created_at": "Tanggal Dibuat",
            "updated_at": "Tanggal Diperbarui",
            
            # Profiles collection
            "profile._id": "ID Profil",
            "profile.full_name": "Nama Lengkap",
            "profile.gender": "Jenis Kelamin",
            "profile.birth_date": "Tanggal Lahir",
            "profile.birth_place": "Tempat Lahir",
            "profile.address": "Alamat",
            "profile.phone_number": "Nomor Telepon",
            "profile.start_year": "Tahun Masuk",
            "profile.end_year": "Tahun Lulus",
            
            # Classes collection (nested)
            "profile.class_detail._id": "ID Kelas",
            "profile.class_detail.name": "Nama Kelas",
            "profile.class_detail.grade_level": "Tingkat Kelas",
            "profile.class_detail.academic_year": "Tahun Akademik",
            
            # Expertise Programs collection (deeply nested)
            "profile.class_detail.expertise._id": "ID Jurusan",
            "profile.class_detail.expertise.name": "Nama Jurusan",
            "profile.class_detail.expertise.abbreviation": "Singkatan Jurusan",
            "profile.class_detail.expertise.description": "Deskripsi Jurusan",
            
            # Teaching Assignments
            "teaching_assignment.class_id": "ID Kelas Mengajar",
            "teaching_assignment.subject_id": "ID Mata Pelajaran",
            "teaching_assignment.teacher_id": "ID Guru",
            "teaching_assignment.academic_period_id": "ID Periode Akademik",
            
            # Question Banks
            "question_bank.question_type": "Jenis Soal",
            "question_bank.difficulty": "Tingkat Kesulitan",
            "question_bank.question_text": "Teks Soal",
            "question_bank.points": "Poin Soal",
            "question_bank.tags": "Tag Soal",
            
            # Question Sets
            "question_set.name": "Nama Set Soal",
            "question_set.grade_level": "Tingkat Kelas",
            "question_set.status": "Status Set",
            "question_set.is_public": "Akses Publik",
            "question_set.total_questions": "Total Soal",
            "question_set.total_points": "Total Poin",
            
            # Exams
            "exam.title": "Judul Ujian",
            "exam.exam_type": "Jenis Ujian",
            "exam.duration_minutes": "Durasi (Menit)",
            "exam.availability_start_time": "Mulai Tersedia",
            "exam.availability_end_time": "Selesai Tersedia",
            "exam.status": "Status Ujian",
            
            # Common fields
            "created_by": "Dibuat Oleh",
            "updated_by": "Diperbarui Oleh",
            "deleted_at": "Tanggal Dihapus",
            "archived_at": "Tanggal Diarsipkan"
        }
        
        # Fields yang biasanya tidak perlu di export (ObjectIds)
        self.id_fields = [
            "_id", "profile._id", "profile.class_detail._id", 
            "profile.class_detail.expertise._id", "user_id", "profile_id",
            "class_id", "subject_id", "teacher_id", "academic_period_id",
            "created_by_teacher_id", "created_by_coordinator_id",
            "head_of_department_id", "homeroom_teacher_id"
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
        """Get available fields for collection with their aliases"""
        available_fields = []
        
        for field_path, alias in self.field_aliases.items():
            if field_path.startswith(collection) or '.' not in field_path:
                available_fields.append({
                    "field": field_path,
                    "alias": alias,
                    "category": self._get_field_category(field_path)
                })
        
        return available_fields
    
    def _get_field_category(self, field_path: str) -> str:
        """Get category for field"""
        for category, fields in self.field_categories.items():
            if field_path in fields:
                return category
        return "other"
    
    def create_smart_field_suggestions(self, main_collection: str) -> Dict[str, List[str]]:
        """Create smart field suggestions based on collection"""
        suggestions = {
            "recommended": [],
            "optional": [],
            "advanced": []
        }
        
        if main_collection == "users":
            suggestions["recommended"] = [
                "login_id", "email", "profile.full_name", 
                "profile.class_detail.name", "profile.class_detail.grade_level"
            ]
            suggestions["optional"] = [
                "profile.gender", "profile.birth_date", 
                "profile.class_detail.expertise.name"
            ]
            suggestions["advanced"] = [
                "is_active", "created_at", "profile.phone_number",
                "profile.address", "profile.class_detail.academic_year"
            ]
        
        return suggestions

# Global instance
field_mapper = FieldMappingSystem()
