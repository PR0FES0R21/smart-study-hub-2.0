# Admin Score Trend Analytics - Contoh Data

## Skenario: Sekolah dengan 22 Kelas, 30 Siswa per Kelas (Total: 660 Siswa)

### 1️⃣ **group_by="class"** - Rata-rata per Kelas

**Request:**
```bash
GET /api/v1/analytics/score-trend?group_by=class
```

**Response akan menampilkan 22 series (satu untuk setiap kelas):**
```json
{
  "series": [
    {
      "label": "Kelas 10-A",
      "data": [
        {
          "date": "2025-08-01T10:00:00Z",
          "score": 82.3,  // Rata-rata 30 siswa kelas 10-A
          "exam_id": "...",
          "exam_title": "UTS Matematika"
        },
        {
          "date": "2025-08-15T10:00:00Z", 
          "score": 85.1,  // Rata-rata 30 siswa kelas 10-A
          "exam_id": "...",
          "exam_title": "Quiz Harian"
        }
      ],
      "metadata": {
        "class_id": "...",
        "grade_level": 10,
        "total_students": 30
      }
    },
    {
      "label": "Kelas 10-B",
      "data": [
        {
          "date": "2025-08-01T10:00:00Z",
          "score": 78.9,  // Rata-rata 30 siswa kelas 10-B
          "exam_id": "...",
          "exam_title": "UTS Matematika" 
        }
      ],
      "metadata": {
        "class_id": "...",
        "grade_level": 10,
        "total_students": 30
      }
    }
    // ... 20 kelas lainnya
  ]
}
```

### 2️⃣ **group_by="grade"** - Rata-rata per Jenjang

**Request:**
```bash
GET /api/v1/analytics/score-trend?group_by=grade
```

**Response akan menampilkan 3 series (untuk kelas 10, 11, 12):**
```json
{
  "series": [
    {
      "label": "Kelas 10", 
      "data": [
        {
          "date": "2025-08-01T10:00:00Z",
          "score": 80.5,  // Rata-rata SEMUA siswa kelas 10 (8 kelas × 30 = 240 siswa)
          "exam_id": "...",
          "exam_title": "UTS Matematika"
        }
      ],
      "metadata": {
        "grade_level": 10,
        "total_students": 240
      }
    },
    {
      "label": "Kelas 11",
      "data": [
        {
          "date": "2025-08-01T10:00:00Z", 
          "score": 82.1,  // Rata-rata SEMUA siswa kelas 11 (7 kelas × 30 = 210 siswa)
          "exam_id": "...",
          "exam_title": "UTS Matematika"
        }
      ],
      "metadata": {
        "grade_level": 11,
        "total_students": 210
      }
    },
    {
      "label": "Kelas 12",
      "data": [
        {
          "date": "2025-08-01T10:00:00Z",
          "score": 84.2,  // Rata-rata SEMUA siswa kelas 12 (7 kelas × 30 = 210 siswa)
          "exam_id": "...",
          "exam_title": "UTS Matematika"
        }
      ],
      "metadata": {
        "grade_level": 12,
        "total_students": 210
      }
    }
  ]
}
```

### 3️⃣ **group_by="subject"** - Rata-rata per Mata Pelajaran

**Request:**
```bash
GET /api/v1/analytics/score-trend?group_by=subject
```

**Response akan menampilkan series per mata pelajaran:**
```json
{
  "series": [
    {
      "label": "Matematika",
      "data": [
        {
          "date": "2025-08-01T10:00:00Z",
          "score": 78.4,  // Rata-rata SEMUA siswa yang ikut ujian Matematika
          "exam_id": "...",
          "exam_title": "UTS Matematika"
        }
      ],
      "metadata": {
        "subject_id": "...",
        "subject_code": "MTK",
        "total_exams": 22  // 22 ujian (satu per kelas)
      }
    },
    {
      "label": "Bahasa Indonesia", 
      "data": [
        {
          "date": "2025-08-05T10:00:00Z",
          "score": 82.1,  // Rata-rata SEMUA siswa yang ikut ujian B.Indo
          "exam_id": "...",
          "exam_title": "UTS Bahasa Indonesia"
        }
      ]
    }
    // ... mata pelajaran lainnya
  ]
}
```

