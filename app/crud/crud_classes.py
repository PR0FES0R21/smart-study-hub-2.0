# ==============================================================================
# File: app/crud/crud_classes.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'classes'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
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

async def get_paginated_classes_with_details(
    db: AsyncIOMotorDatabase, 
    skip: int, 
    limit: int, 
    search: Optional[str] = None,
    grade_level: Optional[int] = None,
    expertise_id: Optional[str] = None,
    academic_year: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mengambil semua kelas dengan detail, filter, paginasi, dan statistik.
    """
    # Tahap 1: Bangun pipeline lookup dasar
    base_pipeline = [
        {"$lookup": {"from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
        {"$unwind": {"path": "$expertise_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "homeroom_teacher_id", "foreignField": "_id", "as": "teacher_user_info"}},
        {"$unwind": {"path": "$teacher_user_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "profiles", "localField": "teacher_user_info.profile_id", "foreignField": "_id", "as": "teacher_profile_info"}},
        {"$unwind": {"path": "$teacher_profile_info", "preserveNullAndEmptyArrays": True}},
        # --- PERBAIKAN: Menambahkan field baru ke $project ---
        {"$project": {
            "grade_level": 1, "expertise_id": 1, "name": 1, "academic_year": 1, "homeroom_teacher_id": 1,
            "expertise_details": 1,
            "homeroom_teacher_details": {
                "$cond": {
                    "if": "$teacher_profile_info",
                    "then": {
                        "_id": "$teacher_user_info._id",
                        "full_name": "$teacher_profile_info.full_name",
                        "gender": "$teacher_profile_info.gender",
                        "profile_picture_url": "$teacher_profile_info.profile_picture_url"
                    },
                    "else": None
                }
            }
        }}
    ]

    # Tahap 2: Bangun query filter dinamis
    match_query = {}
    if grade_level:
        match_query["grade_level"] = grade_level
    if expertise_id:
        match_query["expertise_id"] = ObjectId(expertise_id)
    if academic_year:
        match_query["academic_year"] = academic_year
    if search:
        match_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"academic_year": {"$regex": search, "$options": "i"}},
            {"expertise_details.name": {"$regex": search, "$options": "i"}},
            {"homeroom_teacher_details.full_name": {"$regex": search, "$options": "i"}},
        ]
    
    # Gabungkan pipeline lookup dengan filter
    full_pipeline = base_pipeline + [{"$match": match_query}] if match_query else base_pipeline

    # Tahap 3: Gunakan $facet untuk mendapatkan data dan statistik dalam satu query
    facet_stage = {
        "$facet": {
            "paginated_data": [
                {"$sort": {"grade_level": 1, "name": 1}},
                {"$skip": skip},
                {"$limit": limit}
            ],
            "total_filtered_count": [{"$count": "count"}],
            "grade_10_total": [{"$match": {"grade_level": 10}}, {"$count": "count"}],
            "grade_11_total": [{"$match": {"grade_level": 11}}, {"$count": "count"}],
            "grade_12_total": [{"$match": {"grade_level": 12}}, {"$count": "count"}]
        }
    }
    
    # Jalankan query utama
    main_query_pipeline = [{"$match": match_query}] if match_query else []
    main_query_pipeline.extend(base_pipeline)
    main_query_pipeline.append(facet_stage)
    
    # Jalankan query yang sedikit berbeda untuk statistik total (tanpa filter pencarian)
    stats_pipeline = [{"$match": {k:v for k,v in match_query.items() if k != '$or'}}] if match_query else []
    stats_pipeline.append(facet_stage)

    result = await db["classes"].aggregate(main_query_pipeline).to_list(1)
    stats_result = await db["classes"].aggregate(stats_pipeline).to_list(1)

    data = result[0]['paginated_data'] if result and result[0]['paginated_data'] else []
    total_items = result[0]['total_filtered_count'][0]['count'] if result and result[0]['total_filtered_count'] else 0
    
    grade_10_total = stats_result[0]['grade_10_total'][0]['count'] if stats_result and stats_result[0]['grade_10_total'] else 0
    grade_11_total = stats_result[0]['grade_11_total'][0]['count'] if stats_result and stats_result[0]['grade_11_total'] else 0
    grade_12_total = stats_result[0]['grade_12_total'][0]['count'] if stats_result and stats_result[0]['grade_12_total'] else 0

    return {
        "data": data, 
        "total_items": total_items,
        "grade_10_total": grade_10_total,
        "grade_11_total": grade_11_total,
        "grade_12_total": grade_12_total,
    }

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

async def create_classes_for_next_year(db: AsyncIOMotorDatabase, current_year: str, next_year: str) -> int:
    """Menduplikasi struktur kelas dari tahun saat ini ke tahun berikutnya."""
    current_year_classes = await db["classes"].find({"academic_year": current_year}).to_list(None)
    if not current_year_classes:
        raise HTTPException(status_code=404, detail=f"No classes found for academic year {current_year}")

    new_classes_to_create = []
    for old_class in current_year_classes:
        new_class_doc = {
            "grade_level": old_class["grade_level"],
            "expertise_id": old_class["expertise_id"],
            "name": old_class["name"],
            "academic_year": next_year,
            "homeroom_teacher_id": None # Dikosongkan untuk diisi kembali
        }
        new_classes_to_create.append(new_class_doc)

    if not new_classes_to_create:
        return 0

    result = await db["classes"].insert_many(new_classes_to_create)
    return len(result.inserted_ids)
