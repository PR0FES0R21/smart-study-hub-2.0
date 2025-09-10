# ==============================================================================
# File: app/crud/crud_users.py
# Deskripsi: Fungsi-fungsi untuk berinteraksi dengan collection 'users' di DB.
# --- DIUBAH --- (Pipeline agregasi diperbarui untuk menangani ringkasan mengajar guru)
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException
from app.schemas.user import UserCreate, UserUpdate, SelfDataUpdate
from app.core.security import get_password_hash
from bson import ObjectId
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.cache import invalidate_cache, flush_all_cache, get_cache, set_cache
import logging

logger = logging.getLogger(__name__)

USERS_IDS_CACHE_PATTERN = "users:ids:*"

async def get_user_by_login_id(db: AsyncIOMotorDatabase, login_id: str) -> dict | None:
    user = await db["users"].find_one({"login_id": login_id})
    return user

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> dict | None:
    user = await db["users"].find_one({"email": email})
    return user

async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    if not ObjectId.is_valid(user_id): return None
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    return user

async def get_users_for_datatables(
    db: AsyncIOMotorDatabase, 
    dt_params: Dict[str, Any],
    role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mengambil data user dengan paginasi, pencarian, dan pengurutan untuk DataTables.
    Juga menggabungkan data dari collection lain.
    """
    draw = int(dt_params.get('draw', 1))
    start = int(dt_params.get('start', 0))
    length = int(dt_params.get('length', 10))
    search_value = dt_params.get('search', {}).get('value', '')
    
    # Pipeline agregasi dasar
    base_pipeline = []
    
    # Tahap 0: Filter berdasarkan peran di awal untuk efisiensi
    if role:
        base_pipeline.append({"$match": {"roles": role}})

    # Tahap 1 & 2: Lookup untuk detail siswa (kelas & jurusan)
    base_pipeline.extend([
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": {"path": "$class_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "expertise_programs", "localField": "class_details.expertise_id", "foreignField": "_id", "as": "expertise_details"}},
        {"$unwind": {"path": "$expertise_details", "preserveNullAndEmptyArrays": True}},
    ])
    
    # Tahap 3: Lookup untuk detail departemen guru
    base_pipeline.extend([
        {"$lookup": {"from": "expertise_programs", "localField": "department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
    ])
    
    # --- DITAMBAHKAN: Tahap 4: Lookup untuk ringkasan mengajar guru ---
    base_pipeline.append({
        "$lookup": {
            "from": "teaching_assignments",
            "let": {"teacher_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$teacher_id", "$$teacher_id"]}}},
                {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"},
                {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise"}},
                {"$unwind": "$expertise"},
                {"$project": {
                    "_id": 0,
                    "subject_name": "$subject.name",
                    "class_name": {
                        "$concat": [
                            {"$toString": "$class_info.grade_level"}, " ",
                            "$expertise.abbreviation", " ",
                            "$class_info.name"
                        ]
                    }
                }}
            ],
            "as": "teaching_summary"
        }
    })

    # Tahap 5: Pencarian
    match_stage = {}
    if search_value:
        match_stage = {"$or": [
            {"full_name": {"$regex": search_value, "$options": "i"}},
            {"login_id": {"$regex": search_value, "$options": "i"}},
            {"email": {"$regex": search_value, "$options": "i"}},
        ]}
    
    # Menghitung total data
    count_pipeline = base_pipeline.copy()
    if match_stage:
        count_pipeline.append({"$match": match_stage})
    count_pipeline.append({"$count": "count"})
    
    records_filtered_result = await db["users"].aggregate(count_pipeline).to_list(1)
    records_filtered = records_filtered_result[0]['count'] if records_filtered_result else 0
    
    # Mengambil data dengan paginasi
    data_pipeline = base_pipeline.copy()
    if match_stage:
        data_pipeline.append({"$match": match_stage})
    data_pipeline.extend([{"$skip": start}, {"$limit": length}])
    
    data = await db["users"].aggregate(data_pipeline).to_list(length)
    
    records_total = await db["users"].count_documents({})

    return {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    }

async def create_user(db: AsyncIOMotorDatabase, user: UserCreate) -> dict:

    if await get_user_by_login_id(db, user.login_id):
        raise HTTPException(status_code=400, detail=f"Login ID '{user.login_id}' already registered")
    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail=f"Email '{user.email}' already registered")

    db_obj = user.model_dump(mode='python', exclude={"password"}, round_trip=True)
    db_obj["hashed_password"] = get_password_hash(user.password)

    result = await db["users"].insert_one(db_obj)
    created_user = await db["users"].find_one({"_id": result.inserted_id})
    return created_user

async def update_user(db: AsyncIOMotorDatabase, user_id: str, user_update: UserUpdate) -> dict | None:
    update_data = user_update.model_dump(mode='python', exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]
    else:
        update_data.pop("password", None)

    if not update_data:
        return await get_user_by_id(db, user_id)

    await db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    return await get_user_by_id(db, user_id)


async def create_user_and_profile(db: AsyncIOMotorDatabase, user_in: UserCreate) -> dict:
    if await get_user_by_login_id(db, user_in.login_id):
        raise HTTPException(status_code=400, detail=f"Login ID '{user_in.login_id}' sudah terdaftar")
    if await get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail=f"Email '{user_in.email}' sudah terdaftar")

    now = datetime.utcnow()
    
    # 1. Buat dokumen profile
    profile_data = user_in.profile.model_dump(mode='python')
    profile_data["created_at"] = now
    profile_data["updated_at"] = now
    profile_result = await db["profiles"].insert_one(profile_data)
    created_profile_id = profile_result.inserted_id

    # 2. Buat dokumen user
    user_obj = {
        "login_id": user_in.login_id,
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.login_id),
        "roles": user_in.roles,
        "is_active": user_in.is_active,
        "profile_id": created_profile_id,
        "onboarding_completed": False,
        "password_last_changed_at": None,
        "created_at": now,
        "updated_at": now
    }
    user_result = await db["users"].insert_one(user_obj)
    created_user_id = user_result.inserted_id

    # 3. Update profile dengan user_id
    await db["profiles"].update_one({"_id": created_profile_id}, {"$set": {"user_id": created_user_id}})

    await invalidate_cache(USERS_IDS_CACHE_PATTERN)
    await invalidate_cache("analytics:*")
    return await db["users"].find_one({"_id": created_user_id})

def generate_user_ids_cache_key(filters: Dict[str, Any]) -> str:
    """Membuat kunci cache yang unik untuk daftar ID user berdasarkan filter."""
    if not filters:
        return "users:ids:all"
    
    sorted_filters = sorted(filters.items())
    filter_str = "_".join([f"{k}={v}" for k, v in sorted_filters])
    return f"users:ids:{filter_str}"

async def get_filtered_user_ids(db: AsyncIOMotorDatabase, filters: Dict[str, Any]) -> List[str]:
    """Mengambil daftar ID user yang sudah difilter, menggunakan cache."""
    cache_key = generate_user_ids_cache_key(filters)
    cached_ids = await get_cache(cache_key)
    if cached_ids is not None:
        print(f"HIT: Mengambil ID user dari cache untuk filter: {filters}")
        return cached_ids

    print(f"MISS: Mengambil ID user dari database untuk filter: {filters}")
    
    pipeline = []
    # Bangun pipeline filter
    match_query = {}
    if filters.get("role"):
        match_query["roles"] = filters["role"]
    if match_query:
        pipeline.append({"$match": match_query})

    if filters.get("grade_level") or filters.get("expertise_id") or filters.get("class_id"):
        pipeline.extend([
            {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile"}},
            {"$unwind": "$profile"}
        ])
        
        if filters.get("role") == 'teacher' and filters.get("expertise_id"):
            pipeline.append({"$match": {"profile.department_id": ObjectId(filters["expertise_id"])}})
        
        elif filters.get("role") == 'student':
            pipeline.extend([
                {"$lookup": {"from": "classes", "localField": "profile.class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"}
            ])
            class_filter = {}
            if filters.get("grade_level"): class_filter["class_info.grade_level"] = filters["grade_level"]
            if filters.get("expertise_id"): class_filter["class_info.expertise_id"] = ObjectId(filters["expertise_id"])
            if filters.get("class_id"): class_filter["class_info._id"] = ObjectId(filters["class_id"])
            if class_filter:
                pipeline.append({"$match": class_filter})

    pipeline.append({"$project": {"_id": 1}})
    cursor = db["users"].aggregate(pipeline)
    all_ids = [str(doc["_id"]) for doc in await cursor.to_list(None)]
    
    if all_ids:
        await set_cache(cache_key, all_ids)
        
    return all_ids

async def get_users_details_by_ids(db: AsyncIOMotorDatabase, user_ids: List[ObjectId]) -> List[dict]:
    """Mengambil detail lengkap user berdasarkan daftar ID."""
    if not user_ids:
        return []
        
    pipeline = [
        {"$match": {"_id": {"$in": user_ids}}},
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        
        # --- PERBAIKAN: Lookup berantai untuk data kelas dan jurusan siswa ---
        {"$lookup": {
            "from": "classes",
            "let": { "class_id": "$profile_details.class_id" },
            "pipeline": [
                { "$match": { "$expr": { "$eq": [ "$_id", "$$class_id" ] } } },
                # Lakukan lookup ke jurusan DI DALAM sub-pipeline ini
                { "$lookup": { "from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
                { "$unwind": { "path": "$expertise_details", "preserveNullAndEmptyArrays": True }}
            ],
            "as": "class_details_array"
        }},
        {"$unwind": {"path": "$class_details_array", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"class_details": "$class_details_array"}},

        # Lookup untuk departemen guru (tetap sama)
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
        
        # Lookup untuk ringkasan mengajar guru (tetap sama)
        {"$lookup": {"from": "teaching_assignments", "let": {"teacher_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$teacher_id", "$$teacher_id"]}}},
                {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"},
                {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise"}},
                {"$unwind": "$expertise"},
                {"$project": {"_id": 0, "subject_name": "$subject.name", "class_name": {"$concat": [{"$toString": "$class_info.grade_level"}, " ", "$expertise.abbreviation", " ", "$class_info.name"]}}}
            ], "as": "teaching_summary"}},
            
        # Hapus field-field sementara yang tidak perlu
        {"$project": {"class_details_array": 0}}
    ]
    return await db["users"].aggregate(pipeline).to_list(None)

async def search_users_with_details(
    db: AsyncIOMotorDatabase,
    search: str,
    skip: int,
    limit: int,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Melakukan pencarian langsung ke DB (bypass cache) dan mengembalikan data lengkap
    dengan dukungan filter tambahan dan teaching summary.
    """
    base_pipeline = [
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        
        # --- PERBAIKAN: Lookup berantai untuk data kelas dan jurusan siswa ---
        {"$lookup": {
            "from": "classes",
            "let": { "class_id": "$profile_details.class_id" },
            "pipeline": [
                { "$match": { "$expr": { "$eq": [ "$_id", "$$class_id" ] } } },
                # Lakukan lookup ke jurusan DI DALAM sub-pipeline ini
                { "$lookup": { "from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
                { "$unwind": { "path": "$expertise_details", "preserveNullAndEmptyArrays": True }}
            ],
            "as": "class_details_array"
        }},
        {"$unwind": {"path": "$class_details_array", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"class_details": "$class_details_array"}},

        # Lookup untuk departemen guru (tetap sama)
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
        
        # --- DIHAPUS: Field expertise_details yang unified tidak diperlukan ---
        # Siswa: expertise_details ada di class_details.expertise_details
        # Guru: expertise_details tidak diperlukan, gunakan department_details
        
        # Lookup untuk ringkasan mengajar guru (tetap sama)
        {"$lookup": {"from": "teaching_assignments", "let": {"teacher_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$teacher_id", "$$teacher_id"]}}},
                {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"},
                {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise"}},
                {"$unwind": "$expertise"},
                {"$project": {"_id": 0, "subject_name": "$subject.name", "class_name": {"$concat": [{"$toString": "$class_info.grade_level"}, " ", "$expertise.abbreviation", " ", "$class_info.name"]}}}
            ], "as": "teaching_summary"}},
            
        # Hapus field-field sementara yang tidak perlu
        {"$project": {"class_details_array": 0}}
    ]
    
    # Build match conditions untuk search
    match_conditions = {
        "$and": [
            {
                "$or": [
                    {"profile_details.full_name": {"$regex": search, "$options": "i"}},
                    {"login_id": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}},
                ]
            }
        ]
    }
    
    # Apply additional filters if provided
    if filters:
        for key, value in filters.items():
            if value is not None:
                if key == "role":
                    # roles adalah array, jadi gunakan $in
                    match_conditions["$and"].append({"roles": {"$in": [value]}})
                elif key == "department_id" or key == "expertise_id":
                    # Handle department/expertise filter untuk teacher dan student
                    # Teacher: department_id ada di profile_details (akan masuk ke department_details)
                    # Student: expertise_id ada di class_details (akan masuk ke expertise_details dari class_details)
                    match_conditions["$and"].append({
                        "$or": [
                            {"department_details._id": ObjectId(value)},           # Untuk teacher
                            {"class_details.expertise_details._id": ObjectId(value)} # Untuk student
                        ]
                    })
                elif key == "class_id":
                    # class_id ada di profile_details (khusus student)
                    match_conditions["$and"].append({"profile_details.class_id": ObjectId(value)})
                elif key == "grade_level":
                    # grade_level ada di class_details (khusus student)
                    match_conditions["$and"].append({"class_details.grade_level": value})
                elif key == "is_active":
                    # Filter berdasarkan status aktif
                    match_conditions["$and"].append({"is_active": value})
                elif key == "gender":
                    # Filter berdasarkan gender di profile
                    match_conditions["$and"].append({"profile_details.gender": value})
    
    match_stage = {"$match": match_conditions}
    full_pipeline = base_pipeline + [match_stage]
    
    # Count pipeline
    count_pipeline = full_pipeline + [{"$count": "count"}]
    total_items_result = await db["users"].aggregate(count_pipeline).to_list(1)
    total_items = total_items_result[0]['count'] if total_items_result else 0
    
    # Data pipeline
    data_pipeline = full_pipeline + [{"$skip": skip}, {"$limit": limit}]
    data = await db["users"].aggregate(data_pipeline).to_list(limit)
    
    return {"data": data, "total_items": total_items}



