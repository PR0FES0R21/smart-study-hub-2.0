# ==============================================================================
# File: app/crud/crud_coordination_assignments.py
# Deskripsi: Fungsi CRUD untuk collection 'coordination_assignments'.
# --- UPDATED WITH FULL CRUD + BULK OPERATIONS ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.schemas.coordination_assignment import (
    CoordinationAssignmentCreate, 
    CoordinationAssignmentUpdate,
    BulkCoordinationOperation
)

async def create_coordination(db: AsyncIOMotorDatabase, coord: CoordinationAssignmentCreate, academic_period_id: ObjectId) -> dict:
    """Create single coordination assignment"""
    # Check if coordination already exists for this subject, grade, and academic period
    existing = await db["coordination_assignments"].find_one({
        "subject_id": coord.subject_id, 
        "grade_level": coord.grade_level,
        "academic_period_id": academic_period_id
    })
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"A coordinator for this subject and grade level already exists in this academic period."
        )
    
    coord_dict = coord.model_dump(mode='python')
    coord_dict["academic_period_id"] = academic_period_id
    
    result = await db["coordination_assignments"].insert_one(coord_dict)
    return await db["coordination_assignments"].find_one({"_id": result.inserted_id})

async def get_coordination_by_id(db: AsyncIOMotorDatabase, coordination_id: str) -> Optional[dict]:
    """Get coordination by ID"""
    try:
        obj_id = ObjectId(coordination_id)
        return await db["coordination_assignments"].find_one({"_id": obj_id})
    except Exception:
        return None

async def get_coordinations_by_academic_period(
    db: AsyncIOMotorDatabase, 
    academic_period_id: ObjectId,
    subject_id: Optional[ObjectId] = None,
    grade_level: Optional[int] = None
) -> List[dict]:
    """Get coordinations filtered by academic period and optional filters"""
    filter_query = {"academic_period_id": academic_period_id}
    
    if subject_id:
        filter_query["subject_id"] = subject_id
    if grade_level:
        filter_query["grade_level"] = grade_level
    
    return await db["coordination_assignments"].find(filter_query).to_list(None)

async def get_coordinations_by_user(db: AsyncIOMotorDatabase, user_id: ObjectId, academic_period_id: Optional[ObjectId] = None) -> List[dict]:
    """Get coordinations by coordinator user ID"""
    filter_query = {"coordinator_id": user_id}
    if academic_period_id:
        filter_query["academic_period_id"] = academic_period_id
    
    return await db["coordination_assignments"].find(filter_query).to_list(None)

async def update_coordination(
    db: AsyncIOMotorDatabase, 
    coordination_id: str, 
    coord_update: CoordinationAssignmentUpdate
) -> Optional[dict]:
    """Update coordination assignment"""
    try:
        obj_id = ObjectId(coordination_id)
        
        # Get current coordination
        current_coord = await db["coordination_assignments"].find_one({"_id": obj_id})
        if not current_coord:
            raise HTTPException(status_code=404, detail="Coordination assignment not found")
        
        update_data = coord_update.model_dump(mode='python', exclude_unset=True)
        
        # Check for conflicts if updating subject_id or grade_level
        if "subject_id" in update_data or "grade_level" in update_data:
            check_subject_id = update_data.get("subject_id", current_coord["subject_id"])
            check_grade_level = update_data.get("grade_level", current_coord["grade_level"])
            
            existing = await db["coordination_assignments"].find_one({
                "subject_id": check_subject_id,
                "grade_level": check_grade_level,
                "academic_period_id": current_coord["academic_period_id"],
                "_id": {"$ne": obj_id}
            })
            
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="A coordinator for this subject and grade level already exists in this academic period."
                )
        
        result = await db["coordination_assignments"].update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return None
            
        return await db["coordination_assignments"].find_one({"_id": obj_id})
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        return None

async def delete_coordination(db: AsyncIOMotorDatabase, coordination_id: str) -> bool:
    """Delete coordination assignment"""
    try:
        obj_id = ObjectId(coordination_id)
        result = await db["coordination_assignments"].delete_one({"_id": obj_id})
        return result.deleted_count > 0
    except Exception:
        return False

async def process_bulk_operations(
    db: AsyncIOMotorDatabase, 
    operations: List[BulkCoordinationOperation],
    academic_period_id: ObjectId
) -> Dict[str, Any]:
    """Process bulk coordination operations with detailed results"""
    
    results = {
        "total": len(operations),
        "success": 0,
        "failed": 0,
        "errors": [],
        "processed_operations": []
    }
    
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
                if not operation.data:
                    raise ValueError("Create operation requires data")
                
                coord_create = CoordinationAssignmentCreate(**operation.data)
                result = await create_coordination(db, coord_create, academic_period_id)
                operation_result["success"] = True
                operation_result["data"] = result
                results["success"] += 1
                
            elif operation.type == "update":
                if not operation.id or not operation.data:
                    raise ValueError("Update operation requires both id and data")
                
                coord_update = CoordinationAssignmentUpdate(**operation.data)
                result = await update_coordination(db, operation.id, coord_update)
                
                if result:
                    operation_result["success"] = True
                    operation_result["data"] = result
                    results["success"] += 1
                else:
                    raise ValueError("Coordination not found or no changes made")
                    
            elif operation.type == "delete":
                if not operation.id:
                    raise ValueError("Delete operation requires id")
                
                success = await delete_coordination(db, operation.id)
                if success:
                    operation_result["success"] = True
                    operation_result["data"] = {"deleted": True}
                    results["success"] += 1
                else:
                    raise ValueError("Coordination not found or failed to delete")
            else:
                raise ValueError(f"Unknown operation type: {operation.type}")
                
        except Exception as e:
            operation_result["error"] = str(e)
            results["failed"] += 1
            results["errors"].append({
                "operation_index": index,
                "operation_type": operation.type,
                "error": str(e)
            })
        
        results["processed_operations"].append(operation_result)
    
    return results