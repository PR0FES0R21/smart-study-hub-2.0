Arsitektur Database: School Management System 1.0
Dokumen ini merincikan arsitektur database MongoDB yang dirancang untuk aplikasi School Management System. Arsitektur ini menggunakan pendekatan normalisasi dengan referensi dokumen (ObjectId) untuk memastikan integritas data, skalabilitas, dan efisiensi query.

Bagian 1: Entitas Inti (Core Entities)
Kumpulan collection ini membentuk fondasi data utama yang mendefinisikan pengguna dan struktur dasar sekolah.

1. users
Menyimpan data otentikasi dan peran untuk setiap individu yang dapat login ke sistem.

// Collection: users
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e1a01"),
  "email": "budi.santoso@school.com",      // String, Required, Unique
  "phone_number": "+6281234567890",        // String, Optional, Unique
  "password": "hashed_password_from_bcrypt", // String, Required
  "roles": ["teacher", "department_head"], // Array of Strings, Required
  "profile_id": ObjectId("66854d3e5e1a7c8c8f5e1b02"), // ObjectId, Ref: 'profiles'
  "status": "active",                      // String, Enum: ["active", "inactive", "suspended"]
  "created_at": ISODate("2024-07-03T12:00:00Z"),
  "updated_at": ISODate("2024-07-03T12:00:00Z")
}

2. profiles
Menyimpan data demografis dan informasi spesifik peran yang terhubung ke users.

// Collection: profiles
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e1b02"),
  "user_id": ObjectId("66854d3e5e1a7c8c8f5e1a01"), // ObjectId, Ref: 'users'
  "full_name": "Dr. Budi Santoso, M.Pd.",    // String
  "gender": "male",                         // String, Enum: ["male", "female"]
  "birth_date": ISODate("1985-05-10T00:00:00Z"),
  "birth_place": "Bandung",
  "address": {
    "street": "Jl. Merdeka No. 45",
    "city": "Bandung",
    "province": "Jawa Barat",
    "postal_code": "40115"
  },
  "profile_picture_url": "https://storage.googleapis.com/bucket/profiles/budi.jpg",
  
  // --- Fields untuk Guru/Staf ---
  "employee_id": "T850510", // NIP/NKTAM, String, Unique, Sparse
  "job_title": "Guru Matematika",
  "subjects_taught_ids": [
    ObjectId("66854d3e5e1a7c8c8f5e1d04") // Ref: 'subjects' (Matematika)
  ],

  // --- Fields untuk Siswa ---
  "nis": "S2223001", // Nomor Induk Siswa, String, Unique, Sparse
  "class_id": ObjectId("66854d3e5e1a7c8c8f5e1c03"), // Ref: 'classes'
  "start_year": 2022,
  "end_year": 2025
}

3. expertise_programs (Jurusan)
Mendefinisikan program keahlian atau jurusan yang ada di sekolah.

// Collection: expertise_programs
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e1e05"),
  "name": "Teknik Komputer dan Jaringan",
  "abbreviation": "TKJ",
  "description": "Program keahlian yang berfokus pada perakitan komputer, jaringan dasar, dan administrasi server.",
  "head_of_department_id": ObjectId("66854d3e5e1a7c8c8f5e1b02") // Ref: 'profiles' (Guru Budi)
}

4. subjects (Mata Pelajaran)
Daftar semua mata pelajaran yang diajarkan di sekolah.

// Collection: subjects
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e1d04"),
  "name": "Matematika Wajib",
  "code": "MTK-01"
}

5. classes
Mendefinisikan sebuah rombongan belajar (rombel) atau kelas.

// Collection: classes
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e1c03"),
  "grade_level": 11, // Number (10, 11, 12)
  "expertise_id": ObjectId("66854d3e5e1a7c8c8f5e1e05"), // Ref: 'expertise_programs' (TKJ)
  "name": "1", // Nama unik kelas, misal: "1", "2", "A"
  "academic_year": "2024/2025",
  "homeroom_teacher_id": ObjectId("66854d3e5e1a7c8c8f5e1b02") // Ref: 'profiles' (Wali Kelas)
}

Bagian 2: Entitas Operasional & Transaksional
Kumpulan collection ini mengelola alur kerja harian sekolah, menghubungkan entitas inti dalam konteks waktu dan kegiatan.

6. academic_periods
Mendefinisikan periode waktu akademik (semester, tahun ajaran) untuk mengorganisir data transaksional.

// Collection: academic_periods
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e1f06"),
  "year": "2024/2025",
  "semester": "ganjil", // String, Enum: ["ganjil", "genap"]
  "status": "active",   // String, Enum: ["planning", "active", "archived"]
  "start_date": ISODate("2024-07-15T00:00:00Z"),
  "end_date": ISODate("2024-12-20T00:00:00Z")
}

7. teaching_assignments
Collection "jembatan" yang krusial, mendefinisikan penugasan mengajar spesifik. Ini adalah sumber kebenaran untuk jadwal dan kewenangan.

