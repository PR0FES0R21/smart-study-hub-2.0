# ==============================================================================
# File: app/schemas/export.py
# Deskripsi: Skema Pydantic untuk permintaan ekspor dinamis.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel
from typing import List, Dict, Any

class ProjectionInclude(BaseModel):
    collection: str
    fields: List[str]

class Projection(BaseModel):
    base: List[str]
    includes: List[ProjectionInclude] = []

class ExportRequest(BaseModel):
    base_resource: str
    file_type: str = "xlsx"
    filters: Dict[str, Any] = {}
    projections: Projection