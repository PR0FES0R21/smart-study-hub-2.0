# ==============================================================================
# File: app/schemas/admin_export.py
# Deskripsi: Enhanced schemas untuk admin export dengan nested joins
# ==============================================================================
from typing import Dict, List, Set, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from app.schemas.export import FilterOperator, ExportFormat

class AdvancedFilterCondition(BaseModel):
    """Enhanced filter condition dengan semua operator support"""
    field: str = Field(..., description="Field name to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(..., description="Filter value")
    options: Optional[str] = Field(None, description="Additional options for regex operator")
    
    class Config:
        schema_extra = {
            "example": {
                "field": "grade_level",
                "operator": "in",
                "value": [10, 11, 12]
            }
        }

class AdvancedJoinConfig(BaseModel):
    """Advanced join configuration dengan nested join support"""
    collection: str = Field(..., description="Target collection name")
    local_field: str = Field(..., description="Local field for join")
    foreign_field: str = Field(..., description="Foreign field for join")
    alias: Optional[str] = Field(None, description="Alias for joined collection")
    join_type: str = Field("lookup", description="Type of join: lookup, unwind")
    
    # Field selection
    fields: Optional[List[str]] = Field(None, description="Fields to include from joined collection")
    exclude_fields: Optional[List[str]] = Field(None, description="Fields to exclude from joined collection")
    
    # Filtering pada joined collection
    filters: Optional[List[AdvancedFilterCondition]] = Field(None, description="Filters for joined collection")
    
    # NESTED JOINS - Ini yang bikin powerful!
    joins: Optional[List['AdvancedJoinConfig']] = Field(None, description="Nested joins from this collection")
    
    # Performance options
    preserve_null_and_empty_arrays: bool = Field(True, description="Preserve documents without join matches")
    limit: Optional[int] = Field(None, description="Limit results from this join")
    sort: Optional[Dict[str, int]] = Field(None, description="Sort joined results")
    
    class Config:
        schema_extra = {
            "example": {
                "collection": "profiles",
                "local_field": "profile_id",
                "foreign_field": "_id",
                "fields": ["full_name", "gender", "class_id"],
                "join_type": "unwind",
                "filters": [
                    {
                        "field": "gender",
                        "operator": "eq",
                        "value": "M"
                    }
                ],
                "joins": [
                    {
                        "collection": "classes",
                        "local_field": "class_id",
                        "foreign_field": "_id",
                        "fields": ["name", "grade_level"],
                        "filters": [
                            {
                                "field": "grade_level",
                                "operator": "gte",
                                "value": 10
                            }
                        ]
                    }
                ]
            }
        }

# Enable recursive model
AdvancedJoinConfig.model_rebuild()

class AdvancedExportConfig(BaseModel):
    """Advanced export configuration untuk admin dengan unlimited power"""
    main_collection: str = Field(..., description="Main collection to export from")
    
    # Field selection dari main collection
    fields: Optional[List[str]] = Field(None, description="Fields to include from main collection")
    exclude_fields: Optional[List[str]] = Field(None, description="Fields to exclude from main collection")
    
    # Advanced filtering dengan semua operators
    filters: Optional[List[AdvancedFilterCondition]] = Field(None, description="Filters for main collection")
    
    # Nested joins - unlimited depth!
    joins: Optional[List[AdvancedJoinConfig]] = Field(None, description="Join configurations with nested support")
    
    # Aggregation options
    group_by: Optional[List[str]] = Field(None, description="Group by fields")
    having: Optional[List[AdvancedFilterCondition]] = Field(None, description="Having conditions after grouping")
    
    # Result options
    sort: Optional[Dict[str, int]] = Field(None, description="Sort configuration")
    skip: Optional[int] = Field(None, description="Number of documents to skip")
    limit: Optional[int] = Field(None, description="Maximum number of documents to return")
    
    # Performance hints
    allow_disk_use: bool = Field(True, description="Allow using disk for large operations")
    max_time_ms: Optional[int] = Field(None, description="Maximum execution time in milliseconds")
    
    class Config:
        schema_extra = {
            "example": {
                "main_collection": "users",
                "fields": ["username", "email", "roles"],
                "filters": [
                    {
                        "field": "roles",
                        "operator": "eq",
                        "value": "student"
                    },
                    {
                        "field": "created_at",
                        "operator": "gte",
                        "value": "2024-01-01"
                    }
                ],
                "joins": [
                    {
                        "collection": "profiles",
                        "local_field": "profile_id",
                        "foreign_field": "_id",
                        "fields": ["full_name", "gender"],
                        "joins": [
                            {
                                "collection": "classes",
                                "local_field": "class_id",
                                "foreign_field": "_id",
                                "fields": ["name", "grade_level"],
                                "filters": [
                                    {
                                        "field": "grade_level",
                                        "operator": "in",
                                        "value": [10, 11, 12]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "sort": {"username": 1},
                "limit": 1000
            }
        }

class AdvancedExportRequest(BaseModel):
    """Request schema untuk advanced export"""
    config: AdvancedExportConfig = Field(..., description="Advanced export configuration")
    format: ExportFormat = Field(ExportFormat.EXCEL, description="Export format")
    filename: Optional[str] = Field(None, description="Custom filename")
    async_export: bool = Field(False, description="Process export asynchronously")
    
    # Advanced options
    explain: bool = Field(False, description="Return query execution plan instead of executing")
    dry_run: bool = Field(False, description="Validate and estimate without executing")
    
    class Config:
        schema_extra = {
            "example": {
                "config": {
                    "main_collection": "users",
                    "fields": ["username", "email"],
                    "filters": [
                        {
                            "field": "roles",
                            "operator": "eq", 
                            "value": "student"
                        }
                    ],
                    "joins": [
                        {
                            "collection": "profiles",
                            "local_field": "profile_id",
                            "foreign_field": "_id",
                            "fields": ["full_name"],
                            "joins": [
                                {
                                    "collection": "classes",
                                    "local_field": "class_id",
                                    "foreign_field": "_id",
                                    "fields": ["name", "grade_level"]
                                }
                            ]
                        }
                    ],
                    "limit": 100
                },
                "format": "excel",
                "filename": "advanced_student_export"
            }
        }

class AdvancedValidateRequest(BaseModel):
    """Request untuk validasi advanced export config"""
    config: AdvancedExportConfig = Field(..., description="Advanced export configuration to validate")

class AdvancedExportResponse(BaseModel):
    """Response schema untuk advanced export"""
    success: bool = Field(..., description="Export success status")
    message: str = Field(..., description="Response message")
    
    # Export details
    task_id: Optional[str] = Field(None, description="Task ID for async exports")
    file_url: Optional[str] = Field(None, description="Download URL for completed exports")
    record_count: Optional[int] = Field(None, description="Number of records exported")
    
    # Performance info
    execution_time_ms: Optional[int] = Field(None, description="Query execution time in milliseconds")
    estimated_file_size: Optional[str] = Field(None, description="Estimated file size")
    pipeline_stages: Optional[int] = Field(None, description="Number of aggregation pipeline stages")
    
    # Query info (for explain mode)
    execution_plan: Optional[Dict[str, Any]] = Field(None, description="MongoDB execution plan")
    estimated_records: Optional[int] = Field(None, description="Estimated number of records")
    warnings: Optional[List[str]] = Field(None, description="Performance or complexity warnings")

class AdvancedValidateResponse(BaseModel):
    """Response schema untuk advanced export validation"""
    valid: bool = Field(..., description="Validation status")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Structure analysis
    estimated_records: Optional[int] = Field(None, description="Estimated number of records")
    pipeline_complexity: Optional[str] = Field(None, description="Pipeline complexity level")
    estimated_execution_time: Optional[str] = Field(None, description="Estimated execution time")
    
    # Join analysis
    total_joins: Optional[int] = Field(None, description="Total number of joins")
    max_join_depth: Optional[int] = Field(None, description="Maximum join depth")
    collections_involved: Optional[List[str]] = Field(None, description="All collections involved in query")

# Utility types
class JoinPath(BaseModel):
    """Represents a join path for analysis"""
    collections: List[str] = Field(..., description="Collections in the join path")
    depth: int = Field(..., description="Join depth")
    estimated_cost: Optional[float] = Field(None, description="Estimated query cost")

class QueryComplexity(str, Enum):
    """Query complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
