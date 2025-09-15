# Export System API Testing Payloads

Testing payloads untuk Flexible Export System yang bisa digunakan di OpenAPI/Swagger UI.

## 🔐 Authentication
Semua endpoint membutuhkan Bearer token di header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
```

---

## 1. GET /api/v1/exports/collections
**Deskripsi:** Mendapatkan daftar collection yang tersedia

**Method:** GET  
**Headers:** Authorization: Bearer {token}  
**Body:** Tidak perlu body

---

## 2. GET /api/v1/exports/formats
**Deskripsi:** Mendapatkan format export yang didukung

**Method:** GET  
**Headers:** Authorization: Bearer {token}  
**Body:** Tidak perlu body

---

## 3. POST /api/v1/exports/validate
**Deskripsi:** Validasi konfigurasi export

**Method:** POST  
**Headers:** 
- Authorization: Bearer {token}
- Content-Type: application/json

### 3.1 Payload Validasi Basic Config
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
    "limit": 100
  }
}
```

### 3.2 Payload Validasi Complex Config dengan Joins
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
        "fields": ["full_name", "birth_date", "gender"],
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
    "limit": 200
  }
}
```

---

## 4. POST /api/v1/exports/execute
**Deskripsi:** Menjalankan export data

**Method:** POST  
**Headers:** 
- Authorization: Bearer {token}
- Content-Type: application/json

### 4.1 Simple Student Export (JSON)
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
    "limit": 10
  },
  "format": "json",
  "filename": "simple_students_test",
  "async_export": false
}
```

### 4.2 Student Export dengan Profile Data (Excel)
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
    "limit": 25
  },
  "format": "excel",
  "filename": "students_with_profile_test"
}
```

### 4.3 Teacher Data Export (CSV)
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
      }
    ],
    "sort": {"profiles.full_name": 1},
    "limit": 15
  },
  "format": "csv",
  "filename": "teachers_test"
}
```

### 4.4 Exam Results Export
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
    "limit": 50
  },
  "format": "excel",
  "filename": "exam_results_test"
}
```

### 4.5 Advanced Filtering Example
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
    "limit": 100
  },
  "format": "excel",
  "filename": "filtered_students_advanced"
}
```

### 4.6 Async Export Test (untuk export besar)
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
  "filename": "large_async_export_test",
  "async_export": true
}
```

---

## 5. GET /api/v1/exports/status/{task_id}
**Deskripsi:** Cek status export async

**Method:** GET  
**Headers:** Authorization: Bearer {token}  
**URL Parameter:** task_id (didapat dari response async export)  
**Body:** Tidak perlu body

**Contoh URL:** `/api/v1/exports/status/12345-abcde-67890`

---

## 6. GET /api/v1/exports/download/{filename}
**Deskripsi:** Download file export

**Method:** GET  
**Headers:** Authorization: Bearer {token}  
**URL Parameter:** filename (didapat dari response export)  
**Body:** Tidak perlu body

**Contoh URL:** `/api/v1/exports/download/students_export_20241212_1234.xlsx`

---

## 7. POST /api/v1/exports/quick/students
**Deskripsi:** Quick export students

**Method:** POST  
**Headers:** Authorization: Bearer {token}  
**Query Parameters:**

### 7.1 Export Semua Students (Excel)
**URL:** `/api/v1/exports/quick/students?format=excel`  
**Body:** Tidak perlu body

### 7.2 Export Students by Grade Level (CSV)
**URL:** `/api/v1/exports/quick/students?format=csv&grade_level=10`  
**Body:** Tidak perlu body

### 7.3 Export Students by Grade Level (JSON)
**URL:** `/api/v1/exports/quick/students?format=json&grade_level=12`  
**Body:** Tidak perlu body

---

## 8. POST /api/v1/exports/quick/exam-results
**Deskripsi:** Quick export exam results

**Method:** POST  
**Headers:** Authorization: Bearer {token}  
**Query Parameters:**

### 8.1 Export Semua Exam Results (Excel)
**URL:** `/api/v1/exports/quick/exam-results?format=excel`  
**Body:** Tidak perlu body

### 8.2 Export Exam Results by Specific Exam (CSV)
**URL:** `/api/v1/exports/quick/exam-results?format=csv&exam_id=EXAM_ID_HERE`  
**Body:** Tidak perlu body  
*Note: Ganti EXAM_ID_HERE dengan ObjectId yang valid*

---

## 🚨 Error Testing Payloads

### 9.1 Invalid Collection
```json
{
  "config": {
    "main_collection": "invalid_collection",
    "fields": ["field1", "field2"]
  },
  "format": "excel"
}
```
**Expected:** 400 Bad Request

### 9.2 Invalid Fields
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
**Expected:** 400 Bad Request

### 9.3 Invalid Format
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["username", "email"]
  },
  "format": "pdf"
}
```
**Expected:** 400 Bad Request

### 9.4 Invalid Join
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
**Expected:** 400 Bad Request

### 9.5 Sensitive Fields (Non-Admin User)
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
**Expected:** 403 Forbidden (jika menggunakan teacher token)

---

## 📝 Testing Flow Recommendations

### Basic Flow:
1. **GET /collections** - Lihat collections yang tersedia
2. **GET /formats** - Lihat format yang didukung
3. **POST /validate** - Validasi config sebelum export
4. **POST /execute** - Jalankan export
5. **GET /download/{filename}** - Download hasil export

### Async Flow:
1. **POST /execute** dengan `async_export: true`
2. **GET /status/{task_id}** - Cek status berulang
3. **GET /download/{filename}** - Download saat selesai

### Quick Export Flow:
1. **POST /quick/students** atau **POST /quick/exam-results**
2. **GET /download/{filename}** - Download langsung

---

## 🛠️ Tips Testing:

1. **Mulai dengan payload sederhana** (Simple Student Export)
2. **Test error cases** untuk memastikan validation bekerja
3. **Test dengan berbagai format** (json, csv, excel)
4. **Test dengan data volume kecil** dulu
5. **Test async export** untuk data besar
6. **Pastikan token valid** dan sesuai role

Semua payload ini sudah siap pakai di OpenAPI/Swagger UI! 🚀
