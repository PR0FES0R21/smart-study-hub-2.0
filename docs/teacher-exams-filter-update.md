# Teacher Exams Endpoint Update

## Overview
Endpoint `/api/v1/exams/teacher` telah diperbarui dengan parameter filter tambahan `exam_type` dan `search` untuk memudahkan guru dalam mencari dan memfilter ujian berdasarkan tipe dan pencarian teks.

## Parameter Baru

### 1. Parameter exam_type
- **Parameter**: `exam_type` (optional)
- **Type**: String  
- **Description**: Filter berdasarkan tipe ujian
- **Valid Values**: 
  - `quiz` - Kuis
  - `daily_test` - Ulangan harian
  - `practice` - Latihan
  - `official_uts` - UTS resmi
  - `official_uas` - UAS resmi
- **Default**: None (menampilkan semua tipe)

### 2. Parameter search
- **Parameter**: `search` (optional)
- **Type**: String
- **Description**: Pencarian berdasarkan judul ujian atau nama mata pelajaran
- **Search Target**:
  - Judul ujian (case-insensitive)
  - Nama mata pelajaran (case-insensitive)
- **Default**: None (tidak ada filter pencarian)

## Cara Penggunaan

### Mengambil Semua Ujian (Seperti Sebelumnya)
```http
GET /api/v1/exams/teacher
```

### Filter berdasarkan Tipe Ujian
```http
# Hanya ujian kuis
GET /api/v1/exams/teacher?exam_type=quiz

# Hanya ujian UTS resmi
GET /api/v1/exams/teacher?exam_type=official_uts

# Hanya ujian UAS resmi  
GET /api/v1/exams/teacher?exam_type=official_uas
```

### Pencarian berdasarkan Teks
```http
# Cari ujian dengan kata "matematika"
GET /api/v1/exams/teacher?search=matematika

# Cari ujian dengan kata "bab 1"
GET /api/v1/exams/teacher?search=bab%201
```

### Kombinasi Filter
```http
# Cari kuis matematika
GET /api/v1/exams/teacher?exam_type=quiz&search=matematika

# Cari ujian resmi dengan kata "semester"
GET /api/v1/exams/teacher?exam_type=official_uts&search=semester

# Kombinasi dengan filter lain yang sudah ada
GET /api/v1/exams/teacher?exam_type=quiz&search=fisika&class_id=CLASS_ID&page=1&limit=10
```

## Response Structure
Response tetap sama seperti sebelumnya dengan struktur `PaginatedExamResponse`:

```json
{
  "total_items": 25,
  "total_pages": 3,
  "current_page": 1,
  "limit": 10,
  "data": [
    {
      "_id": "exam_id_here",
      "title": "Kuis Matematika Bab 1",
      "exam_type": "quiz",
      "subject_details": {
        "name": "Matematika",
        "code": "MTK"
      },
      "class_details": {
        "name": "A",
        "grade_level": 10
      },
      "analytics_status": "completed",
      // ... field lainnya
    }
  ]
}
```

## Implementation Details

### Database Query Optimization
- Filter `exam_type` diterapkan pada tahap awal di aggregation pipeline
- Search filter menggunakan regex case-insensitive untuk performa optimal
- Search dilakukan pada field:
  - `title` (judul ujian)
  - `subject_details.name` (nama mata pelajaran)

### Search Functionality
- **Case-insensitive**: Pencarian tidak membedakan huruf besar/kecil
- **Partial match**: Mendukung pencarian sebagian kata
- **Multi-field**: Mencari di judul ujian dan nama mata pelajaran secara bersamaan

## Use Cases

### Untuk Guru
1. **Filter by Type**: Guru dapat dengan mudah melihat hanya ujian quiz untuk evaluasi harian
2. **Search by Subject**: Guru yang mengajar multiple mata pelajaran dapat cari ujian spesifik
3. **Quick Find**: Cari ujian berdasarkan topik/bab tertentu

### Contoh Real-world Usage
```http
# Guru ingin melihat semua kuis matematika
GET /api/v1/exams/teacher?exam_type=quiz&search=matematika

# Guru ingin mencari ujian dengan topik "trigonometri"
GET /api/v1/exams/teacher?search=trigonometri

# Admin ingin melihat semua UTS resmi
GET /api/v1/exams/teacher?exam_type=official_uts
```

## Backward Compatibility

- ✅ Tidak ada breaking changes
- ✅ Parameter existing tetap berfungsi: `academic_period_id`, `class_id`, `page`, `limit`
- ✅ Response structure tidak berubah
- ✅ Endpoint tanpa parameter baru tetap mengembalikan semua data

## Testing

Contoh testing endpoint:

```bash
# Test basic functionality (tanpa filter)
curl -X GET "https://testing.cigarverse.space/api/v1/exams/teacher" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test filter by type
curl -X GET "https://testing.cigarverse.space/api/v1/exams/teacher?exam_type=quiz" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test search
curl -X GET "https://testing.cigarverse.space/api/v1/exams/teacher?search=matematika" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test combined filters
curl -X GET "https://testing.cigarverse.space/api/v1/exams/teacher?exam_type=quiz&search=fisika&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Performance Notes

- Filter `exam_type` sangat efisien karena menggunakan index database
- Search menggunakan regex, performance baik untuk dataset moderate size
- Aggregation pipeline dioptimalkan untuk mengurangi document processing
- Filter diterapkan secara bertahap untuk efisiensi maksimal

## Frontend Integration

Frontend dapat menggunakan parameter ini untuk:

1. **Dropdown filter** untuk exam_type
2. **Search box** untuk pencarian real-time 
3. **Advanced filtering** dengan kombinasi multiple parameter
4. **Quick filters** untuk tipe ujian yang sering diakses

Contoh JavaScript fetch:
```javascript
// Filter by type
const response = await fetch('/api/v1/exams/teacher?exam_type=quiz', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Search with pagination
const searchResults = await fetch(
  `/api/v1/exams/teacher?search=${encodeURIComponent(searchTerm)}&page=${page}&limit=${limit}`, 
  { headers: { 'Authorization': `Bearer ${token}` } }
);
```