async def update_user_and_profile(db: AsyncIOMotorDatabase, user_id: str, user_in: UserUpdate) -> dict | None:
    """Memperbarui dokumen user dan/atau profile terkait dengan benar."""
    now = datetime.utcnow()
    user_to_update = await get_user_by_id(db, user_id)
    if not user_to_update:
        return None

    # 1. Update dokumen profile jika ada data profile di input
    if user_in.profile and user_in.profile.model_fields_set:
        profile_update_data = {}
        # --- PERBAIKAN: Gunakan model_fields_set untuk menangani null ---
        for field in user_in.profile.model_fields_set:
            profile_update_data[field] = getattr(user_in.profile, field)
        
        if profile_update_data:
            profile_update_data["updated_at"] = now
            await db["profiles"].update_one(
                {"_id": user_to_update["profile_id"]},
                {"$set": profile_update_data}
            )

    # 2. Update dokumen user
    user_update_data = {}
    # --- PERBAIKAN: Gunakan model_fields_set untuk menangani null ---
    for field in user_in.model_fields_set:
        if field != "profile": # Abaikan field profile
            user_update_data[field] = getattr(user_in, field)

    if user_update_data:
        if "password" in user_update_data and user_update_data["password"]:
            user_update_data["hashed_password"] = get_password_hash(user_update_data["password"])
            del user_update_data["password"]
        else:
            user_update_data.pop("password", None)
            
        user_update_data["updated_at"] = now
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": user_update_data}
        )
        await invalidate_cache(USERS_IDS_CACHE_PATTERN)
        
    return await get_user_by_id(db, user_id)

