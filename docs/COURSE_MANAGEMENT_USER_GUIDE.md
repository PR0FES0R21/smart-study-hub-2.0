# 📚 **Smart Study Hub 2.0 - Course Management System**
## **Complete User Guide & API Documentation**

> **Version**: 2.0.0  
> **Status**: ✅ Production Ready  
> **API Base URL**: `http://localhost:8000/api/v1`  

---

## 🎯 **SYSTEM OVERVIEW**

Smart Study Hub 2.0 Course Management System menggunakan **GitHub-style workflow** yang memungkinkan:

- **🎓 Coordinators**: Membuat dan mengelola master courses
- **👨‍🏫 Teachers**: Fork courses, customize untuk kelas mereka, submit improvements
- **👩‍💻 Collaborative**: Pull request system untuk quality control
- **📊 Trackable**: Complete audit trail semua perubahan

---

## 🔄 **WORKFLOW DIAGRAM**

```
📋 COORDINATOR                    👨‍🏫 TEACHER                     👩‍🎓 STUDENT
     │                              │                              │
     ▼                              ▼                              ▼
┌─────────────────┐         ┌─────────────────┐           ┌─────────────────┐
│ Create Course   │         │ Fork Master     │           │ View Course     │
│ Family (Master) │◄────────┤ Course          │           │ Content         │
└─────────────────┘         └─────────────────┘           └─────────────────┘
     │                              │                              │
     ▼                              ▼                              ▼
┌─────────────────┐         ┌─────────────────┐           ┌─────────────────┐
│ Review & Approve│         │ Customize Content│           │ Track Progress  │
│ Pull Requests   │◄────────┤ for Classes     │           │ & Completion    │
└─────────────────┘         └─────────────────┘           └─────────────────┘
     │                              │                              
     ▼                              ▼                              
┌─────────────────┐         ┌─────────────────┐                    
│ Merge Changes   │         │ Submit Pull     │                    
│ to Master       │         │ Request         │                    
└─────────────────┘         └─────────────────┘                    
```

---

## 🚀 **GETTING STARTED GUIDE**

### **Step 1: Authentication**

Semua API endpoints memerlukan authentication. Login terlebih dahulu:

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
    "login_id": "coordinator@school.edu",
    "password": "your_password"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
        "_id": "64f5a1b2c8d4e5f6a7b8c9d0",
        "roles": ["coordinator"],
        "email": "coordinator@school.edu"
    }
}
```

**Gunakan token untuk semua request:**
```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 👨‍💼 **COORDINATOR WORKFLOW**

### **1. Create Course Family**

Coordinator membuat course family baru (master course):

```bash
POST /api/v1/course-management/families
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
    "base_title": "Matematika Kelas 10",
    "subject_id": "64f5a1b2c8d4e5f6a7b8c9d1",
    "grade_level": 10,
    "description": "Matematika untuk kelas 10 mencakup aljabar, geometri, dan statistik",
    "modules": [
        {
            "title": "Aljabar Linear",
            "description": "Pengenalan sistem persamaan linear dan matriks",
            "order": 1,
            "lessons": [
                {
                    "title": "Sistem Persamaan Linear",
                    "description": "Memahami konsep dasar sistem persamaan linear",
                    "order": 1,
                    "content_markdown": "# Sistem Persamaan Linear\n\nSistem persamaan linear adalah...\n\n## Contoh:\n2x + 3y = 12\nx - y = 1\n\n{{quiz:quiz_persamaan_001}}",
                    "estimated_duration": 60,
                    "difficulty_level": "medium",
                    "learning_objectives": [
                        "Memahami konsep sistem persamaan linear",
                        "Mampu menyelesaikan sistem persamaan dengan 2 variabel"
                    ],
                    "embedded_components": [
                        {
                            "component_id": "quiz_persamaan_001",
                            "type": "quiz",
                            "position": 1,
                            "required": true,
                            "data": {
                                "questions": [
                                    {
                                        "question": "Berapa nilai x dari sistem: 2x + y = 8, x - y = 1?",
                                        "type": "multiple_choice",
                                        "options": ["x = 3", "x = 2", "x = 4", "x = 1"],
                                        "correct_answer": "x = 3"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ]
}
```

