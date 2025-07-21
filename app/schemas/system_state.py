# ==============================================================================
# File: app/schemas/system_state.py
# Deskripsi: Skema Pydantic untuk "Papan Pengumuman" status sistem.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class SystemTaskState(BaseModel):
    task_name: str
    status: str = "idle" # idle, processing, completed, failed
    current_step: str = "Menunggu"
    progress: int = 0 # Persentase 0-100
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    error_details: Optional[str] = None