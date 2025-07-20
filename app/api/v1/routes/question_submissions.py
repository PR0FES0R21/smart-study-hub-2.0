# ==============================================================================
# File: app/api/v1/routes/question_submissions.py
# Deskripsi: Endpoint untuk alur kerja review oleh koordinator.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_submissions, crud_coordination_assignments
from app.schemas.question_submission import SubmissionStatusUpdate, QuestionSubmissionPublic

router = APIRouter()

@router.get("/for-review", response_model=List[QuestionSubmissionPublic])
async def get_submissions(
    purpose: str = Query(..., description="Tujuan ujian, cth: 'UTS Ganjil 2025'"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Koordinator mengambil daftar soal yang diajukan untuk tujuan tertentu.
    """
    # Cari semua kontrak koordinasi milik user ini
    coordination_contracts = await crud_coordination_assignments.get_coordinations_by_user(db, current_user["_id"])
    if not coordination_contracts:
        raise HTTPException(status_code=403, detail="You are not a coordinator.")
    
    coordination_ids = [c["_id"] for c in coordination_contracts]
    
    # Ambil semua pengajuan yang statusnya 'submitted'
    return await crud_question_submissions.get_submissions_for_coordinator(
        db, coordination_ids, purpose, "submitted"
    )

@router.put("/{submission_id}/status", response_model=QuestionSubmissionPublic)
async def update_submission(
    submission_id: str,
    status_in: SubmissionStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """Koordinator menyetujui atau menolak sebuah pengajuan soal."""
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=400, detail="Invalid submission ID.")
    
    # (Di sini perlu ditambahkan validasi untuk memastikan hanya koordinator yang berwenang yang bisa mengubah status)
    
    return await crud_question_submissions.update_submission_status(db, ObjectId(submission_id), status_in)
