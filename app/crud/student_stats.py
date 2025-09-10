# ==============================================================================
# File: app/crud/student_stats.py
# Deskripsi: CRUD untuk menghitung statistik ujian siswa dari exam_sessions
# ==============================================================================

from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.student_stats import StudentStatsResponse

async def get_student_exam_stats(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> StudentStatsResponse:
    """
    Hitung statistik ujian siswa dari collection exam_sessions.
    - Hanya menghitung sesi dengan status 'graded' dan score != null
    - Optional filter tanggal berdasarkan submitted_at
    """
    match_stage: Dict[str, Any] = {
        "student_id": ObjectId(student_id),
        "status": "graded",
        "score": {"$ne": None}
    }

    if start_date or end_date:
        date_filter: Dict[str, Any] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        match_stage["submitted_at"] = date_filter

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": None,
                "total_exams": {"$sum": 1},
                "average_score": {"$avg": "$score"},
                "highest_score": {"$max": "$score"},
                "lowest_score": {"$min": "$score"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "total_exams": 1,
                # Pembulatan 2 desimal
                "average_score": {"$round": ["$average_score", 2]},
                "highest_score": {"$round": ["$highest_score", 2]},
                "lowest_score": {"$round": ["$lowest_score", 2]},
            }
        }
    ]

    results = await db.exam_sessions.aggregate(pipeline).to_list(length=1)

    # Jika tidak ada data, kembalikan default 0
    if not results:
        return StudentStatsResponse(
            student_id=ObjectId(student_id),
            total_exams=0,
            average_score=0.0,
            highest_score=0.0,
            lowest_score=0.0,
            filters={
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }
        )

    doc = results[0]
    return StudentStatsResponse(
        student_id=ObjectId(student_id),
        total_exams=doc.get("total_exams", 0),
        average_score=float(doc.get("average_score", 0.0)),
        highest_score=float(doc.get("highest_score", 0.0)),
        lowest_score=float(doc.get("lowest_score", 0.0)),
        filters={
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }
    )

