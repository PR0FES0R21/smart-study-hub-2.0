# SMK Class Format Examples

## 🎓 **Format Kelas Baru: "Kelas {grade} {expertise_abbreviation} {class_name}"**

Sekarang sistem akan menampilkan nama kelas yang lebih informatif dan sesuai dengan struktur SMK yang sebenarnya.

### **Contoh SMK dengan 5 Jurusan:**

#### **Kelas 10 (8 kelas total)**
- `Kelas 10 TKJ 1` - Teknik Komputer dan Jaringan kelas 1
- `Kelas 10 TKJ 2` - Teknik Komputer dan Jaringan kelas 2  
- `Kelas 10 RPL 1` - Rekayasa Perangkat Lunak kelas 1
- `Kelas 10 RPL 2` - Rekayasa Perangkat Lunak kelas 2
- `Kelas 10 MM 1` - Multimedia kelas 1
- `Kelas 10 MM 2` - Multimedia kelas 2
- `Kelas 10 TKR 1` - Teknik Kendaraan Ringan kelas 1
- `Kelas 10 TSM 1` - Teknik Sepeda Motor kelas 1

#### **Kelas 11 (7 kelas total)**
- `Kelas 11 TKJ 1` - Teknik Komputer dan Jaringan kelas 1
- `Kelas 11 TKJ 2` - Teknik Komputer dan Jaringan kelas 2
- `Kelas 11 RPL 1` - Rekayasa Perangkat Lunak kelas 1
- `Kelas 11 RPL 2` - Rekayasa Perangkat Lunak kelas 2
- `Kelas 11 MM 1` - Multimedia kelas 1
- `Kelas 11 TKR 1` - Teknik Kendaraan Ringan kelas 1
- `Kelas 11 TSM 1` - Teknik Sepeda Motor kelas 1

#### **Kelas 12 (7 kelas total)**
- `Kelas 12 TKJ 1` - Teknik Komputer dan Jaringan kelas 1
- `Kelas 12 TKJ 2` - Teknik Komputer dan Jaringan kelas 2
- `Kelas 12 RPL 1` - Rekayasa Perangkat Lunak kelas 1
- `Kelas 12 RPL 2` - Rekayasa Perangkat Lunak kelas 2
- `Kelas 12 MM 1` - Multimedia kelas 1
- `Kelas 12 TKR 1` - Teknik Kendaraan Ringan kelas 1
- `Kelas 12 TSM 1` - Teknik Sepeda Motor kelas 1

---

## 📊 **Contoh Response dengan Format Baru**

### **Admin Request: `group_by=class`**
```bash
GET /api/v1/analytics/score-trend?group_by=class&grade_level=12
```

**Response:**
```json
{
  "series": [
    {
      "label": "Kelas 12 TKJ 1",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 82.3, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 79.5, "exam_title": "UTS Pemrograman Dasar"}
      ],
      "metadata": {
        "student_count": 32,
        "grade_level": 12,
        "expertise_abbreviation": "TKJ",
        "expertise_name": "Teknik Komputer dan Jaringan"
      }
    },
    {
      "label": "Kelas 12 TKJ 2",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 78.9, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 82.1, "exam_title": "UTS Pemrograman Dasar"}
      ],
      "metadata": {
        "student_count": 31,
        "grade_level": 12,
        "expertise_abbreviation": "TKJ",
        "expertise_name": "Teknik Komputer dan Jaringan"
      }
    },
    {
      "label": "Kelas 12 RPL 1",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 85.2, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 88.7, "exam_title": "UTS Pemrograman Dasar"}
      ],
      "metadata": {
        "student_count": 30,
        "grade_level": 12,
        "expertise_abbreviation": "RPL",
        "expertise_name": "Rekayasa Perangkat Lunak"
      }
    },
    {
      "label": "Kelas 12 RPL 2",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 83.1, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 86.4, "exam_title": "UTS Pemrograman Dasar"}
      ],
      "metadata": {
        "student_count": 29,
        "grade_level": 12,
        "expertise_abbreviation": "RPL",
        "expertise_name": "Rekayasa Perangkat Lunak"
      }
    },
    {
      "label": "Kelas 12 MM 1",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 81.7, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 84.2, "exam_title": "UTS Desain Grafis"}
      ],
      "metadata": {
        "student_count": 28,
        "grade_level": 12,
        "expertise_abbreviation": "MM",
        "expertise_name": "Multimedia"
      }
    },
    {
      "label": "Kelas 12 TKR 1",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 76.3, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 82.9, "exam_title": "UTS Sistem Kelistrikan"}
      ],
      "metadata": {
        "student_count": 30,
        "grade_level": 12,
        "expertise_abbreviation": "TKR",
        "expertise_name": "Teknik Kendaraan Ringan"
      }
    },
    {
      "label": "Kelas 12 TSM 1",
      "data": [
        {"date": "2025-08-05T10:00:00Z", "score": 75.8, "exam_title": "UTS Matematika"},
        {"date": "2025-08-12T10:00:00Z", "score": 80.1, "exam_title": "UTS Motor Listrik"}
      ],
      "metadata": {
        "student_count": 32,
        "grade_level": 12,
        "expertise_abbreviation": "TSM",
        "expertise_name": "Teknik Sepeda Motor"
      }
    }
  ]
}
```

