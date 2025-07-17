# ==============================================================================
# File: app/core/logging.py
# Deskripsi: Helper terpusat untuk membuat log aktivitas.
# --- DIUBAH --- (Dibuat lebih robust untuk menangani user anonim)
# ==============================================================================
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from user_agents import parse
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from app.crud import crud_activity_logs
from .websocket import manager

async def create_activity_log(
    db: AsyncIOMotorDatabase,
    request: Request,
    user_data: Dict[str, Any],
    activity: str,
    description: str,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None
):
    """
    Helper untuk membuat dan menyimpan log aktivitas di background.
    Secara otomatis mengambil IP dan info perangkat dari request.
    """
    user_agent_string = request.headers.get("user-agent", "unknown")
    user_agent = parse(user_agent_string)

    full_name = "Anonymous"
    user_id = user_data.get("_id")

    if user_id and str(user_id) != "ANONYMOUS" and ObjectId.is_valid(str(user_id)):
        profile = await db["profiles"].find_one({"user_id": user_id})
        if profile:
            full_name = profile.get("full_name", "N/A")
    else:
        full_name = f"Attempted: {user_data.get('login_id', 'Unknown')}"

    log_data = {
        "user_data": {
            "user_id": str(user_id),
            "full_name": full_name,
            "user_roles": user_data.get("roles", [])
        },
        "activity": activity,
        "description": description,
        "ip_address": request.client.host,
        "device_info": {
            "device_type": "desktop" if user_agent.is_pc else "mobile" if user_agent.is_mobile else "tablet" if user_agent.is_tablet else "other",
            "os_name": user_agent.os.family,
            "os_version": user_agent.os.version_string,
            "browser_name": user_agent.browser.family,
            "browser_version": user_agent.browser.version_string,
            "user_agent": user_agent_string
        },
        "status": status,
        "details": details or {}
    }

    await crud_activity_logs.create_log(db, log_data)
    
    ws_message = {
        "type": "new_activity_log",
        "data": {
            "full_name": full_name,
            "description": description,
            "browser_name": user_agent.browser.family,
            "timestamp": datetime.utcnow().isoformat(),
            "device_type": "desktop" if user_agent.is_pc else "mobile" if user_agent.is_mobile else "tablet" if user_agent.is_tablet else "other" 
        }
    }
    
    # --- PERBAIKAN: Memanggil fungsi broadcast yang benar ---
    await manager.broadcast_to_roles(ws_message, target_roles=["admin"])
    
    print(f"Activity logged and broadcasted: {activity} by {user_data.get('login_id') or 'Anonymous'}")