**Response:**
```json
{
    "id": "64f5a1b2c8d4e5f6a7b8c9d2",
    "course_family_id": "64f5a1b2c8d4e5f6a7b8c9d2",
    "base_title": "Matematika Kelas 10",
    "subject_id": "64f5a1b2c8d4e5f6a7b8c9d1",
    "grade_level": 10,
    "coordinator_id": "64f5a1b2c8d4e5f6a7b8c9d0",
    "current_master_version_id": "64f5a1b2c8d4e5f6a7b8c9d3",
    "current_version": "1.0.0",
    "total_versions": 1,
    "total_forks": 0,
    "total_pull_requests": 0,
    "created_at": "2025-01-01T10:00:00Z"
}
```

### **2. View All Course Families**

```bash
GET /api/v1/course-management/families/{family_id}
Authorization: Bearer {token}
```

### **3. Monitor Pull Requests**

Coordinator dapat melihat semua pull requests yang submitted:

```bash
GET /api/v1/course-management/pull-requests?status=pending
Authorization: Bearer {token}
```

**Response:**
```json
{
    "items": [
        {
            "id": "64f5a1b2c8d4e5f6a7b8c9d4",
            "pr_number": 1,
            "title": "Add Interactive Math Exercises for TKJ Students",
            "course_family_id": "64f5a1b2c8d4e5f6a7b8c9d2",
            "requested_by": "64f5a1b2c8d4e5f6a7b8c9d5",
            "requested_by_name": "Bu Sari (Math Teacher)",
            "status": "pending",
            "created_at": "2025-01-01T14:30:00Z",
            "changes_count": 3,
            "changes_summary": {
                "add": 2,
                "modify": 1
            }
        }
    ],
    "total_count": 5,
    "total_pending": 3,
    "total_approved": 2
}
```

### **4. Review & Approve Pull Request**

```bash
GET /api/v1/course-management/pull-requests/{pr_id}
Authorization: Bearer {token}
```

**Detailed PR View:**
```json
{
    "id": "64f5a1b2c8d4e5f6a7b8c9d4",
    "pr_number": 1,
    "title": "Add Interactive Math Exercises for TKJ Students",
    "description": "TKJ students need more hands-on practice with real-world applications. Added interactive exercises with programming context.",
    "requested_by_name": "Bu Sari",
    "changes": [
        {
            "action": "add_lesson",
            "target_type": "lesson",
            "title": "Math for Programming",
            "description": "Applied mathematics in programming context",
            "rationale": "TKJ students relate better to programming examples",
            "insertion_data": {
                "title": "Algoritma dan Matematika",
                "content_markdown": "# Matematika dalam Pemrograman\n\nPada pemrograman, kita sering menggunakan...\n\n{{interactive:coding_exercise_001}}",
                "embedded_components": [...]
            }
        }
    ],
    "impact_assessment": {
        "affected_classes": ["64f5a1b2c8d4e5f6a7b8c9d6"],
        "affected_students": 32,
        "student_impact": "medium"
    }
}
```

**Approve Pull Request:**
```bash
POST /api/v1/course-management/pull-requests/{pr_id}/review
Authorization: Bearer {token}
Content-Type: application/json

{
    "decision": "approve",
    "comment": "Excellent improvement! The programming context will definitely help TKJ students understand mathematical concepts better. Approved for merge."
}
```

**Response:**
```json
{
    "id": "64f5a1b2c8d4e5f6a7b8c9d4",
    "status": "merged",
    "merged_at": "2025-01-01T15:45:00Z",
    "merged_version_id": "64f5a1b2c8d4e5f6a7b8c9d7",
    "approval_workflow": [
        {
            "step_number": 1,
            "action": "submitted",
            "actor_name": "Bu Sari",
            "timestamp": "2025-01-01T14:30:00Z"
        },
        {
            "step_number": 2,
            "action": "approved",
            "actor_name": "Pak Koordinator",
            "timestamp": "2025-01-01T15:45:00Z",
            "comment": "Excellent improvement! Approved for merge."
        },
        {
            "step_number": 3,
            "action": "merged",
            "actor_name": "System",
            "timestamp": "2025-01-01T15:45:00Z"
        }
    ]
}
```

