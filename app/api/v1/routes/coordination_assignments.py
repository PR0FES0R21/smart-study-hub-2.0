# ==============================================================================
# File: app/api/v1/routes/coordination_assignments.py
# Deskripsi: Endpoint API untuk manajemen Koordinator.
# --- UPDATED WITH FULL CRUD + BULK OPERATIONS + WEBSOCKET ---
# ==============================================================================
from fastapi import APIRouter, Depends, status, HTTPException, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
import asyncio
import json
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_coordination_assignments
from app.schemas.coordination_assignment import (
    CoordinationAssignmentCreate, 
    CoordinationAssignmentUpdate,
    CoordinationAssignmentPublic,
    CoordinationAssignmentFilter,
    BulkCoordinationRequest,
    BulkCoordinationResponse
)
from app.core.websocket import manager

router = APIRouter()

# ===== SINGLE OPERATIONS =====

@router.post("/", response_model=CoordinationAssignmentPublic, status_code=status.HTTP_201_CREATED)
async def create_coordination_assignment(
    coord_in: CoordinationAssignmentCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    academic_period: dict = Depends(deps.get_current_academic_period)
):
    """Membuat penunjukan koordinator baru. Hanya untuk admin."""
    return await crud_coordination_assignments.create_coordination(
        db, coord_in, academic_period["_id"]
    )

