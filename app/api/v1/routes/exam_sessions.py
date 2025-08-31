# ==============================================================================
# File: app/api/v1/routes/exam_sessions.py
# Deskripsi: Endpoint API untuk interaksi selama sesi ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.api.v1 import deps
from app.crud import crud_exam_sessions, crud_exams
from app.schemas.exam_session import (
    AnswerUpdate, QuestionForStudent, ExamSessionPublic, 
    SubmitAllPayload
)

router = APIRouter()

@router.put("/{session_id}/answer", status_code=status.HTTP_204_NO_CONTENT)
async def save_answer(
    session_id: str,
    answer_in: AnswerUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Endpoint untuk autosave jawaban siswa.
    """
    session = await crud_exam_sessions.get_session_by_id(db, session_id)
    if not session or session["student_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Exam session not found or not owned by user")
    
    if session["status"] != "ongoing":
        raise HTTPException(status_code=400, detail="Exam session is not ongoing")
        
    await crud_exam_sessions.update_student_answer(db, session_id=session["_id"], answer_update=answer_in)
    
    # (Di sini kita juga bisa menambahkan logika untuk log interaksi)
    
    return

@router.get("/{session_id}/questions", response_model=List[QuestionForStudent])
async def get_exam_questions_for_student(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """Mengambil daftar soal yang sudah diacak untuk sesi ujian siswa."""
    session = await crud_exam_sessions.get_session_by_id(db, session_id)
    if not session or session["student_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Exam session not found or not owned by user")
    
    exam = await crud_exams.get_exam_by_id(db, str(session["exam_id"]))
    if not exam:
        raise HTTPException(status_code=404, detail="Associated exam not found")
        
    return await crud_exam_sessions.get_shuffled_questions_for_session(db, session, exam)

# --- DITAMBAHKAN ---
@router.post("/{session_id}/submit", response_model=ExamSessionPublic)
async def submit_exam(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """Menyelesaikan ujian, memicu penilaian, dan mengembalikan hasil sesi."""
    session = await crud_exam_sessions.get_session_by_id(db, session_id)
    if not session or session["student_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Exam session not found or not owned by user")
    
    if session["status"] != "ongoing":
        raise HTTPException(status_code=400, detail="Exam has already been submitted")

    exam = await crud_exams.get_exam_by_id(db, str(session["exam_id"]))
    if not exam:
        raise HTTPException(status_code=404, detail="Associated exam not found")

    return await crud_exam_sessions.submit_and_grade_session(db, session, exam)

# --- DITAMBAHKAN ---
@router.get("/{session_id}/result", response_model=ExamSessionPublic)
async def get_session_result(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """Mengambil hasil sesi ujian setelah selesai."""
    session = await crud_exam_sessions.get_session_by_id(db, session_id)
    if not session or session["student_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Exam session not found or not owned by user")
    
    exam = await crud_exams.get_exam_by_id(db, str(session["exam_id"]))
    if not exam:
        raise HTTPException(status_code=404, detail="Associated exam not found")

    if session["status"] != "graded":
        raise HTTPException(status_code=400, detail="Exam is not graded yet")
    
    if not exam.get("settings", {}).get("show_results_after_submission", False):
        raise HTTPException(status_code=403, detail="Results are not available for this exam")

    return session

def calculate_fraud_score(violations: List[dict]) -> float:
    """
    Calculate fraud score based on violations (0.0 - 1.0).
    Higher score = more suspicious.
    """
    if not violations:
        return 0.0
    
    severity_weights = {
        "low": 0.1,
        "medium": 0.3, 
        "high": 0.6,
        "critical": 1.0
    }
    
    total_weight = sum(severity_weights.get(v.get("severity", "medium"), 0.3) for v in violations)
    violation_count_penalty = min(len(violations) * 0.05, 0.3)  # Cap at 0.3
    
    return min(total_weight + violation_count_penalty, 1.0)

@router.post("/{session_id}/submit-all", response_model=ExamSessionPublic)
async def submit_exam_with_full_data(
    session_id: str,
    payload: SubmitAllPayload,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Submit ujian dengan data lengkap: answers + interaction logs + violations + metadata.
    Endpoint baru untuk approach 'submit all' dengan fraud detection.
    """
    session = await crud_exam_sessions.get_session_by_id(db, session_id)
    if not session or session["student_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Exam session not found or not owned by user")
    
    if session["status"] != "ongoing":
        raise HTTPException(status_code=400, detail="Exam has already been submitted")

    exam = await crud_exams.get_exam_by_id(db, str(session["exam_id"]))
    if not exam:
        raise HTTPException(status_code=404, detail="Associated exam not found")

    # Process submission dengan data lengkap + fraud detection
    return await crud_exam_sessions.submit_and_grade_session_v2(db, session, exam, payload)

