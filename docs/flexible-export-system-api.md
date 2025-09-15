# Flexible Export System API Documentation

## Overview
Flexible Export System MVP memungkinkan export data dengan konfigurasi yang fleksibel dari berbagai collection dalam database. Sistem ini mendukung filtering, joining, dan export ke berbagai format (Excel, CSV, JSON).

## Base URL
```
/api/v1/exports
```

## Authentication
Semua endpoint membutuhkan authentication. Gunakan Bearer token di header:
```
Authorization: Bearer <your_access_token>
```

## Core Concepts

### 1. Export Configuration
Export configuration adalah JSON object yang mendefinisikan:
- Collection utama yang akan di-export
- Fields yang ingin disertakan
- Filters untuk memfilter data
- Joins ke collection lain
- Sorting dan pagination

### 2. Security & Permissions
- Sistem menggunakan role-based access control
- Setiap collection memiliki allowed fields dan sensitive fields
- Admin memiliki akses ke semua fields, teacher terbatas
- Joins hanya diperbolehkan ke collection yang whitelisted

### 3. Export Formats
- `excel`: Excel spreadsheet (.xlsx) 
- `csv`: Comma-separated values (.csv)
- `json`: JSON format (.json)

## API Endpoints

### GET /collections
Mengambil daftar collection yang tersedia untuk export.

**Response:**
```json
{
  "collections": [
    {
      "name": "users",
      "display_name": "Users",
      "description": "Data from users collection",
      "available_fields": ["_id", "username", "email", "roles"],
      "sensitive_fields": ["hashed_password"],
      "joinable_collections": ["profiles", "exam_sessions"],
      "common_filters": ["roles", "is_active", "created_at"]
    }
  ]
}
```

### GET /formats
Mengambil daftar format export yang didukung.

**Response:**
```json
{
  "supported_formats": ["excel", "csv", "json"],
  "descriptions": {
    "excel": "Excel spreadsheet (.xlsx)",
    "csv": "Comma-separated values (.csv)",
    "json": "JSON format (.json)"
  }
}
```

### POST /validate
Validasi konfigurasi export sebelum eksekusi.

**Request Body:**
```json
{
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
        "fields": ["full_name", "birth_date"],
        "join_type": "unwind"
      }
    ],
    "sort": {"username": 1},
    "limit": 1000
  }
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Large export (>5000 records) may impact performance"],
  "estimated_records": 150,
  "required_permissions": []
}
```

### POST /execute
Eksekusi export data berdasarkan konfigurasi.

