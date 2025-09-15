# Flexible Export System - Testing Payloads

## Base URL & Authentication
```
Base URL: http://localhost:8000/api/v1/exports
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

## 1. GET /collections
**Purpose:** Get available collections for current user

### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/exports/collections" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Expected Response
```json
{
  "collections": [
    {
      "name": "users",
      "display_name": "Users",
      "available_fields": ["_id", "username", "email", "roles"],
      "sensitive_fields": ["hashed_password"],
      "joinable_collections": ["profiles", "exam_sessions"],
      "common_filters": ["roles", "is_active"]
    }
  ]
}
```

## 2. GET /formats
**Purpose:** Get supported export formats

### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/exports/formats" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Expected Response
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

## 3. POST /validate
**Purpose:** Validate export configuration before execution

### Payload 1: Basic Student Export Validation
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
        "fields": ["full_name", "birth_date", "gender"],
        "join_type": "unwind"
      }
    ],
    "sort": {"username": 1},
    "limit": 100
  }
}
```

### Payload 2: Complex Multi-Join Validation
```json
{
  "config": {
    "main_collection": "exam_sessions",
    "fields": ["score", "status", "started_at", "submitted_at"],
    "filters": [
      {
        "field": "status",
        "operator": "eq",
        "value": "graded"
      },
      {
        "field": "score",
        "operator": "gte",
        "value": 70
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
      },
      {
        "collection": "exams",
        "local_field": "exam_id",
        "foreign_field": "_id",
        "fields": ["title", "exam_type"],
        "join_type": "unwind"
      }
    ],
    "sort": {"score": -1},
    "limit": 500
  }
}
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/exports/validate" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "main_collection": "users",
      "fields": ["username", "email"],
      "filters": [{"field": "roles", "operator": "eq", "value": "student"}],
      "limit": 100
    }
  }'
```

### Expected Response
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "estimated_records": 150,
  "required_permissions": []
}
```

## 4. POST /execute
**Purpose:** Execute export with various configurations

### Payload 1: Basic Student Export (Sync)
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email", "is_active", "created_at"],
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
        "fields": ["full_name", "birth_date", "gender", "class_id"],
        "join_type": "unwind"
      },
      {
        "collection": "classes",
        "local_field": "profiles.class_id",
        "foreign_field": "_id",
        "fields": ["name", "grade_level"],
        "join_type": "unwind"
      }
    ],
    "sort": {"profiles.full_name": 1},
    "limit": 50
  },
  "format": "excel",
  "filename": "students_export_test",
  "async_export": false
}
```

### Payload 2: Teacher Data Export
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email", "is_active"],
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
    ],
    "sort": {"profiles.full_name": 1},
    "limit": 25
  },
  "format": "csv",
  "filename": "teachers_export_test",
  "async_export": false
}
```

### Payload 3: Exam Results Export
```json
{
  "config": {
    "main_collection": "exam_sessions",
    "fields": ["score", "status", "started_at", "submitted_at", "time_spent_minutes"],
    "filters": [
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
      },
      {
        "collection": "exams",
        "local_field": "exam_id",
        "foreign_field": "_id",
        "fields": ["title", "exam_type"],
        "join_type": "unwind"
      }
    ],
    "sort": {"score": -1},
    "limit": 100
  },
  "format": "json",
  "filename": "exam_results_test",
  "async_export": false
}
```

### Payload 4: Async Export (Large Dataset)
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
        "fields": ["full_name"],
        "join_type": "unwind"
      }
    ],
    "limit": 2000
  },
  "format": "excel",
  "filename": "large_export_test",
  "async_export": true
}
```

### Payload 5: Advanced Filtering
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email", "created_at"],
    "filters": [
      {
        "field": "roles",
        "operator": "eq",
        "value": "student"
      },
      {
        "field": "is_active",
        "operator": "eq",
        "value": true
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
        "fields": ["full_name", "class_id"],
        "join_type": "unwind"
      },
      {
        "collection": "classes",
        "local_field": "profiles.class_id",
        "foreign_field": "_id",
        "fields": ["name", "grade_level"],
        "join_type": "unwind",
        "filters": [
          {
            "field": "grade_level",
            "operator": "in",
            "value": [10, 11, 12]
          }
        ]
      }
    ],
    "sort": {"created_at": -1},
    "limit": 200
  },
  "format": "excel",
  "filename": "filtered_students_test"
}
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/exports/execute" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "main_collection": "users",
      "fields": ["username", "email"],
      "filters": [{"field": "roles", "operator": "eq", "value": "student"}],
      "limit": 10
    },
    "format": "excel",
    "filename": "test_export"
  }'
