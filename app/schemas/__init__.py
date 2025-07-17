# ==============================================================================
# File: app/schemas/__init__.py
# Deskripsi: Mengimpor model dan merebuild referensi untuk mengatasi circular import.
# --- DIPERBAIKI ---
# ==============================================================================

# Import semua model yang diperlukan
from .user import (
    UserBase, UserCreate, UserUpdate, UserInDB, 
    UserPublic, UserWithDetails, DataTablesUserResponse
)
from .classes import (
    ClassBase, ClassCreate, ClassUpdate, 
    ClassPublic, ClassWithDetails
)
from .teaching_assignment import TeachingAssignmentWithDetails
from .question_bank import QuestionBankPublic
from .exam import ExamPublic, ExamWithDetails
from .exam_session import ExamSessionPublic
from .analytics import StudentCountByMajor, StudentGrowthDataPoint

# Rebuild model untuk menyelesaikan forward references
# Ini harus dilakukan setelah semua model diimpor
UserWithDetails.model_rebuild()
ClassWithDetails.model_rebuild()
TeachingAssignmentWithDetails.model_rebuild()
QuestionBankPublic.model_rebuild()
ExamPublic.model_rebuild()
ExamSessionPublic.model_rebuild()
ExamWithDetails.model_rebuild()

# Export semua model agar bisa digunakan dengan mudah
__all__ = [
    # User models
    "UserBase", "UserCreate", "UserUpdate", "UserInDB",
    "UserPublic", "UserWithDetails", "DataTablesUserResponse",
    
    # Class models
    "ClassBase", "ClassCreate", "ClassUpdate",
    "ClassPublic", "ClassWithDetails",
]