**Request Body:**
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email", "is_active"],
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
        "fields": ["full_name", "class_id"],
        "join_type": "unwind"
      }
    ],
    "sort": {"username": 1},
    "limit": 500
  },
  "format": "excel",
  "filename": "students_export",
  "async_export": false
}
```

**Response (Sync):**
```json
{
  "success": true,
  "message": "Export completed successfully. 150 records exported.",
  "file_url": "/api/v1/exports/download/students_export_20240312_143022.xlsx",
  "record_count": 150,
  "estimated_file_size": "25.3 KB"
}
```

**Response (Async):**
```json
{
  "success": true,
  "message": "Export started. Check status using task_id.",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### GET /status/{task_id}
Mengambil status export yang sedang berjalan (untuk async export).

**Response:**
```json
{
  "status": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "processing",
    "progress": 75,
    "message": "Exporting 500 records...",
    "file_url": null,
    "created_at": "2024-03-12T14:30:22Z",
    "completed_at": null,
    "error_details": null
  }
}
```

**Status Values:**
- `pending`: Task belum dimulai
- `processing`: Sedang diproses
- `completed`: Selesai dengan sukses
- `failed`: Gagal dengan error

### GET /download/{filename}
Download file hasil export.

**Response:** File binary dengan appropriate headers.

## Quick Export Endpoints

### POST /quick/students
Quick export untuk data siswa.

**Query Parameters:**
- `format`: Format export (excel, csv, json)
- `grade_level`: Filter berdasarkan tingkat kelas (optional)

**Response:** Same as `/execute`

### POST /quick/exam-results  
Quick export untuk hasil ujian.

**Query Parameters:**
- `format`: Format export (excel, csv, json) 
- `exam_id`: Filter berdasarkan exam ID (optional)

**Response:** Same as `/execute`

## Data Models

### FilterCondition
```json
{
  "field": "string",
  "operator": "eq|ne|gt|gte|lt|lte|in|nin|regex|exists",
  "value": "any",
  "options": "string (optional, for regex)"
}
```

### JoinConfig
```json
{
  "collection": "string",
  "local_field": "string", 
  "foreign_field": "string",
  "fields": ["string"],
  "filters": [FilterCondition],
  "alias": "string (optional)",
  "join_type": "lookup|unwind"
}
```

### ExportConfig
```json
{
  "main_collection": "string",
  "fields": ["string"],
  "filters": [FilterCondition],
  "joins": [JoinConfig],
  "sort": {"field": 1|-1},
  "limit": "integer (1-10000)",
  "skip": "integer (>=0)"
}
```

## Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `{"field": "roles", "operator": "eq", "value": "student"}` |
| `ne` | Not equal | `{"field": "is_active", "operator": "ne", "value": false}` |
| `gt` | Greater than | `{"field": "score", "operator": "gt", "value": 80}` |
| `gte` | Greater than equal | `{"field": "created_at", "operator": "gte", "value": "2024-01-01"}` |
| `lt` | Less than | `{"field": "age", "operator": "lt", "value": 25}` |
| `lte` | Less than equal | `{"field": "score", "operator": "lte", "value": 100}` |
| `in` | In array | `{"field": "grade_level", "operator": "in", "value": [10, 11, 12]}` |
| `nin` | Not in array | `{"field": "status", "operator": "nin", "value": ["deleted", "suspended"]}` |
| `regex` | Regex match | `{"field": "name", "operator": "regex", "value": "^John", "options": "i"}` |
| `exists` | Field exists | `{"field": "phone", "operator": "exists", "value": true}` |

## JavaScript Examples

### 1. Get Available Collections
```javascript
async function getAvailableCollections() {
  const response = await fetch('/api/v1/exports/collections', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return await response.json();
}
```

### 2. Validate Export Config
```javascript
async function validateExportConfig(config) {
  const response = await fetch('/api/v1/exports/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ config })
  });
  return await response.json();
}
```

### 3. Execute Export (Sync)
```javascript
async function exportData(config, format = 'excel', filename = null) {
  const response = await fetch('/api/v1/exports/execute', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      config,
      format,
      filename,
      async_export: false
    })
  });
  
  const result = await response.json();
  
  if (result.success && result.file_url) {
    // Download file
    window.open(result.file_url, '_blank');
  }
  
  return result;
}
```

### 4. Execute Export (Async)
```javascript
async function exportDataAsync(config, format = 'excel') {
  const response = await fetch('/api/v1/exports/execute', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      config,
      format,
      async_export: true
    })
  });
  
  const result = await response.json();
  
  if (result.task_id) {
    return pollExportStatus(result.task_id);
  }
  
  return result;
}

async function pollExportStatus(taskId) {
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/v1/exports/status/${taskId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await response.json();
        
        if (result.status.status === 'completed') {
          resolve(result);
        } else if (result.status.status === 'failed') {
          reject(new Error(result.status.error_details));
        } else {
          // Still processing, check again in 2 seconds
          setTimeout(checkStatus, 2000);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    checkStatus();
  });
}
```

### 5. Quick Student Export
```javascript
async function exportStudents(gradeLevel = null, format = 'excel') {
  const params = new URLSearchParams({ format });
  if (gradeLevel) params.append('grade_level', gradeLevel);
  
  const response = await fetch(`/api/v1/exports/quick/students?${params}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
}
```

## Common Use Cases & Examples

### 1. Export Student Data with Grades
```json
{
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
      "fields": ["full_name", "birth_date"],
      "join_type": "unwind"
    },
    {
      "collection": "exam_sessions",
      "local_field": "_id",
      "foreign_field": "student_id",
      "fields": ["score", "exam_id"],
      "filters": [
        {
          "field": "status",
          "operator": "eq",
          "value": "graded"
        }
      ]
    }
  ],
  "sort": {"profiles.full_name": 1}
}
```

### 2. Export Teachers with Subjects
```json
{
  "main_collection": "users",
  "fields": ["username", "email"],
  "filters": [
    {
      "field": "roles",
      "operator": "eq",
      "value": "teacher"
    }
  ],
  "joins": [
    {
      "collection": "profiles", 
      "local_field": "profile_id",
      "foreign_field": "_id",
      "fields": ["full_name"],
      "join_type": "unwind"
    },
    {
      "collection": "teaching_assignments",
      "local_field": "_id",
      "foreign_field": "teacher_id",
      "fields": ["subject_id", "class_id"]
    },
    {
      "collection": "subjects",
      "local_field": "teaching_assignments.subject_id", 
      "foreign_field": "_id",
      "fields": ["name", "code"],
      "join_type": "unwind"
    }
  ]
}
```

### 3. Export Exam Results for Specific Exam
```json
{
  "main_collection": "exam_sessions",
  "fields": ["score", "started_at", "submitted_at"],
  "filters": [
    {
      "field": "exam_id",
      "operator": "eq",
      "value": "6450a1234567890abcdef123"
    },
    {
      "field": "status", 
      "operator": "eq",
      "value": "graded"
    }
  ],
  "joins": [
    {
      "collection": "users",
      "local_field": "student_id",
      "foreign_field": "_id",
      "fields": ["username"],
      "join_type": "unwind" 
    },
    {
      "collection": "profiles",
      "local_field": "users.profile_id",
      "foreign_field": "_id", 
      "fields": ["full_name"],
      "join_type": "unwind"
    }
  ],
  "sort": {"score": -1}
}
```

## Error Handling

### Common Error Responses
```json
{
  "detail": "Invalid export configuration: Collection 'invalid_collection' not allowed"
}
```

```json
{
  "detail": "Export format 'pdf' is not supported"
}
```

```json
{
  "detail": "No data found matching the criteria"
}
```

### Frontend Error Handling
```javascript
async function handleExportError(error) {
  if (error.status === 400) {
    // Validation error
    showError('Invalid export configuration: ' + error.detail);
  } else if (error.status === 403) {
    // Permission error
    showError('You do not have permission to access this data');
  } else if (error.status === 404) {
    // No data found
    showError('No data found matching your criteria');
  } else {
    // General error
    showError('Export failed. Please try again.');
  }
}
```

## Performance Considerations

### When to Use Async Export
- Export > 1000 records
- Complex joins (> 3 collections)
- Large aggregation pipelines
- Heavy processing expected

### Optimization Tips
- Use specific fields instead of exporting all
- Apply filters to reduce data volume  
- Use appropriate limits
- Consider pagination for very large datasets
- Use indexes on filtered fields

## Security Notes

### Access Control
- Only collections in whitelist are accessible
- Sensitive fields require admin role
- Joins are restricted to allowed collections
- User can only access data based on their role

### Best Practices
- Always validate export config before execution
- Handle file cleanup appropriately
- Monitor export usage and performance
- Implement rate limiting if necessary
- Secure file download endpoints

## Support & Troubleshooting

### Common Issues
1. **"Collection not allowed"**: Collection not in security whitelist
2. **"Join not allowed"**: Trying to join to non-whitelisted collection  
3. **"Field not allowed"**: Accessing field not in allowed list
4. **"No data found"**: Filters too restrictive or no matching data

### Debug Steps
1. Use `/validate` endpoint to check config
2. Check user roles and permissions
3. Verify collection and field names
4. Test with simpler configuration first
5. Check server logs for detailed errors

This completes the MVP documentation for the Flexible Export System. The system provides powerful and secure data export capabilities while maintaining proper access control and performance considerations.