@router.get("/{coordination_id}", response_model=CoordinationAssignmentPublic)
async def get_coordination_assignment(
    coordination_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Mendapatkan penunjukan koordinator berdasarkan ID."""
    coordination = await crud_coordination_assignments.get_coordination_by_id(db, coordination_id)
    if not coordination:
        raise HTTPException(status_code=404, detail="Coordination assignment not found")
    return coordination

@router.get("/", response_model=List[CoordinationAssignmentPublic])
async def get_coordination_assignments(
    academic_period_id: Optional[str] = Query(None, description="Filter by academic period ID"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    grade_level: Optional[int] = Query(None, ge=1, le=12, description="Filter by grade level"),
    coordinator_id: Optional[str] = Query(None, description="Filter by coordinator user ID"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    default_academic_period: dict = Depends(deps.get_current_academic_period)
):
    """Mendapatkan daftar penunjukan koordinator dengan filter."""
    
    # Use provided academic_period_id or default to current active period
    target_academic_period_id = None
    if academic_period_id:
        try:
            target_academic_period_id = ObjectId(academic_period_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid academic_period_id format")
    else:
        target_academic_period_id = ObjectId(default_academic_period["_id"])
    
    # Handle coordinator_id filter
    if coordinator_id:
        try:
            coordinator_obj_id = ObjectId(coordinator_id)
            return await crud_coordination_assignments.get_coordinations_by_user(
                db, coordinator_obj_id, target_academic_period_id
            )
        except:
            raise HTTPException(status_code=400, detail="Invalid coordinator_id format")
    
    # Handle subject_id filter
    subject_obj_id = None
    if subject_id:
        try:
            subject_obj_id = ObjectId(subject_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid subject_id format")
    
    return await crud_coordination_assignments.get_coordinations_by_academic_period(
        db, target_academic_period_id, subject_obj_id, grade_level
    )

@router.put("/{coordination_id}", response_model=CoordinationAssignmentPublic)
async def update_coordination_assignment(
    coordination_id: str,
    coord_update: CoordinationAssignmentUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Memperbarui penunjukan koordinator."""
    updated_coordination = await crud_coordination_assignments.update_coordination(
        db, coordination_id, coord_update
    )
    if not updated_coordination:
        raise HTTPException(status_code=404, detail="Coordination assignment not found")
    return updated_coordination

@router.delete("/{coordination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coordination_assignment(
    coordination_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Menghapus penunjukan koordinator."""
    success = await crud_coordination_assignments.delete_coordination(db, coordination_id)
    if not success:
        raise HTTPException(status_code=404, detail="Coordination assignment not found")

# ===== BULK OPERATIONS =====

async def send_progress_update(total: int, current: int, success: int, failed: int, errors: list):
    """Send progress update via WebSocket to admins"""
    try:
        percentage = int((current / total) * 100) if total > 0 else 0
        message = {
            "type": "bulk_progress",
            "progress": {
                "current": current,
                "total": total,
                "percentage": percentage,
                "success": success,
                "failed": failed,
                "errors": errors
            }
        }
        await manager.broadcast_to_roles(message, target_roles=["admin"])
    except Exception as e:
        print(f"Error sending progress update: {e}")

async def process_bulk_operations_with_progress(
    db: AsyncIOMotorDatabase,
    operations: list,
    academic_period_id,
    user_id: str
):
    """Process bulk operations with real-time progress updates"""
    total = len(operations)
    success = 0
    failed = 0
    errors = []
    processed_operations = []
    
    # Send initial progress
    await send_progress_update(total, 0, success, failed, errors)
    
    for index, operation in enumerate(operations):
        operation_result = {
            "index": index,
            "type": operation.type,
            "success": False,
            "error": None,
            "data": None
        }
        
        try:
            if operation.type == "create":
                coord_create = CoordinationAssignmentCreate(**operation.data)
                result = await crud_coordination_assignments.create_coordination(
                    db, coord_create, academic_period_id
                )
                operation_result["success"] = True
                operation_result["data"] = result
                success += 1
                
            elif operation.type == "update":
                coord_update = CoordinationAssignmentUpdate(**operation.data)
                result = await crud_coordination_assignments.update_coordination(
                    db, operation.id, coord_update
                )
                if result:
                    operation_result["success"] = True
                    operation_result["data"] = result
                    success += 1
                else:
                    raise ValueError("Coordination not found or no changes made")
                    
            elif operation.type == "delete":
                delete_success = await crud_coordination_assignments.delete_coordination(
                    db, operation.id
                )
                if delete_success:
                    operation_result["success"] = True
                    operation_result["data"] = {"deleted": True}
                    success += 1
                else:
                    raise ValueError("Coordination not found or failed to delete")
            else:
                raise ValueError(f"Unknown operation type: {operation.type}")
                
        except Exception as e:
            operation_result["error"] = str(e)
            failed += 1
            errors.append({
                "operation_index": index,
                "operation_type": operation.type,
                "error": str(e)
            })
        
        processed_operations.append(operation_result)
        
        # Send progress update every operation
        current = index + 1
        await send_progress_update(total, current, success, failed, errors)
        
        # Small delay to prevent overwhelming
        await asyncio.sleep(0.1)
    
    # Send completion message
    final_results = {
        "total": total,
        "success": success,
        "failed": failed,
        "errors": errors,
        "processed_operations": processed_operations
    }
    
    completion_message = {
        "type": "bulk_complete",
        "results": final_results
    }
    await manager.broadcast_to_roles(completion_message, target_roles=["admin"])
    
    return final_results

@router.post("/bulk", response_model=BulkCoordinationResponse)
async def bulk_coordination_operations(
    request: BulkCoordinationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin),
    default_academic_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Proses operasi koordinator secara massal dengan update real-time via WebSocket.
    Mendukung operasi create, update, dan delete dalam satu request.
    """
    
    if not request.operations:
        raise HTTPException(status_code=400, detail="No operations provided")
    
    # Determine academic period
    target_academic_period_id = request.academic_period_id or default_academic_period["_id"]
    
    # Validate operations first
    for i, op in enumerate(request.operations):
        if op.type in ["update", "delete"] and not op.id:
            raise HTTPException(
                status_code=400, 
                detail=f"Operation {i}: {op.type} requires id"
            )
        if op.type in ["create", "update"] and not op.data:
            raise HTTPException(
                status_code=400, 
                detail=f"Operation {i}: {op.type} requires data"
            )
    
    # Process in background with WebSocket updates
    background_tasks.add_task(
        process_bulk_operations_with_progress,
        db,
        request.operations,
        target_academic_period_id,
        str(current_user["_id"])
    )
    
    # Return immediate response
    return BulkCoordinationResponse(
        total=len(request.operations),
        success=0,
        failed=0,
        errors=[],
        processed_operations=[]
    )