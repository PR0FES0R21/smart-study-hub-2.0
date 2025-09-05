# Exam Analytics Background Tasks

## Overview
Implementasi background tasks untuk mengoptimalkan performa sistem analytics ujian dengan melakukan cache warming setelah ada perubahan data ujian.

## Fitur

### 1. Background Cache Warming
- **File**: `app/tasks/exam_analytics_tasks.py`
- **Fungsi utama**: 
  - `invalidate_and_warm_exam_analytics` - Task utama yang dipanggil setelah submit ujian
  - `warm_exam_analytics_cache` - Task untuk warming cache semua session dalam exam

### 2. Integrasi dengan Submit Process
- **File**: `app/crud/crud_exam_sessions.py`
- Setelah invalidate cache, sistem otomatis menjalankan background task untuk regenerate cache
- Mengurangi waktu tunggu saat user lain meminta analytics data

## Cara Kerja

### Submit Flow
```
Student submits exam 
    ↓
Session scored & saved
    ↓
Analytics cache invalidated (Database + Redis cache)
    ├─ exam_analytics collection (MongoDB)
    ├─ student_class_exam_analytics:period:xxx:student:xxx (Redis)
    ├─ student_individual_stats:period:xxx:student:xxx (Redis)
    ├─ student_full_dashboard:period:xxx:student:xxx (Redis)
    └─ class-level caches (Redis)
    ↓
Background task scheduled untuk regenerate cache
    ↓
Cache warm & ready untuk permintaan selanjutnya
```

### Background Task Flow
```
invalidate_and_warm_exam_analytics(exam_id)
    ↓
1. Invalidate existing cache entries
    ↓
2. Get all submitted/graded sessions
    ↓
3. Generate analytics untuk setiap session
    ↓
4. Cache hasil untuk akses cepat
```

## Keuntungan

1. **Improved Response Time**: Cache sudah siap saat ada request analytics
2. **Better User Experience**: Tidak ada waiting time saat view analytics
3. **Scalable**: Background processing tidak mengganggu flow utama
4. **Fault Tolerant**: Error handling dengan retry mechanism
5. **Complete Cache Invalidation**: Menginvalidate both database dan Redis cache
6. **Multi-level Cache Management**: Student, class, dan exam level invalidation

## Configuration

### Celery Setup
Background tasks menggunakan Celery dengan konfigurasi:
- **Max retries**: 3 untuk warming, 2 untuk invalidate+warm
- **Retry delay**: Exponential backoff (30s, 60s, 120s)
- **Fallback**: Synchronous execution jika Celery tidak tersedia

### Error Handling
- Input validation untuk exam_id
- Graceful failure handling
- Comprehensive logging untuk debugging
- Continue on session-level failures

## Usage

### Automatic (Recommended)
Background tasks automatically triggered saat student submit ujian melalui:
- `submit_and_grade_session()`
- `submit_and_grade_session_v2()`

### Manual (Debug)
```python
from app.tasks.exam_analytics_tasks import invalidate_and_warm_exam_analytics

# Warm cache untuk specific exam
invalidate_and_warm_exam_analytics.delay("exam_id_here")
```

## Cache Patterns Invalidated

### Student-level Cache Keys:
- `student_class_exam_analytics:period:{period_id}:student:{student_id}`
- `student_individual_stats:period:{period_id}:student:{student_id}`
- `student_full_dashboard:period:{period_id}:student:{student_id}`
- `student_subject_performances:period:{period_id}:student:{student_id}`
- `student_exam_history:period:{period_id}:student:{student_id}`
- `student_class_comparison:period:{period_id}:student:{student_id}`

### Class-level Cache Keys:
- `class_exam_analytics:period:{period_id}:class:{class_id}`
- `class_dashboard:period:{period_id}:class:{class_id}`
- `class_performance:period:{period_id}:class:{class_id}`

## Monitoring

Check logs untuk monitoring task execution:
```
[INFO] Invalidated 5 exam analytics cache entries for exam 64f8a9b123456789abcdef01
[INFO] Invalidated 18 student analytics cache entries for exam 64f8a9b123456789abcdef01
[INFO] Scheduled background cache warming for exam 64f8a9b123456789abcdef01
[INFO] Warming analytics cache for 12 sessions in exam 64f8a9b123456789abcdef01
[INFO] Cache warming completed for exam 64f8a9b123456789abcdef01: 12 successful, 0 failed
```

## Requirements

1. **Celery & Redis**: Background task processing
2. **Proper analytics implementation**: Updated `app/crud/exam_analytics.py`
3. **Database access**: MongoDB connection dari background worker

## Future Enhancements

1. **Priority queues**: High priority untuk exam yg baru selesai
2. **Batch processing**: Group multiple exam warming dalam satu task
3. **Selective warming**: Hanya warm analytics untuk active teachers/students
4. **Metrics collection**: Track cache hit rates dan performance impact
