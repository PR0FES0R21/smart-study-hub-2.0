# ==============================================================================
# File: app/crud/crud_exams.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'exams'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.schemas.exam import ExamCreate
import random
from datetime import datetime
import logging

from app.schemas.exam import ExamCreate, ExamQuestionUpdate, ExamUpdate
from app.schemas.exam_session import ExamSessionBase, QuestionMapItem

logger = logging.getLogger(__name__)

async def get_exam_by_id(db: AsyncIOMotorDatabase, exam_id: str) -> dict | None:
    """Mengambil satu dokumen ujian berdasarkan ID."""
    if not ObjectId.is_valid(exam_id): return None
    return await db["exams"].find_one({"_id": ObjectId(exam_id)})

async def create_exam(db: AsyncIOMotorDatabase, exam: ExamCreate) -> dict:
    exam_dict = exam.model_dump(mode='python')
    result = await db["exams"].insert_one(exam_dict)
    created_exam = await db["exams"].find_one({"_id": result.inserted_id})
    return created_exam

async def start_exam_session(db: AsyncIOMotorDatabase, exam: dict, student_id: ObjectId) -> dict:
    """
    Membuat sesi ujian baru untuk siswa, lengkap dengan peta acak.
    PERBAIKAN: Tambah validasi komprehensif + proper shuffle implementation
    """
    
    # === VALIDASI 1: Waktu Pelaksanaan Ujian ===
    now = datetime.utcnow()
    if now < exam["availability_start_time"]:
        raise HTTPException(
            status_code=400, 
            detail="Ujian belum dimulai. Silakan tunggu waktu yang telah ditentukan."
        )
    if now > exam["availability_end_time"]:
        raise HTTPException(
            status_code=400, 
            detail="Waktu ujian telah berakhir. Anda tidak dapat lagi mengerjakan ujian ini."
        )
    
    # === VALIDASI 2: Status Ujian ===
    if exam["status"] != "ongoing":
        if exam["status"] == "pending_questions":
            raise HTTPException(status_code=400, detail="Ujian belum siap. Soal belum ditambahkan.")
        elif exam["status"] == "ready":
            raise HTTPException(status_code=400, detail="Ujian belum dimulai oleh pengawas.")
        elif exam["status"] == "completed":
            raise HTTPException(status_code=400, detail="Ujian telah selesai.")
        else:
            raise HTTPException(status_code=400, detail="Status ujian tidak valid untuk dikerjakan.")
    
    # === VALIDASI 3: Profil Siswa ===
    student_profile = await db["profiles"].find_one({"user_id": student_id})
    if not student_profile:
        raise HTTPException(
            status_code=404, 
            detail="Profil siswa tidak ditemukan. Silakan hubungi administrator."
        )
    
    if not student_profile.get("class_id"):
        raise HTTPException(
            status_code=400, 
            detail="Siswa belum terdaftar di kelas manapun. Silakan hubungi administrator."
        )
    
    # === VALIDASI 4: Kesesuaian Kelas ===
    assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
    if not assignment:
        raise HTTPException(status_code=404, detail="Penugasan mengajar tidak ditemukan.")
    
    if assignment["class_id"] != student_profile["class_id"]:
        raise HTTPException(
            status_code=403, 
            detail="Anda tidak memiliki akses ke ujian ini. Ujian ini diperuntukkan untuk kelas lain."
        )
    
    # === VALIDASI 5: Periode Akademik ===
    if exam.get("academic_period_id") != assignment.get("academic_period_id"):
        raise HTTPException(
            status_code=400, 
            detail="Ujian tidak sesuai dengan periode akademik aktif."
        )
    
    # === VALIDASI 6: Cek Existing Session ===
    existing_session = await db["exam_sessions"].find_one({
        "exam_id": exam["_id"],
        "student_id": student_id,
        "status": {"$in": ["ongoing", "submitted", "graded"]}
    })
    
    if existing_session:
        if existing_session["status"] in ["submitted", "graded"]:
            raise HTTPException(
                status_code=400, 
                detail="Anda sudah mengerjakan ujian ini sebelumnya."
            )
        # Jika status ongoing, kembalikan session yang sudah ada
        return existing_session
    
    # === VALIDASI 7: Cek Soal Tersedia ===
    question_ids = exam.get("question_ids", [])
    if not question_ids:
        raise HTTPException(
            status_code=400, 
            detail="Ujian belum memiliki soal. Silakan hubungi guru pengampu."
        )
    
    # Validasi apakah semua soal masih ada di databasee
    question_count = await db["question_banks"].count_documents({"_id": {"$in": question_ids}})
    if question_count != len(question_ids):
        logger.warning(f"Some questions missing for exam {exam['_id']}, expected {len(question_ids)}, found {question_count}")
        raise HTTPException(
            status_code=500, 
            detail="Beberapa soal ujian tidak tersedia. Silakan hubungi administrator."
        )
    
    # === MEMBUAT SESSION DENGAN PROPER SHUFFLE ===
    exam_settings = exam.get("settings", {})
    shuffle_questions = exam_settings.get("shuffle_questions", False)
    shuffle_options = exam_settings.get("shuffle_options", False)
    
    # 1. Shuffle questions jika diaktifkan
    working_question_ids = question_ids.copy()  # Copy to avoid modifying original
    if shuffle_questions:
        random.shuffle(working_question_ids)
    
    # 2. Fetch questions dan siapkan shuffle options
    questions_cursor = db["question_banks"].find({"_id": {"$in": working_question_ids}})
    questions_data = {q["_id"]: q for q in await questions_cursor.to_list(len(working_question_ids))}
    
    # 3. Build question map dengan shuffled options
    question_map = []
    for i, q_id in enumerate(working_question_ids):
        if q_id not in questions_data:
            logger.error(f"Question {q_id} not found in database")
            continue
            
        question = questions_data[q_id]
        shuffled_option_ids = None
        
        # Shuffle options jika diaktifkan dan ada options
        if shuffle_options and question.get("options"):
            original_options = question["options"]
            # Buat list ID options dalam urutan asli
            original_option_ids = [opt["id"] for opt in original_options]
            # Shuffle urutan ID-nya
            shuffled_option_ids = original_option_ids.copy()
            random.shuffle(shuffled_option_ids)
        
        question_map_item = QuestionMapItem(
            position=i + 1,
            question_id=q_id,
            shuffled_option_ids=shuffled_option_ids
        )
        question_map.append(question_map_item)
    
    # 4. Create session
    session_data = ExamSessionBase(
        exam_id=exam["_id"],
        student_id=student_id,
        question_map=question_map
    )
    
    session_dict = session_data.model_dump(mode='python')
    result = await db["exam_sessions"].insert_one(session_dict)
    created_session = await db["exam_sessions"].find_one({"_id": result.inserted_id})
    
    logger.info(f"New exam session created: {result.inserted_id} for student {student_id} with shuffle_questions={shuffle_questions}, shuffle_options={shuffle_options}")
    return created_session


