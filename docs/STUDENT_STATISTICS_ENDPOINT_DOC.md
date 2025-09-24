# 📊 Student Statistics Endpoint Documentation

## 🎯 Overview

Endpoint baru untuk mendapatkan statistik lengkap siswa yang mencakup performa individu dan perbandingan dengan kelas. Siswa dapat melihat performa mereka sendiri dan membandingkannya langsung dengan performa kelas.

## 🔗 Endpoint Details

**URL:** `GET /api/v1/score-analytics/student/my-statistics`

**Authentication:** Bearer Token (Required)

**Authorization:** Hanya siswa yang dapat mengakses endpoint ini untuk melihat statistik mereka sendiri

## 📋 Response Format

```json
{
  "student_statistics": {
    "overall_average_student": 85.5,
    "best_score_student": 95.0,
    "latest_score_student": 88.0,
    "participant_rate": 85.7,
    "trend_scores_student": [
      {
        "exam_date": "2024-03-15T10:00:00Z",
        "score": 88.0
      },
      {
        "exam_date": "2024-03-10T09:30:00Z", 
        "score": 92.0
      }
    ],
    "score_distribution_student": [
      {
        "range": "81-100",
        "count": 8,
        "percentage": 80.0
      },
      {
        "range": "61-80",
        "count": 2,
        "percentage": 20.0
      },
      {
        "range": "41-60",
        "count": 0,
        "percentage": 0.0
      },
      {
        "range": "21-40",
        "count": 0,
        "percentage": 0.0
      },
      {
        "range": "0-20",
        "count": 0,
        "percentage": 0.0
      }
    ]
  },
  "class_statistics": {
    "overall_average_class": 78.2,
    "class_highest": 98.0,
    "class_lowest": 45.0,
    "trend_scores_class": [
      {
        "exam_date": "2024-03-15T10:00:00Z",
        "average_score": 79.5
      },
      {
        "exam_date": "2024-03-10T09:30:00Z",
        "average_score": 81.2
      }
    ],
    "score_distribution_class": [
      {
        "range": "81-100",
        "count": 12,
        "percentage": 40.0
      },
      {
        "range": "61-80",
        "count": 15,
        "percentage": 50.0
      },
      {
        "range": "41-60",
        "count": 3,
        "percentage": 10.0
      },
      {
        "range": "21-40",
        "count": 0,
        "percentage": 0.0
      },
      {
        "range": "0-20",
        "count": 0,
        "percentage": 0.0
      }
    ]
  }
}
```

## 📊 Field Descriptions

### Student Statistics (Individual)

| Field | Type | Description |
|-------|------|-------------|
| `overall_average_student` | float | Rata-rata nilai dari semua ujian yang sudah dikerjakan siswa |
| `best_score_student` | float | Nilai tertinggi yang pernah dicapai siswa |
| `latest_score_student` | float | Nilai ujian terakhir yang dikerjakan siswa |
| `participant_rate` | float | Persentase keikutsertaan siswa dalam ujian kelas (0-100%) |
| `trend_scores_student` | array | 10 nilai ujian terakhir dengan tanggal ujian |
| `score_distribution_student` | array | Distribusi nilai siswa dalam 5 rentang standar |

### Class Statistics (Comparative)

| Field | Type | Description |
|-------|------|-------------|
| `overall_average_class` | float | Rata-rata nilai semua siswa dalam kelas |
| `class_highest` | float | Nilai tertinggi dalam kelas |
| `class_lowest` | float | Nilai terendah dalam kelas |
| `trend_scores_class` | array | 10 data nilai ujian terakhir kelas (rata-rata per ujian) |
| `score_distribution_class` | array | Distribusi nilai seluruh siswa dalam kelas |

### Score Distribution Format

```json
{
  "range": "81-100",    // Rentang nilai
  "count": 12,          // Jumlah nilai dalam rentang
  "percentage": 40.0    // Persentase dari total
}
```

**Standard Ranges:** 0-20, 21-40, 41-60, 61-80, 81-100

## 🔐 Authentication & Authorization

### Required Headers
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Role Requirements
- ✅ **Student**: Dapat mengakses statistik mereka sendiri
- ❌ **Teacher**: Tidak dapat mengakses endpoint ini
- ❌ **Admin**: Tidak dapat mengakses endpoint ini

