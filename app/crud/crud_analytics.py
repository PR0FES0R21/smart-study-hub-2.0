# ==============================================================================
# File: app/crud/crud_analytics.py
# Deskripsi: Fungsi-fungsi untuk mengambil data analitik.
# --- DITAMBAHKAN ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict
from datetime import datetime
from app.core.cache import get_cache, set_cache
import pymongo
from bson import ObjectId


# Mendefinisikan kunci cache
DASHBOARD_STATS_CACHE_KEY = "analytics:dashboard_stats"
STUDENT_COUNT_CACHE_KEY = "analytics:student_count_by_major"
STUDENT_GROWTH_CACHE_KEY = "analytics:student_growth"
STUDENT_PERFORMANCE_ROSTER_CACHE_KEY = "analytics:student_performance_roster"
GENDER_DISTRIBUTION_CACHE_KEY = "analytics:gender_distribution"
COMPETENCY_PROFILE_CACHE_KEY = "analytics:competency_profile"
TEACHER_DASHBOARD_CACHE_KEY = "analytics:teacher_dashboard"


async def get_student_count_by_major_and_grade(db: AsyncIOMotorDatabase) -> List[dict]:
    """Agregasi untuk menghitung jumlah siswa per jurusan dan per tingkat kelas."""
    # 1. Cek cache dulu
    cached_data = await get_cache(STUDENT_COUNT_CACHE_KEY)
    if cached_data is not None:
        print("HIT: Mengambil data jumlah siswa dari cache.")
        return cached_data

    # 2. Jika tidak ada di cache, query ke DB
    print("MISS: Mengambil data jumlah siswa dari database.")
    pipeline = [
        {"$match": {"roles": "student"}},
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile"}},
        {"$unwind": "$profile"},
        {"$lookup": {"from": "classes", "localField": "profile.class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
        {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise_info"}},
        {"$unwind": "$expertise_info"},
        {"$group": {"_id": {"expertise_name": "$expertise_info.name", "expertise_abbreviation": "$expertise_info.abbreviation", "grade_level": "$class_info.grade_level"}, "count": {"$sum": 1}}},
        {"$group": {"_id": "$_id.expertise_name", "major_name": {"$first": "$_id.expertise_name"}, "major_abbreviation": {"$first": "$_id.expertise_abbreviation"}, "grade_counts": {"$push": {"k": {"$toString": "$_id.grade_level"}, "v": "$count"}}}},
        {"$addFields": {"grades": {"$arrayToObject": "$grade_counts"}}},
        {"$project": {"_id": 0, "major_name": 1, "major_abbreviation": 1, "grade_10_count": {"$ifNull": ["$grades.10", 0]}, "grade_11_count": {"$ifNull": ["$grades.11", 0]}, "grade_12_count": {"$ifNull": ["$grades.12", 0]}}},
        {"$sort": {"major_name": 1}}
    ]
    db_data = await db["users"].aggregate(pipeline).to_list(1000)
    
    # 3. Simpan hasil ke cache sebelum mengembalikan
    await set_cache(STUDENT_COUNT_CACHE_KEY, db_data)
    
    return db_data

async def get_student_growth_over_years(db: AsyncIOMotorDatabase, years_to_check: int = 10) -> List[dict]:
    """Menghitung total populasi siswa aktif untuk setiap tahun dalam N tahun terakhir."""
    # Kunci cache dinamis berdasarkan jumlah tahun
    cache_key = f"{STUDENT_GROWTH_CACHE_KEY}:{years_to_check}"
    
    # 1. Cek cache dulu
    cached_data = await get_cache(cache_key)
    if cached_data is not None:
        print(f"HIT: Mengambil data pertumbuhan siswa ({years_to_check} tahun) dari cache.")
        return cached_data

    # 2. Jika tidak ada di cache, lakukan perhitungan
    print(f"MISS: Menghitung data pertumbuhan siswa ({years_to_check} tahun) dari database.")
    current_year = datetime.utcnow().year
    results = []
    year_range = range(current_year - years_to_check + 1, current_year + 1)
    
    for year in year_range:
        query = {"start_year": {"$lte": year}, "end_year": {"$gte": year}}
        count = await db["profiles"].count_documents(query)
        results.append({"year": year, "student_count": count})
        
    # 3. Simpan hasil ke cache
    await set_cache(cache_key, results)
    
    return results

async def get_browser_usage_stats(db: AsyncIOMotorDatabase) -> List[dict]:
    """Agregasi untuk menghitung persentase penggunaan browser dari log aktivitas."""
    
    # 1. Dapatkan total semua log untuk perhitungan persentase
    total_logs = await db["activity_logs"].count_documents({})
    if total_logs == 0:
        return []

    # 2. Buat pipeline untuk mengelompokkan dan menghitung
    pipeline = [
        {
            "$group": {
                "_id": "$device_info.browser_name",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "browser_name": "$_id",
                "count": 1
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]

    results = await db["activity_logs"].aggregate(pipeline).to_list(100)

    # 3. Hitung persentase di Python
    for item in results:
        item["percentage"] = round((item["count"] / total_logs) * 100, 2)
        
    return results

async def get_dashboard_stats(db: AsyncIOMotorDatabase) -> dict:
    """Mengambil statistik utama untuk dasbor, dengan caching."""
    cached_data = await get_cache(DASHBOARD_STATS_CACHE_KEY)
    if cached_data:
        print("HIT: Mengambil statistik dasbor dari cache.")
        return cached_data
    
    print("MISS: Mengambil statistik dasbor dari database.")
    total_students = await db["users"].count_documents({"roles": "student"})
    total_teachers = await db["users"].count_documents({"roles": "teacher"})
    total_classes = await db["classes"].count_documents({})
    total_subjects = await db["subjects"].count_documents({})

    stats = {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_classes": total_classes,
        "total_subjects": total_subjects,
    }
    
    await set_cache(DASHBOARD_STATS_CACHE_KEY, stats)
    return stats

async def get_top_students_from_last_official_exam(db: AsyncIOMotorDatabase, limit: int = 5) -> List[dict]:
    """
    Mencari ujian resmi terakhir dan mengembalikan N siswa dengan skor tertinggi.
    """
    # 1. Cari ujian resmi (UTS/UAS) yang paling baru selesai
    last_official_exam = await db["exams"].find({
        "exam_type": {"$in": ["official_uts", "official_uas"]},
        "status": "graded" # Asumsi status berubah setelah semua dinilai
    }).sort("availability_start_time", pymongo.DESCENDING).limit(1).to_list(1)

    if not last_official_exam:
        return []
    
    exam = last_official_exam[0]
    exam_id = exam["_id"]
    exam_title = exam["title"]

    # 2. Cari 5 sesi ujian dengan skor tertinggi untuk ujian tersebut
    pipeline = [
        {"$match": {"exam_id": exam_id}},
        {"$sort": {"score": pymongo.DESCENDING}},
        {"$limit": limit},
        # 3. Gabungkan dengan data lain untuk informasi lengkap
        {"$lookup": {"from": "users", "localField": "student_id", "foreignField": "_id", "as": "user_info"}},
        {"$unwind": "$user_info"},
        {"$lookup": {"from": "profiles", "localField": "user_info.profile_id", "foreignField": "_id", "as": "profile_info"}},
        {"$unwind": "$profile_info"},
        {"$lookup": {"from": "classes", "localField": "profile_info.class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
        {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "major_info"}},
        {"$unwind": "$major_info"},
        # 4. Bentuk output akhir
        {"$project": {
            "_id": 0,
            "student_name": "$profile_info.full_name",
            "class_name": {
                "$concat": [{"$toString": "$class_info.grade_level"}, " ", "$major_info.abbreviation", " ", "$class_info.name"]
            },
            "major_abbreviation": "$major_info.abbreviation",
            "score": "$score",
            "exam_title": exam_title
        }}
    ]
    
    top_students = await db["exam_sessions"].aggregate(pipeline).to_list(limit)
    return top_students

async def get_student_performance_roster(db: AsyncIOMotorDatabase, limit: int = None, student_ids: List[str] = None) -> List[dict]:
    """Agregasi untuk membuat laporan rangkuman nilai semua siswa dengan dukungan limit dan caching byids."""
    
    # Buat cache key yang unik berdasarkan parameter
    cache_key = _generate_performance_roster_cache_key(limit, student_ids)
    
    # Cek cache terlebih dahulu
    cached_data = await get_cache(cache_key)
    if cached_data is not None:
        print(f"HIT: Mengambil rangkuman performa siswa dari cache dengan key: {cache_key}")
        return cached_data

    print(f"MISS: Menghitung rangkuman performa siswa dari database dengan key: {cache_key}")
    # Buat match condition untuk sesi ujian
    match_condition = {"status": "graded", "score": {"$ne": None}}
    
    # Jika ada filter student_ids, konversi ke ObjectId dan tambahkan ke match condition
    if student_ids:
        try:
            student_object_ids = [ObjectId(student_id) for student_id in student_ids]
            match_condition["student_id"] = {"$in": student_object_ids}
        except Exception as e:
            print(f"Error converting student_ids to ObjectId: {e}")
            # Jika ada error konversi, return empty list
            return []
    
    pipeline = [
        # 1. Mulai dari sesi ujian yang sudah dinilai dengan filter student_ids jika ada
        {"$match": match_condition},
        # 2. Kelompokkan berdasarkan siswa untuk mengumpulkan skor dan menghitung rata-rata
        {"$group": {
            "_id": "$student_id",
            "scores": {"$push": "$score"},
            "average_score": {"$avg": "$score"}
        }},
        # 3. Gabungkan dengan 'users' untuk mendapatkan profile_id
        {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user_info"}},
        {"$unwind": "$user_info"},
        # 4. Gabungkan dengan 'profiles' untuk mendapatkan nama dan class_id
        {"$lookup": {"from": "profiles", "localField": "user_info.profile_id", "foreignField": "_id", "as": "profile_info"}},
        {"$unwind": "$profile_info"},
        # 5. Gabungkan dengan 'classes' untuk mendapatkan detail kelas
        {"$lookup": {"from": "classes", "localField": "profile_info.class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
        # 6. Gabungkan dengan 'expertise_programs' untuk mendapatkan detail jurusan
        {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "major_info"}},
        {"$unwind": "$major_info"},
        # 7. Bentuk output akhir
        {"$project": {
            "_id": 0,
            "student_id": "$_id",
            "full_name": "$profile_info.full_name",
            "class_name": {"$concat": [{"$toString": "$class_info.grade_level"}, " ", "$major_info.abbreviation", " ", "$class_info.name"]},
            "major_name": "$major_info.name",
            "scores": "$scores",
            "average_score": {"$round": ["$average_score", 2]}
        }},
        {"$sort": {"average_score": -1}}
    ]
    
    # Tambahkan limit jika diperlukan
    if limit is not None and limit > 0:
        pipeline.append({"$limit": limit})
    
    # Eksekusi pipeline dengan atau tanpa limit
    if limit is not None:
        results = await db["exam_sessions"].aggregate(pipeline).to_list(limit)
    else:
        results = await db["exam_sessions"].aggregate(pipeline).to_list(None)
    
    # Cache hasil dengan key yang dinamis
    await set_cache(cache_key, results)
    
    return results

async def get_major_distribution_by_grade(db: AsyncIOMotorDatabase) -> Dict[str, List[dict]]:
    """
    Agregasi untuk menghitung jumlah dan persentase siswa per jurusan 
    untuk setiap tingkat kelas (10, 11, 12).
    """
    # Pipeline dasar untuk mendapatkan data siswa, kelas, dan jurusan
    base_pipeline = [
        {"$match": {"roles": "student"}},
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile"}},
        {"$unwind": "$profile"},
        {"$lookup": {"from": "classes", "localField": "profile.class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
        {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "major_info"}},
        {"$unwind": "$major_info"},
    ]

    # Menggunakan $facet untuk memproses setiap tingkat kelas secara paralel
    facet_pipeline = {
        "$facet": {
            "grade_10": base_pipeline + [
                {"$match": {"class_info.grade_level": 10}},
                {"$group": {"_id": "$major_info.abbreviation", "major_name": {"$first": "$major_info.name"}, "student_count": {"$sum": 1}}}
            ],
            "grade_11": base_pipeline + [
                {"$match": {"class_info.grade_level": 11}},
                {"$group": {"_id": "$major_info.abbreviation", "major_name": {"$first": "$major_info.name"}, "student_count": {"$sum": 1}}}
            ],
            "grade_12": base_pipeline + [
                {"$match": {"class_info.grade_level": 12}},
                {"$group": {"_id": "$major_info.abbreviation", "major_name": {"$first": "$major_info.name"}, "student_count": {"$sum": 1}}}
            ],
        }
    }
    
    result = await db["users"].aggregate([facet_pipeline]).to_list(1)
    
    if not result:
        return {"grade_10": [], "grade_11": [], "grade_12": []}

    data = result[0]
    
    # Fungsi helper untuk menghitung persentase
    def calculate_percentage(grade_data):
        total_students_in_grade = sum(item['student_count'] for item in grade_data)
        if total_students_in_grade == 0:
            return
        
        for item in grade_data:
            item['percentage'] = round((item['student_count'] / total_students_in_grade) * 100, 2)
            item['major_abbreviation'] = item['_id'] # Ganti nama field agar sesuai skema
            del item['_id']


    calculate_percentage(data['grade_10'])
    calculate_percentage(data['grade_11'])
    calculate_percentage(data['grade_12'])

    return data

async def get_major_growth_over_years(db: AsyncIOMotorDatabase, years_to_check: int = 10) -> List[dict]:
    """
    Menghitung total populasi siswa per jurusan untuk setiap tahun dalam N tahun terakhir.
    """
    current_year = datetime.utcnow().year
    year_range = range(current_year - years_to_check + 1, current_year + 1)
    
    # Dapatkan semua jurusan terlebih dahulu untuk membuat template hasil
    majors_cursor = db["expertise_programs"].find({}, {"abbreviation": 1})
    all_majors = {major["abbreviation"]: 0 for major in await majors_cursor.to_list(100)}

    results = []

    for year in year_range:
        pipeline = [
            # 1. Filter profil siswa yang aktif di tahun tersebut
            {"$match": {
                "start_year": {"$lte": year},
                "end_year": {"$gte": year}
            }},
            # 2. Gabungkan dengan data kelas
            {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
            {"$unwind": "$class_info"},
            # 3. Gabungkan dengan data jurusan
            {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "major_info"}},
            {"$unwind": "$major_info"},
            # 4. Kelompokkan berdasarkan singkatan jurusan dan hitung jumlahnya
            {"$group": {
                "_id": "$major_info.abbreviation",
                "count": {"$sum": 1}
            }}
        ]
        
        yearly_counts = await db["profiles"].aggregate(pipeline).to_list(100)
        
        # Buat dictionary hasil untuk tahun ini
        counts_for_year = all_majors.copy()
        for item in yearly_counts:
            counts_for_year[item["_id"]] = item["count"]
            
        results.append({"year": year, "counts": counts_for_year})
        
    return results

async def get_gender_distribution(db: AsyncIOMotorDatabase) -> List[dict]:
    """Menghitung jumlah dan persentase siswa aktif berdasarkan jenis kelamin."""
    cached_data = await get_cache(GENDER_DISTRIBUTION_CACHE_KEY)
    if cached_data is not None:
        print("HIT: Mengambil data distribusi jenis kelamin dari cache.")
        return cached_data

    print("MISS: Menghitung data distribusi jenis kelamin dari database.")
    
    # 1. Pipeline untuk mendapatkan total siswa aktif
    total_active_students_pipeline = [
        {"$match": {"roles": "student", "is_active": True}},
        {"$count": "total"}
    ]
    total_result = await db["users"].aggregate(total_active_students_pipeline).to_list(1)
    total_active_students = total_result[0]['total'] if total_result else 0

    if total_active_students == 0:
        return []

    # 2. Pipeline utama untuk menghitung per jenis kelamin
    pipeline = [
        {"$match": {"roles": "student", "is_active": True}},
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile"}},
        {"$unwind": "$profile"},
        {"$group": {
            "_id": {"$ifNull": ["$profile.gender", "Tidak Diketahui"]}, # Kelompokkan yang null
            "count": {"$sum": 1}
        }},
        {"$project": {
            "_id": 0,
            "gender": "$_id",
            "count": 1
        }}
    ]
    
    results = await db["users"].aggregate(pipeline).to_list(100)

    # 3. Hitung persentase di Python
    for item in results:
        item["percentage"] = round((item["count"] / total_active_students) * 100, 2)
        
    await set_cache(GENDER_DISTRIBUTION_CACHE_KEY, results)
    
    return results

def generate_cache_key(filters: Dict) -> str:
    """Membuat kunci cache yang unik berdasarkan filter."""
    if not filters:
        return "analytics:competency_profile:global"
    
    # Membuat kunci yang terurut agar konsisten
    sorted_filters = sorted(filters.items())
    filter_str = "_".join([f"{k}-{v}" for k, v in sorted_filters])
    return f"analytics:competency_profile:{filter_str}"

# --- DITAMBAHKAN: Fungsi untuk membangun pipeline ---
def build_competency_pipeline(filters: Dict) -> List[Dict]:
    """Membangun pipeline agregasi dasar dengan filter dinamis."""
    pipeline = []
    
    # Tahap filter awal berdasarkan kriteria
    match_filters = {"roles": "student"}
    if filters.get("student_id"):
        match_filters["_id"] = ObjectId(filters["student_id"])
    
    pipeline.append({"$match": match_filters})

    # Gabungkan dengan data lain
    pipeline.extend([
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile"}},
        {"$unwind": "$profile"},
        {"$lookup": {"from": "classes", "localField": "profile.class_id", "foreignField": "_id", "as": "class_info"}},
        {"$unwind": "$class_info"},
    ])

    # Terapkan filter kelas/jurusan setelah join
    class_match_filters = {}
    if filters.get("class_id"):
        class_match_filters["class_info._id"] = ObjectId(filters["class_id"])
    if filters.get("grade_level"):
        class_match_filters["class_info.grade_level"] = int(filters["grade_level"])
    if filters.get("expertise_id"):
        class_match_filters["class_info.expertise_id"] = ObjectId(filters["expertise_id"])
    
    if class_match_filters:
        pipeline.append({"$match": class_match_filters})

    # Lanjutkan join ke sesi ujian dan mata pelajaran
    pipeline.extend([
        {"$lookup": {"from": "exam_sessions", "localField": "_id", "foreignField": "student_id", "as": "sessions"}},
        {"$unwind": "$sessions"},
        {"$match": {"sessions.status": "graded", "sessions.score": {"$ne": None}}},
        {"$lookup": {"from": "exams", "localField": "sessions.exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
    ])
    
    return pipeline

TEACHER_DASHBOARD_CACHE_KEY = "analytics:teacher_dashboard"

async def count_students_by_class_ids(db: AsyncIOMotorDatabase, class_ids: List[ObjectId]) -> int:
    """Menghitung total siswa berdasarkan daftar class_id"""
    if not class_ids:
        return 0
    
    try:
        count = await db["profiles"].count_documents({
            "class_id": {"$in": class_ids}
        })
        return count
    except Exception as e:
        print(f"Error counting students by class_ids: {e}")
        return 0

async def count_exams_by_teaching_assignment_ids(db: AsyncIOMotorDatabase, assignment_ids: List[ObjectId]) -> int:
    """Menghitung total ujian berdasarkan teaching_assignment_ids"""
    if not assignment_ids:
        return 0
    
    try:
        count = await db["exams"].count_documents({
            "teaching_assignment_id": {"$in": assignment_ids}
        })
        return count
    except Exception as e:
        print(f"Error counting exams by assignment_ids: {e}")
        return 0

async def count_questions_by_teacher_id(db: AsyncIOMotorDatabase, teacher_id: str) -> int:
    """Menghitung total soal yang dibuat guru"""
    try:
        teacher_obj_id = ObjectId(teacher_id)
        count = await db["question_banks"].count_documents({
            "created_by_teacher_id": teacher_obj_id
        })
        return count
    except Exception as e:
        print(f"Error counting questions by teacher_id: {e}")
        return 0

async def get_teacher_dashboard_stats(db: AsyncIOMotorDatabase, academic_period: str, teacher_id: str) -> dict:
    """Main function untuk mendapatkan semua stats guru sekaligus"""
    # Check cache first
    cache_key = f"{TEACHER_DASHBOARD_CACHE_KEY}:{teacher_id}"
    cached_data = await get_cache(cache_key)
    if cached_data:
        print(f"HIT: Mengambil teacher dashboard stats dari cache untuk teacher {teacher_id}")
        return cached_data
    
    print(f"MISS: Menghitung teacher dashboard stats dari database untuk teacher {teacher_id}")
    
    # Import here to avoid circular import
    from app.crud.crud_teaching_assignments import (
        get_teaching_assignments_by_teacher_id,
        extract_class_ids_from_assignments,
        extract_assignment_ids_from_assignments
    )
    
    try:
        # Step 1: Get all teaching assignments for this teacher
        assignments = await get_teaching_assignments_by_teacher_id(db, academic_period_id=ObjectId(academic_period), teacher_id=teacher_id)
        total_classes = len(assignments)
        
        if not assignments:
            # If no assignments, return zeros
            stats = {
                "total_classes": 0,
                "total_students": 0,
                "total_exams": 0,
                "total_questions": 0
            }
        else:
            # Step 2: Extract class_ids and assignment_ids
            class_ids = extract_class_ids_from_assignments(assignments)
            assignment_ids = extract_assignment_ids_from_assignments(assignments)
            
            # Step 3: Count students, exams, and questions concurrently
            total_students = await count_students_by_class_ids(db, class_ids)
            total_exams = await count_exams_by_teaching_assignment_ids(db, assignment_ids)
            total_questions = await count_questions_by_teacher_id(db, teacher_id)
            
            stats = {
                "total_classes": total_classes,
                "total_students": total_students,
                "total_exams": total_exams,
                "total_questions": total_questions
            }
        
        # Cache the result for 1 hour (3600 seconds)
        await set_cache(cache_key, stats, ttl=3600)
        return stats
        
    except Exception as e:
        print(f"Error getting teacher dashboard stats for teacher {teacher_id}: {e}")
        # Return zeros in case of error
        return {
            "total_classes": 0,
            "total_students": 0,
            "total_exams": 0,
            "total_questions": 0
        }

def _generate_performance_roster_cache_key(limit: int = None, student_ids: List[str] = None) -> str:
    """Generate unique cache key for student performance roster based on parameters."""
    key_parts = ["analytics:student_performance_roster"]
    
    if limit is not None:
        key_parts.append(f"limit:{limit}")
    else:
        key_parts.append("limit:all")
    
    if student_ids and len(student_ids) > 0:
        # Sort student_ids untuk konsistensi cache key
        sorted_ids = sorted(student_ids)
        # Buat hash dari student_ids untuk menghindari key yang terlalu panjang
        import hashlib
        ids_hash = hashlib.md5(",".join(sorted_ids).encode()).hexdigest()[:8]
        key_parts.append(f"ids:{ids_hash}")
    else:
        key_parts.append("ids:all")
    
    return ":".join(key_parts)
