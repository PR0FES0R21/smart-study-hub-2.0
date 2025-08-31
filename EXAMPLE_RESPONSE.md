# Contoh Response Endpoint `/student` Setelah Perbaikan

## Response Sebelumnya (dengan computed_status)

```json
{
  "total_items": 4,
  "total_pages": 1,
  "current_page": 1,
  "limit": 20,
  "data": [
    {
      "title": "testink",
      "exam_type": "official_uas",
      "status": "pending_questions",
      "computed_status": null,
      "has_session": false,
      "session_score": null
    },
    {
      "title": "ujian testing 1",
      "exam_type": "daily_test",
      "status": "ongoing",
      "computed_status": null,
      "has_session": false,
      "session_score": null
    },
    {
      "title": "Ujian Tengah Semester Genap Tahun Ajaran 2025/2025 Basa Indonesia",
      "exam_type": "official_uts",
      "status": "ready",
      "computed_status": null,
      "has_session": false,
      "session_score": null
    },
    {
      "title": "ujian tkro 5",
      "exam_type": "official_uts",
      "status": "completed", // ← Status exam asli
      "computed_status": null,
      "has_session": true,
      "session_score": 0
    }
  ]
}
```

## Response Setelah Perbaikan (status di-override)

```json
{
  "total_items": 4,
  "total_pages": 1,
  "current_page": 1,
  "limit": 20,
  "data": [
    {
      "title": "testink",
      "exam_type": "official_uas",
      "status": "pending_questions", // ← Tidak ada exam session, gunakan status exam
      "has_session": false,
      "session_score": null
    },
    {
      "title": "ujian testing 1",
      "exam_type": "daily_test",
      "status": "ongoing", // ← Tidak ada exam session, gunakan status exam
      "has_session": false,
      "session_score": null
    },
    {
      "title": "Ujian Tengah Semester Genap Tahun Ajaran 2025/2025 Basa Indonesia",
      "exam_type": "official_uts",
      "status": "ready", // ← Tidak ada exam session, gunakan status exam
      "has_session": false,
      "session_score": null
    },
    {
      "title": "ujian tkro 5",
      "exam_type": "official_uts",
      "status": "completed", // ← Ada exam session dengan status "graded", override menjadi "completed"
      "has_session": true,
      "session_score": 0
    }
  ]
}
```

## Logika Status Baru

### Jika tidak ada exam session:

- Status = status exam asli (`pending_questions`, `ready`, `ongoing`, `completed`)

### Jika ada exam session:

- **Session status = "graded"** → Status = "completed"
- **Session status = "ongoing"** → Status = "ongoing"
- **Session status = "submitted"** → Status = "submitted"

### Contoh Skenario:

1. **Exam status = "ready", no session** → Status = "ready"
2. **Exam status = "ready", session status = "ongoing"** → Status = "ongoing"
3. **Exam status = "ready", session status = "graded"** → Status = "completed"
4. **Exam status = "completed", no session** → Status = "completed"

## Keuntungan Perubahan:

1. **Frontend lebih mudah**: Tidak perlu logic tambahan untuk `computed_status`
2. **Status konsisten**: Status langsung mencerminkan kondisi siswa
3. **Filter lebih akurat**: Filter berdasarkan status yang sudah di-override
4. **Backward compatible**: Field `has_session` dan `session_score` tetap ada
