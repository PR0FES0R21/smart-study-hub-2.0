# Changelog

## [Unreleased]

### Changed

- **Endpoint `/student`**: Memperbaiki logika status untuk mempertimbangkan exam session
  - Menghapus field `computed_status` dari response
  - Status sekarang di-override berdasarkan exam session:
    - Jika ada exam session dengan status "graded" → status = "completed"
    - Jika ada exam session dengan status "ongoing"/"submitted" → gunakan status session
    - Jika tidak ada exam session → gunakan status exam asli
  - Filter berdasarkan status sekarang menggunakan status yang sudah di-override
  - Frontend dapat menggunakan field `has_session` dan `session_score` untuk UI logic

### Technical Details

- Modified `get_exams_by_student()` in `app/crud/crud_exams.py`
- Updated `ExamWithDetails` schema in `app/schemas/exam.py`
- Updated endpoint documentation in `app/api/v1/routes/exams.py`
