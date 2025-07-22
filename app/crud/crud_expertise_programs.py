# ==============================================================================
# File: app/crud/crud_expertise_programs.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'expertise_programs'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import Optional, Dict, Any
from bson import ObjectId

from app.schemas.expertise_program import ExpertiseProgramCreate, ExpertiseProgramUpdate

async def create_expertise_program(db: AsyncIOMotorDatabase, program: ExpertiseProgramCreate) -> dict:
    """Membuat program keahlian (jurusan) baru."""
    # Cek duplikasi berdasarkan singkatan
    existing_program = await db["expertise_programs"].find_one({"abbreviation": program.abbreviation})
    if existing_program:
        raise HTTPException(status_code=400, detail=f"Program with abbreviation '{program.abbreviation}' already exists.")
    
    program_dict = program.dict(exclude_unset=True)
    result = await db["expertise_programs"].insert_one(program_dict)
    created_program = await db["expertise_programs"].find_one({"_id": result.inserted_id})
    return created_program

async def get_all_expertise_programs(
    db: AsyncIOMotorDatabase, 
    skip: int, 
    limit: int, 
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Mengambil semua program keahlian dengan paginasi dan pencarian."""
    query = {}
    if search:
        query = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"abbreviation": {"$regex": search, "$options": "i"}},
            ]
        }

    total_items = await db["expertise_programs"].count_documents(query)
    cursor = db["expertise_programs"].find(query).skip(skip).limit(limit)
    data = await cursor.to_list(length=limit)
    
    return {"data": data, "total_items": total_items}

async def get_expertise_program_by_id(db: AsyncIOMotorDatabase, program_id: str) -> dict | None:
    """Mengambil satu program keahlian berdasarkan ID."""
    if not ObjectId.is_valid(program_id):
        return None
    program = await db["expertise_programs"].find_one({"_id": ObjectId(program_id)})
    return program

async def update_expertise_program(db: AsyncIOMotorDatabase, program_id: str, program_update: ExpertiseProgramUpdate) -> dict | None:
    """Memperbarui program keahlian."""
    if not ObjectId.is_valid(program_id):
        return None
    
    update_data = program_update.dict(exclude_unset=True)
    if not update_data:
        return await get_expertise_program_by_id(db, program_id)

    await db["expertise_programs"].update_one({"_id": ObjectId(program_id)}, {"$set": update_data})
    updated_program = await get_expertise_program_by_id(db, program_id)
    return updated_program

async def delete_expertise_program(db: AsyncIOMotorDatabase, program_id: str) -> bool:
    """Menghapus program keahlian."""
    if not ObjectId.is_valid(program_id):
        return False
    
    result = await db["expertise_programs"].delete_one({"_id": ObjectId(program_id)})
    return result.deleted_count > 0