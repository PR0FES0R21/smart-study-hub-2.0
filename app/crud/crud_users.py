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
from app.core.cache import invalidate_cache

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

    await invalidate_cache("analytics:dashboard_stats")
    await invalidate_cache("analytics:*")
    return await db["users"].find_one({"_id": created_user_id})

async def get_users_with_profiles_for_datatables(
    db: AsyncIOMotorDatabase, 
    dt_params: Dict[str, Any],
    role: Optional[str] = None,
    grade_level: Optional[int] = None,
    expertise_id: Optional[str] = None,
    class_id: Optional[str] = None
) -> Dict[str, Any]:
    draw = int(dt_params.get('draw', 1))
    start = int(dt_params.get('start', 0))
    length = int(dt_params.get('length', 10))
    search_value = dt_params.get('search', '')

    order_column_index = int(dt_params.get('order[0][column]', 0)); order_column_dir = dt_params.get('order[0][dir]', 'asc')
    column_mapping = {0: "login_id", 1: "profile_details.full_name", 2: "email", 3: "roles"}
    sort_field = column_mapping.get(order_column_index, "login_id")
    sort_dir = 1 if order_column_dir == 'asc' else -1
    sort_stage = {"$sort": {sort_field: sort_dir}}

    pipeline = []
    
    # Tahap 0: Filter berdasarkan peran di awal
    if role: pipeline.append({"$match": {"roles": role}})
    
    # Tahap 1: Mengembalikan pipeline lookup yang sudah terbukti bekerja
    pipeline.extend([
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "classes", "localField": "profile_details.class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": {"path": "$class_details", "preserveNullAndEmptyArrays": True}},
    ])

    # --- PERBAIKAN: Menyisipkan filter dinamis di tempat yang tepat ---
    filter_stage = {}
    if class_id:
        filter_stage["class_details._id"] = ObjectId(class_id)
    else:
        if grade_level:
            filter_stage["class_details.grade_level"] = grade_level
        if expertise_id:
            filter_stage["class_details.expertise_id"] = ObjectId(expertise_id)
            
    if filter_stage:
        pipeline.append({"$match": filter_stage})
    # --- AKHIR PERBAIKAN ---

    # Lanjutkan dengan sisa pipeline yang sudah bekerja
    pipeline.extend([
        {"$lookup": {"from": "expertise_programs", "localField": "class_details.expertise_id", "foreignField": "_id", "as": "expertise_details"}},
        {"$unwind": {"path": "$expertise_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"expertise_details": {"$ifNull": ["$expertise_details", "$department_details"]}}},
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
            ], "as": "teaching_summary"}}
    ])

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
    
    records_total = await db["users"].count_documents({})

    return {"draw": draw, "recordsTotal": records_total, "recordsFiltered": records_filtered, "data": data}

async def update_user_and_profile(db: AsyncIOMotorDatabase, user_id: str, user_in: UserUpdate) -> dict | None:
    print("crud :", user_in)
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
        
    return await get_user_by_id(db, user_id)

async def delete_user_and_profile(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    user_to_delete = await get_user_by_id(db, user_id);
    if not user_to_delete: return False
    if "profile_id" in user_to_delete: await db["profiles"].delete_one({"_id": user_to_delete["profile_id"]})
    result = await db["users"].delete_one({"_id": ObjectId(user_id)})
    
    if result.deleted_count > 0:
        await invalidate_cache("analytics:dashboard_stats")
        await invalidate_cache("analytics:student_growth:*")
        await invalidate_cache("analytics:*")

    return result.deleted_count > 0

async def graduate_students_by_grade(db: AsyncIOMotorDatabase, grade_level: int) -> int:
    """Mencari semua siswa di tingkat kelas tertentu dan meluluskan mereka."""
    now = datetime.utcnow()
    
    # 1. Cari semua kelas di tingkat yang ditentukan
    target_classes = await db["classes"].find({"grade_level": grade_level}).to_list(1000)
    if not target_classes:
        return 0
    target_class_ids = [c["_id"] for c in target_classes]

    # 2. Cari semua profil siswa yang ada di kelas-kelas tersebut
    student_profiles_cursor = db["profiles"].find({"class_id": {"$in": target_class_ids}})
    student_profiles = await student_profiles_cursor.to_list(None)
    if not student_profiles:
        return 0
    
    student_user_ids = [p["user_id"] for p in student_profiles]
    student_profile_ids = [p["_id"] for p in student_profiles]

    # 3. Update collection 'users'
    user_update_result = await db["users"].update_many(
        {"_id": {"$in": student_user_ids}},
        {"$set": {"is_active": False, "roles": ["alumni"], "updated_at": now}}
    )

    # 4. Update collection 'profiles'
    await db["profiles"].update_many(
        {"_id": {"$in": student_profile_ids}},
        {"$set": {"class_id": None, "updated_at": now}}
    )

    if user_update_result.modified_count > 0:
        await invalidate_cache("analytics:*")
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

async def get_user_with_details_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    """Mengambil satu user dengan semua data gabungannya."""
    try:
        user_id_obj = ObjectId(user_id)  # Konversi string ke ObjectId
    except:
        return None
    
    pipeline = [
        {"$match": {"_id": user_id_obj}},
        # Gabungkan dengan semua data relevan, mirip dengan datatables
        {"$lookup": {"from": "profiles", "localField": "profile_id", "foreignField": "_id", "as": "profile_details"}},
        {"$unwind": {"path": "$profile_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "classes", "localField": "profile_details.class_id", "foreignField": "_id", "as": "class_details"}},
        {"$unwind": {"path": "$class_details", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "expertise_programs", "localField": "profile_details.department_id", "foreignField": "_id", "as": "department_details"}},
        {"$unwind": {"path": "$department_details", "preserveNullAndEmptyArrays": True}},
    ]
    result = await db["users"].aggregate(pipeline).to_list(1)
    return result[0] if result else None

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