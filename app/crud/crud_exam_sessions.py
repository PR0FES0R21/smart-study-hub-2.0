# ==============================================================================
# File: app/crud/crud_exam_sessions.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'exam_sessions'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, List
from bson import ObjectId
import random
from datetime import datetime
from app.schemas.exam_session import AnswerUpdate, InteractionLogItem
from app.crud.crud_analytics import (
    STUDENT_PERFORMANCE_ROSTER_CACHE_KEY, COMPETENCY_PROFILE_CACHE_KEY
)
from app.core.cache import invalidate_cache
from app.crud.crud_analytics import generate_cache_key
from app.tasks.analytics_tasks import recompute_competency_profile_task

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
    """Mengambil soal sesuai peta acak di sesi dan mengacak opsi jika perlu."""
    question_map = session.get("question_map", [])
    question_ids = [item["question_id"] for item in question_map]

    questions_cursor = db["question_banks"].find({"_id": {"$in": question_ids}})
    questions_from_db = {q["_id"]: q for q in await questions_cursor.to_list(len(question_ids))}

    shuffled_questions = []
    for map_item in question_map:
        q_id = map_item["question_id"]
        if q_id in questions_from_db:
            question_data = questions_from_db[q_id]
            options = question_data.get("options", [])
            
            if exam.get("settings", {}).get("shuffle_options", False) and options:
                random.shuffle(options)

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
    

    return await get_session_by_id(db, str(session["_id"]))