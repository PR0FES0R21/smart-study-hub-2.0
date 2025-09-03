# ==============================================================================
# File: app/crud/crud_exam_sessions.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'exam_sessions'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, List
from bson import ObjectId
import logging
from datetime import datetime
from fastapi import HTTPException
from app.schemas.exam_session import AnswerUpdate, InteractionLogItem, SubmitAllPayload
from app.crud.crud_analytics import (
    STUDENT_PERFORMANCE_ROSTER_CACHE_KEY, COMPETENCY_PROFILE_CACHE_KEY
)
from app.core.cache import invalidate_cache
from app.crud.crud_analytics import generate_cache_key
from app.tasks.analytics_tasks import recompute_competency_profile_task
from app.crud.crud_score_analytics import (
    ADMIN_DASHBOARD_CACHE, TEACHER_DASHBOARD_CACHE, STUDENT_DASHBOARD_CACHE
)
from app.tasks.score_analytics_tasks import (
    precompute_admin_analytics, precompute_teacher_analytics, precompute_student_analytics
)

logger = logging.getLogger(__name__)

async def get_session_by_id(db: AsyncIOMotorDatabase, session_id: str) -> dict | None:
    if not ObjectId.is_valid(session_id): return None
    return await db["exam_sessions"].find_one({"_id": ObjectId(session_id)})

async def update_student_answer(db: AsyncIOMotorDatabase, session_id: ObjectId, answer_update: AnswerUpdate) -> bool:
    """Menyimpan atau memperbarui jawaban siswa dalam sesi."""
    # Gunakan dot notation untuk update field di dalam sub-dokumen/dictionary
    update_result = await db["exam_sessions"].update_one(
        {"_id": session_id},
        {"$set": {f"answers.{str(answer_update.question_id)}": answer_update.student_answer}}
    )
    return update_result.modified_count > 0

async def log_student_interaction(db: AsyncIOMotorDatabase, session_id: ObjectId, log_item: InteractionLogItem) -> bool:
    """Menambahkan log interaksi ke dalam sesi ujian."""
    log_dict = log_item.model_dump(mode='python')
    update_result = await db["exam_sessions"].update_one(
        {"_id": session_id},
        {"$push": {"interaction_logs": log_dict}}
    )
    return update_result.modified_count > 0

async def get_shuffled_questions_for_session(db: AsyncIOMotorDatabase, session: dict, exam: dict) -> List[dict]:
    """
    Mengambil soal sesuai peta acak di sesi (KONSISTEN dengan yang sudah di-save).
    PERBAIKAN: Menggunakan shuffled_option_ids yang sudah di-save, bukan shuffle ulang.
    """
    question_map = session.get("question_map", [])
    question_ids = [item["question_id"] for item in question_map]

    # Fetch questions dari database
    questions_cursor = db["question_banks"].find({"_id": {"$in": question_ids}})
    questions_from_db = {q["_id"]: q for q in await questions_cursor.to_list(len(question_ids))}

    shuffled_questions = []
    for map_item in question_map:
        q_id = map_item["question_id"]
        if q_id not in questions_from_db:
            logger.warning(f"Question {q_id} not found in database")
            continue
            
        question_data = questions_from_db[q_id]
        original_options = question_data.get("options", [])
        
        # Gunakan urutan shuffle yang sudah di-save (KONSISTEN!)
        if map_item.get("shuffled_option_ids") and original_options:
            shuffled_option_ids = map_item["shuffled_option_ids"]
            # Buat mapping dari ID ke option
            options_by_id = {opt["id"]: opt for opt in original_options}
            # Susun ulang sesuai urutan yang sudah di-shuffle
            ordered_options = []
            for opt_id in shuffled_option_ids:
                if opt_id in options_by_id:
                    ordered_options.append(options_by_id[opt_id])
            options = ordered_options
            logger.debug(f"Using shuffled options for question {q_id}")
        else:
            # Tidak ada shuffle atau tidak ada options
            options = original_options
            logger.debug(f"Using original options for question {q_id}")

        # Hapus kunci jawaban sebelum mengirim ke siswa
        options_for_student = [{"id": opt["id"], "text": opt["text"]} for opt in options]

        shuffled_questions.append({
            "id": question_data["_id"],
            "position": map_item["position"],
            "question_text": question_data["question_text"],
            "question_type": question_data["question_type"],
            "points": question_data["points"],
            "options": options_for_student
        })
    
    # Sort berdasarkan position untuk memastikan urutan yang benar
    shuffled_questions.sort(key=lambda x: x["position"])
    
    logger.info(f"Retrieved {len(shuffled_questions)} questions for session {session['_id']} with proper shuffle mapping")
    return shuffled_questions


