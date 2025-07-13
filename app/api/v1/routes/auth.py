# ==============================================================================
# File: app/api/v1/routes/auth.py
# --- DIUBAH --- (Menambahkan logging untuk percobaan login yang gagal)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import timedelta

from app.core.config import settings
from app.core import security
from app.crud import crud_users
from app.api.v1 import deps
from app.core.logging import create_activity_log

router = APIRouter()

@router.post("/login")
async def login_for_access_token(
    response: Response,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(deps.get_database), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Login user, set cookie, dan mencatat aktivitas di background.
    """
    user = await crud_users.get_user_by_login_id(db, login_id=form_data.username)
    
    # --- PERBAIKAN: Logika untuk menangani login gagal ---
    if not user or not security.verify_password(form_data.password, user["hashed_password"]):
        # Buat data log untuk percobaan yang gagal
        log_user_data = user if user else {
            "_id": "ANONYMOUS",
            "login_id": form_data.username,
            "roles": ["anonymous"]
        }
        background_tasks.add_task(
            create_activity_log,
            db=db,
            request=request,
            user_data=log_user_data,
            activity="USER_LOGIN_FAILED",
            description=f"Failed login attempt for user '{form_data.username}'.",
            status="FAILED",
            details={"method": "POST", "endpoint": "/api/v1/auth/login"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Login ID or password",
        )
    
    # --- Logika untuk login sukses (tidak berubah) ---
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    background_tasks.add_task(
        create_activity_log,
        db=db,
        request=request,
        user_data=user,
        activity="USER_LOGIN",
        description=f"User '{user['login_id']}' logged in successfully.",
        details={"method": "POST", "endpoint": "/api/v1/auth/login"}
    )
    
    return {"message": "Login successful"}