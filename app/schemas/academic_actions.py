# ==============================================================================
# File: app/schemas/academic_actions.py
# Deskripsi: Skema Pydantic untuk Aksi Akademik.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel
from typing import List

class AcademicYearRequest(BaseModel):
    current_academic_year: str # Contoh: "2024/2025"
    next_academic_year: str    # Contoh: "2025/2026"

class PromoteStudentsRequest(BaseModel):
    from_grade_level: int # Contoh: 10
    from_academic_year: str # Contoh: "2024/2025"
    to_academic_year: str   # Contoh: "2025/2026"