# --- DITAMBAHKAN ---
async def submit_and_grade_session(db: AsyncIOMotorDatabase, session: dict, exam: dict) -> dict:
    """Menyelesaikan sesi, menilai, dan menyimpan skor."""
    student_answers = session.get("answers", {})
    question_ids = [ObjectId(qid) for qid in student_answers.keys()]
    
    questions_cursor = db["question_banks"].find({"_id": {"$in": question_ids}})
    correct_answers_map = {q["_id"]: q for q in await questions_cursor.to_list(len(question_ids))}

    total_score = 0
    total_max_points = 0

    for q_id_str, student_answer in student_answers.items():
        q_id = ObjectId(q_id_str)
        if q_id in correct_answers_map:
            question = correct_answers_map[q_id]
            total_max_points += question.get("points", 0)
            
            if question["question_type"] == "multiple_choice":
                correct_option_id = next((opt["id"] for opt in question["options"] if opt["is_correct"]), None)
                if str(correct_option_id) == student_answer:
                    total_score += question.get("points", 0)

    # Hitung skor akhir (skala 0-100)
    final_score = (total_score / total_max_points) * 100 if total_max_points > 0 else 0
    
    update_data = {
        "status": "graded",
        "submitted_at": datetime.utcnow(),
        "score": final_score
    }
    
    await db["exam_sessions"].update_one({"_id": session["_id"]}, {"$set": update_data})

    await invalidate_cache(STUDENT_PERFORMANCE_ROSTER_CACHE_KEY)
    await invalidate_cache(COMPETENCY_PROFILE_CACHE_KEY)

    student_profile = await db["profiles"].find_one({"user_id": session["student_id"]})
    student_class = await db["classes"].find_one({"_id": student_profile["class_id"]})

    # Hapus cache global
    await invalidate_cache(generate_cache_key({}))
    recompute_competency_profile_task.delay({})

    await invalidate_cache(generate_cache_key({"grade_level": student_class["grade_level"]}))
    recompute_competency_profile_task.delay({"grade_level": student_class["grade_level"]})
    
    # --- Invalidasi cache Score Analytics yang relevan ---
    try:
        academic_period_id = str(exam.get("academic_period_id")) if exam.get("academic_period_id") else None
        if academic_period_id:
            await invalidate_cache(ADMIN_DASHBOARD_CACHE.format(period=academic_period_id))
        assignment = await db["teaching_assignments"].find_one({"_id": exam.get("teaching_assignment_id")}) if exam.get("teaching_assignment_id") else None
        if assignment and assignment.get("teacher_id") and academic_period_id:
            await invalidate_cache(TEACHER_DASHBOARD_CACHE.format(teacher=str(assignment["teacher_id"]), period=academic_period_id))
        if academic_period_id:
            await invalidate_cache(STUDENT_DASHBOARD_CACHE.format(student=str(session["student_id"]), period=academic_period_id))
        
        # Optional precompute to warm caches
        if academic_period_id:
            precompute_admin_analytics.delay(academic_period_id)
            if assignment and assignment.get("teacher_id"):
                precompute_teacher_analytics.delay(str(assignment["teacher_id"]), academic_period_id)
            precompute_student_analytics.delay(str(session["student_id"]), academic_period_id)
    except Exception as e:
        logger.warning(f"Score analytics cache invalidation/precompute failed: {e}")
    
    return await get_session_by_id(db, str(session["_id"]))