async def add_questions_to_exam(db: AsyncIOMotorDatabase, exam_id: ObjectId, questions_update: ExamQuestionUpdate) -> dict | None:
    """Menambahkan atau memperbarui daftar soal dalam sebuah ujian."""
    update_data = {
        "question_ids": questions_update.question_ids,
        "status": "ready" # Ubah status menjadi siap dikerjakan
    }
    await db["exams"].update_one({"_id": exam_id}, {"$set": update_data})
    return await db["exams"].find_one({"_id": exam_id})

async def get_all_exams_with_details(
    db: AsyncIOMotorDatabase, 
    filters: Dict[str, Any],
    skip: int,
    limit: int,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mengambil semua ujian dengan detail lengkap, mendukung filter, paginasi, dan pencarian.
    Versi ini sudah diperbaiki untuk menangani kasus di mana data kelas (class) tidak ditemukan.
    """
    pipeline = []
    
    initial_match = {"exam_type": {"$ne": None}}  # PERBAIKAN: Selalu filter out exam_type null
    if "academic_period_id" in filters:
        initial_match["academic_period_id"] = filters["academic_period_id"]
    if "exam_type" in filters:
        initial_match["exam_type"] = filters["exam_type"]
    
    pipeline.append({"$match": initial_match})

    # Pipeline lookup yang sudah diperbaiki
    lookup_pipeline = [
        {"$lookup": {"from": "academic_periods", "localField": "academic_period_id", "foreignField": "_id", "as": "academic_period_details"}},
        {"$unwind": {"path": "$academic_period_details", "preserveNullAndEmptyArrays": True}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment_details"}},
        {"$unwind": {"path": "$teaching_assignment_details", "preserveNullAndEmptyArrays": True}},
        
        {"$lookup": {"from": "subjects", "localField": "teaching_assignment_details.subject_id", "foreignField": "_id", "as": "teaching_assignment_details.subject_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.subject_details", "preserveNullAndEmptyArrays": True}},
        
        {"$lookup": {"from": "classes", "localField": "teaching_assignment_details.class_id", "foreignField": "_id", "as": "teaching_assignment_details.class_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.class_details", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {"from": "expertise_programs", "localField": "teaching_assignment_details.class_details.expertise_id", "foreignField": "_id", "as": "teaching_assignment_details.class_details.expertise_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.class_details.expertise_details", "preserveNullAndEmptyArrays": True}},

        # ⭐ PERBAIKAN UTAMA: Membersihkan class_details jika data aslinya tidak ada
        {
            "$addFields": {
                "teaching_assignment_details.class_details": {
                    "$cond": {
                        # Cek keberadaan _id sebagai indikator validitas data kelas
                        "if": "$teaching_assignment_details.class_details._id",
                        # Jika ada, pertahankan objek class_details yang sudah digabung
                        "then": "$teaching_assignment_details.class_details",
                        # Jika tidak ada, ganti seluruh objek menjadi null
                        "else": None 
                    }
                }
            }
        },
        
        {"$lookup": {"from": "users", "localField": "teaching_assignment_details.teacher_id", "foreignField": "_id", "as": "teaching_assignment_details.teacher_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.teacher_details", "preserveNullAndEmptyArrays": True}},
        
        {"$project": {"teaching_assignment_details.teacher_details.hashed_password": 0}},
    ]
    pipeline.extend(lookup_pipeline)
    
    # Filter kedua berdasarkan data yang sudah di-join
    if "teacher_id" in filters:
        pipeline.append({"$match": {"teaching_assignment_details.teacher_id": filters["teacher_id"]}})
        
    # Filter pencarian
    if search:
        pipeline.append({"$match": {
            "$or": [
                {"title": {"$regex": search, "$options": "i"}},
                {"teaching_assignment_details.subject_details.name": {"$regex": search, "$options": "i"}},
                {"teaching_assignment_details.teacher_details.full_name": {"$regex": search, "$options": "i"}},
            ]
        }})

    # Menggunakan $facet untuk mendapatkan data dan total count dalam satu query
    facet_stage = {
        "$facet": {
            "data": [
                {"$sort": {"availability_start_time": -1}},
                {"$skip": skip},
                {"$limit": limit}
            ],
            "total_count": [
                {"$count": "count"}
            ]
        }
    }
    pipeline.append(facet_stage)
    
    result = await db["exams"].aggregate(pipeline).to_list(1)
    
    data = result[0]['data'] if result and result[0]['data'] else []
    total_items = result[0]['total_count'][0]['count'] if result and result[0]['total_count'] else 0
    
    return {"data": data, "total_items": total_items}

async def update_exam(db: AsyncIOMotorDatabase, exam_id: str, exam_update: ExamUpdate) -> dict | None:
    """Memperbarui detail ujian."""
    if not ObjectId.is_valid(exam_id): return None
    
    update_data = exam_update.model_dump(mode='python', exclude_unset=True)
    if not update_data:
        return await get_exam_by_id(db, exam_id)

    # PERBAIKAN: Filter out None values untuk mencegah overwrite dengan None
    # Ini penting untuk field yang required seperti exam_type
    filtered_update_data = {k: v for k, v in update_data.items() if v is not None}
    
    if not filtered_update_data:
        return await get_exam_by_id(db, exam_id)
    
    filtered_update_data["updated_at"] = datetime.utcnow()
    
    await db["exams"].update_one(
        {"_id": ObjectId(exam_id)},
        {"$set": filtered_update_data}
    )
    return await get_exam_by_id(db, exam_id)

async def set_exam_status(db: AsyncIOMotorDatabase, exam_id: str, status: str) -> dict | None:
    """Mengubah status ujian (misal: menjadi 'ongoing')."""
    if not ObjectId.is_valid(exam_id): return None
    await db["exams"].update_one(
        {"_id": ObjectId(exam_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    return await get_exam_by_id(db, exam_id)

async def delete_exam_and_sessions(db: AsyncIOMotorDatabase, exam_id: str) -> bool:
    """Menghapus dokumen ujian dan semua sesi ujian terkait."""
    if not ObjectId.is_valid(exam_id): return False
    
    # Hapus semua sesi ujian yang terkait terlebih dahulu
    await db["exam_sessions"].delete_many({"exam_id": ObjectId(exam_id)})
    
    # Hapus dokumen ujian utama
    result = await db["exams"].delete_one({"_id": ObjectId(exam_id)})
    return result.deleted_count > 0

async def get_exam_details_by_id(db: AsyncIOMotorDatabase, exam_id: str) -> dict | None:
    """Mengambil detail ujian lengkap, TAPI tanpa isi soalnya."""
    if not ObjectId.is_valid(exam_id): return None
    
    # Kita gunakan pipeline yang sama dengan get_all_exams, tapi dengan $match di awal
    pipeline = [
        {"$match": {"_id": ObjectId(exam_id)}},
        {"$lookup": {"from": "academic_periods", "localField": "academic_period_id", "foreignField": "_id", "as": "academic_period_details"}},
        {"$unwind": {"path": "$academic_period_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "teaching_assignments", "localField": "teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment_details"}},
        {"$unwind": {"path": "$teaching_assignment_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "subjects", "localField": "teaching_assignment_details.subject_id", "foreignField": "_id", "as": "teaching_assignment_details.subject_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.subject_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "classes", "localField": "teaching_assignment_details.class_id", "foreignField": "_id", "as": "teaching_assignment_details.class_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.class_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "teaching_assignment_details.teacher_id", "foreignField": "_id", "as": "teaching_assignment_details.teacher_details"}},
        {"$unwind": {"path": "$teaching_assignment_details.teacher_details", "preserveNullAndEmptyArrays": True}},
        {"$project": {"teaching_assignment_details.teacher_details.hashed_password": 0}},
    ]
    
    result = await db["exams"].aggregate(pipeline).to_list(1)
    return result[0] if result else None

async def delete_exam_by_assignment_id(db: AsyncIOMotorDatabase, assignment_id: ObjectId) -> bool:
    if not ObjectId.is_valid(assignment_id): return False
    result = await db["exams"].delete_many({"teaching_assignment_id": ObjectId(assignment_id)})
    return result.deleted_count > 0

async def delete_exam_by_assignment_ids(
    db: AsyncIOMotorDatabase,
    assignment_ids: List[str]
) -> bool:
    """
    Menghapus semua exam berdasarkan list teaching_assignment_id.
    Hanya ObjectId valid yang akan diproses.
    """
    if not assignment_ids:
        logger.warning("Tidak ada assignment_id yang diberikan untuk dihapus.")
        return False

    try:
        # Filter hanya ObjectId yang valid
        valid_ids = [ObjectId(i) for i in assignment_ids if ObjectId.is_valid(i)]

        if not valid_ids:
            logger.warning("Tidak ada ObjectId yang valid dari assignment_ids.")
            return False

        result = await db["exams"].delete_many({
            "teaching_assignment_id": {"$in": valid_ids}
        })

        logger.info(f"Berhasil menghapus {result.deleted_count} exam(s).")
        return True

    except Exception as e:
        logger.exception("Gagal menghapus exams berdasarkan assignment_ids.")
        return False

# --- TAMBAHKAN DI CRUD EXAMS ---
async def get_exams_by_teacher(
    db: AsyncIOMotorDatabase,
    teacher_id: str,
    academic_period_id: Optional[str] = None,
    class_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
    
    from app.crud.crud_teaching_assignments import get_filtered_assignment_ids
    """Mengambil ujian untuk guru dengan validasi akses."""
    # Validasi ObjectId
    if not ObjectId.is_valid(teacher_id):
        raise HTTPException(status_code=400, detail="Invalid teacher ID")
    
    teacher_obj_id = ObjectId(teacher_id)
    
    # Ambil assignment IDs dengan filter class_id jika ada
    filters = {"teacher_id": teacher_obj_id}
    if class_id:
        if not ObjectId.is_valid(class_id):
            raise HTTPException(status_code=400, detail="Invalid class ID")
        filters["class_id"] = ObjectId(class_id)
    
    assignment_ids = await get_filtered_assignment_ids(db, academic_period_id=academic_period_id, filters=filters)
    
    if not assignment_ids:
        return {"data": [], "total_items": 0}
    
    # Filter ujian berdasarkan assignment IDs
    pipeline = [
        {"$match": {
            "teaching_assignment_id": {"$in": [ObjectId(aid) for aid in assignment_ids]},
            "exam_type": {"$ne": None}  # PERBAIKAN: Filter out data dengan exam_type null
        }},
        {"$lookup": {"from": "teaching_assignments", "localField": "teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment"}},
        {"$unwind": "$teaching_assignment"},
        {"$lookup": {"from": "subjects", "localField": "teaching_assignment.subject_id", "foreignField": "_id", "as": "subject_details"}},
        {"$unwind": "$subject_details"},
        {"$lookup": {"from": "classes", "localField": "teaching_assignment.class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": "$class_details"},
    ]
    
    # Filter berdasarkan academic_period_id
    if academic_period_id:
        if not ObjectId.is_valid(academic_period_id):
            raise HTTPException(status_code=400, detail="Invalid academic period ID")
        pipeline.append({"$match": {"academic_period_id": ObjectId(academic_period_id)}})
    
    # Paginasi
    total_pipeline = pipeline.copy()
    total_pipeline.append({"$count": "total_items"})
    total_result = await db["exams"].aggregate(total_pipeline).to_list(None)
    total_items = total_result[0]["total_items"] if total_result else 0
    
    pipeline.extend([
        {"$sort": {"availability_start_time": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ])
    
    exams = await db["exams"].aggregate(pipeline).to_list(None)
    return {"data": exams, "total_items": total_items}

async def get_exams_by_student(
    db: AsyncIOMotorDatabase,
    student_profile: dict,
    academic_period_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
    
    from app.crud.crud_teaching_assignments import get_filtered_assignment_ids
    """Mengambil ujian untuk siswa berdasarkan class_id dari profil."""
    class_id = student_profile.get("class_id")
    if not class_id:
        raise HTTPException(status_code=400, detail="Student has no assigned class")
    
    # Ambil semua assignment IDs untuk class_id ini
    assignment_ids = await get_filtered_assignment_ids(db, academic_period_id=academic_period_id, filters={"class_id": class_id})
    print(assignment_ids)
    
    if not assignment_ids:
        return {"data": [], "total_items": 0}
    
    # Query ujian dengan validasi academic_period
    pipeline = [
        {"$match": {
            "teaching_assignment_id": {"$in": [ObjectId(aid) for aid in assignment_ids]},
            "exam_type": {"$ne": None}  # PERBAIKAN: Filter out data dengan exam_type null
        }},
        {"$lookup": {"from": "teaching_assignments", "localField": "teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment"}},
        {"$unwind": "$teaching_assignment"},
        {"$lookup": {"from": "subjects", "localField": "teaching_assignment.subject_id", "foreignField": "_id", "as": "subject_details"}},
        {"$unwind": "$subject_details"},
    ]
    
    if academic_period_id:
        if not ObjectId.is_valid(academic_period_id):
            raise HTTPException(status_code=400, detail="Invalid academic period ID")
        pipeline.append({"$match": {"academic_period_id": ObjectId(academic_period_id)}})
    
    # Filter berdasarkan status jika diberikan
    if status and status != 'all':
        pipeline.append({"$match": {"status": status}})
    
    # Hitung total
    total_pipeline = pipeline.copy()
    total_pipeline.append({"$count": "total_items"})
    total_result = await db["exams"].aggregate(total_pipeline).to_list(None)
    total_items = total_result[0]["total_items"] if total_result else 0
    
    # Paginasi
    pipeline.extend([
        {"$sort": {"availability_start_time": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ])
    
    exams = await db["exams"].aggregate(pipeline).to_list(None)
    return {"data": exams, "total_items": total_items}