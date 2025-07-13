# ==============================================================================
# File: app/schemas/activity_log.py
# Deskripsi: Skema Pydantic untuk log aktivitas.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import PyObjectId

class LogUserData(BaseModel):
    user_id: str
    full_name: str
    user_roles: List[str]

class LogDeviceInfo(BaseModel):
    device_type: str
    os_name: str
    os_version: str
    browser_name: str
    browser_version: str
    user_agent: str

class ActivityLogBase(BaseModel):
    user_data: LogUserData
    activity: str
    description: str
    ip_address: str
    device_info: LogDeviceInfo
    status: str
    details: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ActivityLogPublic(ActivityLogBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True