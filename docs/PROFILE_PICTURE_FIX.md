# Fix Profile Picture URL dalam Response

## Masalah yang Ditemukan

Dalam response API question sets, field `profile_picture_url` menunjukkan `null` meskipun data ada di database. Response menunjukkan:

```json
"created_by": {
  "_id": "68822f07979cbba23e6db950",
  "full_name": "Agus Santoso",
  "profile_picture_key": null  // ← Harusnya profile_picture_url dengan nilai yang benar
}
```

Padahal di database:

```json
{
  "profile_picture_key": "profiles/31e4de77-1248-4553-9f05-62a7456361be.jpg",
  "profile_picture_url": "https://cdn.cigarverse.space/profiles/31e4de77-1248-4553-9f05-62a7456361be.jpg"
}
```

## Root Cause

1. **Schema Mismatch**: Schema `TeacherBasic` menggunakan `profile_picture_key` tapi aggregation pipeline menggunakan `profile_picture_url`
2. **Inconsistent Field Names**: Beberapa tempat masih menggunakan `profile_picture_key` dalam projection

## Perubahan yang Dilakukan

### 1. Update Schema TeacherBasic

**File: `app/schemas/user.py`**

```python
class TeacherBasic(BaseModel):
    """Schema untuk daftar guru sederhana (hanya ID dan nama)"""
    id: PyObjectId = Field(alias="_id")
    full_name: str
    profile_picture_url: Optional[str] = None  # ← Changed from profile_picture_key

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
```

### 2. Update Projection di User CRUD

**File: `app/crud/crud_users.py`**

```python
{"$project": {
    "_id": 1,
    "full_name": "$profile_details.full_name",
    "profile_picture_url": "$profile_details.profile_picture_url"  # ← Changed from profile_picture_key
}},
```

## Impact Analysis

### ✅ Affected Components:

1. **Question Sets Response** - Field `created_by.profile_picture_url` sekarang akan menampilkan URL yang benar
2. **Permission Holders** - Semua user dalam permission holders akan menampilkan profile picture URL
3. **User Search/List** - Response user search akan konsisten menggunakan profile_picture_url

### ✅ Backward Compatibility:

- API response structure tetap sama, hanya field name yang diperbaiki
- Frontend yang sudah menggunakan `profile_picture_url` akan langsung mendapat data yang benar
- Schema masih mendukung null values untuk user tanpa profile picture

### ✅ Database Schema:

- Tidak ada perubahan database schema
- Field `profile_picture_key` dan `profile_picture_url` tetap ada di database
- Hanya response API yang diperbaiki

## Expected Result

Setelah fix ini, response API akan menampilkan:

```json
{
  "data": [
    {
      "created_by": {
        "_id": "68822f07979cbba23e6db950",
        "full_name": "Agus Santoso",
        "profile_picture_url": "https://cdn.cigarverse.space/profiles/31e4de77-1248-4553-9f05-62a7456361be.jpg"
      },
      "permission_holders": {
        "can_edit": [
          {
            "_id": "68822f07979cbba23e6db950",
            "full_name": "Agus Santoso",
            "profile_picture_url": "https://cdn.cigarverse.space/profiles/31e4de77-1248-4553-9f05-62a7456361be.jpg"
          }
        ]
      }
    }
  ]
}
```

## Files Modified

1. **`app/schemas/user.py`** - Updated TeacherBasic schema
2. **`app/crud/crud_users.py`** - Fixed projection in user aggregation
3. **`app/crud/crud_question_sets.py`** - Already correct (was using profile_picture_url)
4. **`app/api/v1/routes/question_sets.py`** - Already correct (was using profile_picture_url)

## Testing

Untuk memverifikasi fix ini bekerja:

1. **Hit API question sets list**: `GET /api/v1/question-sets/`
2. **Check response**: Field `created_by.profile_picture_url` dan `permission_holders[].profile_picture_url` harus menampilkan URL yang benar
3. **Verify data**: URL harus sesuai dengan data di database collection `profiles`

## Note

Fix ini menyelesaikan inkonsistensi antara field names di schema vs database projection, memastikan profile picture URL ditampilkan dengan benar di semua response API yang melibatkan user data.
