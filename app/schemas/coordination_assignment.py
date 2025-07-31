# ==============================================================================
# File: app/schemas/coordination_assignment.py
# Deskripsi: Skema Pydantic untuk Penunjukan Koordinator.
# --- UPDATED WITH FULL SCHEMAS + BULK OPERATIONS ---
# ==============================================================================
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from .base import PyObjectId

class CoordinationAssignmentBase(BaseModel):
    subject_id: PyObjectId
    grade_level: int = Field(..., ge=1, le=12, description="Grade level 1-12")
    coordinator_id: PyObjectId

class CoordinationAssignmentCreate(CoordinationAssignmentBase):
    pass

class CoordinationAssignmentUpdate(BaseModel):
    subject_id: Optional[PyObjectId] = None
    grade_level: Optional[int] = Field(None, ge=1, le=12, description="Grade level 1-12")
    coordinator_id: Optional[PyObjectId] = None

class CoordinationAssignmentPublic(CoordinationAssignmentBase):
    id: PyObjectId = Field(alias="_id")
    academic_period_id: PyObjectId
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class BulkCoordinationOperation(BaseModel):
    type: Literal["create", "update", "delete"]
    id: Optional[str] = None  # Required for update/delete operations
    data: Optional[Dict[str, Any]] = None  # Required for create/update operations
    
    @validator('id')
    def validate_id_for_operations(cls, v, values):
        operation_type = values.get('type')
        if operation_type in ['update', 'delete'] and not v:
            raise ValueError(f'{operation_type} operation requires id')
        return v
    
    @validator('data')
    def validate_data_for_operations(cls, v, values):
        operation_type = values.get('type')
        if operation_type in ['create', 'update'] and not v:
            raise ValueError(f'{operation_type} operation requires data')
        return v

class BulkCoordinationRequest(BaseModel):
    operations: List[BulkCoordinationOperation]
    academic_period_id: Optional[PyObjectId] = None  # If not provided, use current active period

class BulkCoordinationResponse(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[Dict[str, Any]]
    processed_operations: List[Dict[str, Any]]

class CoordinationAssignmentFilter(BaseModel):
    academic_period_id: Optional[PyObjectId] = None
    subject_id: Optional[PyObjectId] = None
    grade_level: Optional[int] = Field(None, ge=1, le=12)
    coordinator_id: Optional[PyObjectId] = None

# WebSocket message schemas for real-time updates
class BulkProgressMessage(BaseModel):
    type: Literal["bulk_progress"]
    progress: Dict[str, Any]
    
class BulkCompleteMessage(BaseModel):
    type: Literal["bulk_complete"]
    results: BulkCoordinationResponse

class AvailableCoordinatorResponse(BaseModel):
    # Coordinator info
    coordinator_id: str
    coordinator_name: str
    coordinator_email: str
    coordinator_phone: Optional[str] = None
    
    # Coordination assignment info
    coordination_assignment_id: str
    subject_id: str
    subject_name: str
    subject_code: str
    grade_level: int
    
    # Context info - kenapa user bisa submit ke koordinator ini
    matching_reason: str  # "same_subject_grade" 
    user_classes_in_subject: List[str]  # Kelas yang diajar user untuk subject+grade ini
    coordinator_responsible_for: str  # "Koordinator Bahasa Indonesia Kelas 10"
    
    # Stats info (optional, bisa berguna)
    total_teachers_under_coordination: Optional[int] = None
    
    class Config:
        from_attributes = True
