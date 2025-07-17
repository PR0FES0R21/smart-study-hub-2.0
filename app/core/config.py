# ==============================================================================
# File: app/core/config.py
# Deskripsi: Mengelola semua konfigurasi aplikasi menggunakan Pydantic.
# Membaca variabel dari file .env.
# ==============================================================================
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str
    API_V1_STR: str
    
    # Konfigurasi MongoDB
    DATABASE_URL: str
    DATABASE_NAME: str

    # Konfigurasi Redis
    REDIS_URL: str

    # Kunci Rahasia untuk JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300000

    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str
    R2_PUBLIC_URL: str

    class Config:
        env_file = ".env.example"
        env_file_encoding = 'utf-8'

# Membuat satu instance dari Settings yang akan digunakan di seluruh aplikasi
settings = Settings()