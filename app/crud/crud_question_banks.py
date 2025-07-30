# ==============================================================================
# File: app/crud/crud_question_submissions.py (IMPROVED VERSION)
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

async def get_submissions_for_coordinator(
    db: AsyncIOMotorDatabase, 
    coordination_ids: List[ObjectId], 
    purpose: str, 
    status: str
) -> List[dict]:
    """Mengambil pengajuan soal untuk koordinator berdasarkan tujuan dan status."""
    pipeline = [
        {"$match": {
            "coordination_assignment_id": {"$in": coordination_ids},
            "purpose": purpose,
            "status": status
        }},
        # Gabungkan dengan detail soalnya
        {"$lookup": {
            "from": "question_banks", 
            "localField": "question_id", 
            "foreignField": "_id", 
            "as": "question_details"
        }},
        {"$unwind": "$question_details"},
        # Gabungkan dengan info guru yang submit
        {"$lookup": {
            "from": "users", 
            "localField": "submitted_by_teacher_id", 
            "foreignField": "_id", 
            "as": "submitter_info"
        }},
        {"$unwind": "$submitter_info"},
        # Gabungkan dengan info koordinator
        {"$lookup": {
            "from": "coordination_assignments", 
            "localField": "coordination_assignment_id", 
            "foreignField": "_id", 
            "as": "coordination_info"
        }},
        {"$unwind": "$coordination_info"},
        # Gabungkan dengan info mata pelajaran
        {"$lookup": {
            "from": "subjects", 
            "localField": "coordination_info.subject_id", 
            "foreignField": "_id", 
            "as": "subject_info"
        }},
        {"$unwind": "$subject_info"}
    ]
    return await db["question_submissions"].aggregate(pipeline).to_list(None)

async def get_submitted_questions_with_details(
    db: AsyncIOMotorDatabase, 
    coordination_ids: List[ObjectId], 
    purpose: str, 
    status: str
) -> List[dict]:
    """
    Mengambil soal yang di-submit dengan detail lengkap.
    Digunakan untuk koordinator melihat soal yang bisa diakses.
    """
    pipeline = [
        {"$match": {
            "coordination_assignment_id": {"$in": coordination_ids},
            "purpose": purpose,
            "status": status
        }},
        {"$lookup": {
            "from": "question_banks", 
            "localField": "question_id", 
            "foreignField": "_id", 
            "as": "question_details"
        }},
        {"$unwind": "$question_details"}
    ]
    return await db["question_submissions"].aggregate(pipeline).to_list(None)

async def update_submission_status(
    db: AsyncIOMotorDatabase, 
    submission_id: ObjectId, 
    status_update: SubmissionStatusUpdate
) -> dict | None:
    """Memperbarui status sebuah pengajuan soal."""
    update_data = status_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db["question_submissions"].update_one(
        {"_id": submission_id},
        {"$set": update_data}
    )
    return await db["question_submissions"].find_one({"_id": submission_id})

async def get_my_submissions(
    db: AsyncIOMotorDatabase, 
    teacher_id: ObjectId, 
    academic_period_id: ObjectId,
    purpose: str = None
) -> List[dict]:
    """Mengambil daftar submission yang dibuat oleh guru tertentu."""
    match_filter = {
        "submitted_by_teacher_id": teacher_id,
        "academic_period_id": academic_period_id
    }
    
    if purpose:
        match_filter["purpose"] = purpose
    
    pipeline = [
        {"$match": match_filter},
        {"$lookup": {
            "from": "question_banks", 
            "localField": "question_id", 
            "foreignField": "_id", 
            "as": "question_details"
        }},
        {"$unwind": "$question_details"},
        {"$lookup": {
            "from": "coordination_assignments", 
            "localField": "coordination_assignment_id", 
            "foreignField": "_id", 
            "as": "coordination_info"
        }},
        {"$unwind": "$coordination_info"},
        {"$lookup": {
            "from": "users", 
            "localField": "coordination_info.coordinator_id", 
            "foreignField": "_id", 
            "as": "coordinator_info"
        }},
        {"$unwind": "$coordinator_info"},
        {"$sort": {"created_at": -1}}
    ]
    return await db["question_submissions"].aggregate(pipeline).to_list(None)

async def get_questions_for_question_bank_creation(
    db: AsyncIOMotorDatabase, 
    coordination_ids: List[ObjectId], 
    purpose: str
) -> List[dict]:
    """
    Mengambil semua soal approved untuk membuat paket soal.
    Digunakan oleh koordinator untuk menyusun paket soal.
    """
    pipeline = [
        {"$match": {
            "coordination_assignment_id": {"$in": coordination_ids},
            "purpose": purpose,
            "status": "approved"
        }},
        {"$lookup": {
            "from": "question_banks", 
            "localField": "question_id", 
            "foreignField": "_id", 
            "as": "question_details"
        }},
        {"$unwind": "$question_details"},
        {"$lookup": {
            "from": "users", 
            "localField": "submitted_by_teacher_id", 
            "foreignField": "_id", 
            "as": "submitter_info"
        }},
        {"$unwind": "$submitter_info"},
        {"$group": {
            "_id": "$question_details._id",
            "question": {"$first": "$question_details"},
            "submitter": {"$first": "$submitter_info"},
            "submission_info": {"$first": "$$ROOT"}
        }},
        {"$sort": {"question.difficulty": 1, "question.created_at": 1}}
    ]
    return await db["question_submissions"].aggregate(pipeline).to_list(None)