### How to Get Access Token
```bash
# Login as student
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=student_login_id&password=student_password"
```

## 🚀 Usage Examples

### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/score-analytics/student/my-statistics" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Python (httpx)
```python
import httpx

async def get_my_statistics(access_token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(
            "http://localhost:8000/api/v1/score-analytics/student/my-statistics",
            headers=headers
        )
        return response.json()
```

### JavaScript (fetch)
```javascript
const getMyStatistics = async (accessToken) => {
  const response = await fetch('/api/v1/score-analytics/student/my-statistics', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};
```

## ⚡ Performance Features

### Caching Strategy
- **Cache Duration:** 1 hour (3600 seconds)
- **Cache Keys:** Unique per student and academic period
- **Cache Invalidation:** Automatic when exam sessions are updated

### Database Optimization
- Uses MongoDB aggregation pipelines for efficient queries
- Minimal data transfer with proper projection
- Indexes should be present on frequently queried fields

## 🛡️ Error Handling

### HTTP Status Codes

| Status | Description |
|--------|-------------|
| `200` | Success - Statistics retrieved |
| `401` | Unauthorized - Invalid or missing token |
| `403` | Forbidden - User is not a student |
| `500` | Internal Server Error - Database or processing error |

### Error Response Format
```json
{
  "detail": "Error message in Indonesian"
}
```

### Common Errors

1. **403 Forbidden**
   ```json
   {
     "detail": "Endpoint ini hanya dapat diakses oleh siswa"
   }
   ```

2. **500 Internal Server Error**
   ```json
   {
     "detail": "Terjadi kesalahan saat mengambil statistik siswa"
   }
   ```

## 📐 Data Calculations

### Participant Rate Calculation
```
participant_rate = (jumlah ujian yang dikerjakan siswa / total ujian kelas) * 100
```

- Hanya menghitung exam sessions dengan status "graded"
- Total ujian kelas dihitung berdasarkan teaching assignments untuk kelas siswa
- Dibatasi pada periode akademik aktif saat ini

### Score Distribution
- Menggunakan 5 rentang standar: 0-20, 21-40, 41-60, 61-80, 81-100
- Count: jumlah nilai dalam rentang
- Percentage: (count / total_scores) * 100

### Trend Data
- Diurutkan berdasarkan tanggal ujian terbaru
- Maksimal 10 data terakhir
- Format: array of objects dengan exam_date dan score/average_score

## 🔄 Cache Invalidation

Cache akan otomatis di-invalidate ketika:
- Exam session baru ditambahkan/diupdate
- Status exam session berubah menjadi "graded"
- Data user atau profile siswa berubah

## 🧪 Testing

### Unit Test
```bash
# Test database functions
python test_student_statistics_endpoint.py
```

### API Integration Test
```bash
# Test full API endpoint (requires server running)
python test_my_statistics_endpoint.py
```

### Manual Testing
1. Start FastAPI server: `uvicorn app.main:app --reload`
2. Login as student to get token
3. Call the endpoint with the token
4. Verify response format and data

## 📈 Implementation Files

### Modified Files
- `app/api/v1/routes/score_analytics.py` - New endpoint implementation
- `app/crud/crud_score_analytics.py` - CRUD functions for calculations
- `app/schemas/score_analytics.py` - Response models and validation

### New Functions
- `get_student_individual_statistics()` - Individual student metrics
- `get_student_class_statistics()` - Class comparative metrics  
- `get_combined_student_statistics()` - Combined response
- `get_my_student_statistics()` - API endpoint handler

## 🎯 Usage for Frontend Development

Endpoint ini cocok untuk:
- **Dashboard siswa** - Menampilkan overview performa
- **Progress tracking** - Monitoring perkembangan nilai
- **Class comparison** - Membandingkan dengan teman sekelas
- **Data visualization** - Charts dan graphs untuk trend
- **Motivational features** - Progress indicators dan achievements

## ✅ Validation

Semua field wajib ada dalam response, bahkan jika nilainya 0/null/empty array, sesuai dengan requirement yang diminta.

## 🚀 Ready for Production

Endpoint ini sudah siap digunakan dengan features:
- ✅ Proper authentication & authorization
- ✅ Intelligent caching
- ✅ Error handling
- ✅ Performance optimization
- ✅ Consistent response format
- ✅ Comprehensive testing
