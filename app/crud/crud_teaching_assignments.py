# ==============================================================================
# File: app/crud/crud_teaching_assignments.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'teaching_assignments'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Optional
from bson import ObjectId

from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentUpdate

async def create_teaching_assignment(db: AsyncIOMotorDatabase, assignment: TeachingAssignmentCreate) -> dict:
    """Membuat penugasan mengajar baru."""
    # Cek duplikasi
    existing = await db["teaching_assignments"].find_one({
        "class_id": assignment.class_id,
        "subject_id": assignment.subject_id,
        "teacher_id": assignment.teacher_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="This exact teaching assignment already exists.")
    
    assignment_dict = assignment.model_dump(mode='python')
    result = await db["teaching_assignments"].insert_one(assignment_dict)
    created = await db["teaching_assignments"].find_one({"_id": result.inserted_id})
    return created

async def get_all_assignments_with_details(db: AsyncIOMotorDatabase) -> List[dict]:
    """Mengambil semua penugasan dengan detailnya."""
    pipeline = [
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": "$class_details"},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject_details"}},
        {"$unwind": "$subject_details"},
        {"$lookup": {"from": "users", "localField": "teacher_id", "foreignField": "_id", "as": "teacher_details"}},
        {"$unwind": "$teacher_details"},
        {"$project": {"teacher_details.hashed_password": 0}} # Hapus password dari output
    ]
    assignments = await db["teaching_assignments"].aggregate(pipeline).to_list(1000)
    return assignments

async def delete_teaching_assignment(db: AsyncIOMotorDatabase, assignment_id: str) -> bool:
    """Menghapus penugasan mengajar."""
    if not ObjectId.is_valid(assignment_id): return False
    result = await db["teaching_assignments"].delete_one({"_id": ObjectId(assignment_id)})
    return result.deleted_count > 0

async def find_assignments_by_criteria(
    db: AsyncIOMotorDatabase, 
    subject_id: ObjectId,
    grade_level: Optional[int] = None,
    expertise_id: Optional[ObjectId] = None,
    class_id: Optional[ObjectId] = None
) -> List[dict]:
    """Mencari penugasan mengajar berdasarkan kriteria untuk pembuatan ujian massal."""
    if class_id:
        return await db["teaching_assignments"].find({"class_id": class_id, "subject_id": subject_id}).to_list(1000)

    # Jika tidak menargetkan kelas spesifik, kita perlu join dengan collection 'classes'
    pipeline = []
    class_match_criteria = {}
    if grade_level: class_match_criteria["grade_level"] = grade_level
    if expertise_id: class_match_criteria["expertise_id"] = expertise_id

    pipeline.extend([
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
        {"$match": {"subject_id": subject_id, **{f"class_info.{k}": v for k, v in class_match_criteria.items()}}}
    ])
    
    return await db["teaching_assignments"].aggregate(pipeline).to_list(1000)

async def update_teaching_assignment(db: AsyncIOMotorDatabase, assignment_id: ObjectId, assignment_update: TeachingAssignmentUpdate) -> dict | None:
    """Memperbarui penugasan mengajar (misalnya, mengganti guru)."""
    update_data = assignment_update.model_dump(mode='python', exclude_unset=True)
    if not update_data:
        return await db["teaching_assignments"].find_one({"_id": assignment_id})
        
    await db["teaching_assignments"].update_one(
        {"_id": assignment_id},
        {"$set": update_data}
    )
    return await db["teaching_assignments"].find_one({"_id": assignment_id})