// Collection: teaching_assignments
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e2a07"),
  "academic_period_id": ObjectId("66854d3e5e1a7c8c8f5e1f06"), // Ref: 'academic_periods'
  "class_id": ObjectId("66854d3e5e1a7c8c8f5e1c03"),           // Ref: 'classes' (XI TKJ 1)
  "subject_id": ObjectId("66854d3e5e1a7c8c8f5e1d04"),         // Ref: 'subjects' (Matematika)
  "teacher_profile_id": ObjectId("66854d3e5e1a7c8c8f5e1b02"), // Ref: 'profiles' (Guru Budi)
  "day_of_week": "monday",
  "start_time": "07:30",
  "end_time": "09:00"
}

8. student_records
Log untuk mencatat kejadian non-akademik siswa (pelanggaran, prestasi, dll).

// Collection: student_records
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e2b08"),
  "student_profile_id": ObjectId("..."), // Ref: 'profiles' (Siswa)
  "record_type": "achievement",        // String, Enum: ["disciplinary", "achievement", "counseling"]
  "date": ISODate("2024-10-28T09:00:00Z"),
  "description": "Juara 1 Lomba Kompetensi Siswa (LKS) tingkat Kabupaten.",
  "reported_by_id": ObjectId("66854d3e5e1a7c8c8f5e1b02"), // Ref: 'profiles' (Guru)
  "details": {
    "competition_name": "LKS Web Technologies 2024",
    "certificate_url": "https://storage.googleapis.com/bucket/sertifikat/lks.pdf"
  }
}

Bagian 3: Modul Ujian dan Penilaian
Kumpulan collection yang didedikasikan untuk alur kerja ujian online, dari pembuatan soal hingga rekap nilai akhir.

9. question_banks
Bank soal yang dapat digunakan kembali untuk berbagai ujian.

// Collection: question_banks
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e3c09"),
  "subject_id": ObjectId("66854d3e5e1a7c8c8f5e1d04"),
  "created_by_teacher_id": ObjectId("66854d3e5e1a7c8c8f5e1b02"),
  "question_type": "multiple_choice",
  "difficulty": "medium",
  "question_text": "Jika f(x) = 2x + 3, maka f(4) adalah...",
  "options": [
    { "text": "11", "is_correct": true },
    { "text": "8", "is_correct": false },
    { "text": "10", "is_correct": false }
  ],
  "points": 10,
  "tags": ["fungsi", "aljabar"],
  "created_at": ISODate("2024-09-01T10:00:00Z")
}

10. exams
Mendefinisikan sebuah sesi ujian, termasuk pengaturan dan daftar soalnya.

// Collection: exams
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e3d10"),
  "title": "Ujian Tengah Semester Matematika",
  "teaching_assignment_id": ObjectId("66854d3e5e1a7c8c8f5e2a07"), // Kunci penghubung
  "exam_type": "multiple_choice",
  "duration_minutes": 90,
  "availability_start_time": ISODate("2024-10-15T08:00:00Z"),
  "availability_end_time": ISODate("2024-10-15T12:00:00Z"),
  "status": "published",
  "question_ids": [
    ObjectId("66854d3e5e1a7c8c8f5e3c09"),
    ObjectId("...")
  ],
  "settings": {
    "shuffle_questions": true,
    "tab_switch_detection": true
  },
  "created_at": ISODate("2024-10-01T14:00:00Z")
}

11. exam_sessions
Mencatat progres dan jawaban setiap siswa yang sedang atau telah mengerjakan ujian.

// Collection: exam_sessions
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e3e11"),
  "exam_id": ObjectId("66854d3e5e1a7c8c8f5e3d10"),
  "student_profile_id": ObjectId("..."), // Ref: 'profiles' (Siswa)
  "status": "submitted",
  "started_at": ISODate("2024-10-15T08:05:10Z"),
  "submitted_at": ISODate("2024-10-15T09:30:00Z"),
  "answers": [
    {
      "question_id": ObjectId("66854d3e5e1a7c8c8f5e3c09"),
      "answer": "11",
      "is_correct": true,
      "points_awarded": 10
    }
  ],
  "final_score": 95.0,
  "cheating_logs": [],
  "is_graded": true,
  "graded_at": ISODate("2024-10-15T09:30:01Z")
}

12. grades
Buku nilai digital (Rapor) yang mengagregasi semua komponen penilaian menjadi nilai akhir.

// Collection: grades
{
  "_id": ObjectId("66854d3e5e1a7c8c8f5e3f12"),
  "student_profile_id": ObjectId("..."), // Ref: 'profiles' (Siswa)
  "teaching_assignment_id": ObjectId("66854d3e5e1a7c8c8f5e2a07"),
  "academic_period_id": ObjectId("66854d3e5e1a7c8c8f5e1f06"),
  "components": {
    "assignments": 90,
    "mid_term_exam": 95, // Diambil dari 'exam_sessions'
    "final_exam": 88,
    "attendance": 100
  },
  "final_score": 91.25,
  "letter_grade": "A",
  "teacher_notes": "Pemahaman konsep sangat baik.",
  "last_updated_at": ISODate("2024-12-18T11:00:00Z")
}


oh iya, bagaimana kita menerapkan cacheing pada redis, dimana nantinya kita akan menyimpan data didalam redis agar tidak terlalu membebani database. kita akan pantau secara cerdas, dimana setiap kali data berubah atau setiap kali ada request yang merubah data (berhubungan dengan data tertentu) maka data tertentu yang disimpan di redis akan di hapus dan di set ulang.