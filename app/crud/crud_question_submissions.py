# ==============================================================================
# File: app/crud/crud_question_submissions.py
# Deskripsi: Fungsi CRUD untuk collection 'question_submissions'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.schemas.question_submission import SubmissionStatusUpdate

async def create_submissions(db: AsyncIOMotorDatabase, submissions_data: List[dict]) -> bool:
    """Membuat beberapa dokumen pengajuan soal baru."""
    if not submissions_data:
        return False
    await db["question_submissions"].insert_many(submissions_data)
    return True

async def get_submissions_for_coordinator(
    db: AsyncIOMotorDatabase, 
    coordination_ids: List[ObjectId], 
    academic_period_id: ObjectId,
    search: Optional[str] = None,
    purpose: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None
) -> List[dict]:
    """Mengambil pengajuan soal untuk koordinator dengan berbagai filter."""
    match_filter = {
        "coordination_assignment_id": {"$in": coordination_ids},
        "academic_period_id": academic_period_id
    }
    
    # Filter optional
    if purpose:
        match_filter["purpose"] = {"$regex": purpose, "$options": "i"}
    if status:
        match_filter["status"] = status
    
    pipeline = [
        {"$match": match_filter},
        # Gabungkan dengan detail soalnya
        {
            "$lookup": {
                "from": "question_banks", 
                "localField": "question_id", 
                "foreignField": "_id", 
                "as": "question_details"
            }
        },
        {"$unwind": "$question_details"},
    ]
    
    # Filter berdasarkan question details
    question_match = {}
    if question_type:
        question_match["question_details.question_type"] = question_type
    if difficulty:
        question_match["question_details.difficulty"] = difficulty
    if search:
        question_match["$or"] = [
            {"question_details.question_text": {"$regex": search, "$options": "i"}},
            {"question_details.tags": {"$regex": search, "$options": "i"}}
        ]
    
    if question_match:
        pipeline.append({"$match": question_match})
    
    # Sorting berdasarkan tanggal submit terbaru
    pipeline.append({"$sort": {"created_at": -1}})
    
    return await db["question_submissions"].aggregate(pipeline).to_list(None)

async def get_submissions_by_teacher(
    db: AsyncIOMotorDatabase,
    teacher_id: ObjectId,
    academic_period_id: ObjectId,
    search: Optional[str] = None,
    purpose: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None
) -> List[dict]:
    """Mengambil pengajuan soal yang dibuat oleh guru tertentu dengan berbagai filter."""
    match_filter = {
        "submitted_by_teacher_id": teacher_id,
        "academic_period_id": academic_period_id
    }
    
    # Filter optional
    if purpose:
        match_filter["purpose"] = {"$regex": purpose, "$options": "i"}
    if status:
        match_filter["status"] = status
    
    pipeline = [
        {"$match": match_filter},
        # Gabungkan dengan detail soalnya
        {
            "$lookup": {
                "from": "question_banks", 
                "localField": "question_id", 
                "foreignField": "_id", 
                "as": "question_details"
            }
        },
        {"$unwind": "$question_details"},
    ]
    
    # Filter berdasarkan question details
    question_match = {}
    if question_type:
        question_match["question_details.question_type"] = question_type
    if difficulty:
        question_match["question_details.difficulty"] = difficulty
    if search:
        question_match["$or"] = [
            {"question_details.question_text": {"$regex": search, "$options": "i"}},
            {"question_details.tags": {"$regex": search, "$options": "i"}}
        ]
    
    if question_match:
        pipeline.append({"$match": question_match})
    
    # Sorting berdasarkan tanggal submit terbaru
    pipeline.append({"$sort": {"created_at": -1}})
    
    return await db["question_submissions"].aggregate(pipeline).to_list(None)

async def update_submission_status(db: AsyncIOMotorDatabase, submission_id: ObjectId, status_update: SubmissionStatusUpdate) -> dict | None:
    """Memperbarui status sebuah pengajuan soal."""
    update_data = status_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db["question_submissions"].update_one(
        {"_id": submission_id},
        {"$set": update_data}
    )
    return await db["question_submissions"].find_one({"_id": submission_id})
