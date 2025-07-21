# ==============================================================================
# File: create_first_admin.py
# Deskripsi: Script untuk membuat user admin pertama kali.
# Jalankan dari direktori utama proyek: python create_first_admin.py
# --- DIUBAH --- (Logika disesuaikan dengan login_id)
# ==============================================================================
import asyncio
import getpass
from motor.motor_asyncio import AsyncIOMotorDatabase

# Kita perlu setup path agar bisa mengimpor dari folder 'app'
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import db, close_db_connection
from app.core.security import get_password_hash
from app.crud.crud_users import get_user_by_login_id

async def create_admin(db: AsyncIOMotorDatabase):
    """Fungsi utama untuk membuat admin."""
    print("--- Membuat User Admin Pertama ---")
    
    # --- DIUBAH --- Meminta NKTAM sebagai Login ID
    login_id = input("Masukkan NKTAM untuk admin (ini akan menjadi ID Login): ")
    email = input("Masukkan email untuk admin: ")
    full_name = input("Masukkan nama lengkap admin: ")
    
    # Menggunakan getpass agar password tidak terlihat saat diketik
    password = getpass.getpass("Masukkan password untuk admin: ")
    password_confirm = getpass.getpass("Konfirmasi password: ")

    if password != password_confirm:
        print("\n[ERROR] Password tidak cocok. Silakan coba lagi.")
        return

    # Periksa apakah user sudah ada
    existing_user = await get_user_by_login_id(db, login_id)
    if existing_user:
        print(f"\n[ERROR] User dengan Login ID '{login_id}' sudah ada di database.")
        return

    # Buat objek user untuk disimpan
    admin_user_data = {
        "login_id": login_id,
        "email": email,
        "full_name": full_name,
        "hashed_password": get_password_hash(password),
        "is_active": True,
        "roles": ["admin"] # Menambahkan peran 'admin'
    }

    # Simpan ke database
    result = await db["users"].insert_one(admin_user_data)
    print(f"\n[SUCCESS] User admin berhasil dibuat dengan ID: {result.inserted_id}")


async def main():
    """Fungsi pembungkus untuk menjalankan proses dan menutup koneksi."""
    await create_admin(db)
    await close_db_connection()


if __name__ == "__main__":
    # Menjalankan fungsi async utama
    asyncio.run(main())