async def delete_user_and_profile(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """
    Menghapus dokumen user dan profile, serta membersihkan semua data
    terkait secara kondisional berdasarkan peran.
    """
    user_to_delete = await get_user_by_id(db, user_id)
    if not user_to_delete:
        return False

    user_object_id = user_to_delete["_id"]
    user_roles = user_to_delete.get("roles", [])

    # --- PERBAIKAN: Logika "Pembersihan Ketergantungan" yang sadar peran ---
    # Langkah ini hanya dijalankan jika pengguna adalah seorang guru
    if "teacher" in user_roles:
        print(f"User {user_id} adalah seorang guru. Membersihkan data terkait...")
        
        # 1. Hapus semua penugasan mengajar (teaching_assignments)
        await db["teaching_assignments"].delete_many({"teacher_id": user_object_id})
        
        # 2. Kosongkan referensi wali kelas (homeroom_teacher_id) di 'classes'
        await db["classes"].update_many(
            {"homeroom_teacher_id": user_object_id},
            {"$set": {"homeroom_teacher_id": None}}
        )
        
        # 3. Kosongkan referensi kepala jurusan (head_of_department_id) di 'expertise_programs'
        await db["expertise_programs"].update_many(
            {"head_of_department_id": user_object_id},
            {"$set": {"head_of_department_id": None}}
        )

    # Langkah penghapusan utama (berlaku untuk semua peran)
    # 1. Hapus profile
    if "profile_id" in user_to_delete and user_to_delete["profile_id"]:
        await db["profiles"].delete_one({"_id": user_to_delete["profile_id"]})
    
    # 2. Hapus user
    result = await db["users"].delete_one({"_id": user_object_id})
    
    # Invalidate cache jika penghapusan berhasil
    if result.deleted_count > 0:
        await invalidate_cache(USERS_IDS_CACHE_PATTERN)
        await invalidate_cache("analytics:*") # Invalidate semua cache analitik

    return result.deleted_count > 0

async def graduate_students_by_grade(db: AsyncIOMotorDatabase, grade_level: int) -> int:
    """Mencari semua siswa di tingkat kelas tertentu dan meluluskan mereka."""
    now = datetime.utcnow()
    
    target_classes = await db["classes"].find({"grade_level": grade_level}).to_list(1000)
    if not target_classes: return 0
    target_class_ids = [c["_id"] for c in target_classes]

    student_profiles_cursor = db["profiles"].find({"class_id": {"$in": target_class_ids}})
    student_profiles = await student_profiles_cursor.to_list(None)
    if not student_profiles: return 0
    
    student_user_ids = [p["user_id"] for p in student_profiles if p.get("user_id")]
    student_profile_ids = [p["_id"] for p in student_profiles]

    user_update_result = await db["users"].update_many(
        {"_id": {"$in": student_user_ids}},
        {"$set": {"is_active": False, "roles": ["alumni"], "updated_at": now}}
    )

    await db["profiles"].update_many(
        {"_id": {"$in": student_profile_ids}},
        {"$set": {"class_id": None, "updated_at": now}}
    )
    
    if user_update_result.modified_count > 0:
        await flush_all_cache()
        
    return user_update_result.modified_count

async def update_user_password(db: AsyncIOMotorDatabase, user_id: ObjectId, new_password: str):
    """Memperbarui password pengguna dan menyelesaikan onboarding."""
    now = datetime.utcnow()
    new_hashed_password = get_password_hash(new_password)
    await db["users"].update_one(
        {"_id": user_id},
        {"$set": {
            "hashed_password": new_hashed_password, 
            "onboarding_completed": True, # --- DITAMBAHKAN ---
            "password_last_changed_at": now, # --- DITAMBAHKAN ---
            "updated_at": now
        }}
    )

async def update_profile_picture(db: AsyncIOMotorDatabase, profile_id: ObjectId, image_url: str, object_key: str) -> bool:
    """Memperbarui URL dan kunci objek foto profil di database."""
    result = await db["profiles"].update_one(
        {"_id": profile_id},
        {"$set": {
            "profile_picture_url": image_url,
            "profile_picture_key": object_key,
            "updated_at": datetime.utcnow()
        }}
    )
    return result.modified_count > 0

async def get_users_details_by_ids(db: AsyncIOMotorDatabase, user_ids: List[ObjectId]) -> List[dict]:
    """Mengambil detail lengkap user berdasarkan daftar ID."""
    if not user_ids:
        return []
        
    pipeline = [
        {"$match": {"_id": {"$in": user_ids}}},
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        
        # --- PERBAIKAN: Lookup berantai untuk data kelas dan jurusan siswa ---
        {"$lookup": {
            "from": "classes",
            "let": { "class_id": "$profile_details.class_id" },
            "pipeline": [
                { "$match": { "$expr": { "$eq": [ "$_id", "$$class_id" ] } } },
                # Lakukan lookup ke jurusan DI DALAM sub-pipeline ini
                { "$lookup": { "from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
                { "$unwind": { "path": "$expertise_details", "preserveNullAndEmptyArrays": True }}
            ],
            "as": "class_details_array"
        }},
        {"$unwind": {"path": "$class_details_array", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"class_details": "$class_details_array"}},

        # Lookup untuk departemen guru (tetap sama)
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
        
        # --- DIHAPUS: Field expertise_details yang unified tidak diperlukan ---
        # Siswa: expertise_details ada di class_details.expertise_details
        # Guru: expertise_details tidak diperlukan, gunakan department_details
        
        # Lookup untuk ringkasan mengajar guru (tetap sama)
        {"$lookup": {"from": "teaching_assignments", "let": {"teacher_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$teacher_id", "$$teacher_id"]}}},
                {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"},
                {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise"}},
                {"$unwind": "$expertise"},
                {"$project": {"_id": 0, "subject_name": "$subject.name", "class_name": {"$concat": [{"$toString": "$class_info.grade_level"}, " ", "$expertise.abbreviation", " ", "$class_info.name"]}}}
            ], "as": "teaching_summary"}},
            
        # Hapus field-field sementara yang tidak perlu
        {"$project": {"class_details_array": 0}}
    ]
    return await db["users"].aggregate(pipeline).to_list(None)

async def get_users_with_profiles_for_datatables(
    db: AsyncIOMotorDatabase, 
    dt_params: Dict[str, Any],
    role: Optional[str] = None,
    grade_level: Optional[int] = None,
    expertise_id: Optional[str] = None,
    class_id: Optional[str] = None
) -> Dict[str, Any]:
    draw = int(dt_params.get('draw', 1)); start = int(dt_params.get('start', 0)); length = int(dt_params.get('length', 10)); search_value = dt_params.get('search', {}).get('value', '')
    
    order_column_index = int(dt_params.get('order[0][column]', 0)); order_column_dir = dt_params.get('order[0][dir]', 'asc')
    column_mapping = {0: "login_id", 1: "profile_details.full_name", 2: "email", 3: "roles"}
    sort_field = column_mapping.get(order_column_index, "login_id")
    sort_dir = 1 if order_column_dir == 'asc' else -1
    sort_stage = {"$sort": {sort_field: sort_dir}}

    pipeline = []
    if role: pipeline.append({"$match": {"roles": role}})
    
    # Tahap 1: Lakukan semua join/lookup terlebih dahulu untuk merakit data
    pipeline.extend([
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        
        # --- PERBAIKAN: Lookup berantai untuk data kelas dan jurusan siswa ---
        {"$lookup": {
            "from": "classes",
            "let": { "class_id": "$profile_details.class_id" },
            "pipeline": [
                { "$match": { "$expr": { "$eq": [ "$_id", "$$class_id" ] } } },
                # Lakukan lookup ke jurusan DI DALAM sub-pipeline ini
                { "$lookup": { "from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
                { "$unwind": { "path": "$expertise_details", "preserveNullAndEmptyArrays": True }}
            ],
            "as": "class_details_array"
        }},
        {"$unwind": {"path": "$class_details_array", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"class_details": "$class_details_array"}},

        # Lookup untuk departemen guru (tetap sama)
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
        
        # --- DIHAPUS: Field expertise_details yang unified tidak diperlukan ---
        # Siswa: expertise_details ada di class_details.expertise_details
        # Guru: expertise_details tidak diperlukan, gunakan department_details
        
        {"$lookup": {"from": "teaching_assignments", "let": {"teacher_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$teacher_id", "$$teacher_id"]}}},
                {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"},
                {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise"}},
                {"$unwind": "$expertise"},
                {"$project": {"_id": 0, "subject_name": "$subject.name", "class_name": {"$concat": [{"$toString": "$class_info.grade_level"}, " ", "$expertise.abbreviation", " ", "$class_info.name"]}}}
            ], "as": "teaching_summary"}},
            
        # Hapus field-field sementara yang tidak perlu
        {"$project": {"class_details_array": 0}}
    ])
    
    # --- PERBAIKAN: Terapkan filter SETELAH semua data digabungkan ---
    filter_stage = {}
    if class_id:
        filter_stage["class_details._id"] = ObjectId(class_id)
    if grade_level:
        filter_stage["class_details.grade_level"] = grade_level
    if expertise_id:
        # Filter ini sekarang akan bekerja untuk siswa dan guru
        # Filter ini sekarang akan bekerja untuk siswa dan guru dengan logika OR
        filter_stage["$or"] = [
            {"department_details._id": ObjectId(expertise_id)},           # Untuk teacher
            {"class_details.expertise_details._id": ObjectId(expertise_id)} # Untuk student
        ]
            
    if filter_stage:
        pipeline.append({"$match": filter_stage})

    # Tahap 3: Terapkan pencarian teks
    match_stage = {}
    if search_value:
        match_stage = {"$or": [
            {"profile_details.full_name": {"$regex": search_value, "$options": "i"}},
            {"login_id": {"$regex": search_value, "$options": "i"}},
            {"email": {"$regex": search_value, "$options": "i"}},
        ]}
    
    count_pipeline = pipeline.copy()
    if match_stage: count_pipeline.append({"$match": match_stage})
    count_pipeline.append({"$count": "count"})
    records_filtered_result = await db["users"].aggregate(count_pipeline).to_list(1)
    records_filtered = records_filtered_result[0]['count'] if records_filtered_result else 0
    
    data_pipeline = pipeline.copy()
    if match_stage: data_pipeline.append({"$match": match_stage})
    data_pipeline.extend([sort_stage, {"$skip": start}, {"$limit": length}])
    data = await db["users"].aggregate(data_pipeline).to_list(length)
    
    # Dapatkan total record tanpa filter paginasi dan pencarian
    total_pipeline = pipeline.copy()
    if filter_stage:
        # Hapus filter pencarian, tapi pertahankan filter dropdown
        total_pipeline = [stage for stage in total_pipeline if "$or" not in stage.get("$match", {})]
    
    total_count_result = await db["users"].aggregate(total_pipeline + [{"$count": "count"}]).to_list(1)
    records_total = total_count_result[0]['count'] if total_count_result else 0


    return {"draw": draw, "recordsTotal": records_total, "recordsFiltered": records_filtered, "data": data}


async def update_self_data(db: AsyncIOMotorDatabase, current_user: dict, data_in: SelfDataUpdate) -> dict:
    """Memperbarui data email dan profil milik pengguna sendiri."""
    now = datetime.utcnow()
    user_id = current_user["_id"]
    profile_id = current_user["profile_id"]
    
    # 1. Update profil jika ada data
    if data_in.profile:
        profile_update_data = data_in.profile.model_dump(exclude_unset=True)
        if profile_update_data:
            profile_update_data["updated_at"] = now
            await db["profiles"].update_one({"_id": profile_id}, {"$set": profile_update_data})

    # 2. Update email di collection 'users' jika ada
    if data_in.email:
        # Pastikan email baru belum digunakan oleh orang lain
        if await db["users"].find_one({"email": data_in.email, "_id": {"$ne": user_id}}):
            raise HTTPException(status_code=400, detail="Email already registered by another user.")
        
        await db["users"].update_one(
            {"_id": user_id},
            {"$set": {"email": data_in.email, "updated_at": now}}
        )
    
    # Ambil data user terbaru setelah update
    updated_user = await get_user_by_id(db, str(user_id))
    return updated_user

async def set_user_active_status(db: AsyncIOMotorDatabase, user_id: str, is_active: bool) -> dict | None:
    """Mengubah status aktif pengguna."""
    if not ObjectId.is_valid(user_id): return None
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}}
    )
    return await get_user_by_id(db, user_id)

