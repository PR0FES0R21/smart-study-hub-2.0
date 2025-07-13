# ==============================================================================
# File: app/core/r2_setup.py
# Deskripsi: Inisialisasi klien untuk Cloudflare R2.
# --- DITAMBAHKAN --- (Menggantikan cloudinary_setup.py)
# ==============================================================================
import boto3
from .config import settings

# R2 kompatibel dengan API S3, jadi kita menggunakan boto3
s3_client = boto3.client(
    service_name='s3',
    endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    region_name="auto", # atau region spesifik jika perlu
)