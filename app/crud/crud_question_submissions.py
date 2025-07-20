# ==============================================================================
# File: app/crud/crud_question_submissions.py
# Deskripsi: Fungsi CRUD untuk collection 'question_submissions'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId
from datetime import datetime
from app.schemas.question_submission import SubmissionStatusUpdate

async def create_submissions(db: AsyncIOMotorDatabase, submissions_data: List[dict]) -> bool:
    """Membuat beberapa dokumen pengajuan soal baru."""
    if not submissions_data:
        return False
    await db["question_submissions"].insert_many(submissions_data)
    return True

async def get_submissions_for_coordinator(db: AsyncIOMotorDatabase, coordination_ids: List[ObjectId], purpose: str, status: str) -> List[dict]:
    """Mengambil pengajuan soal untuk koordinator berdasarkan tujuan dan status."""
    pipeline = [
        {"$match": {
            "coordination_assignment_id": {"$in": coordination_ids},
            "purpose": purpose,
            "status": status
        }},
        # Gabungkan dengan detail soalnya
        {"$lookup": {"from": "question_banks", "localField": "question_id", "foreignField": "_id", "as": "question_details"}},
        {"$unwind": "$question_details"},
    ]
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
