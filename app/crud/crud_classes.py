# ==============================================================================
# File: app/crud/crud_classes.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'classes'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List
from bson import ObjectId

from app.schemas.classes import ClassCreate, ClassUpdate
from app.core.cache import invalidate_cache

async def create_class(db: AsyncIOMotorDatabase, class_in: ClassCreate) -> dict:
    """Membuat kelas baru."""
    # Cek duplikasi: kelas dengan nama, jurusan, dan tahun ajaran yang sama tidak boleh ada
    existing_class = await db["classes"].find_one({
        "grade_level": class_in.grade_level,
        "expertise_id": class_in.expertise_id,
        "name": class_in.name,
        "academic_year": class_in.academic_year
    })
    if existing_class:
        raise HTTPException(status_code=400, detail="Class with the same details already exists.")
    
    class_dict = class_in.dict(exclude_unset=True)
    result = await db["classes"].insert_one(class_dict)
    created_class = await db["classes"].find_one({"_id": result.inserted_id})
    await invalidate_cache("analytics:dashboard_stats")
    return created_class

async def get_all_classes_with_details(db: AsyncIOMotorDatabase) -> List[dict]:
    """Mengambil semua kelas dengan detail jurusan dan wali kelas."""
    pipeline = [
        {
            "$lookup": {
                "from": "expertise_programs",
                "localField": "expertise_id",
                "foreignField": "_id",
                "as": "expertise_details_array"
            }
        },
        {
            "$unwind": {
                "path": "$expertise_details_array",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "homeroom_teacher_id",
                "foreignField": "_id",
                "as": "homeroom_teacher_details_array"
            }
        },
        {
            "$unwind": {
                "path": "$homeroom_teacher_details_array",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$addFields": {
                "expertise_details": "$expertise_details_array",
                "homeroom_teacher_details": "$homeroom_teacher_details_array"
            }
        },
        {
            "$project": {
                "expertise_details_array": 0,
                "homeroom_teacher_details_array": 0,
                "homeroom_teacher_details.hashed_password": 0 # Pastikan tidak mengirim hash password
            }
        }
    ]
    classes = await db["classes"].aggregate(pipeline).to_list(1000)
    return classes

async def get_class_by_id(db: AsyncIOMotorDatabase, class_id: str) -> dict | None:
    """Mengambil satu kelas berdasarkan ID."""
    if not ObjectId.is_valid(class_id): return None
    return await db["classes"].find_one({"_id": ObjectId(class_id)})

async def update_class(db: AsyncIOMotorDatabase, class_id: str, class_update: ClassUpdate) -> dict | None:
    """Memperbarui kelas."""
    if not ObjectId.is_valid(class_id): return None
    
    update_data = class_update.dict(exclude_unset=True)
    if not update_data:
        return await get_class_by_id(db, class_id)

    await db["classes"].update_one({"_id": ObjectId(class_id)}, {"$set": update_data})
    return await get_class_by_id(db, class_id)

async def delete_class(db: AsyncIOMotorDatabase, class_id: str) -> bool:
    """Menghapus kelas."""
    if not ObjectId.is_valid(class_id): return False
    
    result = await db["classes"].delete_one({"_id": ObjectId(class_id)})
    if result.deleted_count > 0:
        await invalidate_cache("analytics:dashboard_stats")
    return result.deleted_count > 0
