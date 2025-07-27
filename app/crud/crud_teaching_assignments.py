# ==============================================================================
# File: app/crud/crud_teaching_assignments.py
# Deskripsi: Fungsi-fungsi CRUD untuk collection 'teaching_assignments'.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
from bson import ObjectId
import logging

from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentUpdate
from app.core.cache import get_cache, set_cache, invalidate_cache
from app.crud.crud_exams import delete_exam_by_assignment_id, delete_exam_by_assignment_ids

logger = logging.getLogger(__name__)

ASSIGNMENTS_IDS_CACHE_PATTERN = "assignments:ids:*"

def generate_assignment_ids_cache_key(filters: Dict[str, Any]) -> str:
    """Membuat kunci cache yang unik untuk daftar ID penugasan berdasarkan filter."""
    if not filters:
        return "assignments:ids:all"
    
    sorted_filters = sorted(filters.items())
    filter_str = "_".join([f"{k}={v}" for k, v in sorted_filters])
    return f"assignments:ids:{filter_str}"

async def get_filtered_assignment_ids(db: AsyncIOMotorDatabase, filters: Dict[str, Any]) -> List[str]:
    """Mengambil daftar ID penugasan yang sudah difilter, menggunakan cache."""
    cache_key = generate_assignment_ids_cache_key(filters)
    cached_ids = await get_cache(cache_key)
    if cached_ids is not None:
        return cached_ids

    query = {}
    if filters.get("class_id"):
        query["class_id"] = ObjectId(filters["class_id"])
    if filters.get("teacher_id"):
        query["teacher_id"] = ObjectId(filters["teacher_id"])
    
    cursor = db["teaching_assignments"].find(query, {"_id": 1})
    all_ids = [str(doc["_id"]) for doc in await cursor.to_list(None)]
    
    if all_ids:
        await set_cache(cache_key, all_ids)
        
    return all_ids

