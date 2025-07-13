# ==============================================================================
# File: app/schemas/base.py
# --- DIUBAH --- (Perbaikan PyObjectId yang Profesional)
# ==============================================================================
from pydantic import BaseModel, EmailStr, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Any, List, Optional
from bson import ObjectId
from datetime import datetime


class PyObjectId(ObjectId):
    """
    Tipe kustom untuk ObjectId MongoDB yang bekerja dengan benar di Pydantic v2.
    - Memvalidasi string atau ObjectId sebagai input.
    - Serialisasi menjadi string HANYA saat membuat JSON (misalnya, untuk respons API).
    - Mempertahankan tipe ObjectId saat menggunakan mode Python (misalnya, untuk menyimpan ke DB).
    """
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        
        def validate_from_str(v: str) -> ObjectId:
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return ObjectId(v)

        # Skema untuk validasi: menerima string atau instance ObjectId
        python_schema = core_schema.union_schema(
            [
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(validate_from_str)
                ])
            ]
        )
        
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=python_schema,
            # Serialisasi ke string HANYA saat mode 'json' (bukan 'python')
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: str(instance), when_used='json'
            ),
        )
    

# ==============================================================================
# Schemas untuk Collection: `users` & `profiles`
# ==============================================================================

# --- Users ---
class UserBase(BaseModel):
    login_id: str = Field(..., description="NIS untuk siswa, NKTAM untuk guru/admin.")
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    roles: List[str] = []

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None

class UserInDB(UserBase):
    hashed_password: str

class UserPublic(UserBase):
    id: PyObjectId = Field(alias="_id")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

# --- Profiles (akan digabungkan dengan User untuk MVP, tapi ini desainnya) ---
# Untuk saat ini, kita akan gabungkan field-field penting ke User.
# Jika aplikasi berkembang, memisahkan Profile adalah langkah yang baik.

# ==============================================================================
# Schemas untuk Collection: `academic_periods`
# ==============================================================================
class AcademicPeriodBase(BaseModel):
    year: str
    semester: str # "ganjil" atau "genap"
    status: str # "planning", "active", "archived"
    start_date: datetime
    end_date: datetime

class AcademicPeriodCreate(AcademicPeriodBase):
    pass

class AcademicPeriodUpdate(BaseModel):
    year: Optional[str] = None
    semester: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class AcademicPeriodPublic(AcademicPeriodBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# ==============================================================================
# Schemas untuk Collection: `expertise_programs` (Jurusan)
# ==============================================================================
class ExpertiseProgramBase(BaseModel):
    name: str
    abbreviation: str
    description: Optional[str] = None
    head_of_department_id: Optional[PyObjectId] = None # Ref: users

class ExpertiseProgramCreate(ExpertiseProgramBase):
    pass

class ExpertiseProgramUpdate(BaseModel):
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    description: Optional[str] = None
    head_of_department_id: Optional[PyObjectId] = None

class ExpertiseProgramPublic(ExpertiseProgramBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# ==============================================================================
# Schemas untuk Collection: `subjects` (Mata Pelajaran)
# ==============================================================================
class SubjectBase(BaseModel):
    name: str
    code: str

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class SubjectPublic(SubjectBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# ==============================================================================
# Schemas untuk Collection: `classes`
# ==============================================================================
class ClassBase(BaseModel):
    grade_level: int # 10, 11, 12
    expertise_id: PyObjectId # Ref: expertise_programs
    name: str # "1", "2", "A", "B"
    academic_year: str
    homeroom_teacher_id: Optional[PyObjectId] = None # Ref: users

class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    grade_level: Optional[int] = None
    expertise_id: Optional[PyObjectId] = None
    name: Optional[str] = None
    academic_year: Optional[str] = None
    homeroom_teacher_id: Optional[PyObjectId] = None

class ClassPublic(ClassBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# ==============================================================================
# Schemas untuk Collection: `teaching_assignments`
# ==============================================================================
class TeachingAssignmentBase(BaseModel):
    academic_period_id: PyObjectId # Ref: academic_periods
    class_id: PyObjectId # Ref: classes
    subject_id: PyObjectId # Ref: subjects
    teacher_id: PyObjectId # Ref: users

class TeachingAssignmentCreate(TeachingAssignmentBase):
    pass

class TeachingAssignmentUpdate(BaseModel):
    academic_period_id: Optional[PyObjectId] = None
    class_id: Optional[PyObjectId] = None
    subject_id: Optional[PyObjectId] = None
    teacher_id: Optional[PyObjectId] = None

class TeachingAssignmentPublic(TeachingAssignmentBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# ==============================================================================
# Schemas untuk Collection: `question_banks`
# ==============================================================================
class QuestionOption(BaseModel):
    text: str
    is_correct: bool

class QuestionBankBase(BaseModel):
    subject_id: PyObjectId # Ref: subjects
    created_by_teacher_id: PyObjectId # Ref: users
    question_type: str # "multiple_choice", "essay"
    difficulty: str # "easy", "medium", "hard"
    question_text: str
    options: Optional[List[QuestionOption]] = None
    points: int
    tags: Optional[List[str]] = []

class QuestionBankCreate(QuestionBankBase):
    pass

class QuestionBankUpdate(BaseModel):
    # Semua field opsional untuk update
    subject_id: Optional[PyObjectId] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[QuestionOption]] = None
    points: Optional[int] = None
    tags: Optional[List[str]] = None

class QuestionBankPublic(QuestionBankBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True

# ==============================================================================
# Schemas untuk Collection: `exams`
# ==============================================================================
class ExamSettings(BaseModel):
    shuffle_questions: bool = False
    shuffle_options: bool = False
    show_results_after_submission: bool = False
    tab_switch_detection: bool = True
    fullscreen_enforcement: bool = True

class ExamBase(BaseModel):
    title: str
    teaching_assignment_id: PyObjectId # Ref: teaching_assignments
    exam_type: str # "multiple_choice", "essay", "mixed"
    instructions: Optional[str] = None
    duration_minutes: int
    availability_start_time: datetime
    availability_end_time: datetime
    status: str # "draft", "published", "ongoing", "completed"
    question_ids: List[PyObjectId] = [] # Ref: question_banks
    settings: ExamSettings = Field(default_factory=ExamSettings)

class ExamCreate(ExamBase):
    pass

class ExamUpdate(BaseModel):
    # Semua field opsional untuk update
    title: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = None
    availability_start_time: Optional[datetime] = None
    availability_end_time: Optional[datetime] = None
    status: Optional[str] = None
    question_ids: Optional[List[PyObjectId]] = None
    settings: Optional[ExamSettings] = None

class ExamPublic(ExamBase):
    id: PyObjectId = Field(alias="_id")
    class Config: from_attributes = True; arbitrary_types_allowed = True
