# FRONTEND API GUIDE - New Course System

**Version:** v1.0  
**Last Updated:** 2025-10-23  
**API Base URL:** `http://localhost:8000/api/v1` (Development)

---

## 📋 **TABLE OF CONTENTS**

1. [Authentication](#authentication)
2. [Teacher APIs](#teacher-apis)
3. [Student APIs](#student-apis)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Frontend Flows](#frontend-flows)
7. [State Management](#state-management)

---

## 🔐 **AUTHENTICATION**

### **Login**

All API calls require JWT token in Authorization header.

**Endpoint:**
```
POST /auth/login
```

**Request:**
```json
{
  "email": "user@school.com",
  "password": "password123"
}
```

**Response (Success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "_id": "507f1f77bcf86cd799439011",
    "email": "user@school.com",
    "username": "user",
    "roles": ["teacher"],
    "full_name": "John Doe"
  }
}
```

**Usage in subsequent requests:**
```javascript
// Add to all API requests
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

---

## 👨‍🏫 **TEACHER APIs**

### **1. Assign Course to Class**

**Purpose:** Teacher assigns a course to their class

**Endpoint:**
```
POST /course-assignments
```

**Request Headers:**
```
Authorization: Bearer {teacher_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "course_id": "673f1a2b3c4d5e6f7a8b9c0d",
  "class_id": "673f1a2b3c4d5e6f7a8b9c0e",
  "start_date": "2024-01-10T00:00:00Z",  // Optional
  "end_date": "2024-06-30T00:00:00Z",    // Optional
  "settings": {}                          // Optional custom settings
}
```

**Response (Success 201):**
```json
{
  "success": true,
  "message": "Course assigned to class successfully",
  "assignment": {
    "id": "673f1a2b3c4d5e6f7a8b9c10",
    "course_id": "673f1a2b3c4d5e6f7a8b9c0d",
    "course_title": "Matematika Kelas 10",
    "class_id": "673f1a2b3c4d5e6f7a8b9c0e",
    "class_name": "10A",
    "teacher_id": "673f1a2b3c4d5e6f7a8b9c0f",
    "teacher_name": "Pak Budi",
    "metadata": {
      "total_students": 30,
      "started_students": 0,
      "completed_students": 0,
      "average_progress": 0.0,
      "average_score": 0.0,
      "last_calculated": "2024-01-20T10:00:00Z"
    },
    "class_overrides": {
      "unlocked_modules": [],
      "student_overrides": []
    },
    "settings": {},
    "assigned_at": "2024-01-20T10:00:00Z",
    "start_date": "2024-01-10T00:00:00Z",
    "end_date": "2024-06-30T00:00:00Z",
    "status": "active",
    "created_at": "2024-01-20T10:00:00Z",
    "updated_at": "2024-01-20T10:00:00Z",
    "can_edit": true,
    "can_delete": true,
    "can_override": true
  }
}
```

**Response (Error 400):**
```json
{
  "detail": "Course already assigned to this class"
}
```

**Response (Error 403):**
```json
{
  "detail": "Only teachers of this class can assign courses"
}
```

**Response (Error 404):**
```json
{
  "detail": "Course not found"
}
// or
{
  "detail": "Class not found"
}
```

---

### **2. Get Assignment Details**

**Purpose:** Get full details of a course assignment

**Endpoint:**
```
GET /course-assignments/{assignment_id}
```

**Request Headers:**
```
Authorization: Bearer {teacher_token}
```

**Response (Success 200):**
```json
{
  "success": true,
  "assignment": {
    // Same structure as create response
    "id": "...",
    "course_title": "...",
    "class_name": "...",
    "metadata": {...},
    "class_overrides": {...},
    ...
  }
}
```

---

### **3. List Assignments by Class**

**Purpose:** Get all course assignments for a specific class

**Endpoint:**
```
GET /course-assignments/class/{class_id}?include_archived=false
```

**Query Parameters:**
- `include_archived` (boolean, optional) - Include archived assignments (default: false)

**Request Headers:**
```
Authorization: Bearer {teacher_token}
```

**Response (Success 200):**
```json
{
  "success": true,
  "total": 2,
  "assignments": [
    {
      "id": "...",
      "course_title": "Matematika Kelas 10",
      "class_name": "10A",
      "status": "active",
      ...
    },
    {
      "id": "...",
      "course_title": "Fisika Kelas 10",
      "class_name": "10A",
      "status": "active",
      ...
    }
  ]
}
```

---

### **4. List Assignments by Course**

**Purpose:** Get all class assignments for a specific course

**Endpoint:**
```
GET /course-assignments/course/{course_id}?include_archived=false
```

**Response:** Same format as list by class

---

### **5. Update Assignment Settings**

**Purpose:** Update custom settings for an assignment

**Endpoint:**
```
PUT /course-assignments/{assignment_id}/settings
```

**Request Body:**
```json
{
  "start_date": "2024-01-15T00:00:00Z",  // Optional
  "end_date": "2024-07-31T00:00:00Z",    // Optional
  "settings": {                           // Optional
    "allow_skip": true,
    "custom_setting": "value"
  }
}
```

**Response (Success 200):**
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "assignment": {
    // Updated assignment object
  }
}
```

---

### **6. Archive Assignment**

**Purpose:** Soft delete assignment (students lose access)

**Endpoint:**
```
DELETE /course-assignments/{assignment_id}
```

**Response (Success 200):**
```json
{
  "success": true,
  "message": "Assignment archived successfully"
}
```

**Note:** This sets status to "archived". Student can't access anymore but data preserved.

---

### **7. Restore Assignment**

**Purpose:** Restore archived assignment

**Endpoint:**
```
POST /course-assignments/{assignment_id}/restore
```

**Response (Success 200):**
```json
{
  "success": true,
  "message": "Assignment restored successfully",
  "assignment": {
    // Restored assignment with status: "active"
  }
}
```

---

### **8. Add Student Override (Unlock Content)**

**Purpose:** Unlock specific modules/lessons for a specific student

**Endpoint:**
```
POST /course-assignments/{assignment_id}/overrides
```

**Request Body:**
```json
{
  "student_id": "673f1a2b3c4d5e6f7a8b9c11",
  "unlocked_modules": [
    "673f1a2b3c4d5e6f7a8b9c12"  // Module IDs to unlock
  ],
  "unlocked_lessons": [
    "673f1a2b3c4d5e6f7a8b9c13"  // Lesson IDs to unlock
  ],
  "reason": "Student request untuk persiapan ujian"  // Optional
}
```

**Response (Success 200):**
```json
{
  "success": true,
  "message": "Student override added successfully",
  "overrides": {
    "unlocked_modules": [],
    "student_overrides": [
      {
        "student_id": "673f1a2b3c4d5e6f7a8b9c11",
        "student_name": "Ahmad Fauzi",
        "unlocked_modules": ["673f1a2b3c4d5e6f7a8b9c12"],
        "unlocked_lessons": ["673f1a2b3c4d5e6f7a8b9c13"],
        "reason": "Student request untuk persiapan ujian",
        "overridden_by": "673f1a2b3c4d5e6f7a8b9c0f",
        "overridden_by_name": "Pak Budi",
        "created_at": "2024-01-20T14:30:00Z"
      }
    ]
  }
}
```

**Use Case:**
```
Student requests access to locked module for exam preparation.
Teacher can grant temporary access using this endpoint.
```

---

### **9. Remove Student Override**

**Purpose:** Remove unlock override for a student

**Endpoint:**
```
DELETE /course-assignments/{assignment_id}/overrides/{student_id}
```

**Response (Success 200):**
```json
{
  "success": true,
  "message": "Student override removed successfully"
}
```

---

## 👨‍🎓 **STUDENT APIs**

### **1. List My Courses**

**Purpose:** Get all courses accessible to student via their class

**Endpoint:**
```
GET /my/courses
```

**Request Headers:**
```
Authorization: Bearer {student_token}
```

**Response (Success 200):**
```json
{
  "success": true,
  "total": 2,
  "courses": [
    {
      "course": {
        "id": "673f1a2b3c4d5e6f7a8b9c0d",
        "title": "Matematika Kelas 10",
        "description": "Course matematika untuk kelas 10",
        "total_modules": 3
      },
      "assignment": {
        "id": "673f1a2b3c4d5e6f7a8b9c10",
        "start_date": "2024-01-10T00:00:00Z",
        "end_date": "2024-06-30T00:00:00Z"
      },
      "progress": {
        "student_id": "673f1a2b3c4d5e6f7a8b9c11",
        "course_class_setting_id": "673f1a2b3c4d5e6f7a8b9c10",
        "course_id": "673f1a2b3c4d5e6f7a8b9c0d",
        "course_title": "Matematika Kelas 10",
        "total_modules": 3,
        "completed_modules": 1,
        "in_progress_modules": 1,
        "total_lessons": 10,
        "completed_lessons": 4,
        "in_progress_lessons": 2,
        "completion_percentage": 40.0,
        "average_score": 82.5,
        "total_time_spent": 7200,  // in seconds
        "status": "in_progress",   // not_started | in_progress | completed
        "started_at": "2024-01-10T08:00:00Z",
        "completed_at": null,
        "last_activity": "2024-01-20T15:30:00Z"
      },
      "modules": [
        {
          "module_id": "673f1a2b3c4d5e6f7a8b9c12",
          "order": 1,
          "completed": true,
          "locked": false,
          "accessible": true,
          "override_unlocked": false
        },
        {
          "module_id": "673f1a2b3c4d5e6f7a8b9c13",
          "order": 2,
          "completed": false,
          "locked": false,        // Currently working on this
          "accessible": true,
          "override_unlocked": false
        },
        {
          "module_id": "673f1a2b3c4d5e6f7a8b9c14",
          "order": 3,
          "completed": false,
          "locked": true,         // Locked until Module 2 done
          "accessible": false,
          "override_unlocked": false
        }
      ]
    }
  ]
}
```

**Frontend Display:**
```javascript
// Use this data to show:
// 1. Course card with progress bar (completion_percentage)
// 2. Module list with lock icons
// 3. "Continue Learning" button pointing to first incomplete module
// 4. Stats: completed_lessons / total_lessons
```

---

### **2. Get Course Detail with Lock Status**

**Purpose:** Get complete course structure with module/lesson lock status

**Endpoint:**
```
GET /my/courses/{course_id}
```

**Request Headers:**
```
Authorization: Bearer {student_token}
```

**Response (Success 200):**
```json
{
  "success": true,
  "course": {
    "id": "673f1a2b3c4d5e6f7a8b9c0d",
    "title": "Matematika Kelas 10",
    "description": "...",
    "sequential_mode": true,
    "total_modules": 3
  },
  "progress": {
    // Same as in list courses
    "completion_percentage": 40.0,
    "status": "in_progress",
    ...
  },
  "modules": [
    {
      "module_id": "673f1a2b3c4d5e6f7a8b9c12",
      "title": "Module 1: Aljabar",
      "order": 1,
      "completed": true,
      "locked": false,
      "accessible": true,
      "override_unlocked": false,
      "lessons": [
        {
          "lesson_id": "673f1a2b3c4d5e6f7a8b9c15",
          "order": 1,
          "module_id": "673f1a2b3c4d5e6f7a8b9c12",
          "completed": true,
          "locked": false,
          "accessible": true,
          "override_unlocked": false
        },
        {
          "lesson_id": "673f1a2b3c4d5e6f7a8b9c16",
          "order": 2,
          "module_id": "673f1a2b3c4d5e6f7a8b9c12",
          "completed": true,
          "locked": false,
          "accessible": true,
          "override_unlocked": false
        }
      ]
    },
    {
      "module_id": "673f1a2b3c4d5e6f7a8b9c13",
      "title": "Module 2: Geometri",
      "order": 2,
      "completed": false,
      "locked": false,
      "accessible": true,
      "override_unlocked": false,
      "lessons": [
        {
          "lesson_id": "673f1a2b3c4d5e6f7a8b9c17",
          "order": 1,
          "module_id": "673f1a2b3c4d5e6f7a8b9c13",
          "completed": true,
          "locked": false,
          "accessible": true,
          "override_unlocked": false
        },
        {
          "lesson_id": "673f1a2b3c4d5e6f7a8b9c18",
          "order": 2,
          "module_id": "673f1a2b3c4d5e6f7a8b9c13",
          "completed": false,
          "locked": false,        // ← Next lesson to do
          "accessible": true,
          "override_unlocked": false
        },
        {
          "lesson_id": "673f1a2b3c4d5e6f7a8b9c19",
          "order": 3,
          "module_id": "673f1a2b3c4d5e6f7a8b9c13",
          "completed": false,
          "locked": true,         // ← Locked until lesson 2 done
          "accessible": false,
          "override_unlocked": false
        }
      ]
    },
    {
      "module_id": "673f1a2b3c4d5e6f7a8b9c14",
      "title": "Module 3: Trigonometri",
      "order": 3,
      "completed": false,
      "locked": true,               // ← Module locked
      "accessible": false,
      "override_unlocked": false,
      "lessons": []                 // ← No lessons shown (module locked)
    }
  ]
}
```

**Response (Error 404):**
```json
{
  "detail": "Course not assigned to your class"
}
```

**Frontend Usage:**
```javascript
// Display:
// 1. Course header with title, description
// 2. Progress bar (completion_percentage)
// 3. Module list with expand/collapse
// 4. Lesson list per module
// 5. Lock icons on locked items
// 6. "Continue" button on first incomplete lesson
// 7. Gray out locked items
// 8. Show "🔓 Override" badge if override_unlocked = true
```

---

### **3. Complete Lesson & Navigate to Next**

**Purpose:** Mark current lesson as completed and get next lesson info

**Endpoint:**
```
POST /my/courses/{course_id}/lessons/{lesson_id}/next
```

**Request Headers:**
```
Authorization: Bearer {student_token}
```

**Request Body:**
```
No body needed
```

**Response (Success 200):**
```json
{
  "success": true,
  "message": "Lesson completed!",
  "completed_content": {
    "content_type": "lesson",
    "lesson_id": "673f1a2b3c4d5e6f7a8b9c18",
    "title": "Lesson 2.2: Lingkaran"
  },
  "next_content": {
    "content_type": "lesson",
    "content_id": "673f1a2b3c4d5e6f7a8b9c19",
    "title": "Lesson 2.3: Ellips",
    "module_id": "673f1a2b3c4d5e6f7a8b9c13"
  },
  "has_next": true,
  "course_completed": false
}
```

**Response (Last Lesson in Module):**
```json
{
  "success": true,
  "message": "Lesson completed!",
  "completed_content": {
    "content_type": "lesson",
    "lesson_id": "673f1a2b3c4d5e6f7a8b9c19",
    "title": "Lesson 2.3: Ellips"
  },
  "next_content": {
    "content_type": "lesson",
    "content_id": "673f1a2b3c4d5e6f7a8b9c1a",  // First lesson of next module
    "title": "Lesson 3.1: Sin Cos Tan",
    "module_id": "673f1a2b3c4d5e6f7a8b9c14"
  },
  "has_next": true,
  "course_completed": false
}
```

**Response (Course Completed):**
```json
{
  "success": true,
  "message": "Lesson completed!",
  "completed_content": {
    "content_type": "lesson",
    "lesson_id": "673f1a2b3c4d5e6f7a8b9c1a",
    "title": "Lesson 3.1: Sin Cos Tan"
  },
  "next_content": null,           // ← No more lessons
  "has_next": false,
  "course_completed": true        // ← Course done!
}
```

**Frontend Flow:**
```javascript
// When student clicks "Next" button at end of lesson:

async function handleNextLesson() {
  const response = await fetch(
    `/my/courses/${courseId}/lessons/${currentLessonId}/next`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}` } }
  );
  
  const data = await response.json();
  
  if (data.has_next) {
    // Navigate to next lesson
    router.push(`/courses/${courseId}/lessons/${data.next_content.content_id}`);
  } else if (data.course_completed) {
    // Show completion celebration
    showCompletionModal();
    router.push(`/courses/${courseId}/completed`);
  }
}
```

---

### **4. Get Course Progress Details**

**Purpose:** Get detailed progress list for analytics/review

**Endpoint:**
```
GET /my/courses/{course_id}/progress
```

**Request Headers:**
```
Authorization: Bearer {student_token}
```

**Response (Success 200):**
```json
{
  "success": true,
  "summary": {
    "student_id": "673f1a2b3c4d5e6f7a8b9c11",
    "course_class_setting_id": "673f1a2b3c4d5e6f7a8b9c10",
    "course_id": "673f1a2b3c4d5e6f7a8b9c0d",
    "course_title": "Matematika Kelas 10",
    "total_modules": 3,
    "completed_modules": 1,
    "in_progress_modules": 1,
    "total_lessons": 10,
    "completed_lessons": 4,
    "in_progress_lessons": 2,
    "completion_percentage": 40.0,
    "average_score": 82.5,
    "total_time_spent": 7200,
    "status": "in_progress",
    "started_at": "2024-01-10T08:00:00Z",
    "completed_at": null,
    "last_activity": "2024-01-20T15:30:00Z"
  },
  "progress": [
    {
      "id": "673f1a2b3c4d5e6f7a8b9c1b",
      "student_id": "673f1a2b3c4d5e6f7a8b9c11",
      "course_class_setting_id": "673f1a2b3c4d5e6f7a8b9c10",
      "module_id": "673f1a2b3c4d5e6f7a8b9c12",
      "lesson_id": "673f1a2b3c4d5e6f7a8b9c15",
      "page_number": null,
      "content_type": "lesson",
      "status": "completed",
      "completed_at": "2024-01-10T10:30:00Z",
      "time_spent": 1800,  // 30 minutes
      "score": 90.0,
      "max_score": 100.0,
      "submission": null,
      "attempts": 1,
      "started_at": "2024-01-10T10:00:00Z",
      "last_activity": "2024-01-10T10:30:00Z",
      "created_at": "2024-01-10T10:00:00Z",
      "updated_at": "2024-01-10T10:30:00Z"
    },
    // ... more progress entries
  ]
}
```

**Frontend Usage:**
```javascript
// Display progress page:
// - Overall stats from summary
// - Timeline of completed lessons
// - Time spent per lesson (chart)
// - Scores per lesson (if applicable)
```

---

## 📊 **DATA MODELS**

### **Module Lock Status**
```typescript
interface ModuleLockStatus {
  module_id: string;
  title?: string;
  order: number;
  completed: boolean;      // Student completed this module
  locked: boolean;         // Locked by sequential rule
  accessible: boolean;     // Can access (unlocked OR override)
  override_unlocked: boolean;  // Unlocked by teacher override
}
```

**UI Logic:**
```javascript
// Show lock icon if locked
if (module.locked && !module.accessible) {
  showLockIcon();
}

// Show override badge if unlocked by teacher
if (module.override_unlocked) {
  showOverrideBadge();
}

// Allow click only if accessible
if (module.accessible) {
  enableClick();
}

// Show checkmark if completed
if (module.completed) {
  showCheckmark();
}
```

---

### **Lesson Lock Status**
```typescript
interface LessonLockStatus {
  lesson_id: string;
  title?: string;
  order: number;
  module_id: string;
  completed: boolean;
  locked: boolean;
  accessible: boolean;
  override_unlocked: boolean;
}
```

---

### **Progress Summary**
```typescript
interface ProgressSummary {
  student_id: string;
  course_class_setting_id: string;
  course_id: string;
  course_title: string;
  
  // Module stats
  total_modules: number;
  completed_modules: number;
  in_progress_modules: number;
  
  // Lesson stats
  total_lessons: number;
  completed_lessons: number;
  in_progress_lessons: number;
  
  // Overall
  completion_percentage: number;  // 0-100
  average_score: number;          // 0-100
  total_time_spent: number;       // seconds
  
  // Status
  status: 'not_started' | 'in_progress' | 'completed';
  started_at: string | null;      // ISO 8601 date
  completed_at: string | null;
  last_activity: string | null;
}
```

---

### **Assignment**
```typescript
interface CourseAssignment {
  id: string;
  course_id: string;
  course_title: string;
  class_id: string;
  class_name: string;
  teacher_id: string;
  teacher_name: string;
  
  metadata: {
    total_students: number;
    started_students: number;
    completed_students: number;
    average_progress: number;
    average_score: number;
    last_calculated: string;
  };
  
  class_overrides: {
    unlocked_modules: string[];
    student_overrides: StudentOverride[];
  };
  
  settings: Record<string, any>;
  
  assigned_at: string;
  start_date: string | null;
  end_date: string | null;
  status: 'active' | 'archived';
  
  // Permissions
  can_edit: boolean;
  can_delete: boolean;
  can_override: boolean;
}
```

---

## ⚠️ **ERROR HANDLING**

### **HTTP Status Codes**

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | GET requests successful |
| 201 | Created | POST create successful |
| 400 | Bad Request | Invalid data, duplicate assignment |
| 401 | Unauthorized | Token missing or invalid |
| 403 | Forbidden | No permission for action |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Server-side error |

---

### **Error Response Format**

**All errors return:**
```json
{
  "detail": "Error message here"
}
```

**Common Error Messages:**

**Authentication:**
```json
{"detail": "Could not validate credentials"}
{"detail": "Token has expired"}
```

**Authorization:**
```json
{"detail": "Only teachers of this class can assign courses"}
{"detail": "Only the assigned teacher can update settings"}
{"detail": "This endpoint is for students only"}
```

**Not Found:**
```json
{"detail": "Course not found"}
{"detail": "Class not found"}
{"detail": "Assignment not found"}
{"detail": "Course not assigned to your class"}
```

**Bad Request:**
```json
{"detail": "Course already assigned to this class"}
{"detail": "Invalid course_id format"}
```

---

### **Frontend Error Handling**

```javascript
async function apiCall(endpoint, options) {
  try {
    const response = await fetch(endpoint, options);
    
    if (!response.ok) {
      const error = await response.json();
      
      switch (response.status) {
        case 401:
          // Token expired, redirect to login
          clearToken();
          router.push('/login');
          break;
          
        case 403:
          // No permission
          showToast('error', error.detail || 'You do not have permission');
          break;
          
        case 404:
          // Not found
          showToast('error', error.detail || 'Resource not found');
          break;
          
        case 400:
          // Bad request (user error)
          showToast('warning', error.detail || 'Invalid request');
          break;
          
        case 500:
          // Server error
          showToast('error', 'Server error, please try again');
          logError(error);
          break;
      }
      
      throw new Error(error.detail);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

---

## 🔄 **FRONTEND FLOWS**

### **Flow 1: Teacher Assigns Course**

```
┌─────────────┐
│ Teacher     │
│ Dashboard   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Select Class    │
│ Select Course   │
│ Set Dates       │
└──────┬──────────┘
       │
       ▼
POST /course-assignments
{course_id, class_id, start_date, end_date}
       │
       ▼
┌─────────────────┐
│ Show Success    │
│ "Course Assigned"│
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Redirect to     │
│ Assignment List │
└─────────────────┘
```

**Code Example:**
```javascript
// Teacher assigns course
async function assignCourse(courseId, classId, startDate, endDate) {
  const response = await fetch('/api/v1/course-assignments', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      course_id: courseId,
      class_id: classId,
      start_date: startDate,
      end_date: endDate
    })
  });
  
  if (response.ok) {
    const data = await response.json();
    showToast('success', 'Course assigned successfully');
    router.push(`/teacher/assignments/${data.assignment.id}`);
  }
}
```

---

### **Flow 2: Student Accesses Course**

```
┌─────────────┐
│ Student     │
│ Dashboard   │
└──────┬──────┘
       │
       ▼
