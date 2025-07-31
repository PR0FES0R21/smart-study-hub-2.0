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
    CoordinationAssignmentCreate, CoordinationAssignmentUpdate,
    CoordinationAssignmentPublic, CoordinationAssignmentFilter,
    BulkCoordinationRequest, BulkCoordinationResponse,
    AvailableCoordinatorResponse
)
from app.core.websocket import manager

router = APIRouter()

@router.get("/available-coordinators", response_model=List[AvailableCoordinatorResponse])
async def get_available_coordinators_for_teacher(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    active_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mendapatkan list koordinator yang available untuk guru berdasarkan teaching assignments.
    Response lebih informatif dengan context dan stats.
    """
    teacher_id = current_user["_id"]
    
    pipeline = [
        # 1. Match teaching assignments untuk guru ini di academic period aktif
        {
            "$match": {
                "teacher_id": ObjectId(teacher_id),
                "academic_period_id": ObjectId(active_period["_id"])
            }
        },
        
        # 2. Join dengan classes untuk dapetin grade_level
        {
            "$lookup": {
                "from": "classes",
                "localField": "class_id",
                "foreignField": "_id",
                "as": "class_info"
            }
        },
        {"$unwind": "$class_info"},
        
        # 3. Join dengan subjects untuk dapetin subject name
        {
            "$lookup": {
                "from": "subjects", 
                "localField": "subject_id",
                "foreignField": "_id",
                "as": "subject_info"
            }
        },
        {"$unwind": "$subject_info"},
        
        # 4. Group untuk mendapatkan unique combination subject_id + grade_level yang diajar guru ini
        {
            "$group": {
                "_id": {
                    "subject_id": "$subject_id",
                    "grade_level": "$class_info.grade_level"
                },
                "subject_id": {"$first": "$subject_id"},
                "subject_name": {"$first": "$subject_info.name"},
                "subject_code": {"$first": "$subject_info.code"},
                "grade_level": {"$first": "$class_info.grade_level"},
                "user_classes": {"$addToSet": "$class_info.name"}
            }
        },
        
        # 5. Lookup coordination_assignments untuk setiap kombinasi subject+grade
        {
            "$lookup": {
                "from": "coordination_assignments",
                "let": {
                    "subject_id": "$subject_id",
                    "grade_level": "$grade_level"
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$subject_id", "$$subject_id"]},
                                    {"$eq": ["$grade_level", "$$grade_level"]},
                                    {"$eq": ["$academic_period_id", ObjectId(active_period["_id"])]},
                                    {"$ne": ["$coordinator_id", ObjectId(teacher_id)]}
                                ]
                            }
                        }
                    }
                ],
                "as": "coordination"
            }
        },
        
        # 6. Filter hanya yang ada koordinatornya
        {
            "$match": {
                "coordination": {"$ne": []}
            }
        },
        {"$unwind": "$coordination"},
        
        # 7. Join dengan users untuk dapetin coordinator info
        {
            "$lookup": {
                "from": "users",
                "localField": "coordination.coordinator_id", 
                "foreignField": "_id",
                "as": "coordinator_user"
            }
        },
        {"$unwind": "$coordinator_user"},
        
        # 8. Join dengan profiles untuk dapetin coordinator info lengkap
        {
            "$lookup": {
                "from": "profiles",
                "localField": "coordinator_user.profile_id",
                "foreignField": "_id", 
                "as": "coordinator_profile"
            }
        },
        {"$unwind": "$coordinator_profile"},
        
        # 9. Lookup untuk hitung total teachers under coordination ini
        {
            "$lookup": {
                "from": "teaching_assignments",
                "let": {
                    "coord_subject_id": "$coordination.subject_id",
                    "coord_grade_level": "$coordination.grade_level"
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$subject_id", "$$coord_subject_id"]},
                                    {"$eq": ["$academic_period_id", ObjectId(active_period["_id"])]}
                                ]
                            }
                        }
                    },
                    {
                        "$lookup": {
                            "from": "classes",
                            "localField": "class_id",
                            "foreignField": "_id",
                            "as": "class_info"
                        }
                    },
                    {"$unwind": "$class_info"},
                    {
                        "$match": {
                            "$expr": {"$eq": ["$class_info.grade_level", "$$coord_grade_level"]}
                        }
                    },
                    {
                        "$group": {
                            "_id": "$teacher_id"
                        }
                    }
                ],
                "as": "teachers_under_coordination"
            }
        },
        
        # 10. Project hasil final dengan informasi lengkap
        {
            "$project": {
                "coordination_assignment_id": "$coordination._id",
                "coordinator_id": "$coordination.coordinator_id",
                "coordinator_name": "$coordinator_profile.full_name",
                "coordinator_email": "$coordinator_user.email",
                "coordinator_phone": {"$ifNull": ["$coordinator_profile.phone_number", None]},
                "subject_id": "$subject_id",
                "subject_name": "$subject_name", 
                "subject_code": "$subject_code",
                "grade_level": "$grade_level",
                "matching_reason": "same_subject_grade",
                "user_classes_in_subject": "$user_classes",
                "coordinator_responsible_for": {
                    "$concat": [
                        "Koordinator ", 
                        "$subject_name", 
                        " Kelas ", 
                        {"$toString": "$grade_level"}
                    ]
                },
                "total_teachers_under_coordination": {"$size": "$teachers_under_coordination"}
            }
        },
        
        # 11. Sort berdasarkan subject name dan grade level
        {
            "$sort": {
                "subject_name": 1,
                "grade_level": 1
            }
        }
    ]
    
    result = await db["teaching_assignments"].aggregate(pipeline).to_list(None)
    
    # Convert to response format
    available_coordinators = []
    for item in result:
        available_coordinators.append({
            "coordinator_id": str(item["coordinator_id"]),
            "coordinator_name": item["coordinator_name"],
            "coordinator_email": item["coordinator_email"],
            "coordinator_phone": item.get("coordinator_phone"),
            "coordination_assignment_id": str(item["coordination_assignment_id"]),
            "subject_id": str(item["subject_id"]),
            "subject_name": item["subject_name"],
            "subject_code": item["subject_code"],
            "grade_level": item["grade_level"],
            "matching_reason": item["matching_reason"],
            "user_classes_in_subject": item["user_classes_in_subject"],
            "coordinator_responsible_for": item["coordinator_responsible_for"],
            "total_teachers_under_coordination": item["total_teachers_under_coordination"]
        })
    
    return available_coordinators

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