---

## 👨‍🏫 **TEACHER WORKFLOW**

### **1. View Available Courses**

Teacher dapat melihat semua master courses yang bisa di-fork:

```bash
GET /api/v1/course-management/versions?is_master=true&is_active=true
Authorization: Bearer {token}
```

### **2. Fork Master Course**

Teacher membuat fork untuk kelas-kelas yang diajar:

```bash
POST /api/v1/course-management/versions/{master_version_id}/fork
Authorization: Bearer {token}
Content-Type: application/json

{
    "class_ids": [
        "64f5a1b2c8d4e5f6a7b8c9d6", // TKJ 1
        "64f5a1b2c8d4e5f6a7b8c9d7"  // TKJ 2
    ],
    "fork_title_suffix": "TKJ Focus"
}
```

**Response:**
```json
{
    "id": "64f5a1b2c8d4e5f6a7b8c9d8",
    "course_family_id": "64f5a1b2c8d4e5f6a7b8c9d2",
    "version": "1.0.0-teacher-64f5a1b2c8d4e5f6a7b8c9d5-v1",
    "title": "Matematika Kelas 10 - TKJ Focus (Fork)",
    "is_master": false,
    "fork_type": "teacher_fork",
    "teacher_id": "64f5a1b2c8d4e5f6a7b8c9d5",
    "class_ids": ["64f5a1b2c8d4e5f6a7b8c9d6", "64f5a1b2c8d4e5f6a7b8c9d7"],
    "modules": [...], // Copied from master
    "user_can_edit": true,
    "user_can_create_pr": true
}
```

### **3. Customize Course Content**

Teacher dapat mengedit fork untuk menyesuaikan dengan kebutuhan kelas:

```bash
PUT /api/v1/course-management/versions/{fork_version_id}/content
Authorization: Bearer {token}
Content-Type: application/json

{
    "modules": [
        {
            "module_id": "64f5a1b2c8d4e5f6a7b8c9d9",
            "title": "Aljabar Linear untuk TKJ",
            "description": "Aljabar linear dengan aplikasi programming",
            "order": 1,
            "lessons": [
                {
                    "lesson_id": "64f5a1b2c8d4e5f6a7b8c9da",
                    "title": "Sistem Persamaan dalam Algoritma",
                    "content_markdown": "# Sistem Persamaan Linear dalam Pemrograman\n\nDalam dunia programming, sistem persamaan linear digunakan untuk:\n- Optimisasi algoritma\n- Machine Learning basics\n- Game physics\n\n```python\n# Contoh sederhana\nx = 2\ny = 3\nresult = 2*x + 3*y  # Hasil: 13\n```\n\n{{quiz:programming_math_001}}\n\n## Praktik Coding\n\n{{assignment:coding_exercise_linear}}",
                    "embedded_components": [
                        {
                            "component_id": "programming_math_001",
                            "type": "quiz",
                            "position": 1,
                            "data": {
                                "questions": [
                                    {
                                        "question": "Dalam Python, berapa hasil dari: 3*x + 2*y jika x=4 dan y=5?",
                                        "type": "multiple_choice",
                                        "options": ["22", "23", "24", "25"],
                                        "correct_answer": "22"
                                    }
                                ]
                            }
                        },
                        {
                            "component_id": "coding_exercise_linear",
                            "type": "assignment",
                            "position": 2,
                            "data": {
                                "type": "file_upload",
                                "title": "Implementasi Sistem Persamaan",
                                "description": "Buat program Python yang menyelesaikan sistem persamaan 2x2",
                                "requirements": {
                                    "file_types": [".py", ".ipynb"],
                                    "max_size": "5MB",
                                    "deadline": "2025-01-15T23:59:00Z"
                                }
                            }
                        }
                    ]
                }
            ]
        }
    ]
}
```

### **4. Submit Improvements via Pull Request**

Setelah customize course dan melihat hasilnya bagus, teacher dapat submit improvements ke master:

```bash
POST /api/v1/course-management/versions/{fork_version_id}/pull-requests
Authorization: Bearer {token}
Content-Type: application/json

