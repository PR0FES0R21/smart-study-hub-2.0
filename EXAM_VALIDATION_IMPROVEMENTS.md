# Exam Validation and Shuffle Implementation Improvements

## Overview

Perbaikan ini menangani dua masalah utama dalam sistem ujian:

1. **Validasi Submit yang Lebih Ketat** - Memastikan siswa menjawab semua soal sebelum submit
2. **Implementasi Shuffle yang Sesuai Settings** - Memastikan shuffle berjalan sesuai konfigurasi guru/admin

## 1. Enhanced Submit Validation

### Masalah Sebelumnya
- Siswa bisa submit ujian meskipun belum menjawab semua soal
- Tidak ada validasi ketat untuk memastikan kelengkapan jawaban
- Kurangnya feedback yang jelas tentang soal yang belum terjawab

### Solusi yang Diterapkan

#### A. 4-Level Validation System
```python
# === VALIDASI 1: Cek apakah semua soal terjawab ===
# Memastikan semua soal dalam question_map terjawab

# === VALIDASI 2: Cek apakah ada soal yang tidak valid ===
# Memastikan semua question_id valid dan ada di database

# === VALIDASI 3: Cek apakah session masih ongoing ===
# Memastikan session masih aktif untuk submit

# === VALIDASI 4: Cek waktu ujian ===
# Memastikan belum melewati batas waktu ujian
```

#### B. Detailed Error Messages
```python
raise HTTPException(
    status_code=400,
    detail=f"Tidak dapat submit ujian. Anda belum menjawab {total_questions - answered_questions} soal. "
           f"Soal yang belum terjawab: {', '.join(map(str, unanswered_questions))}"
)
```

#### C. Completion Statistics
```python
"completion_stats": {
    "total_questions": total_questions,
    "answered_questions": answered_questions,
    "completion_percentage": (answered_questions / total_questions) * 100
}
```

## 2. Improved Shuffle Implementation

### Masalah Sebelumnya
- Shuffle tidak selalu mengikuti settings exam
- Inkonsistensi antara shuffle questions dan shuffle options
- Kurangnya logging untuk debugging

### Solusi yang Diterapkan

#### A. Settings-Based Shuffle
```python
exam_settings = exam.get("settings", {})
shuffle_questions = exam_settings.get("shuffle_questions", False)
shuffle_options = exam_settings.get("shuffle_options", False)
```

#### B. Consistent Question Shuffling
```python
# 1. Shuffle questions jika diaktifkan
working_question_ids = question_ids.copy()
if shuffle_questions:
    random.shuffle(working_question_ids)
    logger.info(f"Questions shuffled for exam {exam['_id']}")
```

#### C. Consistent Option Shuffling
```python
# Shuffle options jika diaktifkan dan ada options
if shuffle_options and question.get("options"):
    original_option_ids = [opt["id"] for opt in original_options]
    shuffled_option_ids = original_option_ids.copy()
    random.shuffle(shuffled_option_ids)
    logger.info(f"Options shuffled for question {q_id}")
elif question.get("options"):
    # Jika tidak di-shuffle, tetap simpan urutan asli untuk konsistensi
    shuffled_option_ids = [opt["id"] for opt in original_options]
```

#### D. Proper Question Map Structure
```python
question_map_item = QuestionMapItem(
    position=i + 1,
    question_id=q_id,
    shuffled_option_ids=shuffled_option_ids  # Konsisten dengan settings
)
```

## 3. Implementation Details

### Files Modified

1. **`app/crud/crud_exam_sessions.py`**
   - Enhanced `submit_and_grade_session_v2()` with strict validation
   - Improved `get_shuffled_questions_for_session()` for consistency
   - Added comprehensive logging

2. **`app/crud/crud_exams.py`**
   - Enhanced `start_exam_session()` with proper shuffle implementation
   - Added settings-based shuffle logic
   - Improved logging for debugging

### Key Functions

#### `submit_and_grade_session_v2()`
- **Purpose**: Submit exam with comprehensive validation
- **Validation**: 4-level validation system
- **Features**: Completion tracking, fraud detection, detailed error messages

#### `start_exam_session()`
- **Purpose**: Create new exam session with proper shuffle
- **Shuffle**: Settings-based question and option shuffling
- **Features**: Consistent mapping, comprehensive logging

#### `get_shuffled_questions_for_session()`
- **Purpose**: Retrieve questions with proper shuffle mapping
- **Consistency**: Uses saved shuffle mapping from session
- **Features**: Debug logging, position-based sorting

## 4. Usage Examples

### Exam Settings Configuration
```json
{
  "settings": {
    "shuffle_questions": true,
    "shuffle_options": true,
    "show_results_after_submission": true
  }
}
```

### Submit Validation Flow
1. Student attempts to submit exam
2. System checks all questions are answered
3. System validates question IDs
4. System checks session status
5. System checks time limits
6. If all validations pass, exam is graded and submitted

### Shuffle Implementation Flow
1. Exam session is created
2. System reads exam settings
3. If `shuffle_questions: true`, questions are randomized
4. If `shuffle_options: true`, options for each question are randomized
5. Shuffle mapping is saved in `question_map`
6. Questions are retrieved using saved mapping for consistency

## 5. Benefits

### For Students
- Clear feedback when exam is incomplete
- Consistent question and option ordering
- Better user experience with detailed error messages

### For Teachers/Admins
- Reliable shuffle implementation
- Proper validation prevents incomplete submissions
- Comprehensive logging for debugging

### For System
- More robust validation system
- Consistent data integrity
- Better audit trail with detailed logging

## 6. Testing Recommendations

### Validation Testing
- Test submit with incomplete answers
- Test submit with invalid question IDs
- Test submit with expired session
- Test submit with expired exam time

### Shuffle Testing
- Test with `shuffle_questions: true/false`
- Test with `shuffle_options: true/false`
- Test consistency across multiple sessions
- Test with different question types

### Edge Cases
- Test with empty question sets
- Test with questions without options
- Test with very large question sets
- Test concurrent session creation
