# ==============================================================================
# File: app/api/v1/routes/admin_export_files.py
# Deskripsi: Admin Export File Management API Endpoints
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
import os
import logging

from app.api.v1 import deps
from app.services.admin_export_file_service import AdminExportFileService
from app.models.admin_export_files import (
    AdminExportFileListResponse, AdminExportFileResponse, BulkDeleteRequest, 
    BulkDeleteResponse, AdminExportAnalytics, FileDownloadRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/files", response_model=AdminExportFileListResponse)
async def list_admin_export_files(
    page: int = Query(1, ge=1, description="Nomor halaman"),
    per_page: int = Query(20, ge=1, le=100, description="Jumlah files per halaman"),
    sort_by: str = Query("file_metadata.created_at", description="Field untuk sorting"),
    sort_order: int = Query(-1, ge=-1, le=1, description="Order: -1 desc, 1 asc"),
    format_filter: Optional[str] = Query(None, description="Filter berdasarkan format file"),
    admin_filter: Optional[str] = Query(None, description="Filter berdasarkan admin ID"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    List semua admin export files dengan pagination dan filtering - ADMIN ONLY.
    """
    try:
        admin_file_service = AdminExportFileService(db)
        
        result = await admin_file_service.list_admin_files(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
            format_filter=format_filter,
            admin_filter=admin_filter
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error listing admin files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list admin export files")

@router.get("/files/{file_id}", response_model=AdminExportFileResponse)
async def get_admin_export_file(
    file_id: str,
    include_logs: bool = Query(False, description="Include download logs"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Get detailed information untuk specific admin export file - ADMIN ONLY.
    """
    try:
        admin_file_service = AdminExportFileService(db)
        
        # Get file info
        admin_file = await admin_file_service.get_admin_file_by_id(file_id)
        if not admin_file:
            raise HTTPException(status_code=404, detail="Admin export file not found")
        
        download_logs = None
        if include_logs:
            download_logs = await admin_file_service.get_file_download_logs(file_id)
        
        return AdminExportFileResponse(
            file=admin_file,
            download_logs=download_logs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin export file")

@router.get("/files/{file_id}/download")
async def download_admin_export_file(
    file_id: str,
    request: Request,
    download_request: FileDownloadRequest = Depends(),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Download admin export file dengan logging - ADMIN ONLY.
    """
    try:
        admin_file_service = AdminExportFileService(db)
        
        # Get file info
        admin_file = await admin_file_service.get_admin_file_by_id(file_id)
        if not admin_file:
            raise HTTPException(status_code=404, detail="Admin export file not found")
        
        # Get physical file path
        file_path = admin_file_service.get_admin_export_path(admin_file.system_filename)
        
        if not file_path.exists():
            logger.error(f"Physical file not found: {file_path}")
            raise HTTPException(status_code=404, detail="Physical file not found")
        
        # Log download activity
        admin_id = str(current_user["_id"])
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        await admin_file_service.log_file_download(
            file_id=file_id,
            admin_id=admin_id,
            ip_address=ip_address,
            user_agent=user_agent,
            file_size=admin_file.file_metadata.size,
            download_purpose=download_request.download_purpose
        )
        
        logger.info(f"Admin file download: {file_id} by {admin_id}")
        
        # Get proper file extension for download filename
        from app.schemas.export import ExportFormat
        format_enum = ExportFormat(admin_file.file_metadata.format)
        file_extension = admin_file_service.get_file_extension(format_enum)
        download_filename = f"{admin_file.display_name}.{file_extension}"
        
        # Return file dengan proper headers
        return FileResponse(
            path=str(file_path),
            filename=download_filename,
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename=\"{download_filename}\""
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading admin file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download admin export file")

@router.delete("/files/{file_id}")
async def delete_admin_export_file(
    file_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Delete specific admin export file - ADMIN ONLY.
    """
    try:
        admin_file_service = AdminExportFileService(db)
        
        success = await admin_file_service.delete_admin_file(file_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Admin export file not found")
        
        logger.info(f"Admin file deleted: {file_id} by {current_user['_id']}")
        
        return {"success": True, "message": f"File {file_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting admin file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete admin export file")

@router.post("/files/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_admin_export_files(
    request: BulkDeleteRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Bulk delete multiple admin export files - ADMIN ONLY.
    """
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=400, 
                detail="Bulk delete requires confirmation. Set 'confirm' to true."
            )
        
        if len(request.file_ids) > 100:
            raise HTTPException(
                status_code=400, 
                detail="Too many files selected. Maximum 100 files per batch."
            )
        
        admin_file_service = AdminExportFileService(db)
        
        result = await admin_file_service.bulk_delete_admin_files(request.file_ids)
        
        logger.info(
            f"Bulk delete completed by {current_user['_id']}: "
            f"{result.deleted_count} files deleted, {len(result.failed_deletes)} failed"
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk delete admin export files")

@router.delete("/files/all")
async def delete_all_admin_export_files(
    confirm: bool = Query(False, description="Confirmation untuk delete all"),
    admin_filter: Optional[str] = Query(None, description="Delete hanya files dari admin tertentu"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Delete all admin export files - ADMIN ONLY.
    Extremely dangerous operation, requires explicit confirmation.
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="Delete all requires explicit confirmation. Set 'confirm' query parameter to true."
            )
        
        admin_file_service = AdminExportFileService(db)
        
        result = await admin_file_service.delete_all_admin_files(admin_filter)
        
        logger.warning(
            f"Delete all admin files executed by {current_user['_id']}: "
            f"{result.deleted_count} files deleted"
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete all: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete all admin export files")

@router.get("/files/{file_id}/logs")
async def get_file_download_logs(
    file_id: str,
    limit: int = Query(50, ge=1, le=200, description="Jumlah logs maksimal"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Get download logs untuk specific file - ADMIN ONLY.
    """
    try:
        admin_file_service = AdminExportFileService(db)
        
        # Verify file exists
        admin_file = await admin_file_service.get_admin_file_by_id(file_id)
        if not admin_file:
            raise HTTPException(status_code=404, detail="Admin export file not found")
        
        logs = await admin_file_service.get_file_download_logs(file_id, limit)
        
        return {
            "file_id": file_id,
            "display_name": admin_file.display_name,
            "total_downloads": admin_file.stats.download_count,
            "logs": logs,
            "log_count": len(logs)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download logs for {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get download logs")

@router.get("/analytics", response_model=AdminExportAnalytics)
async def get_admin_export_analytics(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Get comprehensive analytics tentang admin exports - ADMIN ONLY.
    """
    try:
        admin_file_service = AdminExportFileService(db)
        
        analytics = await admin_file_service.get_admin_export_analytics()
        
        return analytics
    
    except Exception as e:
        logger.error(f"Error getting admin export analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin export analytics")
