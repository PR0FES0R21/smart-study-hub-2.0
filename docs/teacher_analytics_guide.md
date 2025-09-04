# 📊 Panduan Lengkap Teacher Analytics API

## 🎯 Overview
Teacher Analytics API memungkinkan guru untuk:
- Generate analisis mendalam untuk ujian yang mereka buat
- Melihat performa siswa secara detail
- Mendapatkan insights tentang kualitas soal
- Export data analisis dalam berbagai format
- Monitor progress generation analytics

---

## 🚀 Flow Penggunaan Lengkap

### 1. **Persiapan & Login**
Pastikan Anda sudah login sebagai guru dan memiliki token JWT yang valid.

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "guru123",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 2. **Cek Dashboard Overview**
Mulai dengan melihat overview analytics yang sudah ada.

```http
GET /api/v1/teacher-analytics/dashboard
Authorization: Bearer your_token_here
```

**Response:**
```json
{
  "total_exams": 15,
  "exams_with_analytics": 8,
  "analytics_coverage": 53.3,
  "total_students_taught": 120,
  "average_class_performance": 75.2,
  "recent_tasks": [...],
  "pending_tasks": 2,
  "failed_tasks": 0
}
```

**Interpretasi:**
- Anda punya 15 ujian total
- 8 sudah ada analytics (53.3% coverage)
- Rata-rata performa kelas 75.2
- Ada 2 task yang sedang pending

---

### 3. **List Ujian & Status Analytics**
Lihat semua ujian Anda dan status analytics masing-masing.

```http
GET /api/v1/teacher-analytics/?page=1&limit=20
Authorization: Bearer your_token_here
```

**Response:**
```json
{
  "total_items": 15,
  "total_pages": 1,
  "current_page": 1,
  "limit": 20,
  "data": [
    {
      "exam_id": "68920557e58cfa66adfcdd7f",
      "exam_title": "Ujian Matematika Semester 1",
      "class_name": "XII RPL 1",
      "total_students": 32,
      "completion_rate": 87.5,
      "class_average": 78.3,
      "status": "completed",  // Ada analytics
      "generated_at": "2025-01-04T10:30:00Z",
      "has_analytics": true
    },
    {
      "exam_id": "68920557e58cfa66adfcdd8g",
      "exam_title": "Ujian Fisika Bab 1",
      "class_name": "XII RPL 1",
      "total_students": 32,
      "completion_rate": 90.6,
      "class_average": 0,
      "status": "pending",  // Belum ada analytics
      "generated_at": null,
      "has_analytics": false
    }
  ]
}
```

**Interpretasi:**
- Ujian pertama sudah ada analytics (status: completed)
- Ujian kedua belum ada analytics (status: pending)

---

### 4. **Generate Analytics untuk Ujian Baru**
Untuk ujian yang belum ada analytics, generate terlebih dahulu.

```http
POST /api/v1/teacher-analytics/exams/68920557e58cfa66adfcdd8g/analytics/generate
Authorization: Bearer your_token_here
Content-Type: application/json

{
  "force_regenerate": false,
  "include_comparison": true
}
```

**Response:**
```json
{
  "message": "Analytics generation started",
  "task_id": "analytics_68920557e58cfa66adfcdd8g_68822f07979cbba23e6db950_1756978696",
  "status": "pending",
  "estimated_time_minutes": 2,
  "check_status_endpoint": "/teacher-analytics/tasks/analytics_68920557e58cfa66adfcdd8g_68822f07979cbba23e6db950_1756978696/status"
}
```

**Parameter Penjelasan:**
- `force_regenerate`: false = skip jika sudah ada, true = regenerate paksa
- `include_comparison`: true = include perbandingan dengan ujian serupa

---

### 5. **Monitor Progress Generation**
Cek status task yang sedang berjalan.

```http
GET /api/v1/teacher-analytics/tasks/analytics_68920557e58cfa66adfcdd8g_68822f07979cbba23e6db950_1756978696/status
Authorization: Bearer your_token_here
```

**Response (Sedang Processing):**
```json
{
  "task_id": "analytics_68920557e58cfa66adfcdd8g_68822f07979cbba23e6db950_1756978696",
  "exam_id": "68920557e58cfa66adfcdd8g",
  "teacher_id": "68822f07979cbba23e6db950",
  "status": "processing",
  "progress": 45.0,
  "started_at": "2025-01-04T11:00:00Z",
  "completed_at": null,
  "error_message": null
}
```

**Response (Selesai):**
```json
{
  "task_id": "analytics_68920557e58cfa66adfcdd8g_68822f07979cbba23e6db950_1756978696",
  "exam_id": "68920557e58cfa66adfcdd8g",
  "teacher_id": "68822f07979cbba23e6db950",
  "status": "completed",
  "progress": 100.0,
  "started_at": "2025-01-04T11:00:00Z",
  "completed_at": "2025-01-04T11:02:15Z",
  "error_message": null
}
```

