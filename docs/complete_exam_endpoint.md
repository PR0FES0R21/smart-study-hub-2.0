# 📝 Endpoint: Complete Exam Manually

## 🎯 Overview

Endpoint baru untuk menyelesaikan ujian secara manual dengan mengubah status ujian menjadi `completed`. Endpoint ini berguna ketika:

- Ujian perlu diselesaikan paksa karena kendala teknis
- Waktu ujian habis tapi sistem belum otomatis mengubah status
- Pengawas perlu mengakhiri ujian lebih awal
- Ada situasi darurat yang memerlukan penghentian ujian

---

## 📋 Endpoint Details

**URL:** `POST /api/v1/exams/{exam_id}/complete`

**Response Model:** `ExamPublic`

**Authorization Required:** Yes (Bearer Token)

---

## 🔑 Authorization & Access Control

Endpoint ini hanya dapat diakses oleh:

1. **Admin** - Dapat menyelesaikan ujian apapun
2. **Guru yang ditugaskan** - Hanya ujian yang menjadi tanggung jawabnya
3. **Pengawas (Proctor)** - Ujian yang dia awasi (berdasarkan `proctor_ids`)

---

## 📥 Request Schema

```json
{
  "confirmation": true,
  "reason": "Optional reason for completing exam manually"
}
```

### Parameters:

- **confirmation** (boolean, required): Harus `true` sebagai konfirmasi
- **reason** (string, optional): Alasan menyelesaikan ujian secara manual

---

## 📤 Response Examples

### ✅ Success Response (200)

```json
{
  "_id": "68920557e58cfa66adfcdd7f",
  "title": "Ujian Matematika Semester 1",
  "exam_type": "official_uts",
  "duration_minutes": 120,
  "availability_start_time": "2025-01-10T08:00:00Z",
  "availability_end_time": "2025-01-10T10:00:00Z",
  "status": "completed",
  "completed_at": "2025-01-10T09:30:15Z",
  "completed_by": "68822f07979cbba23e6db950",
  "completion_reason": "Sistem bermasalah, diselesaikan manual",
  "settings": {
    "shuffle_questions": true,
    "shuffle_options": true,
    "show_results_after_submission": false
  },
  "teaching_assignment_id": "68920557e58cfa66adfcdd8a",
  "proctor_ids": ["68822f07979cbba23e6db950"],
  "academic_period_id": "68920557e58cfa66adfcdd9a"
}
```

### ❌ Error Responses

#### 400 - Bad Request (Confirmation Required)
```json
{
  "detail": "Confirmation is required to complete the exam manually"
}
```

#### 400 - Bad Request (Exam Already Completed)
```json
{
  "detail": "Exam is already completed"
}
```

#### 400 - Bad Request (Invalid Status)
```json
{
  "detail": "Cannot complete exam with status 'pending_questions'. Exam must be started (ongoing) first."
}
```

#### 403 - Forbidden
```json
{
  "detail": "You are not authorized to complete this exam. Only admin, assigned teacher, or proctors can complete exams manually."
}
```

#### 404 - Not Found
```json
{
  "detail": "Exam not found"
}
```

---

## 🧪 Testing Examples

### Using cURL

```bash
# Get JWT Token first
export TOKEN="your_jwt_token_here"
export EXAM_ID="68920557e58cfa66adfcdd7f"

# Complete exam with reason
curl -X POST "http://localhost:8000/api/v1/exams/$EXAM_ID/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation": true,
    "reason": "Kendala teknis pada server, ujian diselesaikan manual"
  }'

# Complete exam without reason
curl -X POST "http://localhost:8000/api/v1/exams/$EXAM_ID/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation": true
  }'
```

### Using JavaScript/Fetch

```javascript
const completeExam = async (examId, reason = null) => {
  try {
    const response = await fetch(`/api/v1/exams/${examId}/complete`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        confirmation: true,
        reason: reason
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }
    
    const completedExam = await response.json();
    console.log('Exam completed successfully:', completedExam);
    return completedExam;
    
  } catch (error) {
    console.error('Error completing exam:', error.message);
    throw error;
  }
};

// Usage
completeExam('68920557e58cfa66adfcdd7f', 'Sistem bermasalah')
  .then(exam => {
    alert(`Ujian "${exam.title}" berhasil diselesaikan!`);
  })
  .catch(error => {
    alert(`Error: ${error.message}`);
  });
```

---

## ⚠️ Validations & Business Rules

### 1. **Confirmation Required**
```javascript
// Request harus include confirmation: true
{
  "confirmation": true  // Wajib dan harus true
}
```

### 2. **Status Validation**
Ujian hanya bisa diselesaikan jika statusnya **BUKAN**:
- `pending_questions` (belum ada soal)
- `ready` (belum dimulai)

