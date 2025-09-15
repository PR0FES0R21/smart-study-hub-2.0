# ==============================================================================
# File: app/schemas/export.py
# Deskripsi: Schema untuk flexible export system
# ==============================================================================
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class ExportFormat(str, Enum):
    EXCEL = "excel"
    CSV = "csv" 
    JSON = "json"
    PDF = "pdf"

class FilterOperator(str, Enum):
    EQ = "eq"           # equal
    NE = "ne"           # not equal
    GT = "gt"           # greater than
    GTE = "gte"         # greater than equal
    LT = "lt"           # less than
    LTE = "lte"         # less than equal
    IN = "in"           # in array
    NIN = "nin"         # not in array
    REGEX = "regex"     # regex match
    EXISTS = "exists"   # field exists

class FilterCondition(BaseModel):
    field: str
    operator: FilterOperator
    value: Any
    options: Optional[str] = None  # untuk regex options seperti "i" (case insensitive)

class JoinConfig(BaseModel):
    collection: str = Field(..., description="Collection name to join")
    local_field: str = Field(..., description="Field in main collection")
    foreign_field: str = Field(..., description="Field in joined collection")
    fields: List[str] = Field(default=[], description="Fields to include from joined collection")
    filters: List[FilterCondition] = Field(default=[], description="Filters to apply on joined collection")
    alias: Optional[str] = Field(None, description="Alias for joined data")
    join_type: Literal["lookup", "unwind"] = Field(default="lookup", description="Type of join")

class ExportConfig(BaseModel):
    main_collection: str = Field(..., description="Primary collection to export from")
    fields: List[str] = Field(default=[], description="Fields to include from main collection")
    filters: List[FilterCondition] = Field(default=[], description="Filters for main collection")
    joins: List[JoinConfig] = Field(default=[], description="Collections to join")
    sort: Dict[str, int] = Field(default={}, description="Sort configuration (field: 1/-1)")
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Maximum records to export")
    skip: Optional[int] = Field(0, ge=0, description="Records to skip")
    
    @validator('main_collection')
    def validate_main_collection(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('main_collection must be a non-empty string')
        return v

class ExportRequest(BaseModel):
    config: ExportConfig
    format: ExportFormat = Field(default=ExportFormat.EXCEL)
    filename: Optional[str] = Field(None, description="Custom filename for export")
    async_export: bool = Field(False, description="Whether to process export asynchronously")
    
    @validator('filename')
    def validate_filename(cls, v, values):
        if v and not v.replace('_', '').replace('-', '').replace(' ', '').replace('.', '').isalnum():
            # Basic filename validation - only allow alphanumeric, underscore, hyphen, space, dot
            raise ValueError('filename contains invalid characters')
        return v

class ExportTemplate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    config: ExportConfig
    created_by: str = Field(..., description="User who created the template")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = Field(False, description="Whether template is public")
    tags: List[str] = Field(default=[], description="Tags for categorization")

class AvailableCollection(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    available_fields: List[str]
    sensitive_fields: List[str] = Field(default=[], description="Fields requiring higher permissions")
    joinable_collections: List[str] = Field(default=[], description="Collections that can be joined")
    common_filters: List[str] = Field(default=[], description="Commonly used filter fields")

class ExportStatus(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: Optional[int] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None

class ExportResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None  # for async exports
    file_url: Optional[str] = None  # for sync exports
    record_count: Optional[int] = None
    estimated_file_size: Optional[str] = None

class ValidateConfigRequest(BaseModel):
    config: ExportConfig

class ValidateConfigResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default=[])
    warnings: List[str] = Field(default=[])
    estimated_records: Optional[int] = None
    required_permissions: List[str] = Field(default=[])

# Response models for API
class AvailableCollectionsResponse(BaseModel):
    collections: List[AvailableCollection]

class ExportTemplatesResponse(BaseModel):
    templates: List[ExportTemplate]
    total_count: int

class ExportStatusResponse(BaseModel):
    status: ExportStatus

# Configuration models for system setup
class CollectionPermission(BaseModel):
    name: str
    allowed_fields: List[str]
    sensitive_fields: List[str] = Field(default=[])
    allowed_joins: List[str] = Field(default=[])
    allowed_filters: List[str] = Field(default=[])
    required_roles: List[str] = Field(default=[], description="Roles required to access this collection")

class ExportSystemConfig(BaseModel):
    max_records_per_export: int = Field(default=10000)
    max_file_size_mb: int = Field(default=50)
    async_threshold_records: int = Field(default=1000, description="Records count to force async processing")
    allowed_formats: List[ExportFormat] = Field(default=[ExportFormat.EXCEL, ExportFormat.CSV, ExportFormat.JSON])
    file_retention_days: int = Field(default=7, description="Days to keep export files")
    rate_limit_per_user: int = Field(default=10, description="Max exports per user per hour")
