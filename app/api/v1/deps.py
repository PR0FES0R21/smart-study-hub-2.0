# ==============================================================================
# File: app/api/v1/deps.py
# --- DIUBAH TOTAL --- (Beralih ke Bearer Token)
# ==============================================================================
from fastapi import Depends, HTTPException, status, WebSocket, Path, Query
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.config import settings
from app.core import security
from app.core.db import db
from app.schemas.token import TokenData
from app.crud import crud_users, crud_exams, crud_academic_periods
from app.core.cache import get_cache, set_cache


# Skema OAuth2, menunjuk ke endpoint login untuk dokumentasi
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_database() -> AsyncIOMotorDatabase: return db

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """
    Mendekode token JWT dari header Authorization dan mendapatkan data user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = await crud_users.get_user_by_id(db, user_id=token_data.user_id)
    if user is None: raise credentials_exception
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_active"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_user_for_ws(
    websocket: WebSocket,
    token: str | None = Query(None), # <-- Baca token dari query parameter
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """Dependency khusus untuk otentikasi koneksi WebSocket."""
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise JWTError("No user_id in token")
        user = await crud_users.get_user_by_id(db, user_id=user_id)
        if not user or not user.get("is_active"): raise JWTError("User not found or inactive")
        return user
    except (JWTError, HTTPException):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None

async def get_exam_room_participant(
    websocket: WebSocket,
    exam_id: str = Path(...),
    user: dict = Depends(get_current_user_for_ws),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    # ... (logika otorisasi ruangan tidak berubah) ...
    if not user: return None
    exam = await crud_exams.get_exam_by_id(db, exam_id)
    if not exam: await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Exam not found"); return None
    user_id = user["_id"]; participant_role = None
    proctor_ids_as_str = [str(p_id) for p_id in exam.get("proctor_ids", [])]
    if str(user_id) in proctor_ids_as_str: participant_role = "proctor"
    else:
        assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
        if assignment:
            profile = await db["profiles"].find_one({"user_id": user_id})
            if profile and str(profile.get("class_id")) == str(assignment.get("class_id")): participant_role = "student"
    if not participant_role: await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized"); return None
    user["participant_role"] = participant_role
    return user

async def get_current_active_teacher(current_user: dict = Depends(get_current_active_user)) -> dict:
    if "teacher" not in current_user.get("roles", []): raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user

async def get_current_active_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    if "admin" not in current_user.get("roles", []): raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user

async def get_current_academic_period(db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
    """
    Dependency 'pintar' untuk mendapatkan periode akademik aktif.
    Menggunakan cache untuk performa maksimal.
    """
    cached_period = await get_cache(crud_academic_periods.ACADEMIC_PERIOD_ACTIVE_CACHE_KEY)
    if cached_period:
        print("HIT: Mengambil periode akademik aktif dari cache.")
        return cached_period
    
    print("MISS: Mengambil periode akademik aktif dari database.")
    active_period = await crud_academic_periods.get_active_period(db)
    
    if not active_period:
        raise HTTPException(status_code=503, detail="Tidak ada periode akademik yang aktif. Silakan hubungi administrator.")
    
    # Simpan ke cache tanpa TTL (persisten) sebelum mengembalikan
    await set_cache(crud_academic_periods.ACADEMIC_PERIOD_ACTIVE_CACHE_KEY, active_period)
    
    return active_period