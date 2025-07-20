# ==============================================================================
# File: app/crud/crud_coordination_assignments.py
# Deskripsi: Fungsi CRUD untuk collection 'coordination_assignments'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List
from bson import ObjectId
from app.schemas.coordination_assignment import CoordinationAssignmentCreate

async def create_coordination(db: AsyncIOMotorDatabase, coord: CoordinationAssignmentCreate) -> dict:
    if await db["coordination_assignments"].find_one({"subject_id": coord.subject_id, "grade_level": coord.grade_level}):
        raise HTTPException(status_code=400, detail="A coordinator for this subject and grade level already exists.")
    
    coord_dict = coord.model_dump(mode='python')
    result = await db["coordination_assignments"].insert_one(coord_dict)
    return await db["coordination_assignments"].find_one({"_id": result.inserted_id})

async def get_coordinations_by_user(db: AsyncIOMotorDatabase, user_id: ObjectId) -> List[dict]:
    return await db["coordination_assignments"].find({"coordinator_id": user_id}).to_list(None)