Status yang valid untuk diselesaikan:
- `ongoing` (sedang berlangsung)
- `submitted` (sudah ada submission)

### 3. **Authorization Hierarchy**
```
Admin > Teacher (assigned) > Proctor
```

### 4. **Audit Logging**
Setiap completion akan dicatat dengan:
- User ID yang melakukan
- Role user (admin/teacher/proctor)  
- Timestamp
- Reason (jika ada)
- Status sebelumnya

---

## 📊 Database Changes

Ketika ujian diselesaikan manual, field berikut akan ditambahkan/diupdate:

```javascript
{
  "status": "completed",
  "completed_at": "2025-01-10T09:30:15Z",      // Timestamp completion
  "completed_by": "68822f07979cbba23e6db950",   // User ID yang complete
  "completion_reason": "Optional reason",        // Alasan jika ada
  "updated_at": "2025-01-10T09:30:15Z"          // Update timestamp
}
```

---

## 🔄 Integration with Other Systems

### 1. **Teacher Analytics**
Ujian yang diselesaikan manual tetap bisa di-generate analytics:
```bash
POST /api/v1/teacher-analytics/exams/{exam_id}/analytics/generate
```

### 2. **WebSocket Notifications** (Future Enhancement)
```javascript
// Notifikasi ke siswa (commented out di code)
{
  "type": "EXAM_COMPLETED",
  "exam_id": "68920557e58cfa66adfcdd7f", 
  "message": "Ujian telah diselesaikan oleh pengawas"
}
```

### 3. **Activity Logs**
Sistem akan log aktivitas completion:
```
EXAM_COMPLETE_MANUAL: TEACHER 68822f07979cbba23e6db950 manually completing exam 68920557e58cfa66adfcdd7f. Previous status: ongoing. Reason: Sistem bermasalah
```

---

## 💡 Use Cases & Scenarios

### **Scenario 1: Sistem Bermasalah**
```json
{
  "confirmation": true,
  "reason": "Server database bermasalah, siswa tidak bisa submit"
}
```

### **Scenario 2: Waktu Habis**
```json
{
  "confirmation": true,
  "reason": "Waktu ujian habis, sistem belum auto-complete"
}
```

### **Scenario 3: Situasi Darurat**
```json
{
  "confirmation": true,
  "reason": "Gempa bumi, ujian dihentikan untuk evakuasi"
}
```

### **Scenario 4: Permintaan Siswa**
```json
{
  "confirmation": true,
  "reason": "Mayoritas siswa sudah selesai, diminta untuk diakhiri"
}
```

---

## 🛡️ Security Considerations

### 1. **Access Control**
- Triple validation: Admin OR Teacher OR Proctor
- ObjectId validation untuk exam_id
- JWT token validation

### 2. **Audit Trail**
- Semua aktivitas tercatat di log
- User tracking dengan role
- Reason tracking untuk accountability

### 3. **Business Logic Protection**
- Prevent completion of non-started exams
- Prevent double completion
- Confirmation required to prevent accidental completion

---

## 🎯 Best Practices

### 1. **Frontend Implementation**
```javascript
// Tampilkan konfirmasi dialog
const confirmCompletion = () => {
  const reason = prompt("Alasan menyelesaikan ujian (opsional):");
  
  if (confirm("Yakin ingin menyelesaikan ujian ini?")) {
    completeExam(examId, reason);
  }
};
```

### 2. **Error Handling**
```javascript
// Handle berbagai error scenarios
const handleCompletionError = (error) => {
  if (error.message.includes("Confirmation is required")) {
    alert("Konfirmasi diperlukan untuk menyelesaikan ujian");
  } else if (error.message.includes("not authorized")) {
    alert("Anda tidak memiliki akses untuk menyelesaikan ujian ini");
  } else if (error.message.includes("already completed")) {
    alert("Ujian sudah diselesaikan sebelumnya");
  } else {
    alert("Terjadi kesalahan: " + error.message);
  }
};
```

### 3. **Status Checking**
```javascript
// Cek status ujian sebelum complete
const canCompleteExam = (exam) => {
  const validStatuses = ['ongoing', 'submitted'];
  return validStatuses.includes(exam.status);
};
```

---

## ✅ Success Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "completed" |
| `completed_at` | datetime | Timestamp saat diselesaikan |
| `completed_by` | ObjectId | ID user yang menyelesaikan |
| `completion_reason` | string | Alasan completion (optional) |
| `updated_at` | datetime | Timestamp update terakhir |

---

Endpoint ini memberikan kontrol penuh kepada admin, guru, dan pengawas untuk mengelola lifecycle ujian dengan accountability yang baik melalui audit logging dan authorization yang ketat! 🚀