```

### Expected Response (Sync)
```json
{
  "success": true,
  "message": "Export completed successfully. 50 records exported.",
  "file_url": "/api/v1/exports/download/students_export_test_20241201_143022.xlsx",
  "record_count": 50,
  "estimated_file_size": "15.2 KB"
}
```

### Expected Response (Async)
```json
{
  "success": true,
  "message": "Export started. Check status using task_id.",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## 5. GET /status/{task_id}
**Purpose:** Check async export status

### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/exports/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Expected Responses

#### Processing
```json
{
  "status": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "processing",
    "progress": 75,
    "message": "Exporting 2000 records...",
    "file_url": null,
    "created_at": "2024-12-01T14:30:22Z",
    "completed_at": null,
    "error_details": null
  }
}
```

#### Completed
```json
{
  "status": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "completed",
    "progress": 100,
    "message": "Export completed. 2000 records exported.",
    "file_url": "/api/v1/exports/download/large_export_test_20241201_143525.xlsx",
    "created_at": "2024-12-01T14:30:22Z",
    "completed_at": "2024-12-01T14:35:25Z",
    "error_details": null
  }
}
```

## 6. GET /download/{filename}
**Purpose:** Download exported file

### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/exports/download/students_export_test_20241201_143022.xlsx" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -o "downloaded_export.xlsx"
```

## 7. POST /quick/students
**Purpose:** Quick student export with simple parameters

### Query Parameters Test 1: All Students Excel
```bash
curl -X POST "http://localhost:8000/api/v1/exports/quick/students?format=excel" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Query Parameters Test 2: Grade 10 Students CSV
```bash
curl -X POST "http://localhost:8000/api/v1/exports/quick/students?format=csv&grade_level=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Query Parameters Test 3: Grade 12 Students JSON
```bash
curl -X POST "http://localhost:8000/api/v1/exports/quick/students?format=json&grade_level=12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 8. POST /quick/exam-results
**Purpose:** Quick exam results export

### Query Parameters Test 1: All Exam Results
```bash
curl -X POST "http://localhost:8000/api/v1/exports/quick/exam-results?format=excel" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Query Parameters Test 2: Specific Exam Results
```bash
curl -X POST "http://localhost:8000/api/v1/exports/quick/exam-results?format=csv&exam_id=6450a1234567890abcdef123" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Error Testing Payloads

### 1. Invalid Collection
```json
{
  "config": {
    "main_collection": "invalid_collection",
    "fields": ["field1", "field2"]
  },
  "format": "excel"
}
```

### 2. Invalid Fields
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["invalid_field", "another_invalid_field"],
    "filters": [{"field": "roles", "operator": "eq", "value": "student"}]
  },
  "format": "excel"
}
```

### 3. Invalid Join
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username"],
    "joins": [
      {
        "collection": "invalid_collection",
        "local_field": "profile_id",
        "foreign_field": "_id",
        "fields": ["full_name"]
      }
    ]
  },
  "format": "excel"
}
```

### 4. Sensitive Fields (Non-Admin)
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "hashed_password"],
    "filters": [{"field": "roles", "operator": "eq", "value": "student"}]
  },
  "format": "excel"
}
```

### 5. Invalid Format
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email"]
  },
  "format": "pdf"
}
```

## Complete Testing Script (PowerShell)

```powershell
# Set your token and base URL
$token = "YOUR_ACCESS_TOKEN_HERE"
$baseUrl = "http://localhost:8000/api/v1/exports"
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Test 1: Get Collections
Write-Host "Testing GET /collections..."
$response1 = Invoke-RestMethod -Uri "$baseUrl/collections" -Headers $headers -Method Get
Write-Host "Collections found:" $response1.collections.Count

# Test 2: Get Formats
Write-Host "Testing GET /formats..."
$response2 = Invoke-RestMethod -Uri "$baseUrl/formats" -Headers $headers -Method Get
Write-Host "Supported formats:" ($response2.supported_formats -join ", ")

# Test 3: Validate Config
Write-Host "Testing POST /validate..."
$validatePayload = @{
    config = @{
        main_collection = "users"
        fields = @("username", "email")
        filters = @(@{
            field = "roles"
            operator = "eq"
            value = "student"
        })
        limit = 10
    }
} | ConvertTo-Json -Depth 10

$response3 = Invoke-RestMethod -Uri "$baseUrl/validate" -Headers $headers -Method Post -Body $validatePayload
Write-Host "Validation result:" $response3.valid

# Test 4: Execute Export
Write-Host "Testing POST /execute..."
$executePayload = @{
    config = @{
        main_collection = "users"
        fields = @("username", "email")
        filters = @(@{
            field = "roles"
            operator = "eq"
            value = "student"
        })
        limit = 5
    }
    format = "json"
    filename = "test_export"
} | ConvertTo-Json -Depth 10

$response4 = Invoke-RestMethod -Uri "$baseUrl/execute" -Headers $headers -Method Post -Body $executePayload
Write-Host "Export result:" $response4.success

# Test 5: Quick Student Export
Write-Host "Testing POST /quick/students..."
$response5 = Invoke-RestMethod -Uri "$baseUrl/quick/students?format=json&grade_level=10" -Headers $headers -Method Post
Write-Host "Quick export result:" $response5.success

Write-Host "All tests completed!"
```

## Testing Checklist

### ✅ Basic Functionality
- [ ] GET /collections returns available collections
- [ ] GET /formats returns supported formats
- [ ] POST /validate works with valid config
- [ ] POST /execute creates export file successfully
- [ ] GET /download serves file correctly

### ✅ Security Testing  
- [ ] Invalid collections are rejected
- [ ] Invalid fields are rejected
- [ ] Sensitive fields require admin role
- [ ] Invalid joins are rejected
- [ ] File download path traversal protection

### ✅ Performance Testing
- [ ] Small exports (< 100 records) work sync
- [ ] Large exports (> 1000 records) go async
- [ ] Status tracking works for async exports
- [ ] File cleanup works properly

### ✅ Format Testing
- [ ] Excel export creates proper .xlsx file
- [ ] CSV export creates proper .csv file  
- [ ] JSON export creates proper .json file
- [ ] Files can be opened/read correctly

### ✅ Error Handling
- [ ] Invalid payloads return proper errors
- [ ] Missing authentication returns 401
- [ ] Invalid permissions return 403
- [ ] No data found returns 404
- [ ] Server errors return 500

## Tips for Testing

1. **Start Simple**: Test dengan payload paling basic dulu
2. **Check Logs**: Monitor server logs untuk debug
3. **File Verification**: Download dan buka file hasil export
4. **Security Testing**: Test dengan user yang berbeda role
5. **Performance**: Test dengan dataset yang berbeda ukuran
6. **Error Cases**: Test semua error scenarios

Dengan testing payloads ini, kamu bisa memastikan semua functionality export system bekerja dengan baik! 🚀
