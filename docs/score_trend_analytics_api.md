# Score Trend Analytics API Documentation

## Overview

Score Trend Analytics menyediakan analisis trend nilai ujian berdasarkan role pengguna dengan filtering yang fleksibel. API ini mendukung 3 role utama:

1. **Student**: Hanya dapat melihat trend nilai pribadi
2. **Teacher**: Dapat melihat trend kelas dan mata pelajaran yang diajar  
3. **Admin**: Dapat melihat semua trend dengan filtering lengkap

## Endpoints

### GET /api/v1/analytics/score-trend

**Parameters:**
- `start_date` (optional): Tanggal mulai analisis (ISO format)
- `end_date` (optional): Tanggal akhir analisis (ISO format)
- `class_id` (optional): Filter berdasarkan ID kelas
- `grade_level` (optional): Filter berdasarkan jenjang kelas
- `subject_id` (optional): Filter berdasarkan mata pelajaran
- `expertise_id` (optional): Filter berdasarkan program keahlian
- `teacher_id` (optional): Filter berdasarkan guru (admin only)
- `student_id` (optional): Filter berdasarkan siswa (admin only)
- `academic_period_id` (optional): Filter berdasarkan periode akademik
- `group_by` (default: "class"): Pengelompokan data ("class", "subject", "grade", "teacher", "student")

### POST /api/v1/analytics/score-trend

**Request Body:**
```json
{
  "start_date": "2025-07-01T00:00:00Z",
  "end_date": "2025-09-30T00:00:00Z",
  "class_id": "60d21b4667d0d8992e610c86",
  "grade_level": 12,
  "subject_id": "60d21b4667d0d8992e610c87",
  "group_by": "class"
}
```

## Response Format

```json
{
  "series": [
    {
      "label": "Kelas 12 RPL 1",
      "data": [
        {
          "date": "2025-08-01T00:00:00Z",
          "score": 85.5,
          "exam_id": "60d21b4667d0d8992e610c85",
          "exam_title": "Ulangan Tengah Semester",
          "subject_name": "Matematika",
          "subject_code": "MTK"
        },
        {
          "date": "2025-08-15T00:00:00Z",
          "score": 78.2,
          "exam_id": "60d21b4667d0d8992e610c86",
          "exam_title": "Quiz Harian",
          "subject_name": "Matematika",
          "subject_code": "MTK"
        }
      ],
      "metadata": {
        "class_id": "60d21b4667d0d8992e610c86",
        "grade_level": 12,
        "student_count": 30,
        "expertise_abbreviation": "RPL",
        "expertise_name": "Rekayasa Perangkat Lunak"
      }
    }
  ],
  "metadata": {
    "user_role": ["teacher"],
    "group_by": "class",
    "filters_applied": {
      "date_range": {
        "start": "2025-07-01T00:00:00Z",
        "end": "2025-09-30T00:00:00Z"
      },
      "class_id": "60d21b4667d0d8992e610c86"
    },
    "generated_at": "2025-09-06T17:45:00Z"
  }
}
```

## Role-Based Access Control

### Student Role
**Akses:** Hanya data pribadi
**Parameter yang tersedia:**
- `start_date`, `end_date`
- `group_by` (diabaikan, selalu menampilkan data personal)

**Contoh Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/score-trend?start_date=2025-08-01T00:00:00Z&end_date=2025-09-01T00:00:00Z" \
  -H "Authorization: Bearer <student_token>"
```

**Contoh Response (Student):**
```json
{
  "series": [
    {
      "label": "Nilai Saya",
      "data": [
        {
          "date": "2025-08-05T10:30:00Z",
          "score": 85.0,
          "exam_id": "60d21b4667d0d8992e610c85",
          "exam_title": "Ulangan Matematika",
          "subject_name": "Matematika",
          "subject_code": "MTK"
        }
      ],
      "metadata": {
        "student_id": "60d21b4667d0d8992e610c89"
      }
    }
  ],
  "metadata": {
    "user_role": ["student"],
    "group_by": "student"
  }
}
```

### Teacher Role
**Akses:** Kelas dan mata pelajaran yang diajar
**Parameter yang tersedia:**
- `start_date`, `end_date`, `class_id`, `subject_id`, `group_by`

**Contoh Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/score-trend?group_by=subject&start_date=2025-08-01T00:00:00Z" \
  -H "Authorization: Bearer <teacher_token>"
```

**Contoh Response (Teacher):**
```json
{
  "series": [
    {
      "label": "Matematika",
      "data": [
        {
          "date": "2025-08-05T10:30:00Z",
          "score": 82.3,
          "exam_id": "60d21b4667d0d8992e610c85",
          "exam_title": "Ulangan Harian",
          "subject_name": "Matematika",
          "subject_code": "MTK"
        }
      ],
      "metadata": {
        "subject_id": "60d21b4667d0d8992e610c87",
        "subject_code": "MTK"
      }
    }
  ],
  "metadata": {
    "user_role": ["teacher"],
    "group_by": "subject"
  }
}
```

