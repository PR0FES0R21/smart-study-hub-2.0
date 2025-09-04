# 🧪 Contoh Praktis Testing Teacher Analytics dengan cURL

## 📋 Prerequisites
1. Server berjalan di `http://localhost:8000`
2. Sudah memiliki token JWT untuk guru
3. Sudah ada ujian dengan ID yang valid
4. Ada siswa yang sudah menyelesaikan ujian

---

## 🔑 1. Login untuk Mendapatkan Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "guru123",
    "password": "password123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Copy token untuk digunakan di request berikutnya!**

---

## 📊 2. Cek Dashboard Overview

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:8000/api/v1/teacher-analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "total_exams": 5,
  "exams_with_analytics": 2,
  "analytics_coverage": 40.0,
  "total_students_taught": 64,
  "average_class_performance": 78.5,
  "recent_tasks": [
    {
      "task_id": "analytics_...",
      "status": "completed",
      "started_at": "2025-01-04T10:30:00Z"
    }
  ],
  "pending_tasks": 0,
  "failed_tasks": 0
}
```

---

## 📝 3. List Semua Ujian & Status Analytics

```bash
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "total_items": 5,
  "total_pages": 1,
  "current_page": 1,
  "limit": 10,
  "data": [
    {
      "exam_id": "68920557e58cfa66adfcdd7f",
      "exam_title": "Ujian Matematika Semester 1",
      "class_name": "XII RPL 1",
      "total_students": 32,
      "completion_rate": 87.5,
      "class_average": 78.3,
      "status": "completed",
      "generated_at": "2025-01-04T10:30:00Z",
      "has_analytics": true
    },
    {
      "exam_id": "68920557e58cfa66adfcdd8a",
      "exam_title": "Ujian Fisika Bab 2",
      "class_name": "XII RPL 1", 
      "total_students": 32,
      "completion_rate": 93.8,
      "class_average": 0,
      "status": "pending",
      "generated_at": null,
      "has_analytics": false
    }
  ]
}
```

**📌 Copy exam_id yang belum ada analytics untuk langkah berikutnya!**

---

## ⚡ 4. Generate Analytics untuk Ujian Baru

```bash
export EXAM_ID="68920557e58cfa66adfcdd8a"

curl -X POST "http://localhost:8000/api/v1/teacher-analytics/exams/$EXAM_ID/analytics/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_regenerate": false,
    "include_comparison": true
  }'
```

**Response:**
```json
{
  "message": "Analytics generation started",
  "task_id": "analytics_68920557e58cfa66adfcdd8a_68822f07979cbba23e6db950_1756978890",
  "status": "pending",
  "estimated_time_minutes": 2,
  "check_status_endpoint": "/teacher-analytics/tasks/analytics_68920557e58cfa66adfcdd8a_68822f07979cbba23e6db950_1756978890/status"
}
```

**📌 Copy task_id untuk monitoring progress!**

---

## 🔍 5. Monitor Progress Generation

```bash
export TASK_ID="analytics_68920557e58cfa66adfcdd8a_68822f07979cbba23e6db950_1756978890"

# Cek status berkali-kali sampai selesai
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/tasks/$TASK_ID/status" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (Masih Processing):**
```json
{
  "task_id": "analytics_68920557e58cfa66adfcdd8a_68822f07979cbba23e6db950_1756978890",
  "exam_id": "68920557e58cfa66adfcdd8a",
  "teacher_id": "68822f07979cbba23e6db950",
  "status": "processing",
  "progress": 65.0,
  "started_at": "2025-01-04T11:15:00Z",
  "completed_at": null,
  "error_message": null
}
```

**Response (Selesai):**
```json
{
  "task_id": "analytics_68920557e58cfa66adfcdd8a_68822f07979cbba23e6db950_1756978890",
  "exam_id": "68920557e58cfa66adfcdd8a",
  "teacher_id": "68822f07979cbba23e6db950",
  "status": "completed",
  "progress": 100.0,
  "started_at": "2025-01-04T11:15:00Z",
  "completed_at": "2025-01-04T11:17:23Z",
  "error_message": null
}
```