{
    "title": "Add Programming Context to Math Lessons",
    "description": "After teaching this to TKJ students, I found that adding programming context significantly improves their understanding and engagement. The students can relate mathematical concepts to practical coding applications.",
    "target_version_id": "64f5a1b2c8d4e5f6a7b8c9d3",
    "changes": [
        {
            "action": "modify_lesson",
            "target_type": "lesson",
            "target_id": "64f5a1b2c8d4e5f6a7b8c9da",
            "title": "Enhanced Math Lesson with Programming Context",
            "description": "Added Python code examples and programming-related quiz questions",
            "rationale": "TKJ students showed 40% better comprehension when mathematical concepts were presented with programming context. Quiz scores improved from 65% to 87% average.",
            "old_data": {
                "content_markdown": "# Sistem Persamaan Linear\n\nSistem persamaan linear adalah..."
            },
            "new_data": {
                "content_markdown": "# Sistem Persamaan Linear dalam Pemrograman\n\nDalam dunia programming, sistem persamaan linear digunakan untuk:\n- Optimisasi algoritma\n- Machine Learning basics\n- Game physics\n\n```python\n# Contoh sederhana\nx = 2\ny = 3\nresult = 2*x + 3*y  # Hasil: 13\n```"
            },
            "expected_impact": "medium"
        }
    ]
}
```

### **5. View My Courses (Teacher Dashboard)**

```bash
GET /api/v1/course-management/versions?teacher_id={teacher_id}&fork_type=teacher_fork
Authorization: Bearer {token}
```

---

## 👩‍🎓 **STUDENT EXPERIENCE**

### **1. View Enrolled Courses**

Students automatically enrolled ke course yang digunakan teacher di kelas mereka:

```bash
GET /api/v1/lessons/enrolled
Authorization: Bearer {token}
```

### **2. Access Course Content**

```bash
GET /api/v1/course-management/versions/{version_id}
Authorization: Bearer {token}
```

**Student melihat:**
- Rich content dengan markdown formatting
- Interactive quizzes
- Assignment submissions
- Progress tracking
- Due dates dan deadlines

---

## 📊 **RICH CONTENT FEATURES**

### **Markdown Support**

Course content menggunakan markdown dengan extensions:

```markdown
# Lesson Title

Regular markdown content dengan **bold** dan *italic*.

## Embedded Media
![Diagram]({{media:diagram_001.png}})

## Interactive Elements
{{quiz:quiz_linear_001}}

## Programming Examples
```python
def solve_linear(a, b, c, d, e, f):
    # Solve ax + by = e, cx + dy = f
    det = a*d - b*c
    if det != 0:
        x = (e*d - b*f) / det
        y = (a*f - e*c) / det
        return x, y
    return None
```

## Assignments
{{assignment:homework_linear_systems}}

