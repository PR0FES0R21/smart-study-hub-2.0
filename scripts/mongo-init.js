// Smart Study Hub 2.0 - MongoDB Initialization Script
// This script runs when MongoDB container starts for the first time

// Switch to the application database
db = db.getSiblingDB('smart_study_hub');

// Create application user with read/write permissions
db.createUser({
  user: 'ssh_user',
  pwd: 'smartstudyhub2024',
  roles: [
    {
      role: 'readWrite',
      db: 'smart_study_hub'
    }
  ]
});

// Create indexes for better performance
print('Creating indexes for Smart Study Hub collections...');

// Users collection indexes
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "phone_number": 1 }, { unique: true, sparse: true });
db.users.createIndex({ "roles": 1 });
db.users.createIndex({ "status": 1 });
db.users.createIndex({ "created_at": 1 });

// Profiles collection indexes
db.profiles.createIndex({ "user_id": 1 }, { unique: true });
db.profiles.createIndex({ "employee_id": 1 }, { unique: true, sparse: true });
db.profiles.createIndex({ "nis": 1 }, { unique: true, sparse: true });
db.profiles.createIndex({ "class_id": 1 });
db.profiles.createIndex({ "full_name": "text" });

// Classes collection indexes
db.classes.createIndex({ "grade_level": 1, "expertise_id": 1, "name": 1 }, { unique: true });
db.classes.createIndex({ "academic_year": 1 });
db.classes.createIndex({ "homeroom_teacher_id": 1 });

// Subjects collection indexes
db.subjects.createIndex({ "code": 1 }, { unique: true });
db.subjects.createIndex({ "name": "text" });

// Expertise programs collection indexes
db.expertise_programs.createIndex({ "abbreviation": 1 }, { unique: true });
db.expertise_programs.createIndex({ "name": "text" });

// Academic periods collection indexes
db.academic_periods.createIndex({ "year": 1, "semester": 1 }, { unique: true });
db.academic_periods.createIndex({ "status": 1 });
db.academic_periods.createIndex({ "start_date": 1, "end_date": 1 });

// Teaching assignments collection indexes
db.teaching_assignments.createIndex({ 
  "academic_period_id": 1, 
  "class_id": 1, 
  "subject_id": 1, 
  "teacher_profile_id": 1 
}, { unique: true });
db.teaching_assignments.createIndex({ "teacher_profile_id": 1 });
db.teaching_assignments.createIndex({ "class_id": 1 });
db.teaching_assignments.createIndex({ "subject_id": 1 });

// Question banks collection indexes
db.question_banks.createIndex({ "subject_id": 1 });
db.question_banks.createIndex({ "created_by_teacher_id": 1 });
db.question_banks.createIndex({ "question_type": 1 });
db.question_banks.createIndex({ "difficulty": 1 });
db.question_banks.createIndex({ "tags": 1 });
db.question_banks.createIndex({ "created_at": 1 });

// Exams collection indexes
db.exams.createIndex({ "teaching_assignment_id": 1 });
db.exams.createIndex({ "status": 1 });
db.exams.createIndex({ "availability_start_time": 1, "availability_end_time": 1 });
db.exams.createIndex({ "created_at": 1 });

// Exam sessions collection indexes
db.exam_sessions.createIndex({ "exam_id": 1, "student_profile_id": 1 }, { unique: true });
db.exam_sessions.createIndex({ "student_profile_id": 1 });
db.exam_sessions.createIndex({ "status": 1 });
db.exam_sessions.createIndex({ "started_at": 1 });
db.exam_sessions.createIndex({ "submitted_at": 1 });
db.exam_sessions.createIndex({ "final_score": 1 });

// Grades collection indexes
db.grades.createIndex({ 
  "student_profile_id": 1, 
  "teaching_assignment_id": 1, 
  "academic_period_id": 1 
}, { unique: true });
db.grades.createIndex({ "student_profile_id": 1 });
db.grades.createIndex({ "teaching_assignment_id": 1 });
db.grades.createIndex({ "academic_period_id": 1 });
db.grades.createIndex({ "final_score": 1 });
db.grades.createIndex({ "letter_grade": 1 });

// Activity logs collection indexes
db.activity_logs.createIndex({ "user_id": 1 });
db.activity_logs.createIndex({ "action": 1 });
db.activity_logs.createIndex({ "timestamp": 1 });
db.activity_logs.createIndex({ "ip_address": 1 });
db.activity_logs.createIndex({ "user_agent": 1 });

// Admin export files collection indexes
db.admin_export_files.createIndex({ "created_by": 1 });
db.admin_export_files.createIndex({ "status": 1 });
db.admin_export_files.createIndex({ "format": 1 });
db.admin_export_files.createIndex({ "created_at": 1 });
db.admin_export_files.createIndex({ "expires_at": 1 });

print('Indexes created successfully!');

// Insert sample data for development (optional)
if (db.users.countDocuments() === 0) {
  print('Inserting sample data...');
  
  // Sample admin user
  const adminUserId = ObjectId();
  const adminProfileId = ObjectId();
  
  db.users.insertOne({
    _id: adminUserId,
    email: "admin@smartstudyhub.com",
    password: "$2b$12$LQv3c1yqBwEHxPjjxU/Uu.VjMg5/rI5H1.JbD/1aUZOvwuBkEXXAu", // password: admin123
    roles: ["admin"],
    profile_id: adminProfileId,
    status: "active",
    created_at: new Date(),
    updated_at: new Date()
  });
  
  db.profiles.insertOne({
    _id: adminProfileId,
    user_id: adminUserId,
    full_name: "System Administrator",
    gender: "male",
    birth_date: new Date("1990-01-01"),
    birth_place: "Jakarta",
    address: {
      street: "Jl. Admin No. 1",
      city: "Jakarta",
      province: "DKI Jakarta",
      postal_code: "12345"
    },
    employee_id: "ADM001",
    job_title: "System Administrator"
  });
  
  print('Sample admin user created:');
  print('Email: admin@smartstudyhub.com');
  print('Password: admin123');
}

print('MongoDB initialization completed successfully!');
print('Smart Study Hub 2.0 database is ready for use.');