---

### 6. **Akses Analytics Lengkap**
Setelah generation selesai, akses data analytics lengkap.

```http
GET /api/v1/teacher-analytics/exams/68920557e58cfa66adfcdd8g/analytics
Authorization: Bearer your_token_here
```

**Response (Sangat Lengkap):**
```json
{
  "status": "completed",
  "exam_metadata": {
    "exam_id": "68920557e58cfa66adfcdd8g",
    "exam_title": "Ujian Fisika Bab 1",
    "exam_type": "multiple_choice",
    "subject_name": "Fisika",
    "class_name": "XII RPL 1",
    "teacher_name": "Budi Santoso",
    "total_questions": 20,
    "max_score": 100,
    "duration_minutes": 90,
    "availability_start_time": "2025-01-04T08:00:00Z",
    "availability_end_time": "2025-01-04T10:00:00Z",
    "academic_period": "2024/2025 Semester Ganjil"
  },
  "class_statistics": {
    "total_students": 32,
    "students_completed": 29,
    "students_in_progress": 2,
    "students_not_started": 1,
    "completion_rate": 90.6,
    "class_average": 76.8,
    "median_score": 78.0,
    "highest_score": 95.0,
    "lowest_score": 45.0,
    "standard_deviation": 12.3,
    "passing_rate": 82.8,
    "grade_distribution": {
      "A": 5,
      "B": 12,
      "C": 8,
      "D": 3,
      "E": 1
    },
    "score_ranges": {
      "0-20": 0,
      "21-40": 0,
      "41-60": 4,
      "61-80": 18,
      "81-100": 7
    }
  },
  "questions_analysis": [
    {
      "question_id": "question_001",
      "question_number": 1,
      "question_text": "Hukum Newton I menyatakan bahwa...",
      "question_type": "multiple_choice",
      "difficulty": "easy",
      "points": 5,
      "class_accuracy": 0.86,
      "correct_count": 25,
      "wrong_count": 4,
      "unanswered_count": 0,
      "average_time": 45.2,
      "median_time": 42.0,
      "fastest_time": 15.0,
      "slowest_time": 120.0,
      "is_problematic": false,
      "discrimination_index": 0.65,
      "answer_distribution": {
        "A": 25,
        "B": 2,
        "C": 1,
        "D": 1
      },
      "correct_option": "A"
    }
    // ... soal lainnya
  ],
  "student_performances": [
    {
      "student_id": "student_001",
      "student_name": "Alice Wonderland",
      "exam_session_id": "session_001",
      "status": "completed",
      "score": 95.0,
      "percentage": 95.0,
      "rank": 1,
      "percentile": 96.6,
      "grade": "A",
      "duration_taken": 75.3,
      "time_efficiency": 1.26,
      "answered_questions": 20,
      "correct_answers": 19,
      "wrong_answers": 1,
      "unanswered_questions": 0,
      "accuracy_rate": 0.95,
      "violations_count": 0,
      "integrity_score": 1.0,
      "started_at": "2025-01-04T08:05:00Z",
      "submitted_at": "2025-01-04T09:20:18Z"
    }
    // ... siswa lainnya
  ],
  "time_analysis": {
    "average_completion_time": 72.5,
    "median_completion_time": 75.0,
    "fastest_completion": 45.2,
    "slowest_completion": 89.8,
    "standard_deviation": 12.1,
    "time_distribution": {
      "0-30min": 0,
      "31-60min": 3,
      "61-90min": 24,
      "90+min": 2
    },
    "overtime_count": 0,
    "early_submission_count": 3,
    "average_time_per_question": 217.5
  },
  "violation_analysis": {
    "total_violations": 12,
    "students_with_violations": 5,
    "violation_percentage": 17.2,
    "violation_types": {
      "tab_switch": 8,
      "fullscreen_exit": 4
    },
    "severity_distribution": {
      "low": 10,
      "medium": 2,
      "high": 0
    },
    "flagged_students": [],
    "high_risk_count": 0,
    "class_integrity_score": 0.83,
    "integrity_rating": "good"
  },
  "comparison_analysis": {
    "has_comparison": false,
    "comparison_exams": [],
    "score_improvement": null,
    "difficulty_comparison": null,
    "performance_trend": null
  },
  "generated_at": "2025-01-04T11:02:15Z",
  "generation_time": 2.15,
  "cache_expires_at": "2025-01-05T11:02:15Z",
  "data_version": "1.0"
}
```

---

## 📊 Interpretasi Data Analytics