---

## 📈 6. Akses Analytics Lengkap (Setelah Generation Selesai)

```bash
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/exams/$EXAM_ID/analytics" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (Sangat Panjang - Contoh Singkat):**
```json
{
  "status": "completed",
  "exam_metadata": {
    "exam_id": "68920557e58cfa66adfcdd8a",
    "exam_title": "Ujian Fisika Bab 2",
    "subject_name": "Fisika",
    "class_name": "XII RPL 1",
    "teacher_name": "Budi Santoso",
    "total_questions": 25,
    "max_score": 100
  },
  "class_statistics": {
    "total_students": 32,
    "students_completed": 30,
    "completion_rate": 93.8,
    "class_average": 82.1,
    "median_score": 83.0,
    "highest_score": 96.0,
    "lowest_score": 52.0,
    "passing_rate": 86.7,
    "grade_distribution": {
      "A": 8,
      "B": 14,
      "C": 6,
      "D": 2,
      "E": 0
    }
  },
  "questions_analysis": [
    {
      "question_number": 1,
      "question_text": "Gaya gravitasi antara dua benda...",
      "class_accuracy": 0.83,
      "is_problematic": false,
      "discrimination_index": 0.72
    }
  ],
  "student_performances": [
    {
      "rank": 1,
      "student_name": "Alice Wonderland",
      "score": 96.0,
      "grade": "A",
      "percentile": 96.7,
      "integrity_score": 1.0
    }
  ],
  "generated_at": "2025-01-04T11:17:23Z"
}
```

---

## 📊 7. Export Data ke CSV

```bash
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/export/$EXAM_ID?format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  --output "analytics_$EXAM_ID.csv"
```

**File CSV akan tersimpan dengan nama `analytics_68920557e58cfa66adfcdd8a.csv`**

---

## 📋 8. Export Data ke JSON

```bash
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/export/$EXAM_ID?format=json" \
  -H "Authorization: Bearer $TOKEN" \
  --output "analytics_$EXAM_ID.json"
```

**File JSON akan tersimpan dengan nama `analytics_68920557e58cfa66adfcdd8a.json`**

---

## 📝 9. List Semua Task Saya

```bash
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/tasks?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
[
  {
    "task_id": "analytics_68920557e58cfa66adfcdd8a_68822f07979cbba23e6db950_1756978890",
    "exam_id": "68920557e58cfa66adfcdd8a",
    "status": "completed",
    "progress": 100.0,
    "started_at": "2025-01-04T11:15:00Z",
    "completed_at": "2025-01-04T11:17:23Z"
  },
  {
    "task_id": "analytics_68920557e58cfa66adfcdd7f_68822f07979cbba23e6db950_1756975890",
    "exam_id": "68920557e58cfa66adfcdd7f",
    "status": "completed",
    "progress": 100.0,
    "started_at": "2025-01-04T10:30:00Z",
    "completed_at": "2025-01-04T10:32:05Z"
  }
]
```

---

## 🗑️ 10. Hapus Analytics (Jika Perlu Regenerate)

```bash
curl -X DELETE "http://localhost:8000/api/v1/teacher-analytics/exams/$EXAM_ID/analytics" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```
HTTP/1.1 204 No Content
```

---

## 🎯 11. Regenerate Analytics Paksa

```bash
curl -X POST "http://localhost:8000/api/v1/teacher-analytics/exams/$EXAM_ID/analytics/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_regenerate": true,
    "include_comparison": true
  }'
```

---

## 🚦 12. Cancel Task yang Sedang Berjalan

```bash
export RUNNING_TASK_ID="analytics_68920557e58cfa66adfcdd8b_68822f07979cbba23e6db950_1756978999"

curl -X POST "http://localhost:8000/api/v1/teacher-analytics/tasks/$RUNNING_TASK_ID/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "message": "Task cancelled successfully"
}
```

