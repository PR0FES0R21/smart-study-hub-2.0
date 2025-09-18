# ==============================================================================
# File: app/models/admin_export_files.py
# Deskripsi: Database models untuk Admin Export File Management System
# ==============================================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class FileMetadata(BaseModel):
    """Metadata informasi file export"""
    size: int = Field(..., description="Ukuran file dalam bytes")
    format: str = Field(..., description="Format file (excel, csv, json)")
    record_count: int = Field(..., description="Jumlah records yang di-export")
    complexity_score: Optional[int] = Field(None, description="Skor kompleksitas query")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    file_hash: Optional[str] = Field(None, description="SHA256 hash untuk integrity check")

class FileStats(BaseModel):
    """Statistik penggunaan file"""
    download_count: int = Field(default=0, description="Jumlah total download")
    last_downloaded: Optional[datetime] = Field(None, description="Waktu terakhir di-download")
    accessed_by_admins: List[str] = Field(default_factory=list, description="List admin IDs yang pernah download")

class AdminExportFile(BaseModel):
    """Model untuk admin export files collection"""
    id: Optional[str] = Field(None, alias="_id")
    file_id: str = Field(..., description="Unique file identifier")
    created_by_admin: str = Field(..., description="ObjectId admin yang membuat")
    display_name: str = Field(..., description="Nama display untuk user")
    system_filename: str = Field(..., description="Nama file di storage system")
    export_config: Dict[str, Any] = Field(..., description="Konfigurasi export yang digunakan")
    target_collections: List[str] = Field(..., description="Collections yang di-export")
    file_metadata: FileMetadata = Field(..., description="Metadata file")
    stats: FileStats = Field(default_factory=FileStats, description="Statistik penggunaan")
    
    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB document to Pydantic model"""
        if '_id' in data:
            data['id'] = str(data['_id'])
        return cls(**data)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class AdminFileDownloadLog(BaseModel):
    """Model untuk admin file download logs collection"""
    id: Optional[str] = Field(None, alias="_id")
    file_id: str = Field(..., description="File ID yang di-download")
    downloaded_by_admin: str = Field(..., description="Admin ID yang download")
    download_timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: str = Field(..., description="IP address user")
    user_agent: str = Field(..., description="Browser user agent")
    file_size: int = Field(..., description="Ukuran file saat download")
    download_purpose: Optional[str] = Field(None, description="Catatan tujuan download")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

# Request/Response models untuk API
class AdminExportFileListResponse(BaseModel):
    """Response untuk list admin export files"""
    files: List[AdminExportFile]
    total_files: int
    total_size: int  # Total size semua files dalam bytes
    page: int
    per_page: int
    has_next: bool

class AdminExportFileResponse(BaseModel):
    """Response untuk single admin export file"""
    file: AdminExportFile
    download_logs: Optional[List[AdminFileDownloadLog]] = None

class BulkDeleteRequest(BaseModel):
    """Request untuk bulk delete files"""
    file_ids: List[str] = Field(..., description="List file IDs untuk di-delete")
    confirm: bool = Field(False, description="Konfirmasi delete operation")

class BulkDeleteResponse(BaseModel):
    """Response untuk bulk delete operation"""
    success: bool
    deleted_count: int
    failed_deletes: List[str] = Field(default_factory=list)
    message: str

class AdminExportAnalytics(BaseModel):
    """Response untuk export analytics"""
    total_files: int
    total_storage_used: int  # bytes
    most_downloaded_files: List[Dict[str, Any]]
    recent_exports: List[Dict[str, Any]]
    downloads_by_admin: Dict[str, int]
    exports_by_format: Dict[str, int]
    average_file_size: int

class FileDownloadRequest(BaseModel):
    """Request untuk download file dengan optional purpose"""
    download_purpose: Optional[str] = Field(None, description="Catatan tujuan download")