### **Class Statistics**
- **completion_rate**: 90.6% siswa sudah selesai ujian
- **class_average**: 76.8 (cukup baik)
- **passing_rate**: 82.8% siswa lulus (≥60)
- **grade_distribution**: Mayoritas dapat B dan C

### **Questions Analysis**
- **class_accuracy**: 0.86 = 86% siswa menjawab benar
- **is_problematic**: false = soal berkualitas baik
- **discrimination_index**: 0.65 = soal baik membedakan siswa pintar/lemah
- **answer_distribution**: Sebaran pilihan jawaban siswa

### **Student Performances**
- **rank**: Peringkat berdasarkan score
- **percentile**: Posisi siswa dibanding kelas
- **time_efficiency**: Score per menit (semakin tinggi semakin efisien)
- **integrity_score**: 1.0 = tidak ada pelanggaran, 0.0 = banyak pelanggaran

### **Violation Analysis**
- **integrity_rating**: "good" = tingkat kejujuran baik
- **violation_types**: Jenis pelanggaran (tab switch, fullscreen exit)
- **flagged_students**: Siswa yang perlu diperhatikan

---

## 📤 Export Data Analytics

### **Export ke CSV (Data Siswa)**
```http
GET /api/v1/teacher-analytics/export/68920557e58cfa66adfcdd8g?format=csv
Authorization: Bearer your_token_here
```

**Response:** File CSV dengan kolom:
```
Rank,Student Name,Score,Percentage,Grade,Duration (min),Violations,Status
1,Alice Wonderland,95.0,95.0,A,75.3,0,completed
2,Bob Builder,88.0,88.0,B,82.1,1,completed
...
```

### **Export ke JSON (Data Lengkap)**
```http
GET /api/v1/teacher-analytics/export/68920557e58cfa66adfcdd8g?format=json
Authorization: Bearer your_token_here
```

**Response:** File JSON dengan semua data analytics lengkap.

---

## 🔄 Use Cases Praktis

### **Scenario 1: Guru Ingin Evaluasi Soal**
1. Generate analytics untuk ujian
2. Lihat `questions_analysis`
3. Cari soal dengan `is_problematic: true`
4. Perhatikan `class_accuracy` rendah (<0.5)
5. Revisi soal tersebut untuk ujian berikutnya

### **Scenario 2: Guru Ingin Identifikasi Siswa Bermasalah**
1. Akses analytics ujian
2. Lihat `student_performances`
3. Filter siswa dengan `rank` rendah atau `integrity_score` rendah
4. Berikan bimbingan khusus

### **Scenario 3: Guru Ingin Laporan untuk Orangtua**
1. Export data ke CSV
2. Filter berdasarkan siswa tertentu
3. Buat laporan individual
4. Include `percentile`, `grade`, dan `time_efficiency`

### **Scenario 4: Guru Ingin Monitor Kecurangan**
1. Lihat `violation_analysis`
2. Check `flagged_students`
3. Review siswa dengan `integrity_score` rendah
4. Tindak lanjut sesuai kebijakan sekolah

---

## 🎯 Tips Penggunaan

### **Best Practices:**
1. **Generate analytics setelah semua siswa selesai ujian** untuk data akurat
2. **Gunakan `force_regenerate: false`** untuk menghemat resource
3. **Monitor `pending_tasks`** di dashboard secara berkala
4. **Export data** untuk dokumentasi dan laporan

### **Troubleshooting:**
- **Task status "failed"**: Cek `error_message` untuk detail error
- **Analytics tidak muncul**: Pastikan ada siswa yang sudah menyelesaikan ujian
- **Data tidak akurat**: Regenerate dengan `force_regenerate: true`

### **Performance Tips:**
- Analytics generation bisa 1-5 menit tergantung jumlah siswa
- Cache analytics bertahan 24 jam
- Gunakan pagination untuk list ujian banyak

---

## 🔗 Endpoint Reference Cepat

| Method | Endpoint | Fungsi |
|--------|----------|---------|
| `GET` | `/teacher-analytics/dashboard` | Overview analytics |
| `GET` | `/teacher-analytics/` | List ujian & status |
| `POST` | `/teacher-analytics/exams/{exam_id}/analytics/generate` | Generate analytics |
| `GET` | `/teacher-analytics/exams/{exam_id}/analytics` | Akses analytics lengkap |
| `GET` | `/teacher-analytics/tasks/{task_id}/status` | Cek progress generation |
| `GET` | `/teacher-analytics/tasks` | List task saya |
| `GET` | `/teacher-analytics/export/{exam_id}` | Export data |
| `DELETE` | `/teacher-analytics/exams/{exam_id}/analytics` | Hapus analytics |

---

Dengan panduan ini, Anda bisa memanfaatkan Teacher Analytics API secara maksimal untuk evaluasi pembelajaran yang lebih efektif! 🚀
