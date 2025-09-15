# ==============================================================================
# File: app/api/v1/routes/exports.py
# Deskripsi: API endpoints untuk flexible export system
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
import logging
import os
import uuid

from app.api.v1 import deps
from app.schemas.export import (
    ExportRequest, ExportResponse, ValidateConfigRequest, ValidateConfigResponse,
    AvailableCollectionsResponse, ExportStatusResponse, ExportFormat, ExportConfig
)
from app.core.export_security import export_security
from app.core.export_query_builder import ExportQueryBuilder
from app.core.export_handlers import export_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/collections", response_model=AvailableCollectionsResponse)
async def get_available_collections(
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Mengambil daftar collection yang tersedia untuk export berdasarkan role user.
    """
    try:
        user_roles = current_user.get("roles", [])
        collections = export_security.get_available_collections(user_roles)
        
        return AvailableCollectionsResponse(collections=collections)
    
    except Exception as e:
        logger.error(f"Error getting available collections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available collections")

@router.get("/formats")
async def get_supported_formats():
    """
    Mengambil daftar format export yang didukung.
    """
    try:
        supported_formats = export_manager.get_supported_formats()
        return {
            "supported_formats": [fmt.value for fmt in supported_formats],
            "descriptions": {
                "excel": "Excel spreadsheet (.xlsx)",
                "csv": "Comma-separated values (.csv)", 
                "json": "JSON format (.json)"
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting supported formats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported formats")

@router.post("/validate", response_model=ValidateConfigResponse)
async def validate_export_config(
    request: ValidateConfigRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Validasi konfigurasi export sebelum eksekusi.
    """
    try:
        user_roles = current_user.get("roles", [])
        
        # Validasi security dan permissions
        validation_result = export_security.validate_export_config(request.config, user_roles)
        
        if not validation_result["valid"]:
            return ValidateConfigResponse(
                valid=False,
                errors=validation_result["errors"],
                warnings=validation_result.get("warnings", [])
            )
        
        # Estimasi jumlah records jika valid
        query_builder = ExportQueryBuilder()
        estimated_records = await query_builder.estimate_result_count(db, request.config)
        
        # Determine required permissions
        required_permissions = []
        if "admin" not in user_roles:
            # Check for sensitive fields
            for field in request.config.fields:
                collection_perm = export_security.permissions.get(request.config.main_collection)
                if collection_perm and field in collection_perm.sensitive_fields:
                    required_permissions.append("admin")
                    break
        
        return ValidateConfigResponse(
            valid=True,
            errors=[],
            warnings=validation_result.get("warnings", []),
            estimated_records=estimated_records,
            required_permissions=required_permissions
        )
    
    except Exception as e:
        logger.error(f"Error validating export config: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate export configuration")

@router.post("/execute", response_model=ExportResponse)
async def execute_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Eksekusi export data berdasarkan konfigurasi.
    """
    try:
        user_roles = current_user.get("roles", [])
        user_id = str(current_user["_id"])
        
        # Validasi konfigurasi export
        validation_result = export_security.validate_export_config(request.config, user_roles)
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid export configuration: {'; '.join(validation_result['errors'])}"
            )
        
        # Check if format is supported
        if not export_manager.is_format_supported(request.format):
            raise HTTPException(
                status_code=400,
                detail=f"Export format '{request.format}' is not supported"
            )
        
        # Build query pipeline
        query_builder = ExportQueryBuilder()
        pipeline = query_builder.build_pipeline(request.config)
        
        # Estimate result count untuk determine async processing
        estimated_count = await query_builder.estimate_result_count(db, request.config)
        
        # Determine if async processing is needed
        should_async = (
            request.async_export or 
            (estimated_count and estimated_count > 1000) or
            len(pipeline) > 5
        )
        
        if should_async:
            # Process asynchronously
            task_id = str(uuid.uuid4())
            
            # Add background task
            background_tasks.add_task(
                _process_export_async,
                task_id=task_id,
                config=request.config,
                format=request.format,
                filename=request.filename,
                pipeline=pipeline,
                db=db,
                user_id=user_id
            )
            
            return ExportResponse(
                success=True,
                message="Export started. Check status using task_id.",
                task_id=task_id,
                estimated_file_size=export_manager.estimate_file_size([], request.format) if not estimated_count else None
            )
        
        else:
            # Process synchronously
            data = await _execute_query(db, request.config.main_collection, pipeline)
            
            if not data:
                raise HTTPException(status_code=404, detail="No data found matching the criteria")
            
            # Export data
            file_path = export_manager.export_data(data, request.format, request.filename)
            
            # Generate file URL (adjust based on your file serving setup)
            file_url = f"/api/v1/exports/download/{os.path.basename(file_path)}"
            
            return ExportResponse(
                success=True,
                message=f"Export completed successfully. {len(data)} records exported.",
                file_url=file_url,
                record_count=len(data),
                estimated_file_size=export_manager.estimate_file_size(data, request.format)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing export: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute export")

@router.get("/download/{filename}")
async def download_export_file(
    filename: str,
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Download file hasil export.
    """
    try:
        # Basic security check - prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Construct file path (adjust based on your temp directory setup)
        import tempfile
        file_path = os.path.join(tempfile.gettempdir(), filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.get("/status/{task_id}", response_model=ExportStatusResponse)
async def get_export_status(
    task_id: str,
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Mengambil status export yang sedang berjalan.
    """
    try:
        # For MVP, we'll implement a simple file-based status tracking
        # In production, you might want to use Redis or database
        
        status_file = os.path.join(tempfile.gettempdir(), f"export_status_{task_id}.json")
        
        if not os.path.exists(status_file):
            raise HTTPException(status_code=404, detail="Export task not found")
        
        import json
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        
        from app.schemas.export import ExportStatus
        status = ExportStatus(**status_data)
        
        return ExportStatusResponse(status=status)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get export status")

# Helper functions

async def _execute_query(db: AsyncIOMotorDatabase, collection: str, pipeline: List[dict]) -> List[dict]:
    """Execute aggregation pipeline and return results"""
    try:
        cursor = db[collection].aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return results
    except Exception as e:
        logger.error(f"Error executing query on {collection}: {e}")
        raise

async def _process_export_async(
    task_id: str,
    config: ExportConfig,
    format: ExportFormat,
    filename: Optional[str],
    pipeline: List[dict],
    db: AsyncIOMotorDatabase,
    user_id: str
):
    """Process export in background task"""
    import tempfile
    import json
    from datetime import datetime
    
    status_file = os.path.join(tempfile.gettempdir(), f"export_status_{task_id}.json")
    
    try:
        # Update status to processing
        status_data = {
            "task_id": task_id,
            "status": "processing",
            "progress": 0,
            "message": "Starting export...",
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        # Execute query
        status_data["progress"] = 25
        status_data["message"] = "Fetching data..."
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        data = await _execute_query(db, config.main_collection, pipeline)
        
        if not data:
            status_data["status"] = "failed"
            status_data["error_details"] = "No data found matching the criteria"
            with open(status_file, 'w') as f:
                json.dump(status_data, f)
            return
        
        # Export data
        status_data["progress"] = 75
        status_data["message"] = f"Exporting {len(data)} records..."
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        file_path = export_manager.export_data(data, format, filename)
        
        # Update status to completed
        status_data["status"] = "completed"
        status_data["progress"] = 100
        status_data["message"] = f"Export completed. {len(data)} records exported."
        status_data["file_url"] = f"/api/v1/exports/download/{os.path.basename(file_path)}"
        status_data["completed_at"] = datetime.utcnow().isoformat()
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        logger.info(f"Async export {task_id} completed successfully")
    
    except Exception as e:
        logger.error(f"Async export {task_id} failed: {e}")
        
        # Update status to failed
        status_data = {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "message": "Export failed",
            "error_details": str(e),
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)

# Quick export endpoints for common use cases
@router.post("/quick/students")
async def quick_export_students(
    format: ExportFormat = ExportFormat.EXCEL,
    grade_level: Optional[int] = None,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Quick export untuk data siswa dengan filter grade_level.
    """
    from app.schemas.export import FilterCondition, FilterOperator, JoinConfig
    
    try:
        # Build basic student export config
        filters = [FilterCondition(field="roles", operator=FilterOperator.EQ, value="student")]
        
        joins = [
            JoinConfig(
                collection="profiles",
                local_field="profile_id",
                foreign_field="_id",
                fields=["full_name", "birth_date", "gender", "class_id"],
                join_type="unwind"
            ),
            JoinConfig(
                collection="classes",
                local_field="profiles.class_id", 
                foreign_field="_id",
                fields=["name", "grade_level"],
                join_type="unwind",
                filters=[FilterCondition(field="grade_level", operator=FilterOperator.EQ, value=grade_level)] if grade_level else []
            )
        ]
        
        config = ExportConfig(
            main_collection="users",
            fields=["username", "email", "is_active"],
            filters=filters,
            joins=joins,
            sort={"profiles.full_name": 1}
        )
        
        request = ExportRequest(config=config, format=format)
        return await execute_export(request, BackgroundTasks(), db, current_user)
    
    except Exception as e:
        logger.error(f"Error in quick student export: {e}")
        raise HTTPException(status_code=500, detail="Failed to export student data")

@router.post("/quick/exam-results")
async def quick_export_exam_results(
    exam_id: Optional[str] = None,
    format: ExportFormat = ExportFormat.EXCEL,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Quick export untuk hasil ujian.
    """
    from app.schemas.export import FilterCondition, FilterOperator, JoinConfig
    from bson import ObjectId
    
    try:
        # Build exam results export config
        filters = [FilterCondition(field="status", operator=FilterOperator.EQ, value="graded")]
        
        if exam_id:
            filters.append(FilterCondition(field="exam_id", operator=FilterOperator.EQ, value=exam_id))
        
        joins = [
            JoinConfig(
                collection="users",
                local_field="student_id",
                foreign_field="_id", 
                fields=["username"],
                join_type="unwind"
            ),
            JoinConfig(
                collection="profiles",
                local_field="users.profile_id",
                foreign_field="_id",
                fields=["full_name"],
                join_type="unwind"
            ),
            JoinConfig(
                collection="exams",
                local_field="exam_id",
                foreign_field="_id",
                fields=["title", "exam_type"],
                join_type="unwind"
            )
        ]
        
        config = ExportConfig(
            main_collection="exam_sessions",
            fields=["score", "started_at", "submitted_at", "time_spent_minutes"],
            filters=filters,
            joins=joins,
            sort={"score": -1}
        )
        
        request = ExportRequest(config=config, format=format)
        return await execute_export(request, BackgroundTasks(), db, current_user)
    
    except Exception as e:
        logger.error(f"Error in quick exam results export: {e}")
        raise HTTPException(status_code=500, detail="Failed to export exam results")