async def submit_and_grade_session_v2(
    db: AsyncIOMotorDatabase, 
    session: dict, 
    exam: dict, 
    payload: SubmitAllPayload
) -> dict:

    """
    Enhanced submit dengan validation, logging lengkap, dan fraud detection.
    PERBAIKAN: Tambah validasi ketat untuk memastikan semua soal terjawab.
    """
    
    # === VALIDASI 1: Cek apakah semua soal terjawab ===
    student_answers = payload.answers
    question_map = session.get("question_map", [])
    total_questions = len(question_map)
    
    # Hitung soal yang terjawab (tidak None dan tidak string kosong)
    answered_questions = 0
    unanswered_questions = []
    
    for map_item in question_map:
        question_id_str = str(map_item["question_id"])
        student_answer = student_answers.get(question_id_str)
        
        # Cek apakah soal terjawab (tidak None, tidak string kosong, tidak list kosong)
        if student_answer is not None and student_answer != "" and student_answer != []:
            answered_questions += 1
        else:
            unanswered_questions.append(map_item["position"])
    
    # Validasi: Semua soal harus terjawab
    if answered_questions < total_questions:
        raise HTTPException(
            status_code=400,
            detail=f"Tidak dapat submit ujian. Anda belum menjawab {total_questions - answered_questions} soal. "
                   f"Soal yang belum terjawab: {', '.join(map(str, unanswered_questions))}"
        )
    
    # === VALIDASI 2: Cek apakah ada soal yang tidak valid ===
    question_ids = [ObjectId(qid) for qid in student_answers.keys() if student_answers[qid] is not None]
    
    questions_cursor = db["question_banks"].find({"_id": {"$in": question_ids}})
    correct_answers_map = {q["_id"]: q for q in await questions_cursor.to_list(len(question_ids))}
    
    # Validasi: Semua question_id harus valid
    if len(correct_answers_map) != len(question_ids):
        raise HTTPException(
            status_code=400,
            detail="Data jawaban tidak valid. Beberapa soal tidak ditemukan dalam database."
        )

    # === VALIDASI 3: Cek apakah session masih ongoing ===
    if session.get("status") != "ongoing":
        raise HTTPException(
            status_code=400,
            detail="Tidak dapat submit ujian. Sesi ujian sudah tidak aktif."
        )

    # === VALIDASI 4: Cek waktu ujian ===
    now = datetime.utcnow()
    if now > exam["availability_end_time"]:
        raise HTTPException(
            status_code=400,
            detail="Tidak dapat submit ujian. Waktu ujian telah berakhir."
        )

    # 2. Grading logic (sama seperti versi lama)
    total_score = 0
    total_max_points = 0

    for q_id_str, student_answer in student_answers.items():
        if student_answer is None or student_answer == "" or student_answer == []:
            continue  # Skip unanswered questions (seharusnya sudah divalidasi di atas)
            
        q_id = ObjectId(q_id_str)
        if q_id in correct_answers_map:
            question = correct_answers_map[q_id]
            total_max_points += question.get("points", 0)
            
            if question["question_type"] == "multiple_choice":
                correct_option_id = next((opt["id"] for opt in question["options"] if opt["is_correct"]), None)
                if str(correct_option_id) == str(student_answer):
                    total_score += question.get("points", 0)

    # 3. Calculate final score
    final_score = (total_score / total_max_points) * 100 if total_max_points > 0 else 0
    
    # 4. Process violations and calculate fraud score
    violations_data = [violation.model_dump(mode='python') for violation in payload.violations]
    fraud_score = _calculate_fraud_score(violations_data)
    is_flagged = fraud_score > 0.7  # Flag if fraud score > 70%
    
    # 5. Prepare interaction logs
    interaction_logs = [log.model_dump(mode='python') for log in payload.interaction_logs]
    
    # 6. Update session dengan data lengkap
    update_data = {
        "status": "graded",
        "submitted_at": datetime.utcnow(),
        "score": final_score,
        "answers": student_answers,  # Save semua answers sekaligus
        "interaction_logs": interaction_logs,  # Save semua logs sekaligus
        "violations": violations_data,  # Save violations untuk audit
        "fraud_score": fraud_score,  # Auto-calculated fraud score
        "is_flagged_for_review": is_flagged,  # Auto-flag suspicious sessions
        "client_metadata": payload.client_metadata,
        "completion_stats": {
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "completion_percentage": (answered_questions / total_questions) * 100 if total_questions > 0 else 0
        }
    }
    
    await db["exam_sessions"].update_one({"_id": session["_id"]}, {"$set": update_data})

    # 7. Log critical violations for immediate attention
    if is_flagged:
        logger.warning(f"Session {session['_id']} flagged for review - Fraud score: {fraud_score:.2f}")

    # 8. Invalidate cache (sama seperti versi lama)
    await invalidate_cache(STUDENT_PERFORMANCE_ROSTER_CACHE_KEY)
    await invalidate_cache(COMPETENCY_PROFILE_CACHE_KEY)

    student_profile = await db["profiles"].find_one({"user_id": session["student_id"]})
    student_class = await db["classes"].find_one({"_id": student_profile["class_id"]})

    await invalidate_cache(generate_cache_key({}))
    recompute_competency_profile_task.delay({})

    await invalidate_cache(generate_cache_key({"grade_level": student_class["grade_level"]}))
    recompute_competency_profile_task.delay({"grade_level": student_class["grade_level"]})
    
    # --- Invalidasi cache Score Analytics yang relevan ---
    try:
        academic_period_id = str(exam.get("academic_period_id")) if exam.get("academic_period_id") else None
        if academic_period_id:
            await invalidate_cache(ADMIN_DASHBOARD_CACHE.format(period=academic_period_id))
        assignment = await db["teaching_assignments"].find_one({"_id": exam.get("teaching_assignment_id")}) if exam.get("teaching_assignment_id") else None
        if assignment and assignment.get("teacher_id") and academic_period_id:
            await invalidate_cache(TEACHER_DASHBOARD_CACHE.format(teacher=str(assignment["teacher_id"]), period=academic_period_id))
        if academic_period_id:
            await invalidate_cache(STUDENT_DASHBOARD_CACHE.format(student=str(session["student_id"]), period=academic_period_id))

        # Optional precompute to warm caches
        if academic_period_id:
            precompute_admin_analytics.delay(academic_period_id)
            if assignment and assignment.get("teacher_id"):
                precompute_teacher_analytics.delay(str(assignment["teacher_id"]), academic_period_id)
            precompute_student_analytics.delay(str(session["student_id"]), academic_period_id)
    except Exception as e:
        logger.warning(f"Score analytics cache invalidation/precompute failed: {e}")
    
    return await get_session_by_id(db, str(session["_id"]))

def _calculate_fraud_score(violations: List[dict]) -> float:
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