## 🔧 **Bagaimana Aggregation Bekerja**

### MongoDB Aggregation Pipeline:
1. **Match**: Filter exam_sessions yang sudah submitted/graded
2. **Lookup**: Join dengan exams, classes, subjects, teachers
3. **Group**: 
   - Jika `group_by="class"`: Group by class_id, hitung rata-rata score
   - Jika `group_by="grade"`: Group by grade_level, hitung rata-rata score  
   - Jika `group_by="subject"`: Group by subject_id, hitung rata-rata score
4. **Project**: Format output untuk chart

### Contoh Aggregation untuk group_by="class":
```javascript
[
  // Match submitted sessions
  { $match: { status: "submitted", score: { $ne: null } } },
  
  // Join dengan exam, class, subject data
  { $lookup: { from: "exams", ... } },
  { $lookup: { from: "classes", ... } },
  
  // Group by class dan tanggal ujian
  {
    $group: {
      _id: {
        class_id: "$class_id",
        exam_id: "$exam_id",
        date: { $dateToString: { format: "%Y-%m-%d", date: "$submitted_at" } }
      },
      avg_score: { $avg: "$score" },
      exam_title: { $first: "$exam.title" },
      class_name: { $first: "$class.name" },
      grade_level: { $first: "$class.grade_level" },
      exam_date: { $first: "$submitted_at" },
      student_count: { $sum: 1 }
    }
  },
  
  // Sort by date
  { $sort: { "exam_date": 1 } }
]
```

## 🎛️ **Filtering Options untuk Admin**

Admin bisa memfilter data lebih spesifik:

### Filter by Grade Level:
```bash
GET /api/v1/analytics/score-trend?grade_level=12&group_by=class
# Hasil: Hanya kelas 12 (7 kelas) yang ditampilkan
```

### Filter by Class:
```bash
GET /api/v1/analytics/score-trend?class_id=60d21b4667d0d8992e610c86&group_by=student
# Hasil: 30 series (satu per siswa di kelas tersebut)
```

### Filter by Subject:
```bash  
GET /api/v1/analytics/score-trend?subject_id=60d21b4667d0d8992e610c87&group_by=class
# Hasil: Hanya ujian Matematika dari semua kelas
```

### Filter by Date Range:
```bash
GET /api/v1/analytics/score-trend?start_date=2025-08-01&end_date=2025-08-31&group_by=grade
# Hasil: Hanya ujian bulan Agustus, digroup per jenjang
```

## 📈 **Visualisasi Chart**

Dengan 22 kelas, chart akan terlihat seperti:

### Line Chart (group_by="class"):
- **22 garis** berbeda warna untuk setiap kelas
- X-axis: Timeline ujian
- Y-axis: Rata-rata nilai (0-100)
- Tooltip: Detail kelas, jumlah siswa, nama ujian

### Bar Chart (group_by="grade"):
- **3 bar series** untuk kelas 10, 11, 12
- Setiap ujian = satu grup bar
- Mudah membandingkan performa antar jenjang

## ⚡ **Performance Considerations**

Untuk 660 siswa dengan banyak ujian:
- **Aggregation di database** - tidak load semua data ke memory
- **Caching** - result di-cache 30 menit
- **Pagination** - bisa limit jumlah data points
- **Indexing** - MongoDB index pada exam_id, class_id, submitted_at

## 🔍 **Real-World Usage**

**Kepala Sekolah ingin melihat:**
1. **Tren per jenjang**: `group_by=grade` → Lihat kelas mana yang butuh attention
2. **Comparison kelas paralel**: `grade_level=12&group_by=class` → Bandingkan 12-A vs 12-B vs 12-C
3. **Performance per mata pelajaran**: `group_by=subject` → Subject mana yang sulit
4. **Monthly progress**: `start_date=2025-08-01&end_date=2025-08-31` → Progress bulanan

**Data yang dihasilkan:** Actionable insights, bukan overwhelm dengan 660 individual scores!
