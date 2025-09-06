# Admin Use Case: SMK dengan 22 Kelas

## 📊 **Skenario Real**
- **SMK Teknologi**: 22 kelas (10A-10H, 11A-11G, 12A-12G)
- **Total siswa**: 660 siswa (30 siswa per kelas)
- **Mata pelajaran**: 8 mata pelajaran utama
- **Periode**: Semester ganjil 2025/2026

## 🎯 **Admin Request Examples**

### 1. **Overview Semua Kelas** - `group_by=class`
```bash
GET /api/v1/analytics/score-trend?group_by=class&start_date=2025-08-01
```

**Hasil yang akan diterima Admin:**
```json
{
  "series": [
    {
      "label": "Kelas 10-A",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 82.3, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 79.5, "exam_title": "Quiz B.Indonesia"},
        {"date": "2025-08-19T10:00:00Z", "score": 85.1, "exam_title": "UTS Fisika"}
      ],
      "metadata": {"student_count": 30, "grade_level": 10}
    },
    {
      "label": "Kelas 10-B", 
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 78.9, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 81.2, "exam_title": "Quiz B.Indonesia"}
      ],
      "metadata": {"student_count": 29, "grade_level": 10}
    }
    // ... 20 kelas lainnya
  ],
  "metadata": {
    "user_role": ["admin"],
    "group_by": "class"
  }
}
```

**Chart akan menampilkan:** 22 garis trend, satu untuk setiap kelas

---

### 2. **Comparison per Jenjang** - `group_by=grade`
```bash
GET /api/v1/analytics/score-trend?group_by=grade
```

**Hasil yang akan diterima Admin:**
```json
{
  "series": [
    {
      "label": "Kelas 10",
      "data": [
        {
          "date": "2025-08-05T10:00:00Z", 
          "score": 80.2,  // Rata-rata dari 8 kelas × 30 siswa = 240 siswa
          "exam_title": "UTS Matematika"
        },
        {
          "date": "2025-08-12T10:00:00Z",
          "score": 78.9,  // Rata-rata quiz B.Indonesia untuk seluruh kelas 10
          "exam_title": "Quiz B.Indonesia"
        }
      ],
      "metadata": {"student_count": 240, "grade_level": 10}
    },
    {
      "label": "Kelas 11",
      "data": [
        {
          "date": "2025-08-05T10:00:00Z",
          "score": 82.1,  // Rata-rata dari 7 kelas × 30 siswa = 210 siswa
          "exam_title": "UTS Matematika"
        }
      ],
      "metadata": {"student_count": 210, "grade_level": 11}
    },
    {
      "label": "Kelas 12",
      "data": [
        {
          "date": "2025-08-05T10:00:00Z",
          "score": 84.2,  // Rata-rata dari 7 kelas × 30 siswa = 210 siswa
          "exam_title": "UTS Matematika"
        }
      ],
      "metadata": {"student_count": 210, "grade_level": 12}
    }
  ]
}
```

**Chart akan menampilkan:** 3 garis trend untuk jenjang 10, 11, 12

---

### 3. **Analysis per Mata Pelajaran** - `group_by=subject`
```bash
GET /api/v1/analytics/score-trend?group_by=subject
```

**Hasil yang akan diterima Admin:**
```json
{
  "series": [
    {
      "label": "Matematika",
      "data": [
        {
          "date": "2025-08-05T10:00:00Z",
          "score": 78.4,  // Rata-rata SEMUA siswa yang ikut ujian Matematika
          "exam_title": "UTS Matematika"
        },
        {
          "date": "2025-08-26T10:00:00Z",
          "score": 81.2,  // Quiz Matematika berikutnya
          "exam_title": "Quiz Matematika Lanjutan"
        }
      ],
      "metadata": {"student_count": 660, "subject_code": "MTK"}
    },
    {
      "label": "Bahasa Indonesia",
      "data": [
        {
          "date": "2025-08-12T10:00:00Z", 
          "score": 82.1,  // Rata-rata SEMUA siswa yang ikut ujian B.Indo
          "exam_title": "Quiz B.Indonesia"
        }
      ],
      "metadata": {"student_count": 660, "subject_code": "BIND"}
    }
    // ... 6 mata pelajaran lainnya
  ]
}
```

**Chart akan menampilkan:** 8 garis trend untuk setiap mata pelajaran

---

### 4. **Focus pada Kelas 12 saja** - Filter + Group
```bash
GET /api/v1/analytics/score-trend?grade_level=12&group_by=class
```

