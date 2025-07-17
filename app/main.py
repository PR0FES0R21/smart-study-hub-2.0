# ==============================================================================
# File: app/main.py
# --- DIUBAH ---
# ==============================================================================
from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.db import close_db_connection, close_redis_connection
from .api.v1.api import api_router
from .core import r2_setup
from .middleware.onboarding import OnboardingMiddleware
from .core.startup_tasks import initialize_active_period_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Memulai aplikasi: {settings.PROJECT_NAME}")
    await initialize_active_period_cache()
    yield
    print("Mematikan aplikasi...")
    await close_db_connection()
    await close_redis_connection()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(OnboardingMiddleware)

@app.get("/")
def read_root(): return {"message": f"Selamat datang di {settings.PROJECT_NAME}"}

app.include_router(api_router, prefix=settings.API_V1_STR)