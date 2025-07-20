# ==============================================================================
# File: app/core/startup_tasks.py
# Deskripsi: Berisi tugas-tugas yang dijalankan saat aplikasi pertama kali hidup.
# --- DITAMBAHKAN ---
# ==============================================================================
from .db import db
from .cache import get_cache, set_cache
from app.crud import crud_academic_periods
from app.crud import crud_academic_periods, crud_users
from app.schemas.user import UserCreate, ProfileCreate

async def initialize_active_period_cache():
    """
    Memeriksa dan mengisi cache untuk periode akademik aktif saat startup.
    Ini adalah mekanisme "self-healing" jika cache Redis kosong.
    """
    print("Memeriksa cache periode akademik aktif saat startup...")
    
    cache_key = crud_academic_periods.ACADEMIC_PERIOD_ACTIVE_CACHE_KEY
    
    # 1. Cek apakah cache sudah ada
    cached_period = await get_cache(cache_key)
    if cached_period:
        print("Cache periode akademik aktif sudah ada. Tidak ada tindakan yang diperlukan.")
        return

    # 2. Jika cache kosong, coba ambil dari database
    print("Cache kosong. Mencari periode akademik aktif di database...")
    active_period_from_db = await crud_academic_periods.get_active_period(db)

    if active_period_from_db:
        # 3. Jika ditemukan di DB, simpan ke cache
        await set_cache(cache_key, active_period_from_db)
        print(f"Periode aktif '{active_period_from_db['year']} - {active_period_from_db['semester']}' berhasil disimpan ke cache.")
    else:
        # 4. Jika tidak ada di DB, tidak apa-apa. Admin harus mengaturnya nanti.
        print("Tidak ada periode akademik aktif yang ditemukan di database.")

async def create_default_admin():
    """
    Memeriksa dan membuat user admin default jika belum ada.
    """
    print("Memeriksa keberadaan admin default...")
    
    # Data admin default
    default_login_id = "79111953"
    default_email = "user@example.com"
    
    # 1. Cek apakah admin sudah ada
    admin_exists = await crud_users.get_user_by_login_id(db, default_login_id)
    if admin_exists:
        print("Admin default sudah ada di database.")
        return

    # 2. Jika belum ada, buat user baru
    print("Admin default tidak ditemukan. Membuat user baru...")
    try:
        profile_data = ProfileCreate(
            full_name="sayoga pratama",
            gender="Laki Laki",
            birth_place="Padang ratu",
            address="Jl.merpati raya sawah baru",
            phone_number="09889778774",
            department_id="6867dbec901358f21c53d9e8" # Ganti dengan ID Jurusan default jika perlu
        )
        
        user_data = UserCreate(
            login_id=default_login_id,
            email=default_email,
            password=default_login_id, # Menggunakan login_id sebagai password awal
            roles=["admin", "teacher"],
            profile=profile_data
        )
        
        await crud_users.create_user_and_profile(db, user_data)
        print(f"Admin default berhasil dibuat dengan login_id: {default_login_id}")
    except Exception as e:
        print(f"Gagal membuat admin default: {e}")