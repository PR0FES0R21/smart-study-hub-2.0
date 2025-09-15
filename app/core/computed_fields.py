# ==============================================================================
# File: app/core/computed_fields.py
# Deskripsi: System untuk computed fields dan field concatenation
# ==============================================================================
from typing import Dict, List, Optional, Any, Callable
import logging
import re

logger = logging.getLogger(__name__)

class ComputedFieldsSystem:
    """System untuk menangani computed fields dan field concatenation"""
    
    def __init__(self):
        # Predefined computed field templates
        self.computed_field_templates = {
            "class_full_name": {
                "alias": "Nama Kelas Lengkap",
                "template": "{grade_level} {abbreviation} {class_name}",
                "fields": [
                    "profile.class_detail.grade_level",
                    "profile.class_detail.expertise.abbreviation", 
                    "profile.class_detail.name"
                ],
                "example": "12 TKJ 2"
            },
            "student_identity": {
                "alias": "Identitas Siswa",
                "template": "{nis} - {full_name}",
                "fields": [
                    "login_id",
                    "profile.full_name"
                ],
                "example": "79111967 - Alexander Grahambel"
            },
            "academic_info": {
                "alias": "Info Akademik", 
                "template": "{full_name} ({grade_level} {abbreviation})",
                "fields": [
                    "profile.full_name",
                    "profile.class_detail.grade_level",
                    "profile.class_detail.expertise.abbreviation"
                ],
                "example": "Alexander Grahambel (12 TKJ)"
            },
            "contact_info": {
                "alias": "Info Kontak",
                "template": "{full_name} - {email} - {phone}",
                "fields": [
                    "profile.full_name",
                    "email", 
                    "profile.phone_number"
                ],
                "example": "Alexander Grahambel - alex@gmail.com - 08123456789"
            }
        }
        
        # Field formatters for special cases
        self.field_formatters = {
            "phone_number": lambda x: self._format_phone_number(x),
            "birth_date": lambda x: self._format_date(x),
            "created_at": lambda x: self._format_datetime(x)
        }
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number"""
        if not phone:
            return ""
        # Remove spaces and add formatting
        clean_phone = phone.replace(" ", "").replace("-", "")
        if len(clean_phone) >= 10:
            return f"{clean_phone[:4]}-{clean_phone[4:8]}-{clean_phone[8:]}"
        return phone
    
    def _format_date(self, date_val: Any) -> str:
        """Format date"""
        if not date_val:
            return ""
        if hasattr(date_val, 'strftime'):
            return date_val.strftime("%d/%m/%Y")
        return str(date_val)
    
    def _format_datetime(self, datetime_val: Any) -> str:
        """Format datetime"""
        if not datetime_val:
            return ""
        if hasattr(datetime_val, 'strftime'):
            return datetime_val.strftime("%d/%m/%Y %H:%M")
        return str(datetime_val)
    
    def create_custom_computed_field(self, name: str, alias: str, template: str, 
                                   fields: List[str]) -> Dict[str, Any]:
        """Create custom computed field definition"""
        return {
            "name": name,
            "alias": alias,
            "template": template,
            "fields": fields,
            "custom": True
        }
    
    def get_field_value_from_path(self, data: Dict[str, Any], field_path: str) -> str:
        """Extract field value from nested data structure"""
        try:
            # Split field path and navigate through nested structure
            path_parts = field_path.split('.')
            value = data
            
            for part in path_parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                elif isinstance(value, list) and len(value) > 0:
                    # If it's a list, take first item (from joins)
                    value = value[0].get(part, "") if isinstance(value[0], dict) else ""
                else:
                    value = ""
                    break
            
            # Apply field formatter if exists
            field_name = path_parts[-1]  # Get last part of path
            if field_name in self.field_formatters:
                value = self.field_formatters[field_name](value)
            
            return str(value) if value is not None else ""
            
        except Exception as e:
            logger.warning(f"Error extracting field {field_path}: {e}")
            return ""
    
    def compute_field_value(self, computed_field: Dict[str, Any], 
                          record_data: Dict[str, Any]) -> str:
        """Compute the value for a computed field"""
        try:
            template = computed_field["template"]
            fields = computed_field["fields"]
            
            # Extract values for all required fields
            field_values = {}
            
            for field_path in fields:
                # Get field value from nested data
                value = self.get_field_value_from_path(record_data, field_path)
                
                # Create template variable name from field path
                # e.g., "profile.class_detail.grade_level" -> "grade_level"
                # e.g., "profile.full_name" -> "full_name"
                # e.g., "login_id" -> "nis" (special mapping)
                var_name = self._get_template_variable_name(field_path)
                field_values[var_name] = value
            
            # Replace template variables with actual values
            result = template
            for var_name, value in field_values.items():
                placeholder = f"{{{var_name}}}"
                result = result.replace(placeholder, str(value))
            
            # Clean up extra spaces
            result = ' '.join(result.split())
            
            return result
            
        except Exception as e:
            logger.error(f"Error computing field value: {e}")
            return ""
    
    def _get_template_variable_name(self, field_path: str) -> str:
        """Map field path to template variable name"""
        # Special mappings for common cases
        field_mappings = {
            "login_id": "nis",
            "profile.full_name": "full_name",
            "profile.class_detail.name": "class_name",
            "profile.class_detail.grade_level": "grade_level", 
            "profile.class_detail.expertise.name": "expertise_name",
            "profile.class_detail.expertise.abbreviation": "abbreviation",
            "profile.phone_number": "phone",
            "email": "email",
            "profile.gender": "gender",
            "profile.birth_date": "birth_date"
        }
        
        return field_mappings.get(field_path, field_path.split('.')[-1])
    
    def add_computed_fields_to_data(self, data: List[Dict[str, Any]], 
                                   computed_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add computed fields to export data"""
        if not computed_fields:
            return data
        
        enhanced_data = []
        
        for record in data:
            enhanced_record = record.copy()
            
            # Add computed fields
            for computed_field in computed_fields:
                field_alias = computed_field.get("alias", computed_field["name"])
                computed_value = self.compute_field_value(computed_field, record)
                enhanced_record[field_alias] = computed_value
            
            enhanced_data.append(enhanced_record)
        
        return enhanced_data
    
    def get_available_computed_fields(self, main_collection: str = "users") -> Dict[str, Any]:
        """Get available computed field templates"""
        available_fields = {}
        
        for field_name, field_config in self.computed_field_templates.items():
            # Check if all required fields are available for the collection
            # For now, we'll assume all are available for users collection
            if main_collection == "users":
                available_fields[field_name] = {
                    "name": field_name,
                    "alias": field_config["alias"],
                    "template": field_config["template"],
                    "required_fields": field_config["fields"],
                    "example": field_config["example"],
                    "category": self._get_computed_field_category(field_name)
                }
        
        return available_fields
    
    def _get_computed_field_category(self, field_name: str) -> str:
        """Get category for computed field"""
        category_mappings = {
            "class_full_name": "academic_info",
            "student_identity": "user_info", 
            "academic_info": "academic_info",
            "contact_info": "contact_info"
        }
        
        return category_mappings.get(field_name, "custom")
    
    def validate_computed_field_template(self, template: str, fields: List[str]) -> Dict[str, Any]:
        """Validate computed field template"""
        warnings = []
        errors = []
        
        # Find all placeholders in template
        placeholders = re.findall(r'\{([^}]+)\}', template)
        
        # Check if all placeholders have corresponding fields
        field_vars = [self._get_template_variable_name(field) for field in fields]
        
        for placeholder in placeholders:
            if placeholder not in field_vars:
                errors.append(f"Placeholder '{placeholder}' tidak memiliki field yang sesuai")
        
        # Check for unused fields
        for field_var in field_vars:
            if f"{{{field_var}}}" not in template:
                warnings.append(f"Field '{field_var}' tidak digunakan dalam template")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "placeholders": placeholders,
            "field_variables": field_vars
        }

# Global instance
computed_fields_system = ComputedFieldsSystem()