**Hasil yang akan diterima Admin:**
```json
{
  "series": [
    {
      "label": "Kelas 12-A",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 85.2, "exam_title": "UTS Matematika"},
        {"date": "2025-08-19T10:00:00Z", "score": 87.1, "exam_title": "UTS Fisika"}
      ],
      "metadata": {"student_count": 30, "grade_level": 12}
    },
    {
      "label": "Kelas 12-B",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 78.8, "exam_title": "UTS Matematika"},
        {"date": "2025-08-19T10:00:00Z", "score": 82.3, "exam_title": "UTS Fisika"}
      ],
      "metadata": {"student_count": 30, "grade_level": 12}
    }
    // ... 5 kelas 12 lainnya (12-C sampai 12-G)
  ]
}
```

**Chart akan menampilkan:** 7 garis trend hanya untuk kelas 12

---

### 5. **Drill Down ke Kelas Tertentu** - Individual Students
```bash
GET /api/v1/analytics/score-trend?class_id=60d21b4667d0d8992e610c86&group_by=student
```

**Hasil yang akan diterima Admin:**
```json
{
  "series": [
    {
      "label": "Student 688477a78a56906f19d02551",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 85.0, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 78.0, "exam_title": "Quiz B.Indonesia"}
      ],
      "metadata": {"student_count": 1}
    }
    // ... 29 siswa lainnya di kelas tersebut
  ]
}
```

**Chart akan menampilkan:** 30 garis trend untuk setiap siswa di kelas tersebut

---

## 🎪 **Visualisasi Real-World**

### **Chart untuk group_by=class (22 garis)**
```javascript
// Chart.js setup
const colors = [
  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40',
  '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384', '#36A2EB', '#FFCE56',
  // ... 22 warna berbeda
];

const chartData = {
  datasets: data.series.map((series, index) => ({
    label: series.label,
    data: series.data.map(point => ({
      x: new Date(point.date),
      y: point.score
    })),
    borderColor: colors[index % colors.length],
    backgroundColor: colors[index % colors.length] + '20',
    fill: false,
    tension: 0.4
  }))
};
```

### **Chart untuk group_by=grade (3 garis tebal)**
```javascript  
const chartData = {
  datasets: data.series.map((series, index) => ({
    label: series.label,
    data: series.data.map(point => ({
      x: new Date(point.date),
      y: point.score
    })),
    borderColor: ['#FF6384', '#36A2EB', '#4BC0C0'][index],
    borderWidth: 4,  // Lebih tebal karena data penting
    fill: false
  }))
};
```

## 💡 **Insights yang Didapat Admin**

### **Dari group_by=class:**
- "Kelas 10-C consistently underperforming - butuh intervention"
- "Kelas 12-A overachiever - bisa jadi role model"
- "Gap performance antar kelas paralel terlalu besar"

### **Dari group_by=grade:**
- "Kelas 12 trend menurun mendekati UN - perlu intensive coaching"
- "Kelas 10 konsisten naik - program adaptasi berhasil"
- "Overall school performance stabil di 80-82"

### **Dari group_by=subject:**
- "Matematika consistently lowest - perlu review kurikulum"
- "Bahasa Indonesia excellent - bisa share best practice"
- "Science subjects need attention - lab equipment issue?"

## 🔧 **MongoDB Query Yang Dijalankan**

Untuk `group_by=class`, query MongoDB:
```javascript
db.exam_sessions.aggregate([
  {$match: {status: "submitted", score: {$ne: null}}},
  // ... lookups ...
  {
    $group: {
      _id: {
        exam_date: {$dateToString: {format: "%Y-%m-%d", date: "$submitted_at"}},
        exam_id: "$exam._id",
        class_id: "$class._id"  // Group by class
      },
      avg_score: {$avg: "$score"},  // Average of ~30 students per class
      student_count: {$sum: 1},
      exam_title: {$first: "$exam.title"},
      class_name: {$first: "$class.name"},
      grade_level: {$first: "$class.grade_level"}
    }
  }
])
```

**Result**: ~22 documents per exam (satu per kelas)

---

## ✅ **Summary**

Admin dengan 22 kelas **TIDAK** akan kewalahan dengan 660 individual data points. Sistem akan:

1. **Agregasi otomatis** - Data di-group sesuai kebutuhan
2. **Meaningful insights** - 22 trend lines untuk class comparison  
3. **Flexible drilling** - Bisa zoom ke grade/subject/individual
4. **Performance optimized** - MongoDB aggregation, bukan raw data
5. **Chart-ready** - Format langsung untuk Chart.js/ApexCharts

**Admin akan melihat trend yang actionable, bukan overwhelmed dengan raw data!** 🎯
