# ==============================================================================
# File: app/middleware/onboarding.py
# Deskripsi: Middleware untuk memeriksa status onboarding pengguna.
# --- DIUBAH ---
# ==============================================================================
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import status, HTTPException
import re
from typing import Callable, Awaitable

from app.api.v1.deps import get_current_user
from app.core.db import db

class OnboardingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        # Daftar path yang dikecualikan dari pemeriksaan onboarding
        excluded_paths = [
            r"/api/v1/auth/login",
            r"/docs",
            r"/openapi.json",
            r"/api/v1/users/me/change-password",
            r"/api/v1/profiles/me" 
        ]

        # Cek jika path saat ini ada di daftar pengecualian
        if any(re.match(path, request.url.path) for path in excluded_paths):
            return await call_next(request)

        # Coba dapatkan pengguna dari cookie
        access_token = request.cookies.get("access_token")
        if not access_token:
            return await call_next(request) # Lanjutkan jika tidak ada token

        try:
            user = await get_current_user(access_token=access_token, db=db)
            if user and not user.get("onboarding_completed"):
                # Jika onboarding belum selesai, tolak permintaan
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Onboarding required. Please complete your profile and change your password."}
                )
        except HTTPException:
            # Abaikan jika token tidak valid, biarkan proteksi endpoint yang menanganinya
            pass

        response = await call_next(request)
        return response