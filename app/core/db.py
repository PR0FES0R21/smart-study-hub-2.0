# ==============================================================================
# File: app/core/db.py
# Deskripsi: Mengelola koneksi ke database (MongoDB) dan cache (Redis).
# ==============================================================================
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# --- Koneksi MongoDB ---
# Membuat satu instance client yang akan digunakan kembali
from motor.motor_asyncio import AsyncIOMotorClient

db_client = AsyncIOMotorClient(
    settings.DATABASE_URL,
    # Connection Pool Settings
    maxPoolSize=50,           # Max 50 koneksi aktif (sesuaikan dengan load)
    minPoolSize=10,           # Min 10 koneksi standby
    maxIdleTimeMS=30000,      # Tutup koneksi idle setelah 30 detik
    waitQueueTimeoutMS=5000,  # Timeout antrian 5 detik
    # Server Selection
    serverSelectionTimeoutMS=3000,  # Timeout server selection 3 detik
    connectTimeoutMS=3000,          # Timeout koneksi 3 detik
    socketTimeoutMS=10000,          # Timeout socket 10 detik
    # Read/Write Concerns
    retryWrites=True,
    retryReads=True,
    # Compression (opsional, bisa hemat bandwidth)
    compressors="snappy,zlib"
)
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