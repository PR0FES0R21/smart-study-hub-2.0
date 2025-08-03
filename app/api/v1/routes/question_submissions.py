# ==============================================================================
# File: app/api/v1/routes/question_submissions.py
# Deskripsi: Endpoint untuk alur kerja review oleh koordinator.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_submissions, crud_coordination_assignments
from app.schemas.question_submission import SubmissionStatusUpdate, QuestionSubmissionPublic

router = APIRouter()

@router.get("/for-review", response_model=List[QuestionSubmissionPublic])
async def get_submissions_for_review(
    academic_period_id: Optional[str] = Query(None, description="ID periode akademik, kosongkan untuk periode aktif"),
    search: Optional[str] = Query(None, description="Pencarian berdasarkan teks soal atau tag"),
    purpose: Optional[str] = Query(None, description="Filter berdasarkan tujuan ujian"),
    question_type: Optional[str] = Query(None, description="Filter berdasarkan tipe soal: multiple_choice, essay"),
    difficulty: Optional[str] = Query(None, description="Filter berdasarkan tingkat kesulitan: easy, medium, hard"),
    status: Optional[str] = Query(None, description="Filter berdasarkan status: submitted, approved, rejected"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Koordinator mengambil daftar soal yang diajukan dengan berbagai filter.
    Mengembalikan data lengkap termasuk detail soal.
    """
    # Cari semua kontrak koordinasi milik user ini
    coordination_contracts = await crud_coordination_assignments.get_coordinations_by_user(db, current_user["_id"])
    if not coordination_contracts:
        raise HTTPException(status_code=403, detail="You are not a coordinator.")
    
    coordination_ids = [c["_id"] for c in coordination_contracts]
    
    # Tentukan periode akademik yang akan digunakan
    if academic_period_id:
        if not ObjectId.is_valid(academic_period_id):
            raise HTTPException(status_code=400, detail="Invalid academic period ID.")
        period_id = ObjectId(academic_period_id)
    else:
        period_id = ObjectId(current_period["_id"])
    
    # Ambil submissions dengan filter
    submissions = await crud_question_submissions.get_submissions_for_coordinator(
        db=db,
        coordination_ids=coordination_ids,
        academic_period_id=period_id,
        search=search,
        purpose=purpose,
        question_type=question_type,
        difficulty=difficulty,
        status=status
    )
    
    return submissions

@router.get("/my-submissions", response_model=List[QuestionSubmissionPublic])
async def get_my_submissions(
    academic_period_id: Optional[str] = Query(None, description="ID periode akademik, kosongkan untuk periode aktif"),
    search: Optional[str] = Query(None, description="Pencarian berdasarkan teks soal atau tag"),
    purpose: Optional[str] = Query(None, description="Filter berdasarkan tujuan ujian"),
    question_type: Optional[str] = Query(None, description="Filter berdasarkan tipe soal: multiple_choice, essay"),
    difficulty: Optional[str] = Query(None, description="Filter berdasarkan tingkat kesulitan: easy, medium, hard"),
    status: Optional[str] = Query(None, description="Filter berdasarkan status: submitted, approved, rejected"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    current_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Guru mengambil daftar soal yang telah mereka submit ke koordinator.
    Bisa difilter berdasarkan berbagai kriteria.
    """
    # Tentukan periode akademik yang akan digunakan
    if academic_period_id:
        if not ObjectId.is_valid(academic_period_id):
            raise HTTPException(status_code=400, detail="Invalid academic period ID.")
        period_id = ObjectId(academic_period_id)
    else:
        period_id = ObjectId(current_period["_id"])
    
    # Ambil submissions milik guru ini
    submissions = await crud_question_submissions.get_submissions_by_teacher(
        db=db,
        teacher_id=current_user["_id"],
        academic_period_id=period_id,
        search=search,
        purpose=purpose,
        question_type=question_type,
        difficulty=difficulty,
        status=status
    )
    
    return submissions

@router.put("/{submission_id}/status", response_model=QuestionSubmissionPublic)
async def update_submission_status(
    submission_id: str,
    status_in: SubmissionStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """
    Koordinator menyetujui atau menolak sebuah pengajuan soal.
    Hanya koordinator yang berwenang yang bisa mengubah status.
    """
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=400, detail="Invalid submission ID.")
    
    submission_obj_id = ObjectId(submission_id)
    
    # Cek apakah submission ini ada
    submission = await db["question_submissions"].find_one({"_id": submission_obj_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    
    # Cek apakah current user adalah koordinator yang berwenang
    coordination_assignment = await db["coordination_assignments"].find_one({
        "_id": submission["coordination_assignment_id"]
    })
    if not coordination_assignment or coordination_assignment["coordinator_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=403, 
            detail="You are not authorized to review this submission."
        )
    
    # Update status
    updated_submission = await crud_question_submissions.update_submission_status(
        db, submission_obj_id, status_in
    )
    
    if not updated_submission:
        raise HTTPException(status_code=500, detail="Failed to update submission status.")
    
    return updated_submission