---

## 🔄 Script Otomatis untuk Testing

### **Bash Script Lengkap:**

```bash
#!/bin/bash

# Configuration
SERVER="http://localhost:8000"
USERNAME="guru123"
PASSWORD="password123"
EXAM_ID="68920557e58cfa66adfcdd7f"

echo "🔑 Step 1: Login and get token..."
TOKEN_RESPONSE=$(curl -s -X POST "$SERVER/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
    echo "❌ Login failed!"
    exit 1
fi

echo "✅ Login successful!"

echo ""
echo "📊 Step 2: Check dashboard..."
curl -s -X GET "$SERVER/api/v1/teacher-analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "📝 Step 3: List exams..."
curl -s -X GET "$SERVER/api/v1/teacher-analytics/?page=1&limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "⚡ Step 4: Generate analytics..."
GENERATE_RESPONSE=$(curl -s -X POST "$SERVER/api/v1/teacher-analytics/exams/$EXAM_ID/analytics/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_regenerate":false,"include_comparison":true}')

echo $GENERATE_RESPONSE | jq

TASK_ID=$(echo $GENERATE_RESPONSE | jq -r '.task_id')

if [ "$TASK_ID" != "null" ]; then
    echo ""
    echo "🔍 Step 5: Monitor progress..."
    
    while true; do
        TASK_STATUS=$(curl -s -X GET "$SERVER/api/v1/teacher-analytics/tasks/$TASK_ID/status" \
          -H "Authorization: Bearer $TOKEN")
        
        STATUS=$(echo $TASK_STATUS | jq -r '.status')
        PROGRESS=$(echo $TASK_STATUS | jq -r '.progress')
        
        echo "Status: $STATUS, Progress: $PROGRESS%"
        
        if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
            break
        fi
        
        sleep 2
    done
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "📈 Step 6: Get analytics..."
        curl -s -X GET "$SERVER/api/v1/teacher-analytics/exams/$EXAM_ID/analytics" \
          -H "Authorization: Bearer $TOKEN" | jq '.class_statistics'
          
        echo ""
        echo "📊 Step 7: Export to CSV..."
        curl -s -X GET "$SERVER/api/v1/teacher-analytics/export/$EXAM_ID?format=csv" \
          -H "Authorization: Bearer $TOKEN" \
          --output "analytics_$EXAM_ID.csv"
        
        echo "✅ CSV exported to analytics_$EXAM_ID.csv"
    fi
fi

echo ""
echo "🏁 Testing completed!"
```

### **Cara menjalankan script:**

1. Save script di file `test_analytics.sh`
2. Buat executable: `chmod +x test_analytics.sh`
3. Edit konfigurasi (username, password, exam_id)
4. Jalankan: `./test_analytics.sh`

---

## 🧪 Testing Scenarios

### **Scenario 1: Testing Error Handling**

```bash
# Test dengan exam_id yang tidak valid
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/exams/invalid_id/analytics" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 400 Bad Request - Invalid exam ID
```

### **Scenario 2: Testing Authorization**

```bash
# Test tanpa token
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/dashboard"

# Expected: 401 Unauthorized
```

### **Scenario 3: Testing dengan Data Kosong**

```bash
# Test dengan ujian yang belum ada siswa
curl -X GET "http://localhost:8000/api/v1/teacher-analytics/exams/empty_exam_id/analytics" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 404 Not Found - Analytics not found
```

---

## 💡 Tips Testing

1. **Install jq** untuk format JSON yang rapi: `sudo apt-get install jq`
2. **Gunakan variables** untuk exam_id dan token agar mudah diubah
3. **Check response status** dengan flag `-w "%{http_code}"`
4. **Save response** ke file untuk analisis: `--output response.json`
5. **Use verbose mode** untuk debug: `-v`

---

Dengan contoh-contoh ini, Anda bisa dengan mudah testing semua endpoint Teacher Analytics! 🚀
