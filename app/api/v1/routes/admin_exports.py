# ==============================================================================
# File: app/api/v1/routes/admin_exports.py
# Deskripsi: Admin-only advanced export endpoints dengan nested joins
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Dict, Any
import logging
import os
import uuid
import time
from datetime import datetime

from app.api.v1 import deps
from app.schemas.admin_export import (
    AdvancedExportRequest, AdvancedValidateRequest, AdvancedExportResponse, 
    AdvancedValidateResponse, AdvancedExportConfig
)
from app.core.admin_security import admin_export_security
from app.core.advanced_query_builder import AdvancedExportQueryBuilder
from app.core.export_handlers import export_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/validate", response_model=AdvancedValidateResponse)
async def validate_advanced_export_config(
    request: AdvancedValidateRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Validasi konfigurasi advanced export - ADMIN ONLY.
    Mendukung unlimited nested joins dan semua operators.
    """
    try:
        user_roles = current_user.get("roles", [])
        
        # Validasi security dan permissions dengan admin validator
        validation_result = admin_export_security.validate_advanced_export_config(
            request.config, user_roles
        )
        
        if not validation_result["valid"]:
            return AdvancedValidateResponse(
                valid=False,
                errors=validation_result["errors"],
                warnings=validation_result.get("warnings", [])
            )
        
        # Build query dan analyze complexity
        query_builder = AdvancedExportQueryBuilder()
        
        # Estimasi jumlah records
        estimated_records = await query_builder.estimate_advanced_result_count(db, request.config)
        
        # Get query analysis
        query_analysis = query_builder.get_query_analysis(request.config)
        
        # Get performance analysis
        performance_analysis = admin_export_security.analyze_query_performance(request.config)
        
        # Combine warnings
        all_warnings = validation_result.get("warnings", [])
        all_warnings.extend(query_analysis.get("warnings", []))
        all_warnings.extend(performance_analysis.get("recommendations", []))
        
        return AdvancedValidateResponse(
            valid=True,
            errors=[],
            warnings=all_warnings,
            estimated_records=estimated_records,
            pipeline_complexity=query_analysis.get("complexity"),
            estimated_execution_time=_estimate_execution_time(query_analysis, estimated_records),
            total_joins=query_analysis.get("total_joins"),
            max_join_depth=query_analysis.get("max_join_depth"),
            collections_involved=query_analysis.get("collections_involved")
        )
    
    except Exception as e:
        logger.error(f"Error validating advanced export config: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate advanced export configuration")

@router.post("/execute", response_model=AdvancedExportResponse)
async def execute_advanced_export(
    request: AdvancedExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Eksekusi advanced export dengan unlimited nested joins - ADMIN ONLY.
    Mendukung semua operators dan complex filtering.
    """
    try:
        user_roles = current_user.get("roles", [])
        user_id = str(current_user["_id"])
        
        start_time = time.time()
        
        # Validasi konfigurasi export dengan admin validator
        validation_result = admin_export_security.validate_advanced_export_config(
            request.config, user_roles
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid advanced export configuration: {'; '.join(validation_result['errors'])}"
            )
        
        # Handle dry run mode
        if request.dry_run:
            return await _handle_dry_run(request, db, user_id)
        
        # Handle explain mode
        if request.explain:
            return await _handle_explain_mode(request, db, user_id)
        
        # Check if format is supported
        if not export_manager.is_format_supported(request.format):
            raise HTTPException(
                status_code=400,
                detail=f"Export format '{request.format}' is not supported"
            )
        
        # Build advanced query pipeline
        query_builder = AdvancedExportQueryBuilder()
        pipeline = query_builder.build_advanced_pipeline(request.config)
        
        # Get complexity analysis
        query_analysis = query_builder.get_query_analysis(request.config)
        
        # Estimate result count untuk determine async processing
        estimated_count = await query_builder.estimate_advanced_result_count(db, request.config)
        
        # Determine if async processing is needed (lower threshold for complex queries)
        should_async = (
            request.async_export or 
            (estimated_count and estimated_count > 500) or  # Lower threshold for admin
            len(pipeline) > 8 or
            query_analysis.get("complexity") in ["high", "very_high"]
        )
        
        if should_async:
            # Process asynchronously
            task_id = str(uuid.uuid4())
            
            # Add background task
            background_tasks.add_task(
                _process_advanced_export_async,
                task_id=task_id,
                config=request.config,
                format=request.format,
                filename=request.filename,
                pipeline=pipeline,
                db=db,
                user_id=user_id,
                query_analysis=query_analysis
            )
            
            return AdvancedExportResponse(
                success=True,
                message="Advanced export started. Check status using task_id.",
                task_id=task_id,
                execution_time_ms=int((time.time() - start_time) * 1000),
                pipeline_stages=len(pipeline),
                estimated_records=estimated_count,
                warnings=validation_result.get("warnings", [])
            )
        
        else:
            # Process synchronously
            data = await _execute_advanced_query(db, request.config.main_collection, pipeline, request.config)
            
            if not data:
                raise HTTPException(status_code=404, detail="No data found matching the criteria")
            
            # Export data dengan user_id untuk proper storage
            file_path = export_manager.export_data(data, request.format, request.filename, user_id=user_id)
            
            # Generate file URL
            file_url = f"/api/v1/exports/download/{os.path.basename(file_path)}"
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return AdvancedExportResponse(
                success=True,
                message=f"Advanced export completed successfully. {len(data)} records exported.",
                file_url=file_url,
                record_count=len(data),
                execution_time_ms=execution_time,
                estimated_file_size=export_manager.estimate_file_size(data, request.format),
                pipeline_stages=len(pipeline),
                warnings=validation_result.get("warnings", [])
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing advanced export: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute advanced export")

@router.get("/collections/relationships")
async def get_collection_relationships(
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Get collection relationships untuk admin export planning.
    """
    try:
        relationships = {}
        
        for collection in admin_export_security.admin_collections:
            suggestions = admin_export_security.get_collection_suggestions(collection)
            relationships[collection] = {
                "display_name": collection.replace("_", " ").title(),
                "possible_joins": suggestions,
                "total_joinable": len(suggestions)
            }
        
        return {
            "relationships": relationships,
            "total_collections": len(admin_export_security.admin_collections)
        }
    
    except Exception as e:
        logger.error(f"Error getting collection relationships: {e}")
        raise HTTPException(status_code=500, detail="Failed to get collection relationships")

@router.post("/analyze")
async def analyze_advanced_query(
    request: AdvancedValidateRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Analyze advanced query untuk performance insights - ADMIN ONLY.
    """
    try:
        user_roles = current_user.get("roles", [])
        
        # Validasi config
        validation_result = admin_export_security.validate_advanced_export_config(
            request.config, user_roles
        )
        
        if not validation_result["valid"]:
            return {
                "valid": False,
                "errors": validation_result["errors"]
            }
        
        # Build query dan analyze
        query_builder = AdvancedExportQueryBuilder()
        pipeline = query_builder.build_advanced_pipeline(request.config)
        query_analysis = query_builder.get_query_analysis(request.config)
        performance_analysis = admin_export_security.analyze_query_performance(request.config)
        
        # Estimate execution details
        estimated_count = await query_builder.estimate_advanced_result_count(db, request.config)
        
        return {
            "valid": True,
            "query_analysis": query_analysis,
            "performance_analysis": performance_analysis,
            "pipeline_stages": len(pipeline),
            "estimated_records": estimated_count,
            "estimated_execution_time": _estimate_execution_time(query_analysis, estimated_count),
            "mongodb_pipeline": pipeline if len(pipeline) < 10 else pipeline[:10]  # Limit output
        }
    
    except Exception as e:
        logger.error(f"Error analyzing advanced query: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze query")

# Helper functions

async def _execute_advanced_query(db: AsyncIOMotorDatabase, collection: str, 
                                 pipeline: List[dict], config: AdvancedExportConfig) -> List[dict]:
    """Execute advanced aggregation pipeline dengan performance options"""
    try:
        options = {}
        
        if config.allow_disk_use:
            options['allowDiskUse'] = True
        
        if config.max_time_ms:
            options['maxTimeMS'] = config.max_time_ms
        
        cursor = db[collection].aggregate(pipeline, **options)
        results = await cursor.to_list(length=None)
        return results
    
    except Exception as e:
        logger.error(f"Error executing advanced query on {collection}: {e}")
        raise

async def _handle_dry_run(request: AdvancedExportRequest, db: AsyncIOMotorDatabase, 
                         user_id: str) -> AdvancedExportResponse:
    """Handle dry run mode - validate and estimate without executing"""
    query_builder = AdvancedExportQueryBuilder()
    pipeline = query_builder.build_advanced_pipeline(request.config)
    query_analysis = query_builder.get_query_analysis(request.config)
    estimated_count = await query_builder.estimate_advanced_result_count(db, request.config)
    
    return AdvancedExportResponse(
        success=True,
        message=f"Dry run completed. Would export approximately {estimated_count} records.",
        estimated_records=estimated_count,
        pipeline_stages=len(pipeline),
        warnings=query_analysis.get("warnings", [])
    )

async def _handle_explain_mode(request: AdvancedExportRequest, db: AsyncIOMotorDatabase, 
                              user_id: str) -> AdvancedExportResponse:
    """Handle explain mode - return execution plan"""
    query_builder = AdvancedExportQueryBuilder()
    pipeline = query_builder.build_advanced_pipeline(request.config)
    
    # Get execution stats using MongoDB explain
    try:
        explain_result = await db[request.config.main_collection].aggregate(
            pipeline, explain=True
        ).to_list(1)
        
        return AdvancedExportResponse(
            success=True,
            message="Query execution plan generated.",
            execution_plan=explain_result[0] if explain_result else {},
            pipeline_stages=len(pipeline)
        )
    except Exception as e:
        # Fallback to basic analysis
        query_analysis = query_builder.get_query_analysis(request.config)
        return AdvancedExportResponse(
            success=True,
            message="Query analysis completed.",
            execution_plan={"analysis": query_analysis, "pipeline": pipeline},
            pipeline_stages=len(pipeline)
        )

async def _process_advanced_export_async(
    task_id: str,
    config: AdvancedExportConfig,
    format,
    filename: Optional[str],
    pipeline: List[dict],
    db: AsyncIOMotorDatabase,
    user_id: str,
    query_analysis: Dict[str, Any]
):
    """Process advanced export in background task"""
    import tempfile
    import json
    from datetime import datetime
    
    status_file = os.path.join(tempfile.gettempdir(), f"export_status_{task_id}.json")
    
    try:
        start_time = time.time()
        
        # Update status to processing
        status_data = {
            "task_id": task_id,
            "status": "processing",
            "progress": 0,
            "message": "Starting advanced export...",
            "created_at": datetime.utcnow().isoformat(),
            "complexity": query_analysis.get("complexity"),
            "collections_involved": query_analysis.get("collections_involved")
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        # Execute advanced query
        status_data["progress"] = 25
        status_data["message"] = "Executing advanced query..."
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        data = await _execute_advanced_query(db, config.main_collection, pipeline, config)
        
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
        
        file_path = export_manager.export_data(data, format, filename, user_id=user_id)
        
        execution_time = int((time.time() - start_time) * 1000)
        
        # Update status to completed
        status_data["status"] = "completed"
        status_data["progress"] = 100
        status_data["message"] = f"Advanced export completed. {len(data)} records exported."
        status_data["file_url"] = f"/api/v1/exports/download/{os.path.basename(file_path)}"
        status_data["completed_at"] = datetime.utcnow().isoformat()
        status_data["execution_time_ms"] = execution_time
        status_data["record_count"] = len(data)
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        logger.info(f"Advanced async export {task_id} completed successfully in {execution_time}ms")
    
    except Exception as e:
        logger.error(f"Advanced async export {task_id} failed: {e}")
        
        # Update status to failed
        status_data = {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "message": "Advanced export failed",
            "error_details": str(e),
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)

def _estimate_execution_time(query_analysis: Dict[str, Any], estimated_records: Optional[int]) -> str:
    """Estimate query execution time based on complexity"""
    complexity = query_analysis.get("complexity", "low")
    total_joins = query_analysis.get("total_joins", 0)
    records = estimated_records or 0
    
    # Base time estimation
    if complexity == "very_high":
        base_time = 30
    elif complexity == "high":
        base_time = 15
    elif complexity == "medium":
        base_time = 5
    else:
        base_time = 2
    
    # Add time for joins
    join_time = total_joins * 3
    
    # Add time for record count
    record_time = records / 1000  # 1 second per 1000 records
    
    total_seconds = base_time + join_time + record_time
    
    if total_seconds > 60:
        return f"{total_seconds/60:.1f} minutes"
    else:
        return f"{total_seconds:.1f} seconds"
