# ==============================================================================
# File: app/schemas/pagination.py
# Deskripsi: Skema Pydantic generik untuk respons berpaginasi.
# --- DITAMBAHKAN ---
# ==============================================================================
from pydantic import BaseModel
from typing import List, TypeVar, Generic

DataType = TypeVar('DataType')

class PaginatedResponse(BaseModel, Generic[DataType]):
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    data: List[DataType]