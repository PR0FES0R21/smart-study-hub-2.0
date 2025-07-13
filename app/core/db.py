# ==============================================================================
# File: app/core/db.py
# Deskripsi: Mengelola koneksi ke database (MongoDB) dan cache (Redis).
# ==============================================================================
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# --- Koneksi MongoDB ---
# Membuat satu instance client yang akan digunakan kembali
db_client = AsyncIOMotorClient(settings.DATABASE_URL)
# Mendapatkan objek database dari client
db = db_client[settings.DATABASE_NAME]

# --- Koneksi Redis ---
# Membuat satu instance client redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def close_db_connection():
    """Menutup koneksi MongoDB saat aplikasi berhenti."""
    db_client.close()
    print("Koneksi MongoDB ditutup.")

async def close_redis_connection():
    """Menutup koneksi Redis saat aplikasi berhenti."""
    await redis_client.close()
    print("Koneksi Redis ditutup.")