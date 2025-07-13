# ==============================================================================
# File: app/schemas/task.py
# Deskripsi: Skema Pydantic untuk status background task.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel
from typing import Any, Optional

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None