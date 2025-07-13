# ==============================================================================
# File: app/api/v1/routes/academic_actions.py
# Deskripsi: Endpoint untuk aksi akademik massal seperti kelulusan.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1 import deps
from app.crud import crud_users

router = APIRouter()

@router.post("/graduate-students/{grade_level}", status_code=status.HTTP_200_OK)
async def graduate_students_route(
    grade_level: int,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Meluluskan semua siswa di tingkat kelas tertentu.
    Ini akan mengubah status mereka menjadi tidak aktif, peran menjadi alumni,
    dan menghapus referensi kelas mereka.
    """
    if grade_level not in [12]: # Biasanya hanya kelas 12 yang diluluskan
        raise HTTPException(status_code=400, detail="Graduation can only be processed for grade 12.")

    graduated_count = await crud_users.graduate_students_by_grade(db, grade_level)
    
    return {"message": f"Successfully graduated {graduated_count} students from grade {grade_level}."}
