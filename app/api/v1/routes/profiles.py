# ==============================================================================
# File: app/api/v1/routes/profiles.py
# --- DIUBAH TOTAL --- (Menggunakan Cloudflare R2)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import uuid

from app.api.v1 import deps
from app.crud import crud_users
from app.schemas.profile import ProfilePublic
from app.core.db import db
from app.core.r2_setup import s3_client
from app.core.config import settings

router = APIRouter()

@router.post("/me/upload-picture", response_model=ProfilePublic)
async def upload_own_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(deps.get_current_active_user)
):
    """
    Mengunggah foto profil baru ke R2, menghapus yang lama.
    """
    profile_id = current_user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=404, detail="Profile not found for this user.")

    # Cek tipe file
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image type. Only JPEG, PNG, and WebP are allowed.")

    try:
        # 1. Dapatkan kunci objek lama dari profil saat ini
        current_profile = await db["profiles"].find_one({"_id": profile_id})
        old_object_key = current_profile.get("profile_picture_key")

        # 2. Hapus gambar lama di R2 jika ada
        if old_object_key:
            try:
                s3_client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=old_object_key)
                print(f"Old profile picture deleted from R2: {old_object_key}")
            except Exception as e:
                print(f"Could not delete old R2 object: {e}")

        # 3. Buat nama file baru yang unik
        file_extension = file.filename.split('.')[-1]
        new_object_key = f"profiles/{uuid.uuid4()}.{file_extension}"

        # 4. Unggah file baru ke R2
        s3_client.upload_fileobj(
            file.file,
            settings.R2_BUCKET_NAME,
            new_object_key,
            ExtraArgs={'ContentType': file.content_type}
        )
        
        # 5. Buat URL publik
        image_url = f"{settings.R2_PUBLIC_URL}/{new_object_key}"

        # 6. Simpan URL dan kunci objek baru ke database
        await crud_users.update_profile_picture(db, profile_id=profile_id, image_url=image_url, object_key=new_object_key)
        
        # 7. Ambil data profil terbaru untuk dikembalikan
        updated_profile = await db["profiles"].find_one({"_id": profile_id})
        return updated_profile

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during file upload: {str(e)}")
