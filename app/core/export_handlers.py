# ==============================================================================
# File: app/core/export_handlers.py
# Deskripsi: Handlers untuk export data ke berbagai format
# ==============================================================================
import json
import csv
import io
import os
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from pathlib import Path
import logging

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    print("openpyxl not installed. Excel export will not be available.")

from app.schemas.export import ExportFormat
from app.core.field_mapping import field_mapper

logger = logging.getLogger(__name__)

class ExportHandler:
    """Base class untuk export handlers"""
    
    def __init__(self):
        # Get project root directory (3 levels up from this file)
        self.project_root = Path(__file__).parent.parent.parent
        self.storage_dir = self.project_root / "storage"
        self.export_dir = self.storage_dir / "exports" 
        self.temp_dir = self.storage_dir / "temp"
        
        # Create directories if they don't exist
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # For backwards compatibility, keep temp_dir as string
        self.temp_dir_str = str(self.temp_dir)
    
    def get_user_export_dir(self, user_id: str) -> Path:
        """Get user-specific export directory"""
        user_dir = self.export_dir / "users" / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def get_export_filepath(self, filename: str, user_id: str = None) -> str:
        """Get full filepath for export (either user-specific or general)"""
        if user_id:
            export_dir = self.get_user_export_dir(user_id)
        else:
            export_dir = self.export_dir
        
        return str(export_dir / filename)
    
    def _serialize_value(self, value: Any) -> Any:
        """Convert MongoDB types to serializable types"""
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        else:
            return value
    
    def _flatten_document(self, doc: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
        """Flatten nested document for tabular export"""
        items = []
        
        for k, v in doc.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_document(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Handle arrays - take first item for structure or convert to string
                if v and isinstance(v[0], dict):
                    # Array of objects - take first object structure
                    items.extend(self._flatten_document(v[0], new_key, sep=sep).items())
                else:
                    # Array of primitives - convert to string
                    items.append((new_key, str(v) if v else ""))
            else:
                items.append((new_key, self._serialize_value(v)))
        
        return dict(items)
    
    def _get_all_fields(self, data: List[Dict[str, Any]]) -> List[str]:
        """Extract all possible field names from data"""
        fields = set()
        
        for doc in data:
            flattened = self._flatten_document(doc)
            fields.update(flattened.keys())
        
        return sorted(list(fields))

class ExcelExportHandler(ExportHandler):
    """Handler untuk export ke format Excel"""
    
    def __init__(self):
        super().__init__()
        if not HAS_OPENPYXL:
            raise ImportError("openpyxl is required for Excel export")
    
    def _format_worksheet(self, worksheet, headers: List[str]):
        """Apply formatting to worksheet"""
        # Header styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for col_num, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            
            # Auto-adjust column width
            worksheet.column_dimensions[get_column_letter(col_num)].width = min(max(len(str(header)) + 2, 10), 50)
    
    def export(self, data: List[Dict[str, Any]], filename: Optional[str] = None, 
               sheet_name: str = "Export", user_id: Optional[str] = None,
               exclude_ids: bool = True, use_aliases: bool = True, 
               include_empty_fields: bool = False, requested_fields: Optional[List[str]] = None) -> str:
        """Export data to Excel format"""
        try:
            if not data:
                raise ValueError("No data to export")
            
            if not HAS_OPENPYXL:
                raise ValueError("openpyxl is required for Excel export")
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.xlsx"
            elif not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # Create workbook and worksheet
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = sheet_name
            
            # Flatten all documents using field_mapper
            flattened_data = [self._flatten_document(doc) for doc in data]
            
            # Debug: Show sample of raw data and flattened data
            if data:
                logger.info(f"DEBUG SAMPLE RAW DATA (first record keys): {list(data[0].keys())}")
                logger.info(f"DEBUG SAMPLE FLATTENED DATA (first record keys): {list(flattened_data[0].keys())}")
            
            # Use requested_fields if provided, otherwise get all fields from data
            if requested_fields:
                # Get all available fields from flattened data
                all_available_fields = self._get_all_fields(data)
                logger.info(f"DEBUG ALL AVAILABLE FIELDS ({len(all_available_fields)}): {all_available_fields}")
                logger.info(f"DEBUG REQUESTED FIELDS ({len(requested_fields)}): {requested_fields}")
                
                # Filter to only include requested fields and their flattened versions
                filtered_fields = []
                for available_field in all_available_fields:
                    should_include = False
                    match_reason = ""
                    
                    # Check if field is directly requested
                    if available_field in requested_fields:
                        should_include = True
                        match_reason = "direct match"
                    else:
                        # Check if field matches any requested field pattern
                        for requested_field in requested_fields:
                            # Handle exact matches
                            if available_field == requested_field:
                                should_include = True
                                match_reason = f"exact match with {requested_field}"
                                break
                            # Handle prefix matches (e.g., "profiles.full_name" matches available "profiles.full_name")
                            elif available_field.startswith(f"{requested_field}."):
                                should_include = True
                                match_reason = f"prefix match with {requested_field}"
                                break
                            # Handle parent field matches (e.g., requested "profiles.classes.grade_level" includes available "profiles.classes.grade_level")
                            elif requested_field.startswith(f"{available_field}."):
                                # Only include if this is a specific nested field, not a container
                                remaining_path = requested_field[len(available_field)+1:]
                                if "." in remaining_path:  # Has more nesting
                                    should_include = True
                                    match_reason = f"parent match with {requested_field}"
                                    break
                    
                    # Additional check: exclude container fields that are not specifically requested
                    if should_include:
                        # Check if this is a container field (e.g., "profiles.classes") 
                        # when we only want specific nested fields (e.g., "profiles.classes.name")
                        is_container_field = False
                        for requested_field in requested_fields:
                            if (requested_field.startswith(f"{available_field}.") and 
                                available_field != requested_field and
                                available_field.count('.') >= 1):  # Is a nested container
                                is_container_field = True
                                break
                        
                        if is_container_field:
                            # Only include if there's no more specific field requested
                            has_specific_child = any(
                                req.startswith(f"{available_field}.") and req != available_field
                                for req in requested_fields
                            )
                            if has_specific_child:
                                should_include = False
                                match_reason = "excluded container field (has specific children)"
                    
                    if should_include:
                        filtered_fields.append(available_field)
                        logger.debug(f"✅ Including field: {available_field} ({match_reason})")
                    else:
                        logger.debug(f"❌ Excluding field: {available_field}")
                
                all_fields = filtered_fields
                logger.info(f"DEBUG FINAL FILTERED FIELDS ({len(filtered_fields)}): {filtered_fields}")
            else:
                all_fields = self._get_all_fields(data)
                logger.debug(f"Using all fields (no filtering): {all_fields}")
            
            # Process headers with field_mapper
            header_mapping = field_mapper.process_export_headers(
                all_fields,
                exclude_ids=exclude_ids,
                use_aliases=use_aliases
            )
            
            display_headers = list(header_mapping.values())
            original_headers = list(header_mapping.keys())
            
            # Write headers (with aliases if use_aliases=True)
            for col_num, header in enumerate(display_headers, 1):
                worksheet.cell(row=1, column=col_num, value=header)
            
            # Write data
            for row_num, doc in enumerate(flattened_data, 2):
                for col_num, original_header in enumerate(original_headers, 1):
                    value = doc.get(original_header, "")
                    
                    # Skip empty fields if not include_empty_fields
                    if not include_empty_fields and (value is None or value == ""):
                        continue
                        
                    worksheet.cell(row=row_num, column=col_num, value=value)
            
            # Apply formatting
            self._format_worksheet(worksheet, display_headers)
            
            # Save to project storage (not system temp!)
            filepath = self.get_export_filepath(filename, user_id)
            workbook.save(filepath)
            
            logger.info(f"Excel export completed: {filename}, {len(data)} records")
            return filepath
            
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            raise

class CSVExportHandler(ExportHandler):
    """Handler untuk export ke format CSV"""
    
    def export(self, data: List[Dict[str, Any]], filename: Optional[str] = None,
               delimiter: str = ",", encoding: str = "utf-8", user_id: Optional[str] = None,
               exclude_ids: bool = True, use_aliases: bool = True, 
               include_empty_fields: bool = False) -> str:
        """Export data to CSV format"""
        try:
            if not data:
                raise ValueError("No data to export")
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.csv"
            elif not filename.endswith('.csv'):
                filename += '.csv'
            
            # Flatten all documents and get all possible fields
            flattened_data = [self._flatten_document(doc) for doc in data]
            all_fields = self._get_all_fields(data)
            
            # Process headers with field_mapper
            header_mapping = field_mapper.process_export_headers(
                all_fields,
                exclude_ids=exclude_ids,
                use_aliases=use_aliases
            )
            
            display_headers = list(header_mapping.values())
            original_headers = list(header_mapping.keys())
            
            # Create CSV file in project storage
            filepath = self.get_export_filepath(filename, user_id)
            
            with open(filepath, 'w', newline='', encoding=encoding) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=display_headers, delimiter=delimiter)
                writer.writeheader()
                
                for doc in flattened_data:
                    # Map original fields to display headers
                    row = {}
                    for orig_field, display_field in zip(original_headers, display_headers):
                        value = doc.get(orig_field, "")
                        
                        # Skip empty fields if not include_empty_fields
                        if not include_empty_fields and (value is None or value == ""):
                            value = ""
                            
                        row[display_field] = value
                    
                    writer.writerow(row)
            
            logger.info(f"CSV export completed: {filename}, {len(data)} records")
            return filepath
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise

class JSONExportHandler(ExportHandler):
    """Handler untuk export ke format JSON"""
    
    def export(self, data: List[Dict[str, Any]], filename: Optional[str] = None,
               indent: int = 2, ensure_ascii: bool = False, user_id: Optional[str] = None) -> str:
        """Export data to JSON format"""
        try:
            if not data:
                raise ValueError("No data to export")
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.json"
            elif not filename.endswith('.json'):
                filename += '.json'
            
            # Serialize all data
            serialized_data = [self._serialize_value(doc) for doc in data]
            
            # Create JSON file in project storage
            filepath = self.get_export_filepath(filename, user_id)
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(serialized_data, jsonfile, indent=indent, ensure_ascii=ensure_ascii)
            
            logger.info(f"JSON export completed: {filename}, {len(data)} records")
            return filepath
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise

class ExportManager:
    """Manager untuk koordinasi export operations"""
    
    def __init__(self):
        self.handlers = {
            ExportFormat.EXCEL: ExcelExportHandler() if HAS_OPENPYXL else None,
            ExportFormat.CSV: CSVExportHandler(),
            ExportFormat.JSON: JSONExportHandler()
        }
        self._admin_file_service = None
    
    def is_format_supported(self, format: ExportFormat) -> bool:
        """Check if export format is supported"""
        return format in self.handlers and self.handlers[format] is not None
    
    def get_supported_formats(self) -> List[ExportFormat]:
        """Get list of supported export formats"""
        return [fmt for fmt, handler in self.handlers.items() if handler is not None]
    
    def set_admin_file_service(self, admin_file_service):
        """Set admin file service untuk file tracking"""
        self._admin_file_service = admin_file_service
    
    def export_data(self, data: List[Dict[str, Any]], format: ExportFormat, 
                   filename: Optional[str] = None, user_id: Optional[str] = None,
                   exclude_ids: bool = True, use_aliases: bool = True, 
                   include_empty_fields: bool = False, **kwargs) -> str:
        """Export data using specified format with formatting options"""
        if not self.is_format_supported(format):
            raise ValueError(f"Export format '{format}' is not supported")
        
        handler = self.handlers[format]
        
        # Pass formatting options to handler
        formatting_kwargs = {
            'exclude_ids': exclude_ids,
            'use_aliases': use_aliases,
            'include_empty_fields': include_empty_fields,
            **kwargs
        }
        
        return handler.export(data, filename, user_id=user_id, **formatting_kwargs)
    
    async def export_data_with_admin_tracking(
        self,
        data: List[Dict[str, Any]],
        format: ExportFormat,
        display_name: str,
        admin_id: str,
        export_config: Dict[str, Any],
        target_collections: List[str],
        complexity_score: Optional[int] = None,
        **export_kwargs
    ) -> str:
        """Export data dengan admin file tracking"""
        if not self._admin_file_service:
            # Fallback ke export biasa jika service tidak tersedia
            return self.export_data(data, format, display_name, **export_kwargs)
        
        # Export data dulu
        temp_file_path = self.export_data(data, format, display_name, **export_kwargs)
        
        # Save metadata ke database dengan file tracking
        admin_file = await self._admin_file_service.save_export_file(
            admin_id=admin_id,
            display_name=display_name,
            file_path=temp_file_path,
            export_config=export_config,
            target_collections=target_collections,
            record_count=len(data),
            format=format,
            complexity_score=complexity_score
        )
        
        logger.info(f"Admin export completed with tracking: {admin_file.file_id}")
        
        # Return path ke admin export file
        return str(self._admin_file_service.get_admin_export_path(admin_file.system_filename))
    
    def estimate_file_size(self, data: List[Dict[str, Any]], format: ExportFormat) -> str:
        """Estimate the file size of exported data"""
        if not data:
            return "0 KB"
        
        try:
            # Create temporary export to estimate size
            sample_data = data[:min(100, len(data))]  # Use sample for estimation
            temp_file = self.export_data(sample_data, format, "temp_estimate")
            
            if os.path.exists(temp_file):
                sample_size = os.path.getsize(temp_file)
                # Estimate full size based on ratio
                estimated_size = sample_size * (len(data) / len(sample_data))
                
                # Clean up temp file
                os.remove(temp_file)
                
                # Format size
                if estimated_size < 1024:
                    return f"{int(estimated_size)} B"
                elif estimated_size < 1024 * 1024:
                    return f"{estimated_size / 1024:.1f} KB"
                else:
                    return f"{estimated_size / (1024 * 1024):.1f} MB"
            
        except Exception as e:
            logger.warning(f"Could not estimate file size: {e}")
        
        return "Unknown"
    
    def cleanup_file(self, filepath: str) -> bool:
        """Clean up exported file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup file {filepath}: {e}")
        
        return False

# Global instance
export_manager = ExportManager()

# Utility functions for common export scenarios
def export_student_data(data: List[Dict[str, Any]], format: ExportFormat = ExportFormat.EXCEL) -> str:
    """Quick export for student data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_export_{timestamp}"
    return export_manager.export_data(data, format, filename)

def export_exam_results(data: List[Dict[str, Any]], format: ExportFormat = ExportFormat.EXCEL) -> str:
    """Quick export for exam results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"exam_results_{timestamp}"
    return export_manager.export_data(data, format, filename)

def export_teacher_data(data: List[Dict[str, Any]], format: ExportFormat = ExportFormat.EXCEL) -> str:
    """Quick export for teacher data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"teachers_export_{timestamp}"
    return export_manager.export_data(data, format, filename)
