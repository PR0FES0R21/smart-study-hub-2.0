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

logger = logging.getLogger(__name__)

class ExportHandler:
    """Base class untuk export handlers"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
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
               sheet_name: str = "Export") -> str:
        """Export data to Excel format"""
        try:
            if not data:
                raise ValueError("No data to export")
            
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
            
            # Flatten all documents and get all possible fields
            flattened_data = [self._flatten_document(doc) for doc in data]
            headers = self._get_all_fields(data)
            
            # Write headers
            for col_num, header in enumerate(headers, 1):
                worksheet.cell(row=1, column=col_num, value=header)
            
            # Write data
            for row_num, doc in enumerate(flattened_data, 2):
                for col_num, header in enumerate(headers, 1):
                    value = doc.get(header, "")
                    worksheet.cell(row=row_num, column=col_num, value=value)
            
            # Apply formatting
            self._format_worksheet(worksheet, headers)
            
            # Save to temporary file
            filepath = os.path.join(self.temp_dir, filename)
            workbook.save(filepath)
            
            logger.info(f"Excel export completed: {filename}, {len(data)} records")
            return filepath
            
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            raise

class CSVExportHandler(ExportHandler):
    """Handler untuk export ke format CSV"""
    
    def export(self, data: List[Dict[str, Any]], filename: Optional[str] = None,
               delimiter: str = ",", encoding: str = "utf-8") -> str:
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
            headers = self._get_all_fields(data)
            
            # Create CSV file
            filepath = os.path.join(self.temp_dir, filename)
            
            with open(filepath, 'w', newline='', encoding=encoding) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers, delimiter=delimiter)
                writer.writeheader()
                
                for doc in flattened_data:
                    # Ensure all fields exist in each row
                    row = {header: doc.get(header, "") for header in headers}
                    writer.writerow(row)
            
            logger.info(f"CSV export completed: {filename}, {len(data)} records")
            return filepath
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise

class JSONExportHandler(ExportHandler):
    """Handler untuk export ke format JSON"""
    
    def export(self, data: List[Dict[str, Any]], filename: Optional[str] = None,
               indent: int = 2, ensure_ascii: bool = False) -> str:
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
            
            # Create JSON file
            filepath = os.path.join(self.temp_dir, filename)
            
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
    
    def is_format_supported(self, format: ExportFormat) -> bool:
        """Check if export format is supported"""
        return format in self.handlers and self.handlers[format] is not None
    
    def get_supported_formats(self) -> List[ExportFormat]:
        """Get list of supported export formats"""
        return [fmt for fmt, handler in self.handlers.items() if handler is not None]
    
    def export_data(self, data: List[Dict[str, Any]], format: ExportFormat, 
                   filename: Optional[str] = None, **kwargs) -> str:
        """Export data using specified format"""
        if not self.is_format_supported(format):
            raise ValueError(f"Export format '{format}' is not supported")
        
        handler = self.handlers[format]
        return handler.export(data, filename, **kwargs)
    
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