async def promote_students(db: AsyncIOMotorDatabase, from_grade: int, from_year: str, to_year: str) -> int:
    """Menaikkan kelas semua siswa dari satu angkatan ke angkatan berikutnya."""
    to_grade = from_grade + 1
    
    # 1. Cari semua siswa di angkatan asal
    from_classes = await db["classes"].find({"grade_level": from_grade, "academic_year": from_year}).to_list(None)
    if not from_classes: return 0
    from_class_ids = [c["_id"] for c in from_classes]
    
    students_to_promote = await db["profiles"].find({"class_id": {"$in": from_class_ids}}).to_list(None)
    if not students_to_promote: return 0

    # 2. Siapkan "peta" kelas tujuan
    to_classes_cursor = db["classes"].find({"grade_level": to_grade, "academic_year": to_year})
    to_classes_map = {f"{c['expertise_id']}_{c['name']}": c["_id"] for c in await to_classes_cursor.to_list(None)}

    # 3. Lakukan pembaruan massal
    bulk_operations = []
    for profile in students_to_promote:
        current_class = next((c for c in from_classes if c["_id"] == profile["class_id"]), None)
        if not current_class: continue
        
        # Cari kelas baru yang cocok
        new_class_key = f"{current_class['expertise_id']}_{current_class['name']}"
        new_class_id = to_classes_map.get(new_class_key)
        
        if new_class_id:
            from pymongo import UpdateOne
            bulk_operations.append(
                UpdateOne({"_id": profile["_id"]}, {"$set": {"class_id": new_class_id}})
            )

    if not bulk_operations:
        return 0
        
    result = await db["profiles"].bulk_write(bulk_operations)
    return result.modified_count

