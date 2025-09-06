# ==============================================================================
# File: app/main.py (Updated untuk existing structure)
# Deskripsi: Update existing main.py dengan WebSocket Redis bridge support
# ==============================================================================
from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
import logging

from .core.config import settings
from .core.db import close_db_connection, close_redis_connection
from .api.v1.api import api_router
from .core import r2_setup
from .middleware.onboarding import OnboardingMiddleware
from .core.startup_tasks import initialize_active_period_cache, create_default_admin

# Import WebSocket components
from .core.websocket import manager
from .core.redis_websocket import redis_bridge
import sys

# Setup logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log")
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with WebSocket Redis bridge support."""
    
    # STARTUP
    logger.info(f"Memulai aplikasi: {settings.PROJECT_NAME}")
    
    try:
        # Existing startup tasks
        await initialize_active_period_cache()
        await create_default_admin()
        
        # Initialize WebSocket Redis bridge
        logger.info("Menginisialisasi WebSocket Redis bridge...")
        await manager.initialize()
        logger.info("WebSocket Redis bridge berhasil diinisialisasi")
        
    except Exception as e:
        logger.error(f"❌ Error saat startup: {e}")
        raise
    
    logger.info("Startup aplikasi berhasil")
    
    # YIELD (application runs here)
    yield
    
    # SHUTDOWN
    logger.info("Mematikan aplikasi...")
    
    try:
        # Close WebSocket manager
        logger.info("Menutup WebSocket manager...")
        await manager.shutdown()
        
        # Close WebSocket Redis bridge
        logger.info("Menutup WebSocket Redis bridge...")
        await redis_bridge.close()
        logger.info("WebSocket Redis bridge ditutup")
        
        # Existing shutdown tasks
        await close_db_connection()
        await close_redis_connection()
        
    except Exception as e:
        logger.error(f"❌ Error saat shutdown: {e}")
    
    logger.info("Aplikasi berhasil dimatikan")

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
def read_root(): 
    return {
        "message": f"Selamat datang di {settings.PROJECT_NAME}",
        "websocket_status": "enabled with Redis bridge"
    }

# Health check endpoint untuk WebSocket
@app.get("/health/websocket")
async def websocket_health():
    """Health check endpoint untuk WebSocket connections."""
    try:
        stats = await manager.get_connection_stats()
        return {
            "status": "healthy",
            "redis_bridge": "connected",
            "connections": stats
        }
    except Exception as e:
        logger.error(f"WebSocket health check gagal: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

app.include_router(api_router, prefix=settings.API_V1_STR)