GET /my/courses
       │
       ▼
┌──────────────────┐
│ Show Course List │
│ with Progress    │
└──────┬───────────┘
       │
       ▼ (Click course)
GET /my/courses/{id}
       │
       ▼
┌──────────────────────┐
│ Show Course Detail   │
│ - Modules with locks │
│ - Lessons with locks │
│ - Progress bar       │
└──────┬───────────────┘
       │
       ▼ (Click accessible lesson)
┌──────────────────┐
│ Show Lesson      │
│ Content          │
└──────┬───────────┘
       │
       ▼ (Click "Next")
POST /my/courses/{id}/lessons/{lesson_id}/next
       │
       ▼
┌──────────────────┐
│ Navigate to      │
│ Next Lesson      │
└──────────────────┘
```

**Code Example:**
```javascript
// Student course page
function CoursePage({ courseId }) {
  const [courseData, setCourseData] = useState(null);
  
  useEffect(() => {
    async function loadCourse() {
      const response = await fetch(
        `/api/v1/my/courses/${courseId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await response.json();
      setCourseData(data);
    }
    loadCourse();
  }, [courseId]);
  
  return (
    <div>
      <h1>{courseData?.course.title}</h1>
      <ProgressBar percent={courseData?.progress.completion_percentage} />
      
      {courseData?.modules.map(module => (
        <ModuleCard
          key={module.module_id}
          module={module}
          locked={!module.accessible}
        />
      ))}
    </div>
  );
}
```

---

### **Flow 3: Student Completes Lesson**

```
┌──────────────────┐
│ Student Reading  │
│ Lesson Content   │
└──────┬───────────┘
       │
       ▼ (Scroll to end)
┌──────────────────┐
│ Show "Next"      │
│ Button           │
└──────┬───────────┘
       │
       ▼ (Click "Next")
POST /my/courses/{id}/lessons/{lesson_id}/next
       │
       ▼
┌──────────────────────┐
│ Backend:             │
│ - Mark completed     │
│ - Save progress      │
│ - Unlock next lesson │
│ - Return next info   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────┐
│ Show transition  │
│ "Lesson Complete"│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Navigate to      │
│ Next Lesson      │
└──────────────────┘
```

---

### **Flow 4: Teacher Unlocks Content for Student**

```
┌──────────────────┐
│ Teacher View     │
│ Class Progress   │
└──────┬───────────┘
       │
       ▼ (See student stuck)
┌──────────────────┐
│ Click "Override  │
│ Lock" button     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Modal:           │
│ - Select student │
│ - Select module  │
│ - Enter reason   │
└──────┬───────────┘
       │
       ▼
POST /course-assignments/{id}/overrides
{student_id, unlocked_modules, reason}
       │
       ▼
┌──────────────────┐
│ Show Success     │
│ "Content Unlocked"│
└──────┬───────────┘
       │
       ▼
┌──────────────────────┐
│ Student's next view: │
│ - Module accessible  │
│ - Badge: "Unlocked"  │
└──────────────────────┘
```

**Code Example:**
```javascript
// Teacher unlock content
async function unlockForStudent(assignmentId, studentId, moduleIds, reason) {
  const response = await fetch(
    `/api/v1/course-assignments/${assignmentId}/overrides`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        student_id: studentId,
        unlocked_modules: moduleIds,
        unlocked_lessons: [],
        reason: reason
      })
    }
  );
  
  if (response.ok) {
    showToast('success', 'Content unlocked for student');
    refreshClassProgress();
  }
}
```

---

## 💾 **STATE MANAGEMENT**

### **Recommended State Structure**

```typescript
// Global State (Redux/Zustand/Context)
interface AppState {
  auth: {
    token: string | null;
    user: User | null;
    isAuthenticated: boolean;
  };
  
  // For teachers
  teacher: {
    assignments: CourseAssignment[];
    selectedAssignment: CourseAssignment | null;
  };
  
  // For students
  student: {
    courses: CourseWithProgress[];
    selectedCourse: CourseDetail | null;
    currentLesson: Lesson | null;
  };
}
```

---

### **What to Store Locally**

**localStorage:**
```javascript
// Store token
localStorage.setItem('access_token', token);

// Store user info
localStorage.setItem('user', JSON.stringify(user));

// Store last visited course (optional)
localStorage.setItem('last_course_id', courseId);
```

**sessionStorage (for temp data):**
```javascript
// Store current lesson progress (not yet saved)
sessionStorage.setItem('lesson_progress', JSON.stringify({
  lessonId: '...',
  timeSpent: 300,
  currentPage: 2
}));
```

**Don't store:**
- ❌ Course content (too large)
- ❌ Lock status (calculated server-side)
- ❌ Other users' data

---

### **State Updates**

**After login:**
```javascript
// Fetch and store courses
const courses = await fetchMyCourses();
setCourses(courses);
```

**After completing lesson:**
```javascript
// Update local progress
const response = await completeLesson(courseId, lessonId);
if (response.success) {
  // Re-fetch course to get updated lock status
  const updated = await fetchCourseDetail(courseId);
  setCurrentCourse(updated);
}
```

**Polling for updates (optional):**
```javascript
// Poll for assignment updates (teacher dashboard)
setInterval(async () => {
  const assignments = await fetchAssignments();
  setAssignments(assignments);
}, 30000); // Every 30 seconds
```

---

## 🎨 **UI RECOMMENDATIONS**

### **Lock Status Display**

```jsx
// Module card
function ModuleCard({ module }) {
  return (
    <div className={module.accessible ? '' : 'opacity-50 cursor-not-allowed'}>
      <div className="flex items-center justify-between">
        <h3>{module.title}</h3>
        
        {/* Lock icon */}
        {module.locked && !module.accessible && (
          <LockIcon className="text-gray-400" />
        )}
        
        {/* Checkmark if completed */}
        {module.completed && (
          <CheckCircleIcon className="text-green-500" />
        )}
        
        {/* Override badge */}
        {module.override_unlocked && (
          <Badge color="blue">🔓 Unlocked by Teacher</Badge>
        )}
      </div>
      
      {/* Only clickable if accessible */}
      <button
        onClick={() => openModule(module.module_id)}
        disabled={!module.accessible}
      >
        Open Module
      </button>
    </div>
  );
}
```

---

### **Progress Display**

```jsx
// Progress bar component
function CourseProgress({ progress }) {
  return (
    <div>
      <div className="flex justify-between mb-2">
        <span>Progress</span>
        <span>{progress.completion_percentage.toFixed(1)}%</span>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all"
          style={{ width: `${progress.completion_percentage}%` }}
        />
      </div>
      
      <div className="mt-2 text-sm text-gray-600">
        {progress.completed_lessons} / {progress.total_lessons} lessons completed
      </div>
      
      <div className="text-xs text-gray-500">
        Time spent: {Math.floor(progress.total_time_spent / 60)} minutes
      </div>
    </div>
  );
}
```

---

### **Continue Learning Button**

```jsx
// Find first incomplete lesson
function ContinueLearningButton({ courseId, modules }) {
  const firstIncomplete = useMemo(() => {
    for (const module of modules) {
      if (!module.accessible) continue;
      
      for (const lesson of module.lessons || []) {
        if (!lesson.completed && lesson.accessible) {
          return { moduleId: module.module_id, lessonId: lesson.lesson_id };
        }
      }
    }
    return null;
  }, [modules]);
  
  if (!firstIncomplete) return null;
  
  return (
    <button
      onClick={() => router.push(
        `/courses/${courseId}/lessons/${firstIncomplete.lessonId}`
      )}
      className="btn-primary"
    >
      Continue Learning →
    </button>
  );
}
```

---

## 🔍 **DEBUGGING TIPS**

### **Check API Response**

```javascript
// Log full response for debugging
async function fetchCourses() {
  try {
    const response = await fetch('/api/v1/my/courses', {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    console.log('Status:', response.status);
    console.log('Headers:', response.headers);
    
    const data = await response.json();
    console.log('Response:', JSON.stringify(data, null, 2));
    
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

### **Verify Token**

```javascript
// Check if token is valid
function isTokenValid(token) {
  if (!token) return false;
  
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() < exp;
  } catch {
    return false;
  }
}

// Use before API calls
if (!isTokenValid(token)) {
  refreshToken() or redirectToLogin();
}
```

---

### **Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Token missing/expired | Check localStorage, re-login |
| 403 Forbidden | Wrong user role | Verify user.roles array |
| 404 Not Found | Wrong ID format | Check ObjectId format (24 hex chars) |
| Empty courses list | No assignments | Teacher must assign course first |
| All modules locked | Lock calc error | Check sequential_mode & progress |

---

## 📚 **RESOURCES**

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Testing:**
- Test Collection: `docs/API_TEST_COLLECTION.http`
- Testing Guide: `docs/TESTING_GUIDE.md`

**Architecture:**
- Implementation Summary: `docs/API_IMPLEMENTATION_SUMMARY.md`
- Refactor Plan: `docs/REFACTOR_COURSE_SYSTEM.md`

---

## ✅ **CHECKLIST FOR FRONTEND IMPLEMENTATION**

### **Authentication**
- [ ] Implement login flow
- [ ] Store token in localStorage
- [ ] Add Authorization header to all requests
- [ ] Handle token expiration (refresh or redirect)
- [ ] Clear token on logout

### **Teacher Features**
- [ ] Course assignment form
- [ ] Assignment list page
- [ ] Assignment detail page
- [ ] Override unlock modal
- [ ] Archive/restore functionality

### **Student Features**
- [ ] Course list page with progress
- [ ] Course detail page with lock status
- [ ] Lesson viewer
- [ ] Next button with API integration
- [ ] Progress page/dashboard

### **UI Components**
- [ ] Lock icon for locked content
- [ ] Progress bar component
- [ ] Module/Lesson cards
- [ ] Override badge
- [ ] Completion checkmarks
- [ ] Loading states
- [ ] Error messages

### **State Management**
- [ ] Setup state store (Redux/Zustand/Context)
- [ ] Auth state
- [ ] Course state
- [ ] Progress state
- [ ] Loading & error states

### **Error Handling**
- [ ] Handle 401 (redirect to login)
- [ ] Handle 403 (show permission error)
- [ ] Handle 404 (show not found)
- [ ] Handle 500 (show server error)
- [ ] Network error handling

---

**Last Updated:** 2025-10-23  
**Version:** 1.0  
**Questions?** Check `docs/TESTING_GUIDE.md` or API Swagger docs

---

*Happy Coding!* 🚀