### Admin Role
**Akses:** Semua data dengan filtering lengkap
**Parameter yang tersedia:** Semua parameter

**Contoh Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/analytics/score-trend" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "grade_level": 12,
    "group_by": "class",
    "start_date": "2025-08-01T00:00:00Z",
    "end_date": "2025-09-01T00:00:00Z"
  }'
```

**Contoh Response (Admin):**
```json
{
  "series": [
    {
      "label": "Kelas 12-A",
      "data": [
        {
          "date": "2025-08-05T10:30:00Z",
          "score": 85.2,
          "exam_id": "60d21b4667d0d8992e610c85",
          "exam_title": "UTS Matematika",
          "subject_name": "Matematika",
          "subject_code": "MTK"
        }
      ],
      "metadata": {
        "class_id": "60d21b4667d0d8992e610c86",
        "grade_level": 12,
        "expertise_id": "60d21b4667d0d8992e610c90"
      }
    },
    {
      "label": "Kelas 12-B",
      "data": [
        {
          "date": "2025-08-05T10:30:00Z",
          "score": 78.8,
          "exam_id": "60d21b4667d0d8992e610c85",
          "exam_title": "UTS Matematika",
          "subject_name": "Matematika",
          "subject_code": "MTK"
        }
      ],
      "metadata": {
        "class_id": "60d21b4667d0d8992e610c87",
        "grade_level": 12,
        "expertise_id": "60d21b4667d0d8992e610c91"
      }
    }
  ],
  "metadata": {
    "user_role": ["admin"],
    "group_by": "class",
    "filters_applied": {
      "date_range": {
        "start": "2025-08-01T00:00:00Z",
        "end": "2025-09-01T00:00:00Z"
      },
      "grade_level": 12
    }
  }
}
```

## Chart Implementation Examples

### Chart.js Example
```javascript
// Fetch data
const response = await fetch('/api/v1/analytics/score-trend?group_by=class', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await response.json();

// Prepare Chart.js datasets
const datasets = data.series.map((series, index) => ({
  label: series.label,
  data: series.data.map(point => ({
    x: new Date(point.date),
    y: point.score
  })),
  borderColor: colors[index % colors.length],
  backgroundColor: colors[index % colors.length] + '20',
  fill: false
}));

// Create chart
new Chart(ctx, {
  type: 'line',
  data: { datasets },
  options: {
    responsive: true,
    scales: {
      x: { type: 'time', time: { unit: 'day' } },
      y: { beginAtZero: true, max: 100 }
    },
    plugins: {
      tooltip: {
        callbacks: {
          afterLabel: (context) => {
            const dataPoint = data.series[context.datasetIndex].data[context.dataIndex];
            return [`Ujian: ${dataPoint.exam_title}`, `Mata Pelajaran: ${dataPoint.subject_name}`];
          }
        }
      }
    }
  }
});
```

### ApexCharts Example
```javascript
const response = await fetch('/api/v1/analytics/score-trend?group_by=subject');
const data = await response.json();

const options = {
  chart: { type: 'line', height: 400 },
  series: data.series.map(series => ({
    name: series.label,
    data: series.data.map(point => [new Date(point.date).getTime(), point.score])
  })),
  xaxis: { type: 'datetime' },
  yaxis: { min: 0, max: 100 },
  tooltip: {
    custom: ({ series, seriesIndex, dataPointIndex }) => {
      const dataPoint = data.series[seriesIndex].data[dataPointIndex];
      return `<div class="custom-tooltip">
        <strong>${dataPoint.exam_title}</strong><br/>
        Score: ${dataPoint.score}<br/>
        Subject: ${dataPoint.subject_name}
      </div>`;
    }
  }
};

const chart = new ApexCharts(document.querySelector("#chart"), options);
chart.render();
```

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "detail": "group_by must be one of ['class', 'subject', 'grade', 'teacher', 'student']"
}
```

**403 Forbidden:**
```json
{
  "detail": "You can only view analytics for your own classes"
}
```

**404 Not Found:**
```json
{
  "detail": "No data found for the specified filters"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error: Database connection failed"
}
```

## Performance Notes

- Data di-cache selama 30 menit untuk query yang sama
- Aggregation menggunakan MongoDB pipeline untuk performa optimal
- Default date range: 3 bulan terakhir jika tidak dispesifikasi
- Maksimal 1000 data points per series untuk menghindari overload

## Changelog

### v1.0.0 (2025-09-06)
- Initial release dengan role-based access control
- Support untuk grouping berdasarkan class, subject, grade, teacher, student
- Optimized MongoDB aggregation pipeline
- Comprehensive error handling dan logging