## Videos
{{video:explanation_linear_systems.mp4}}
```

### **Embedded Components**

#### **Quiz Component:**
```json
{
    "component_id": "quiz_linear_001",
    "type": "quiz",
    "position": 1,
    "required": true,
    "estimated_duration": 15,
    "data": {
        "title": "Sistem Persamaan Linear",
        "description": "Test pemahaman konsep dasar",
        "questions": [
            {
                "id": "q1",
                "question": "Berapa nilai x dari sistem: 2x + y = 8, x - y = 1?",
                "type": "multiple_choice",
                "options": ["x = 3", "x = 2", "x = 4", "x = 1"],
                "correct_answer": "x = 3",
                "explanation": "Eliminasi y: 2x + y = 8, x - y = 1. Tambahkan: 3x = 9, maka x = 3"
            },
            {
                "id": "q2",
                "question": "Jelaskan langkah-langkah eliminasi:",
                "type": "essay",
                "max_words": 100,
                "rubric": "Harus menyebutkan: eliminasi variabel, substitusi, verifikasi"
            }
        ],
        "settings": {
            "shuffle_questions": false,
            "show_correct_answers": true,
            "attempts_allowed": 3,
            "time_limit": 900
        }
    }
}
```

#### **Assignment Component:**
```json
{
    "component_id": "homework_linear_systems",
    "type": "assignment",
    "position": 2,
    "required": true,
    "data": {
        "title": "Praktik Sistem Persamaan Linear",
        "description": "Selesaikan 5 soal sistem persamaan linear dan buat program Python untuk solusi otomatis",
        "type": "file_upload",
        "requirements": {
            "file_types": [".pdf", ".doc", ".py", ".ipynb"],
            "max_size": "10MB",
            "max_files": 3
        },
        "deadline": "2025-01-15T23:59:00Z",
        "rubric": {
            "math_solutions": 60,
            "code_quality": 25,
            "documentation": 15
        },
        "submission_template": "template_linear_systems.docx"
    }
}
```

#### **Interactive Component:**
```json
{
    "component_id": "interactive_solver",
    "type": "interactive",
    "position": 3,
    "data": {
        "type": "linear_equation_solver",
        "interface": {
            "inputs": ["a", "b", "c", "d", "e", "f"],
            "output": "solution_steps",
            "visualization": true
        },
        "examples": [
            {"a": 2, "b": 1, "c": 1, "d": -1, "e": 8, "f": 1}
        ]
    }
}
```

---

## 📈 **ANALYTICS & MONITORING**

### **1. Course Analytics**

```bash
GET /api/v1/course-management/families/{family_id}/analytics
Authorization: Bearer {token}
```

**Response:**
```json
{
    "course_family_id": "64f5a1b2c8d4e5f6a7b8c9d2",
    "total_versions": 5,
    "total_forks": 12,
    "active_forks": 8,
    "total_prs": 23,
    "approved_prs": 18,
    "avg_review_time_hours": 4.2,
    "total_enrolled_students": 156,
    "average_completion_rate": 78.5,
    "total_learning_time": 2340, // hours
    "changes_last_30_days": 15,
    "most_active_teachers": [
        {
            "teacher_name": "Bu Sari",
            "contributions": 8,
            "approved_prs": 7
        }
    ],
    "content_growth_trend": [
        {
            "month": "2025-01",
            "lessons_added": 12,
            "modules_added": 3,
            "improvements": 25
        }
    ]
}
```

### **2. Change History**

```bash
GET /api/v1/course-management/families/{family_id}/history?page=1&limit=20
Authorization: Bearer {token}
```

**Response:**
```json
{
    "items": [
        {
            "id": "64f5a1b2c8d4e5f6a7b8c9db",
            "change_type": "pr_merged",
            "title": "PR #15 Merged: Interactive Math Exercises",
            "description": "Added programming context to linear algebra lessons",
            "actor_name": "Pak Koordinator",
            "actor_type": "coordinator",
            "timestamp": "2025-01-01T15:45:00Z",
            "impact_level": "medium",
            "notifications_sent": 8
        },
        {
            "id": "64f5a1b2c8d4e5f6a7b8c9dc",
            "change_type": "fork_created",
            "title": "Teacher Fork Created",
            "description": "Bu Sari created fork for TKJ classes",
            "actor_name": "Bu Sari",
            "actor_type": "teacher",
            "timestamp": "2025-01-01T10:30:00Z",
            "impact_level": "low"
        }
    ],
    "total_count": 45,
    "total_by_type": {
        "pr_merged": 12,
        "fork_created": 18,
        "content_updated": 15
    }
}
```

### **3. System Health**

```bash
GET /api/v1/course-management/system/health
Authorization: Bearer {token}
```

**Response:**
```json
{
    "total_course_families": 25,
    "total_versions": 156,
    "total_active_forks": 89,
    "pending_prs": 12,
    "avg_pr_review_time": 4.2,
    "avg_fork_creation_time": 2.1,
    "storage_usage_mb": 245.7,
    "rollback_rate": 0.02,
    "error_rate": 0.001,
    "user_satisfaction": 4.6
}
```

---

## 🔍 **SEARCH & FILTERING**

### **Advanced Course Search:**

```bash
GET /api/v1/course-management/versions?search=matematika&grade_level=10&is_active=true&sort_by=updated_at&sort_direction=desc
```

### **Pull Request Filtering:**

```bash
GET /api/v1/course-management/pull-requests?status=pending&priority=high&created_after=2025-01-01
```

---

## 🚨 **ERROR HANDLING**

### **Common Error Responses:**

#### **403 Forbidden:**
```json
{
    "detail": "Access denied. Required roles: coordinator, admin"
}
```

#### **404 Not Found:**
```json
{
    "detail": "Course version not found"
}
```

#### **422 Validation Error:**
```json
{
    "detail": [
        {
            "loc": ["body", "modules", 0, "title"],
            "msg": "ensure this value has at least 1 characters",
            "type": "value_error.any_str.min_length"
        }
    ]
}
```

---

## 🔐 **PERMISSION MATRIX**

| Action | Admin | Coordinator | Teacher | Student |
|--------|-------|-------------|---------|---------|
| Create Course Family | ✅ | ✅ | ❌ | ❌ |
| Edit Master Course | ✅ | ✅ (own) | ❌ | ❌ |
| Create Teacher Fork | ✅ | ✅ | ✅ | ❌ |
| Edit Teacher Fork | ✅ | ❌ | ✅ (own) | ❌ |
| Submit Pull Request | ✅ | ✅ | ✅ | ❌ |
| Review Pull Request | ✅ | ✅ (target) | ❌ | ❌ |
| View Course Content | ✅ | ✅ | ✅ | ✅ |
| View Analytics | ✅ | ✅ | ❌ | ❌ |

---

## 📝 **INTEGRATION EXAMPLES**

### **Frontend Integration (React):**

```javascript
// Course Management Hook
const useCourseManagement = () => {
    const [courses, setCourses] = useState([]);
    const [pullRequests, setPullRequests] = useState([]);
    
    const fetchCourses = async () => {
        const response = await api.get('/course-management/versions');
        setCourses(response.data.items);
    };
    
    const createFork = async (masterVersionId, classIds) => {
        const response = await api.post(`/course-management/versions/${masterVersionId}/fork`, {
            class_ids: classIds,
            fork_title_suffix: "Custom"
        });
        return response.data;
    };
    
    const submitPullRequest = async (sourceVersionId, targetVersionId, changes) => {
        const response = await api.post(`/course-management/versions/${sourceVersionId}/pull-requests`, {
            title: "Course Improvements",
            description: "Enhanced content based on student feedback",
            target_version_id: targetVersionId,
            changes: changes
        });
        return response.data;
    };
    
    return { courses, pullRequests, fetchCourses, createFork, submitPullRequest };
};