async def get_user_with_details_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    """Mengambil satu user dengan semua data gabungannya."""
    try:
        user_id_obj = ObjectId(user_id)  # Konversi string ke ObjectId
    except:
        return None
    
    pipeline = [
        {"$match": {"_id": user_id_obj}},
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        
        # --- PERBAIKAN: Lookup berantai untuk data kelas dan jurusan siswa ---
        {"$lookup": {
            "from": "classes",
            "let": { "class_id": "$profile_details.class_id" },
            "pipeline": [
                { "$match": { "$expr": { "$eq": [ "$_id", "$$class_id" ] } } },
                # Lakukan lookup ke jurusan DI DALAM sub-pipeline ini
                { "$lookup": { "from": "expertise_programs", "localField": "expertise_id", "foreignField": "_id", "as": "expertise_details"}},
                { "$unwind": { "path": "$expertise_details", "preserveNullAndEmptyArrays": True }}
            ],
            "as": "class_details_array"
        }},
        {"$unwind": {"path": "$class_details_array", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"class_details": "$class_details_array"}},

        # Lookup untuk departemen guru (tetap sama)
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
        
        # --- DIHAPUS: Field expertise_details yang unified tidak diperlukan ---
        # Siswa: expertise_details ada di class_details.expertise_details
        # Guru: expertise_details tidak diperlukan, gunakan department_details
        
        # Lookup untuk ringkasan mengajar guru (tetap sama)
        {"$lookup": {"from": "teaching_assignments", "let": {"teacher_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$teacher_id", "$$teacher_id"]}}},
                {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class_info"}},
                {"$unwind": "$class_info"},
                {"$lookup": {"from": "expertise_programs", "localField": "class_info.expertise_id", "foreignField": "_id", "as": "expertise"}},
                {"$unwind": "$expertise"},
                {"$project": {"_id": 0, "subject_name": "$subject.name", "class_name": {"$concat": [{"$toString": "$class_info.grade_level"}, " ", "$expertise.abbreviation", " ", "$class_info.name"]}}}
            ], "as": "teaching_summary"}},
            
        # Hapus field-field sementara yang tidak perlu
        {"$project": {"class_details_array": 0}}
    ]
    result = await db["users"].aggregate(pipeline).to_list(1)
    return result[0] if result else None

