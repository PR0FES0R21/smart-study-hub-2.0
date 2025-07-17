# ==============================================================================
# File: app/core/startup_tasks.py
# Deskripsi: Berisi tugas-tugas yang dijalankan saat aplikasi pertama kali hidup.
# --- DITAMBAHKAN ---
# ==============================================================================
from .db import db
from .cache import get_cache, set_cache
from app.crud import crud_academic_periods

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