// Rich Text Editor Integration
const CourseEditor = ({ courseContent, onSave }) => {
    const [content, setContent] = useState(courseContent);
    
    const handleEmbedComponent = (type, position) => {
        const componentId = `${type}_${Date.now()}`;
        const markdownInsert = `{{${type}:${componentId}}}`;
        
        // Insert at cursor position
        insertAtCursor(markdownInsert);
        
        // Open component configuration modal
        openComponentModal(type, componentId);
    };
    
    return (
        <div className="course-editor">
            <MarkdownEditor 
                value={content}
                onChange={setContent}
                plugins={['quiz', 'assignment', 'interactive']}
                onEmbedComponent={handleEmbedComponent}
            />
            <ComponentLibrary onInsert={handleEmbedComponent} />
        </div>
    );
};
```

---

## 🎊 **CONCLUSION**

Smart Study Hub 2.0 Course Management System provides:

✅ **GitHub-style Collaboration** - Professional content management workflow  
✅ **Rich Interactive Content** - Markdown + embedded quizzes/assignments  
✅ **Complete Audit Trail** - Track every change and improvement  
✅ **Role-based Permissions** - Secure access control  
✅ **Teacher Empowerment** - Customize content for their classes  
✅ **Quality Control** - Coordinator oversight via pull requests  
✅ **Scalable Architecture** - Handle hundreds of courses and thousands of students  

**Ready for production use dengan comprehensive API documentation dan user guide!** 🚀

---

**📞 Support**: If you need help, check the API documentation at `/docs` or contact the development team.