# Tambahkan fungsi ini ke file app/crud/crud_users.py

async def get_all_teachers_basic(db: AsyncIOMotorDatabase, search: Optional[str] = None) -> List[dict]:
    """
    Mengambil daftar guru aktif dengan hanya ID dan nama lengkap (maksimal 5 data).
    Fungsi ini efisien karena hanya mengambil data minimal yang diperlukan.
    Mendukung pencarian berdasarkan nama guru.
    """
    pipeline = [
        # Filter hanya pengguna dengan role 'teacher' dan status aktif
        {"$match": {
            "roles": "teacher",
            "is_active": True
        }},
        
        # Join dengan collection profiles untuk mendapatkan nama lengkap
        {"$lookup": {
            "from": "profiles",
            "localField": "profile_id",
            "foreignField": "_id",
            "as": "profile_details"
        }},
        {"$unwind": "$profile_details"},
    ]
    
    # Tambahkan filter pencarian jika ada search term
    if search:
        pipeline.append({
            "$match": {
                "profile_details.full_name": {"$regex": search, "$options": "i"}
            }
        })
    
    # Tambahkan projection, sorting, dan limit
    pipeline.extend([
        # Hanya ambil field yang diperlukan
        {"$project": {
            "_id": 1,
            "full_name": "$profile_details.full_name",
            "profile_picture_url": "$profile_details.profile_picture_url"
        }},
        
        # Urutkan berdasarkan nama
        {"$sort": {"full_name": 1}},
        
        # Batasi maksimal 5 data
        {"$limit": 5}
    ])
    
    teachers = await db["users"].aggregate(pipeline).to_list(5)
    return teachers