---

## 📈 **Chart Visualization Benefits**

### **Before (Membingungkan):**
```
- Kelas 12-1
- Kelas 12-2  
- Kelas 12-3
- Kelas 12-4
- Kelas 12-5
- Kelas 12-6
- Kelas 12-7
```
❌ **Tidak jelas:** Kelas mana jurusan apa?

### **After (Informatif):**
```
- Kelas 12 TKJ 1
- Kelas 12 TKJ 2
- Kelas 12 RPL 1
- Kelas 12 RPL 2
- Kelas 12 MM 1
- Kelas 12 TKR 1
- Kelas 12 TSM 1
```
✅ **Jelas:** Langsung tahu jurusan dan paralel kelas

---

## 🎯 **Admin Insights yang Lebih Baik**

Dengan format baru, admin bisa langsung melihat:

### **Performance per Jurusan:**
- **RPL classes** consistently score higher in programming subjects
- **TKJ classes** strong in networking but need help in math
- **MM classes** excel in creative subjects
- **TKR/TSM classes** practical-oriented, theory needs improvement

### **Paralel Class Comparison:**
- `Kelas 12 TKJ 1` vs `Kelas 12 TKJ 2`: Are teaching methods consistent?
- `Kelas 12 RPL 1` vs `Kelas 12 RPL 2`: Resource allocation fair?

### **Subject Relevance:**
- Programming subjects: RPL > TKJ > MM > TKR/TSM
- Math subjects: More consistent across all majors
- Practical subjects: TKR/TSM excel, IT majors struggle

---

## 🔧 **Database Schema Requirements**

Pastikan data di MongoDB sudah sesuai:

### **Classes Collection:**
```json
{
  "_id": ObjectId("..."),
  "grade_level": 12,
  "name": "1",  // Class number/name
  "expertise_id": ObjectId("..."),  // Reference to expertise_programs
  "academic_year": "2025/2026"
}
```

### **Expertise Programs Collection:**
```json
{
  "_id": ObjectId("..."),
  "name": "Teknik Komputer dan Jaringan",
  "abbreviation": "TKJ",  // This is what we use in class labels
  "description": "..."
}
```

### **Expected Result:**
- `grade_level`: 12
- `expertise_abbreviation`: "TKJ"  
- `class_name`: "1"
- **Final Label**: "Kelas 12 TKJ 1"

---

## ✅ **Fallback Handling**

Jika data expertise_programs tidak lengkap:

```javascript
if (grade_level && expertise_abbr && class_name) {
    return `Kelas ${grade_level} ${expertise_abbr} ${class_name}`;
} else if (grade_level && class_name) {
    return `Kelas ${grade_level}-${class_name}`;  // Fallback ke format lama
} else {
    return class_name || "Unknown Class";
}
```

**Sistem tetap berfungsi** meski ada data yang tidak lengkap!
