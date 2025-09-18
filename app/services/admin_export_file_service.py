# ==============================================================================
# File: app/services/admin_export_file_service.py
# Deskripsi: Service layer untuk Admin Export File Management
# ==============================================================================
import os
import hashlib
import secrets
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from app.models.admin_export_files import (
    AdminExportFile, AdminFileDownloadLog, FileMetadata, FileStats,
    AdminExportFileListResponse, BulkDeleteResponse, AdminExportAnalytics
)
from app.schemas.export import ExportFormat

logger = logging.getLogger(__name__)

class AdminExportFileService:
    """Service untuk mengelola admin export files"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.admin_files_collection = db.admin_export_files
        self.download_logs_collection = db.admin_file_download_logs
        
        # Setup storage directories
        self.project_root = Path(__file__).parent.parent.parent
        self.storage_dir = self.project_root / "storage"
        self.admin_exports_dir = self.storage_dir / "admin_exports"
        
        # Create directories
        self.admin_exports_dir.mkdir(parents=True, exist_ok=True)
    
    def sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """Sanitize filename untuk keamanan"""
        # Remove dangerous characters
        safe_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', filename)
        # Replace spaces with underscores
        safe_name = safe_name.strip().replace(' ', '_')
        # Limit length
        return safe_name[:max_length]
    
    def generate_file_id(self) -> str:
        """Generate unique file ID dengan prefix"""
        return f"adm_exp_{secrets.token_hex(4)}"
    
    def get_file_extension(self, format: ExportFormat) -> str:
        """Get proper file extension for export format"""
        extension_map = {
            ExportFormat.EXCEL: "xlsx",
            ExportFormat.CSV: "csv",
            ExportFormat.JSON: "json",
            ExportFormat.PDF: "pdf"
        }
        return extension_map.get(format, format.value)
    
    def generate_secure_filename(self, display_name: str, format: ExportFormat) -> Tuple[str, str]:
        """Generate secure filename dan file_id"""
        file_id = self.generate_file_id()
        safe_name = self.sanitize_filename(display_name)
        file_extension = self.get_file_extension(format)
        system_filename = f"{safe_name}_{file_id}.{file_extension}"
        return file_id, system_filename
    
    def get_admin_export_path(self, system_filename: str) -> Path:
        """Get full path untuk admin export file"""
        return self.admin_exports_dir / system_filename
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash dari file"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    async def save_export_file(
        self,
        admin_id: str,
        display_name: str,
        file_path: str,
        export_config: Dict[str, Any],
        target_collections: List[str],
        record_count: int,
        format: ExportFormat,
        complexity_score: Optional[int] = None
    ) -> AdminExportFile:
        """Save export file metadata ke database"""
        try:
            file_path_obj = Path(file_path)
            
            # Generate secure identifiers
            file_id, system_filename = self.generate_secure_filename(
                display_name, 
                format
            )
            
            # Calculate file size dan hash
            file_size = file_path_obj.stat().st_size if file_path_obj.exists() else 0
            file_hash = self.calculate_file_hash(file_path_obj)
            
            # Move file ke admin exports directory
            target_path = self.get_admin_export_path(system_filename)
            if file_path_obj.exists() and file_path_obj != target_path:
                file_path_obj.rename(target_path)
            
            # Create file metadata
            file_metadata = FileMetadata(
                size=file_size,
                format=format.value,
                record_count=record_count,
                complexity_score=complexity_score,
                created_at=datetime.utcnow(),
                file_hash=file_hash
            )
            
            # Create admin export file record
            admin_file = AdminExportFile(
                file_id=file_id,
                created_by_admin=admin_id,
                display_name=display_name,
                system_filename=system_filename,
                export_config=export_config,
                target_collections=target_collections,
                file_metadata=file_metadata,
                stats=FileStats()
            )
            
            # Save to database
            result = await self.admin_files_collection.insert_one(
                admin_file.model_dump(by_alias=True, exclude={"id"})
            )
            
            admin_file.id = str(result.inserted_id)
            
            logger.info(f"Admin export file saved: {file_id} by admin {admin_id}")
            return admin_file
            
        except Exception as e:
            logger.error(f"Error saving admin export file: {e}")
            raise
    
    async def list_admin_files(
        self, 
        page: int = 1, 
        per_page: int = 20,
        sort_by: str = "created_at",
        sort_order: int = -1,
        format_filter: Optional[str] = None,
        admin_filter: Optional[str] = None
    ) -> AdminExportFileListResponse:
        """List admin export files dengan pagination dan filtering"""
        try:
            # Build query filter
            query = {}
            if format_filter:
                query["file_metadata.format"] = format_filter
            if admin_filter:
                query["created_by_admin"] = admin_filter
            
            # Count total files
            total_files = await self.admin_files_collection.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * per_page
            has_next = skip + per_page < total_files
            
            # Get files
            cursor = self.admin_files_collection.find(query)\
                .sort(sort_by, sort_order)\
                .skip(skip)\
                .limit(per_page)
            
            files_data = await cursor.to_list(length=per_page)
            
            # Convert to AdminExportFile models
            files = []
            total_size = 0
            
            for file_data in files_data:
                file_data["id"] = str(file_data["_id"])
                # Remove the MongoDB _id to avoid duplicate key issue
                if '_id' in file_data:
                    del file_data['_id']
                admin_file = AdminExportFile(**file_data)
                files.append(admin_file)
                total_size += admin_file.file_metadata.size
            
            return AdminExportFileListResponse(
                files=files,
                total_files=total_files,
                total_size=total_size,
                page=page,
                per_page=per_page,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"Error listing admin files: {e}")
            raise
    
    async def get_admin_file_by_id(self, file_id: str) -> Optional[AdminExportFile]:
        """Get admin export file by file_id"""
        try:
            file_data = await self.admin_files_collection.find_one({"file_id": file_id})
            if not file_data:
                return None
            
            file_data["id"] = str(file_data["_id"])
            # Remove the MongoDB _id to avoid duplicate key issue
            if '_id' in file_data:
                del file_data['_id']
            admin_file = AdminExportFile(**file_data)
            return admin_file
            
        except Exception as e:
            logger.error(f"Error getting admin file {file_id}: {e}")
            return None
    
    async def delete_admin_file(self, file_id: str) -> bool:
        """Delete admin export file (database + physical file)"""
        try:
            # Get file info first
            admin_file = await self.get_admin_file_by_id(file_id)
            if not admin_file:
                return False
            
            # Delete physical file
            file_path = self.get_admin_export_path(admin_file.system_filename)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Physical file deleted: {file_path}")
            
            # Delete from database
            result = await self.admin_files_collection.delete_one({"file_id": file_id})
            
            # Delete related download logs
            await self.download_logs_collection.delete_many({"file_id": file_id})
            
            logger.info(f"Admin export file deleted: {file_id}")
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting admin file {file_id}: {e}")
            return False
    
    async def bulk_delete_admin_files(self, file_ids: List[str]) -> BulkDeleteResponse:
        """Bulk delete admin export files"""
        try:
            deleted_count = 0
            failed_deletes = []
            
            for file_id in file_ids:
                try:
                    if await self.delete_admin_file(file_id):
                        deleted_count += 1
                    else:
                        failed_deletes.append(file_id)
                except Exception as e:
                    logger.error(f"Failed to delete file {file_id}: {e}")
                    failed_deletes.append(file_id)
            
            success = deleted_count > 0
            message = f"Successfully deleted {deleted_count} files"
            if failed_deletes:
                message += f", failed to delete {len(failed_deletes)} files"
            
            return BulkDeleteResponse(
                success=success,
                deleted_count=deleted_count,
                failed_deletes=failed_deletes,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error in bulk delete: {e}")
            return BulkDeleteResponse(
                success=False,
                deleted_count=0,
                failed_deletes=file_ids,
                message=f"Bulk delete failed: {str(e)}"
            )
    
    async def delete_all_admin_files(self, admin_id: Optional[str] = None) -> BulkDeleteResponse:
        """Delete all admin export files (optionally filtered by admin)"""
        try:
            query = {}
            if admin_id:
                query["created_by_admin"] = admin_id
            
            # Get all file IDs to delete
            cursor = self.admin_files_collection.find(query, {"file_id": 1})
            files_to_delete = await cursor.to_list(length=None)
            file_ids = [file["file_id"] for file in files_to_delete]
            
            if not file_ids:
                return BulkDeleteResponse(
                    success=True,
                    deleted_count=0,
                    message="No files to delete"
                )
            
            return await self.bulk_delete_admin_files(file_ids)
            
        except Exception as e:
            logger.error(f"Error deleting all admin files: {e}")
            return BulkDeleteResponse(
                success=False,
                deleted_count=0,
                message=f"Delete all failed: {str(e)}"
            )
    
    async def log_file_download(
        self,
        file_id: str,
        admin_id: str,
        ip_address: str,
        user_agent: str,
        file_size: int,
        download_purpose: Optional[str] = None
    ) -> AdminFileDownloadLog:
        """Log file download activity"""
        try:
            download_log = AdminFileDownloadLog(
                file_id=file_id,
                downloaded_by_admin=admin_id,
                ip_address=ip_address,
                user_agent=user_agent,
                file_size=file_size,
                download_purpose=download_purpose
            )
            
            # Save log to database
            result = await self.download_logs_collection.insert_one(
                download_log.model_dump(by_alias=True, exclude={"id"})
            )
            
            download_log.id = str(result.inserted_id)
            
            # Update file stats
            await self.admin_files_collection.update_one(
                {"file_id": file_id},
                {
                    "$inc": {"stats.download_count": 1},
                    "$set": {"stats.last_downloaded": datetime.utcnow()},
                    "$addToSet": {"stats.accessed_by_admins": admin_id}
                }
            )
            
            logger.info(f"Download logged: {file_id} by admin {admin_id}")
            return download_log
            
        except Exception as e:
            logger.error(f"Error logging download: {e}")
            raise
    
    async def get_file_download_logs(
        self, 
        file_id: str, 
        limit: int = 50
    ) -> List[AdminFileDownloadLog]:
        """Get download logs untuk specific file"""
        try:
            cursor = self.download_logs_collection.find({"file_id": file_id})\
                .sort("download_timestamp", -1)\
                .limit(limit)
            
            logs_data = await cursor.to_list(length=limit)
            
            logs = []
            for log_data in logs_data:
                log_data["id"] = str(log_data["_id"])
                # Remove the MongoDB _id to avoid duplicate key issue
                if '_id' in log_data:
                    del log_data['_id']
                logs.append(AdminFileDownloadLog(**log_data))
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting download logs for {file_id}: {e}")
            return []
    
    async def get_admin_export_analytics(self) -> AdminExportAnalytics:
        """Get comprehensive analytics tentang admin exports"""
        try:
            # Aggregate basic stats
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_files": {"$sum": 1},
                        "total_storage": {"$sum": "$file_metadata.size"},
                        "avg_file_size": {"$avg": "$file_metadata.size"}
                    }
                }
            ]
            
            basic_stats = await self.admin_files_collection.aggregate(pipeline).to_list(1)
            basic_stats = basic_stats[0] if basic_stats else {}
            
            # Most downloaded files
            most_downloaded = await self.admin_files_collection.find()\
                .sort("stats.download_count", -1)\
                .limit(5)\
                .to_list(5)
            
            # Recent exports
            recent_exports = await self.admin_files_collection.find()\
                .sort("file_metadata.created_at", -1)\
                .limit(10)\
                .to_list(10)
            
            # Downloads by admin
            downloads_pipeline = [
                {"$unwind": "$stats.accessed_by_admins"},
                {
                    "$group": {
                        "_id": "$stats.accessed_by_admins",
                        "download_count": {"$sum": "$stats.download_count"}
                    }
                },
                {"$sort": {"download_count": -1}}
            ]
            
            downloads_by_admin_data = await self.admin_files_collection.aggregate(downloads_pipeline).to_list(None)
            downloads_by_admin = {item["_id"]: item["download_count"] for item in downloads_by_admin_data}
            
            # Exports by format
            format_pipeline = [
                {
                    "$group": {
                        "_id": "$file_metadata.format",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            exports_by_format_data = await self.admin_files_collection.aggregate(format_pipeline).to_list(None)
            exports_by_format = {item["_id"]: item["count"] for item in exports_by_format_data}
            
            return AdminExportAnalytics(
                total_files=basic_stats.get("total_files", 0),
                total_storage_used=basic_stats.get("total_storage", 0),
                average_file_size=int(basic_stats.get("avg_file_size", 0)),
                most_downloaded_files=[
                    {
                        "file_id": file["file_id"],
                        "display_name": file["display_name"],
                        "download_count": file["stats"]["download_count"]
                    } for file in most_downloaded
                ],
                recent_exports=[
                    {
                        "file_id": file["file_id"],
                        "display_name": file["display_name"],
                        "created_at": file["file_metadata"]["created_at"]
                    } for file in recent_exports
                ],
                downloads_by_admin=downloads_by_admin,
                exports_by_format=exports_by_format
            )
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            raise
