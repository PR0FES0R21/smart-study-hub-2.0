# Student Performance Roster API Update

## Overview
Endpoint `/api/v1/analytics/student-performance-roster` telah diperbarui untuk mendukung parameter `limit` dan caching berdasarkan `student_ids` untuk performa yang lebih baik.

## Fitur Baru

### 1. Parameter Limit
- **Parameter**: `limit` (optional)
- **Type**: Integer (1-1000)
- **Description**: Membatasi jumlah siswa yang dikembalikan
- **Default**: None (mengembalikan semua data)

### 2. Caching byIds
- **Parameter**: `student_ids` (optional)
- **Type**: Array of String
- **Description**: Daftar ID siswa spesifik untuk diambil datanya
- **Benefit**: Cache parsial berdasarkan ID siswa tertentu

## Cara Penggunaan

### Mengambil Semua Data (Seperti Sebelumnya)
```http
GET /api/v1/analytics/student-performance-roster
```

### Mengambil dengan Limit
```http
GET /api/v1/analytics/student-performance-roster?limit=50
```

### Mengambil Siswa Spesifik (Caching byIds)
```http
GET /api/v1/analytics/student-performance-roster?student_ids=6450a1234567890abcdef123&student_ids=6450a1234567890abcdef124
```

### Kombinasi Limit dan Student IDs
```http
GET /api/v1/analytics/student-performance-roster?limit=10&student_ids=6450a1234567890abcdef123&student_ids=6450a1234567890abcdef124
```

## Cache Strategy

### Cache Key Format
Cache key dibuat dengan format: `analytics:student_performance_roster:limit:{limit}:ids:{hash}`

- **limit:all** - jika tidak ada limit
- **limit:{number}** - jika ada limit spesifik
- **ids:all** - jika tidak ada filter student_ids
- **ids:{hash}** - hash MD5 dari sorted student_ids (8 karakter pertama)

### Contoh Cache Keys
- `analytics:student_performance_roster:limit:all:ids:all` - Semua data tanpa filter
- `analytics:student_performance_roster:limit:50:ids:all` - 50 data terbatas tanpa filter student
- `analytics:student_performance_roster:limit:all:ids:a1b2c3d4` - Semua data untuk student_ids tertentu

## Benefits

1. **Performance**: Caching yang lebih granular berdasarkan parameter
2. **Efficiency**: Limit mengurangi load database dan network transfer
3. **Flexibility**: Bisa mengambil data siswa spesifik untuk update parsial
4. **Backward Compatibility**: Endpoint lama tetap berfungsi tanpa parameter

## Implementation Details

### Database Query Optimization
- Filter `student_ids` diterapkan pada tahap awal aggregation pipeline
- Limit diterapkan setelah sorting untuk memastikan hasil terurut
- Pipeline aggregation dioptimalkan untuk mengurangi document processing

### Error Handling
- Invalid `student_ids` akan menghasilkan array kosong dengan log error
- Parameter validation dilakukan di endpoint level
- Graceful fallback jika terjadi error dalam cache operation

## Testing

Untuk testing endpoint:

```bash
# Test basic functionality
curl -X GET "https://testing.cigarverse.space/api/v1/analytics/student-performance-roster"

# Test dengan limit
curl -X GET "https://testing.cigarverse.space/api/v1/analytics/student-performance-roster?limit=10"

# Test dengan student_ids
curl -X GET "https://testing.cigarverse.space/api/v1/analytics/student-performance-roster?student_ids=STUDENT_ID_1&student_ids=STUDENT_ID_2"
```

## Migration Notes

- Tidak ada breaking changes
- Existing frontend code akan tetap berfungsi
- Untuk mendapatkan benefit penuh, frontend dapat diperbarui untuk menggunakan parameter baru
