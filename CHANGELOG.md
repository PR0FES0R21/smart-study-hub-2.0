# Changelog

## [Unreleased]

### Added
- Enhanced validation for exam submission to ensure all questions are answered
- Improved shuffle implementation that respects exam settings (shuffle_questions, shuffle_options)
- Added completion statistics tracking in exam sessions
- Added comprehensive logging for shuffle operations

### Fixed
- Fixed issue where students could submit exams without answering all questions
- Fixed shuffle implementation to properly respect exam settings
- Improved consistency between question shuffling and option shuffling
- Added proper validation for exam session status and timing

### Changed
- Enhanced `submit_and_grade_session_v2` function with strict validation
- Improved `start_exam_session` function with proper shuffle implementation
- Updated `get_shuffled_questions_for_session` for better consistency
- Added detailed error messages for incomplete exam submissions

### Technical Details
- **Validation Enhancement**: Added 4-level validation in submit function:
  1. Check if all questions are answered
  2. Validate question IDs exist in database
  3. Verify session status is still ongoing
  4. Check exam time limits
- **Shuffle Implementation**: Now properly implements:
  - `shuffle_questions`: Randomizes question order
  - `shuffle_options`: Randomizes option order for each question
  - Consistent mapping between shuffled and original order
- **Logging**: Added comprehensive logging for debugging shuffle operations

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