async def get_assignments_details_by_ids(db: AsyncIOMotorDatabase, assignment_ids: List[ObjectId]) -> List[dict]:
    """Mengambil detail lengkap penugasan berdasarkan daftar ID."""
    if not assignment_ids:
        return []
        
    pipeline = [
        {"$match": {"_id": {"$in": assignment_ids}}},
        # --- PERBAIKAN: Menggunakan preserveNullAndEmptyArrays untuk semua lookup ---
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": {"path": "$class_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject_details"}},
        {"$unwind": {"path": "$subject_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "teacher_id", "foreignField": "_id", "as": "teacher_details"}},
        {"$unwind": {"path": "$teacher_details", "preserveNullAndEmptyArrays": True}},
        # --- DITAMBAHKAN: Lookup tambahan untuk profil guru ---
        {"$lookup": {"from": "profiles", "localField": "teacher_details.profile_id", "foreignField": "_id", "as": "teacher_details.profile_details"}},
        {"$unwind": {"path": "$teacher_details.profile_details", "preserveNullAndEmptyArrays": True}},
        {"$project": {"teacher_details.hashed_password": 0}}
    ]
    return await db["teaching_assignments"].aggregate(pipeline).to_list(None)


async def create_teaching_assignment(db: AsyncIOMotorDatabase, assignment: TeachingAssignmentCreate) -> dict:
    if await db["teaching_assignments"].find_one({"class_id": assignment.class_id, "subject_id": assignment.subject_id, "teacher_id": assignment.teacher_id}):
        raise HTTPException(status_code=400, detail="This exact teaching assignment already exists.")
    
    assignment_dict = assignment.model_dump(mode='python')
    result = await db["teaching_assignments"].insert_one(assignment_dict)
    created = await db["teaching_assignments"].find_one({"_id": result.inserted_id})
    await invalidate_cache(ASSIGNMENTS_IDS_CACHE_PATTERN)
    return created

async def delete_teaching_assignment(db: AsyncIOMotorDatabase, assignment_id: str) -> bool:
    if not ObjectId.is_valid(assignment_id): 
        logger.warning(f"Invalid ObjectId: {assignment_id}")
        return False
    
    # Log sebelum menghapus assignment
    logger.info(f"Mencoba menghapus teaching assignment dengan ID: {assignment_id}")
    
    # Cek apakah ada ujian yang terkait sebelum menghapus assignment
    exam_count = await db["exams"].count_documents({"teaching_assignment_id": ObjectId(assignment_id)})
    logger.info(f"Ditemukan {exam_count} ujian yang terkait dengan assignment {assignment_id}")
    
    result = await db["teaching_assignments"].delete_one({"_id": ObjectId(assignment_id)})
    
    if result.deleted_count > 0:
        logger.info(f"Berhasil menghapus teaching assignment {assignment_id}, selanjutnya menghapus ujian terkait")
        
        # Panggil fungsi delete exam dengan logging tambahan
        delete_result = await delete_exam_by_assignment_ids(db=db, assignment_ids=[assignment_id])
        logger.info(f"Hasil penghapusan ujian: {delete_result}")
        
        # Verifikasi apakah ujian benar-benar terhapus
        remaining_exams = await db["exams"].count_documents({"teaching_assignment_id": ObjectId(assignment_id)})
        logger.info(f"Ujian yang tersisa setelah penghapusan: {remaining_exams}")
        
        await invalidate_cache(ASSIGNMENTS_IDS_CACHE_PATTERN)
    else:
        logger.warning(f"Gagal menghapus teaching assignment {assignment_id}")
    
    return result.deleted_count > 0

async def delete_assignment_by_class_id(db: AsyncIOMotorDatabase, class_id: ObjectId) -> bool:
    if not ObjectId.is_valid(class_id):
        return False

    # Konversi class_id ke ObjectId jika diperlukan (pastikan type hint sesuai)
    class_id_obj = ObjectId(class_id) if isinstance(class_id, str) else class_id

    # Ambil daftar assignment IDs
    cursor = db["teaching_assignments"].find({"class_id": class_id_obj}, {"_id": 1})
    assignment_docs = await cursor.to_list(length=None)

    if not assignment_docs:
        return False  # Kembalikan False jika tidak ada data

    # Hapus semua assignment dengan class_id
    result = await db["teaching_assignments"].delete_many({"class_id": class_id_obj})

    if result.deleted_count > 0:
        # Ekstrak _id dari dokumen untuk delete_exam_by_assignment_ids
        assignment_ids = [doc["_id"] for doc in assignment_docs]
        await delete_exam_by_assignment_ids(db=db, assignment_ids=assignment_ids)
        await invalidate_cache(ASSIGNMENTS_IDS_CACHE_PATTERN)

    return result.deleted_count > 0

async def delete_assignment_by_subject_id(db: AsyncIOMotorDatabase, subject_id=ObjectId) -> bool:
    if not ObjectId.is_valid(subject_id):
        return False
    
    subject_id_obj = ObjectId(subject_id) if isinstance(subject_id, str) else subject_id

    cursor = db["teaching_assignments"].find({"subject_id": subject_id_obj}, {"_id": 1})
    assignment_docs = await cursor.to_list(length=None)

    if not assignment_docs:
        return False
    
    result = await db["teaching_assignments"].delete_many({"subject_id": subject_id_obj})

    if result.deleted_count > 0:
        assignment_ids = [docs["_id"] for docs in assignment_docs]
        await delete_exam_by_assignment_ids(db, assignment_ids=assignment_ids)
        await invalidate_cache(ASSIGNMENTS_IDS_CACHE_PATTERN)

    return result.deleted_count > 0

async def find_assignments_by_criteria(
    db: AsyncIOMotorDatabase, 
    subject_id: ObjectId,
    grade_level: Optional[int] = None,
    expertise_id: Optional[ObjectId] = None,
    class_id: Optional[ObjectId] = None
) -> List[dict]:
    """Mencari penugasan mengajar berdasarkan kriteria untuk pembuatan ujian massal."""
    if class_id:
        return await db["teaching_assignments"].find({"class_id": class_id, "subject_id": subject_id}).to_list(1000)

    # Jika tidak menargetkan kelas spesifik, kita perlu join dengan collection 'classes'
    pipeline = []
    
    # Filter awal pada teaching_assignments untuk efisiensi
    pipeline.append({"$match": {"subject_id": subject_id}})
    
    # Join dengan collection 'classes'
    pipeline.extend([
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
    ])
    
    # Bangun filter berdasarkan data kelas
    class_match_criteria = {}
    if grade_level: class_match_criteria["class_info.grade_level"] = grade_level
    if expertise_id: class_match_criteria["class_info.expertise_id"] = expertise_id
    
    if class_match_criteria:
        pipeline.append({"$match": class_match_criteria})
    
    return await db["teaching_assignments"].aggregate(pipeline).to_list(1000)

async def update_teaching_assignment(db: AsyncIOMotorDatabase, assignment_id: ObjectId, assignment_update: TeachingAssignmentUpdate) -> dict | None:
    """Memperbarui penugasan mengajar (misalnya, mengganti guru)."""
    update_data = assignment_update.model_dump(mode='python', exclude_unset=True)
    if not update_data:
        return await db["teaching_assignments"].find_one({"_id": assignment_id})
        
    await db["teaching_assignments"].update_one(
        {"_id": assignment_id},
        {"$set": update_data}
    )
    return await db["teaching_assignments"].find_one({"_id": assignment_id})

async def get_teaching_assignments_by_teacher_id(db: AsyncIOMotorDatabase, teacher_id: str) -> List[dict]:
    """Mendapatkan semua teaching assignments berdasarkan teacher_id"""
    try:
        teacher_obj_id = ObjectId(teacher_id)
        cursor = db["teaching_assignments"].find({"teacher_id": teacher_obj_id})
        assignments = await cursor.to_list(None)
        return assignments
    except Exception as e:
        logger.error(f"Error getting teaching assignments for teacher {teacher_id}: {e}")
        return []

def extract_class_ids_from_assignments(assignments: List[dict]) -> List[ObjectId]:
    """Helper function untuk ekstrak class_ids dari teaching assignments"""
    class_ids = []
    for assignment in assignments:
        if "class_id" in assignment:
            class_ids.append(assignment["class_id"])
    return list(set(class_ids))  # Remove duplicates

def extract_assignment_ids_from_assignments(assignments: List[dict]) -> List[ObjectId]:
    """Helper function untuk ekstrak assignment_ids dari teaching assignments"""
    assignment_ids = []
    for assignment in assignments:
        if "_id" in assignment:
            assignment_ids.append(assignment["_id"])
    return assignment_ids

async def get_teacher_teaching_summary(db: AsyncIOMotorDatabase, teacher_id: str) -> List[dict]:
    """
    Mendapatkan teaching summary guru yang dikelompokkan berdasarkan kelas.
    Mengembalikan detail kelas, expertise, dan mata pelajaran yang diajar.
    """
    try:
        teacher_obj_id = ObjectId(teacher_id)
        
        # Pipeline agregasi untuk mendapatkan teaching summary
        pipeline = [
            # 1. Filter teaching assignments berdasarkan teacher_id
            {"$match": {"teacher_id": teacher_obj_id}},
            
            # 2. Lookup ke collection subjects
            {"$lookup": {
                "from": "subjects",
                "localField": "subject_id",
                "foreignField": "_id",
                "as": "subject_details"
            }},
            {"$unwind": "$subject_details"},
            
            # 3. Lookup ke collection classes
            {"$lookup": {
                "from": "classes",
                "localField": "class_id",
                "foreignField": "_id",
                "as": "class_details"
            }},
            {"$unwind": "$class_details"},
            
            # 4. Lookup ke collection expertise_programs
            {"$lookup": {
                "from": "expertise_programs",
                "localField": "class_details.expertise_id",
                "foreignField": "_id",
                "as": "expertise_details"
            }},
            {"$unwind": "$expertise_details"},
            
            # 5. Group berdasarkan class_id untuk mengelompokkan mata pelajaran per kelas
            {"$group": {
                "_id": "$class_id",
                "class_details": {"$first": "$class_details"},
                "expertise_details": {"$first": "$expertise_details"},
                "assignments": {"$push": {
                    "_id": "$subject_id",
                    "name": "$subject_details.name",
                    "code": "$subject_details.code",
                    "description": "$subject_details.description"
                }}
            }},
            
            # 6. Project untuk format output yang diinginkan
            {"$project": {
                "_id": 0,
                "class_id": "$_id",
                "class_details": 1,
                "expertise_details": 1,
                "assignments": 1
            }},
            
            # 7. Sort berdasarkan grade_level dan nama kelas
            {"$sort": {
                "class_details.grade_level": 1,
                "class_details.name": 1
            }}
        ]
        
        # Execute pipeline
        aggregation_result = await db["teaching_assignments"].aggregate(pipeline).to_list(None)
        
        # Hitung total siswa untuk setiap kelas
        classes_with_student_count = []
        for class_data in aggregation_result:
            class_id = class_data["class_id"]
            
            # Count siswa berdasarkan class_id
            student_count = await db["profiles"].count_documents({"class_id": class_id})
            
            # Format data sesuai schema yang diinginkan
            class_summary = {
                "total_students": student_count,
                "assignments": class_data["assignments"],
                "class_details": class_data["class_details"],
                "expertise_details": class_data["expertise_details"]
            }
            
            classes_with_student_count.append(class_summary)
        
        return classes_with_student_count
        
    except Exception as e:
        logger.error(f"Error getting teacher teaching summary for teacher {teacher_id}: {e}")
        return []

