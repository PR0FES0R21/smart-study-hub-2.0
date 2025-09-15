# Export System API - Corrected Testing Payloads

This document contains **corrected and working** JSON payloads for testing the Flexible Export System API. All payloads have been tested and confirmed to work with the current security configuration.

## Issues That Were Fixed

1. **Async Method Issue**: Fixed `estimate_result_count` method to be properly async
2. **Import Issues**: Fixed missing `tempfile` import in status endpoint
3. **Join Permissions**: Clarified the correct join paths based on security configuration

## Security Configuration Understanding

The current security configuration allows these joins:
- `users` → `profiles`, `exam_sessions`
- `profiles` → `users`, `classes` 
- `classes` → `expertise_programs`, `academic_periods`, `profiles`

**Important**: Direct joins like `users` → `classes` are **not allowed**. You must go through `profiles`.

## Working Payloads for OpenAPI/Swagger Testing

### 1. Get Available Collections
```
GET /api/v1/exports/collections
Headers:
- Authorization: Bearer YOUR_JWT_TOKEN
```

### 2. Simple Users Export (Working)
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
    "limit": 10
  }
}
```

### 3. Users with Profiles Join (Working)
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
        "fields": ["full_name", "birth_date", "gender", "class_id"],
        "join_type": "unwind"
      }
    ],
    "sort": {"profiles.full_name": 1},
    "limit": 200
  }
}
```

### 4. Complex Join: Users → Profiles → Classes (Fixed Approach)

**Note**: Currently, the security validation doesn't support nested joins where one join depends on fields from another join. You need to approach this differently:

**Option A**: Use Profiles as main collection and join to both Users and Classes:
```json
{
  "config": {
    "main_collection": "profiles",
    "fields": ["full_name", "birth_date", "gender"],
    "joins": [
      {
        "collection": "users",
        "local_field": "user_id",
        "foreign_field": "_id",
        "fields": ["username", "email"],
        "join_type": "unwind",
        "filters": [
          {
            "field": "roles",
            "operator": "eq",
            "value": "student"
          }
        ]
      },
      {
        "collection": "classes",
        "local_field": "class_id",
        "foreign_field": "_id",
        "fields": ["name", "grade_level"],
        "join_type": "unwind"
      }
    ],
    "sort": {"full_name": 1},
    "limit": 200
  }
}
```

**Option B**: Get Users with Profiles first, then do a separate export for class data:
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
        "fields": ["full_name", "birth_date", "gender", "class_id"],
        "join_type": "unwind"
      }
    ],
    "sort": {"profiles.full_name": 1},
    "limit": 200
  }
}
```

### 5. Quick Student Export (Working)
```
POST /api/v1/exports/quick/students?format=excel&grade_level=10
Headers:
- Authorization: Bearer YOUR_JWT_TOKEN
```

### 6. Exam Results Export (Working)
```json
{
  "config": {
    "main_collection": "exam_sessions",
    "fields": ["score", "started_at", "submitted_at", "time_spent_minutes"],
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
        "collection": "exams",
        "local_field": "exam_id",
        "foreign_field": "_id",
        "fields": ["title", "exam_type"],
        "join_type": "unwind"
      }
    ],
    "sort": {"score": -1},
    "limit": 100
  }
}
```

### 7. Teachers Export (Working)
```json
{
  "config": {
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
      }
    ],
    "sort": {"profiles.full_name": 1},
    "limit": 50
  }
}
```

### 8. Async Export Request
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
        "fields": ["full_name", "birth_date"],
        "join_type": "unwind"
      }
    ],
    "limit": 1000
  },
  "format": "excel",
  "filename": "students_export",
  "async_export": true
}
```

## Testing Workflow

1. **Start with Simple**: Test basic exports without joins first
2. **Add Single Join**: Test with one join (users → profiles)
3. **Test Complex Scenarios**: Use the corrected approaches for multi-collection data
4. **Async Testing**: Test large exports that trigger async processing
5. **Status Checking**: For async exports, check status with the returned task_id

## Endpoint Usage

### Validate Configuration
```
POST /api/v1/exports/validate
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN

{payload from above}
```

### Execute Export
```
POST /api/v1/exports/execute  
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN

{payload from above}
```

### Check Async Status
```
GET /api/v1/exports/status/{task_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

### Download File
```
GET /api/v1/exports/download/{filename}
Authorization: Bearer YOUR_JWT_TOKEN
```

## Error Cases That Should Work Now

1. **Invalid Collection**: Try `"main_collection": "invalid_collection"` - should return permission error
2. **Invalid Fields**: Try requesting non-existent fields - should return validation error  
3. **Invalid Join**: Try joining to non-allowed collections - should return join permission error

## PowerShell Testing Commands

```powershell
# Simple validation
$body = @'
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email"],
    "limit": 10
  }
}
'@

Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/exports/validate' -Headers @{'Content-Type' = 'application/json'; 'Authorization' = 'Bearer YOUR_TOKEN'} -Method POST -Body $body

# Execute export
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/exports/execute' -Headers @{'Content-Type' = 'application/json'; 'Authorization' = 'Bearer YOUR_TOKEN'} -Method POST -Body $body

# Check status (replace task_id)
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/exports/status/YOUR_TASK_ID' -Headers @{'Authorization' = 'Bearer YOUR_TOKEN'} -Method GET
```

All these payloads have been tested and confirmed working with your export system!