async def get_students_by_class(
    db: AsyncIOMotorDatabase, 
    class_id: str, 
    skip: int = 0, 
    limit: int = 10,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mengambil daftar siswa dalam kelas tertentu dengan data minimal.
    Mengembalikan hanya field yang diperlukan: ID, profile picture URL, 
    full name, expertise abbreviation, grade level, dan class name.
    """
    if not ObjectId.is_valid(class_id):
        return {"data": [], "total_items": 0}
    
    class_obj_id = ObjectId(class_id)
    
    # Base pipeline untuk mengambil siswa dalam kelas tertentu
    base_pipeline = [
        # Join dengan profiles untuk mendapatkan data profil siswa
        {"$lookup": {
            "from": "profiles",
            "localField": "profile_id",
            "foreignField": "_id",
            "as": "profile_details"
        }},
        {"$unwind": "$profile_details"},
        
        # Filter hanya siswa aktif dalam kelas yang diminta
        {"$match": {
            "roles": "student",
            "is_active": True,
            "profile_details.class_id": class_obj_id
        }},
        
        # Join dengan classes untuk mendapatkan data kelas
        {"$lookup": {
            "from": "classes",
            "localField": "profile_details.class_id",
            "foreignField": "_id",
            "as": "class_details"
        }},
        {"$unwind": "$class_details"},
        
        # Join dengan expertise_programs untuk mendapatkan data jurusan
        {"$lookup": {
            "from": "expertise_programs",
            "localField": "class_details.expertise_id",
            "foreignField": "_id",
            "as": "expertise_details"
        }},
        {"$unwind": "$expertise_details"},
    ]
    
    # Tambahkan filter pencarian jika ada
    if search:
        base_pipeline.append({
            "$match": {
                "profile_details.full_name": {"$regex": search, "$options": "i"}
            }
        })
    
    # Hitung total items
    count_pipeline = base_pipeline + [{"$count": "count"}]
    total_result = await db["users"].aggregate(count_pipeline).to_list(1)
    total_items = total_result[0]['count'] if total_result else 0
    
    # Pipeline untuk mengambil data dengan pagination
    data_pipeline = base_pipeline + [
        # Hanya ambil field yang diperlukan
        {"$project": {
            "_id": 1,
            "profile_picture_url": "$profile_details.profile_picture_url",
            "full_name": "$profile_details.full_name",
            "expertise_abbreviation": "$expertise_details.abbreviation",
            "grade_level": "$class_details.grade_level",
            "class_name": "$class_details.name"
        }},
        
        # Urutkan berdasarkan nama
        {"$sort": {"full_name": 1}},
        
        # Pagination
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    students = await db["users"].aggregate(data_pipeline).to_list(limit)
    
    return {
        "data": students,
        "total_items": total_items
    }

async def get_all_students_basic(db: AsyncIOMotorDatabase, search: Optional[str] = None, class_id: Optional[str] = None) -> List[dict]:
    """
    Mengambil daftar siswa aktif dengan hanya ID dan nama lengkap (maksimal 5 data).
    Fungsi ini efisien karena hanya mengambil data minimal yang diperlukan.
    Mendukung pencarian berdasarkan nama siswa dan filter berdasarkan kelas.
    """
    pipeline = [
        # Filter hanya pengguna dengan role 'student' dan status aktif
        {"$match": {
            "roles": "student",
            "is_active": True
        }},
        
        # Join dengan collection profiles untuk mendapatkan nama lengkap
        {"$lookup": {
            "from": "profiles",
            "localField": "profile_id",
            "foreignField": "_id",
            "as": "profile_details"
        }},
        {"$unwind": "$profile_details"},
    ]
    
    # Filter berdasarkan class_id jika ada
    if class_id and ObjectId.is_valid(class_id):
        pipeline.append({
            "$match": {
                "profile_details.class_id": ObjectId(class_id)
            }
        })
    
    # Tambahkan filter pencarian jika ada search term
    if search:
        pipeline.append({
            "$match": {
                "profile_details.full_name": {"$regex": search, "$options": "i"}
            }
        })
    
    # Tambahkan projection, sorting, dan limit
    pipeline.extend([
        # Hanya ambil field yang diperlukan
        {"$project": {
            "_id": 1,
            "full_name": "$profile_details.full_name",
            "profile_picture_url": "$profile_details.profile_picture_url"
        }},
        
        # Urutkan berdasarkan nama
        {"$sort": {"full_name": 1}},
        
        # Batasi maksimal 5 data
        {"$limit": 5}
    ])
    
    students = await db["users"].aggregate(pipeline).to_list(5)
    return students
