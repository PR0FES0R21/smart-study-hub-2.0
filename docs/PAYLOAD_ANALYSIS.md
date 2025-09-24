# 🔍 Analysis of Payload Issues

## Payload Asli Anda (Yang Lebih Baik):
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["email", "login_id", "profile"],
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
        "alias": "profile",
        "join_type": "lookup",
        "fields": ["full_name", "gender", "class_detail", "expertise"],
        "preserve_null_and_empty_arrays": false,
        "joins": [
          {
            "collection": "classes",
            "local_field": "_id",           // ← INI MASALAHNYA!
            "foreign_field": "profile_id",   // ← INI TERBALIK!
            "alias": "class_detail",
            "join_type": "lookup",
            "fields": ["grade_level"],
            "preserve_null_and_empty_arrays": true
          }
        ]
      }
    ]
  }
}
```

## 🐛 Masalah yang Ditemukan:

### 1. **Nested Join Logic Error**
- Untuk nested joins, field references harus mengacu pada collection parent
- `classes` join harusnya: 
  - `local_field: "class_id"` (dari profiles)
  - `foreign_field: "_id"` (dari classes)

### 2. **Query Builder Bug**  
- Advanced query builder tidak menangani nested joins dengan benar
- Pipeline dibangun secara flat, bukan nested di dalam lookup pipeline
- Field references tidak dikonversi dengan benar

### 3. **Missing Fields**
- Field `login_id` tidak ada, seharusnya `username`
- Anda minta field `profile`, `class_detail`, `expertise` tapi ini akan dibuat dari joins

## ✅ Solusi:
1. Perbaiki nested lookup pipeline generation
2. Fix field references dalam nested context
3. Koreksi minor field names
