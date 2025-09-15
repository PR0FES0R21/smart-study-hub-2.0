# Payload Export 10 Data Siswa

## Field yang Diminta:
- Nama siswa (dari profiles.full_name)
- Email (dari users.email) 
- Login ID (dari users.username)
- Grade Level (dari classes.grade_level)
- Class Name (dari classes.name)
- Abbreviation (dari expertise_programs.abbreviation)

## Payload JSON

Karena kita membutuhkan data dari 4 collection berbeda (users, profiles, classes, expertise_programs), kita akan menggunakan `profiles` sebagai main collection karena memiliki relasi langsung ke semua collection yang dibutuhkan.

### Untuk Endpoint /validate atau /execute:

```json
{
  "config": {
    "main_collection": "profiles",
    "fields": ["full_name"],
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
        "fields": ["name", "grade_level", "expertise_id"],
        "join_type": "unwind"
      },
      {
        "collection": "expertise_programs",
        "local_field": "classes.expertise_id",
        "foreign_field": "_id",
        "fields": ["abbreviation"],
        "join_type": "unwind"
      }
    ],
    "sort": {"full_name": 1},
    "limit": 10
  }
}
```

### Untuk Execute dengan Format Excel:

```json
{
  "config": {
    "main_collection": "profiles",
    "fields": ["full_name"],
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
        "fields": ["name", "grade_level", "expertise_id"],
        "join_type": "unwind"
      },
      {
        "collection": "expertise_programs",
        "local_field": "classes.expertise_id",
        "foreign_field": "_id",
        "fields": ["abbreviation"],
        "join_type": "unwind"
      }
    ],
    "sort": {"full_name": 1},
    "limit": 10
  },
  "format": "excel",
  "filename": "data_siswa_10"
}
```

## Struktur Data yang Dihasilkan:

Hasil export akan memiliki struktur seperti ini:

```json
[
  {
    "_id": "...",
    "full_name": "Ahmad Rizki",
    "users": {
      "username": "ahmad.rizki",
      "email": "ahmad.rizki@student.school.id"
    },
    "classes": {
      "name": "XII RPL 1",
      "grade_level": 12,
      "expertise_id": "..."
    },
    "expertise_programs": {
      "abbreviation": "RPL"
    }
  },
  // ... 9 data lainnya
]
```

Dalam format Excel/CSV, akan menjadi kolom:
- full_name
- users.username (Login ID)
- users.email
- classes.grade_level
- classes.name
- expertise_programs.abbreviation

## Alternative Payload (Jika expertise_programs join tidak bekerja):

Jika join ke expertise_programs mengalami masalah, gunakan payload ini yang hanya sampai classes:

```json
{
  "config": {
    "main_collection": "profiles",
    "fields": ["full_name"],
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
    "limit": 10
  },
  "format": "excel",
  "filename": "data_siswa_10_simple"
}
```

## Cara Penggunaan:

1. **Validation**: POST ke `/api/v1/exports/validate`
2. **Execute**: POST ke `/api/v1/exports/execute`
3. **Headers**:
   ```
   Content-Type: application/json
   Authorization: Bearer YOUR_JWT_TOKEN
   ```
