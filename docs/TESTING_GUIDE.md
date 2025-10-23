# TESTING GUIDE - New Course System

## 📋 **TEST SCENARIOS**

### **Prerequisites**
1. Server running: `python main.py` atau `uvicorn main:app --reload`
2. Database connected
3. Test data:
   - 1 Coordinator user
   - 1 Teacher user (with teaching_assignment)
   - 2 Student users (same class)
   - 1 Subject
   - 1 Class
   - 1 Course (with modules & lessons)

---

## 🎯 **TEST SCENARIO 1: Teacher Assigns Course to Class**

### **Setup**
```bash
# Existing data needed:
- Teacher user (ID: teacher_id)
- Class (ID: class_id)
- Course (ID: course_id)
- teaching_assignment: {teacher_id, class_id, status: "active"}
```

### **Test Steps**

#### **Step 1.1: Login as Teacher**
```bash
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "email": "teacher@school.com",
  "password": "password123"
}

# Save token dari response
```

#### **Step 1.2: Assign Course to Class**
```bash
POST http://localhost:8000/api/v1/course-assignments
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "course_id": "{course_id}",
  "class_id": "{class_id}",
  "start_date": "2024-01-10T00:00:00Z",
  "end_date": "2024-06-30T00:00:00Z",
  "settings": {}
}

# Expected Response:
{
  "success": true,
  "message": "Course assigned to class successfully",
  "assignment": {
    "id": "...",
    "course_id": "...",
    "course_title": "...",
    "class_id": "...",
    "class_name": "...",
    "teacher_id": "...",
    "teacher_name": "...",
    "metadata": {
      "total_students": 0,
      "started_students": 0,
      "completed_students": 0,
      "average_progress": 0.0
    },
    "can_edit": true,
    "can_delete": true
  }
}
```

**✅ Verify:**
- Response success = true
- assignment.id exists
- course_title & class_name populated
- can_edit = true

**❌ Error Cases to Test:**
```bash
# Case 1: Already assigned
POST /course-assignments (same course + class)
Expected: 400 "Course already assigned to this class"

# Case 2: Invalid course_id
POST /course-assignments {course_id: "invalid"}
Expected: 404 "Course not found"

# Case 3: Not teacher of class
POST /course-assignments (different class)
Expected: 403 "Only teachers of this class can assign courses"
```

#### **Step 1.3: Get Assignment Details**
```bash
GET http://localhost:8000/api/v1/course-assignments/{assignment_id}
Authorization: Bearer {teacher_token}

# Expected Response:
{
  "success": true,
  "assignment": {
    "id": "...",
    "course_title": "...",
    "class_name": "...",
    "metadata": {...},
    "class_overrides": {
      "unlocked_modules": [],
      "student_overrides": []
    }
  }
}
```

#### **Step 1.4: List Class Assignments**
```bash
GET http://localhost:8000/api/v1/course-assignments/class/{class_id}
Authorization: Bearer {teacher_token}

# Expected Response:
{
  "success": true,
  "total": 1,
  "assignments": [...]
}
```

---

## 🎯 **TEST SCENARIO 2: Student Lists Accessible Courses**

### **Setup**
```bash
# Prerequisites:
- Course assigned to class (from Scenario 1)
- Student user with class_id = assigned class
```

### **Test Steps**

#### **Step 2.1: Login as Student**
```bash
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "email": "student@school.com",
  "password": "password123"
}

# Save token
```

#### **Step 2.2: List My Courses**
```bash
GET http://localhost:8000/api/v1/my/courses
Authorization: Bearer {student_token}

# Expected Response:
{
  "success": true,
  "total": 1,
  "courses": [
    {
      "course": {
        "id": "...",
        "title": "...",
        "description": "...",
        "total_modules": 3
      },
      "assignment": {
        "id": "...",
        "start_date": "...",
        "end_date": "..."
      },
      "progress": {
        "student_id": "...",
        "course_class_setting_id": "...",
        "course_id": "...",
        "course_title": "...",
        "total_modules": 3,
        "completed_modules": 0,
        "in_progress_modules": 0,
        "total_lessons": 10,
        "completed_lessons": 0,
        "in_progress_lessons": 0,
        "completion_percentage": 0.0,
        "average_score": 0.0,
        "total_time_spent": 0,
        "status": "not_started",
        "started_at": null,
        "completed_at": null,
        "last_activity": null
      },
      "modules": [
        {
          "module_id": "...",
          "order": 1,
          "completed": false,
          "locked": false,      // ← First module unlocked
          "accessible": true,
          "override_unlocked": false
        },
        {
          "module_id": "...",
          "order": 2,
          "completed": false,
          "locked": true,       // ← Sequential lock
          "accessible": false,
          "override_unlocked": false
        },
        {
          "module_id": "...",
          "order": 3,
          "completed": false,
          "locked": true,       // ← Sequential lock
          "accessible": false,
          "override_unlocked": false
        }
      ]
    }
  ]
}
```

**✅ Verify:**
- Course appears in list
- progress shows 0% (not started)
- First module accessible = true, locked = false
- Other modules accessible = false, locked = true
- Override_unlocked = false (no overrides yet)

**❌ Error Cases:**
```bash
# Case 1: Non-student user
Login as teacher → GET /my/courses
Expected: 403 "This endpoint is for students only"

# Case 2: No assigned courses
Student in class with no assignments
Expected: 200 {total: 0, courses: []}
```

---

## 🎯 **TEST SCENARIO 3: Student Views Course Detail**

#### **Step 3.1: Get Course Detail**
```bash
GET http://localhost:8000/api/v1/my/courses/{course_id}
Authorization: Bearer {student_token}

# Expected Response:
{
  "success": true,
  "course": {
    "id": "...",
    "title": "...",
    "description": "...",
    "sequential_mode": true,
    "total_modules": 3
  },
  "progress": {...},
  "modules": [
    {
      "module_id": "...",
      "title": "Module 1: Aljabar",
      "order": 1,
      "completed": false,
      "locked": false,
      "accessible": true,
      "override_unlocked": false,
      "lessons": [
        {
          "lesson_id": "...",
          "order": 1,
          "module_id": "...",
          "completed": false,
          "locked": false,     // ← First lesson accessible
          "accessible": true,
          "override_unlocked": false
        },
        {
          "lesson_id": "...",
          "order": 2,
          "module_id": "...",
          "completed": false,
          "locked": true,      // ← Locked until first done
          "accessible": false,
          "override_unlocked": false
        }
      ]
    },
    {
      "module_id": "...",
      "title": "Module 2: Geometri",
      "order": 2,
      "completed": false,
      "locked": true,          // ← Module locked
      "accessible": false,
      "override_unlocked": false,
      "lessons": []            // ← No lessons shown (module locked)
    }
  ]
}
```

**✅ Verify:**
- Course structure complete
- Module 1 accessible with lessons
- Module 1 Lesson 1 accessible
- Module 1 Lesson 2+ locked
- Module 2+ locked with no lessons shown

**❌ Error Cases:**
```bash
# Case 1: Course not assigned to student's class
GET /my/courses/{unassigned_course_id}
Expected: 404 "Course not assigned to your class"

# Case 2: Invalid course_id
GET /my/courses/invalid
Expected: 404 "Course not found"
```

---

## 🎯 **TEST SCENARIO 4: Student Completes Lesson & Navigates**

### **Setup**
```bash
# Student accessed Module 1 Lesson 1
# Now student clicks "Next" button
```

#### **Step 4.1: Complete First Lesson**
```bash
POST http://localhost:8000/api/v1/my/courses/{course_id}/lessons/{first_lesson_id}/next
Authorization: Bearer {student_token}

# Expected Response:
{
  "success": true,
  "message": "Lesson completed!",
  "completed_content": {
    "content_type": "lesson",
    "lesson_id": "...",
    "title": "Lesson 1.1: Persamaan Linear"
  },
  "next_content": {
    "content_type": "lesson",
    "content_id": "...",    // ← Second lesson ID
    "module_id": "..."
  },
  "has_next": true,
  "course_completed": false
}
```

**✅ Verify:**
- Response success = true
- completed_content shows current lesson
- next_content shows next lesson
- has_next = true

#### **Step 4.2: Verify Progress Updated**
```bash
GET http://localhost:8000/api/v1/my/courses/{course_id}
Authorization: Bearer {student_token}

# Expected: Module 1 Lesson 1 now shows:
{
  "lessons": [
    {
      "lesson_id": "...",
      "completed": true,      // ← NOW COMPLETED!
      "locked": false,
      "accessible": true
    },
    {
      "lesson_id": "...",
      "completed": false,
      "locked": false,        // ← NOW UNLOCKED!
      "accessible": true
    }
  ]
}
```

**✅ Verify:**
- First lesson completed = true
- Second lesson now accessible = true, locked = false
- Progress percentage increased

#### **Step 4.3: Complete All Lessons in Module 1**
```bash
# Repeat for each lesson in Module 1
POST /my/courses/{course_id}/lessons/{lesson_id}/next

# After completing last lesson in Module 1:
Expected response.next_content:
{
  "content_type": "lesson",
  "content_id": "...",     // ← First lesson of Module 2!
  "module_id": "..."       // ← Module 2 ID
}
```

**✅ Verify:**
- After Module 1 complete, next_content points to Module 2
- Module 2 now accessible = true (unlocked)

#### **Step 4.4: Get Progress Summary**
```bash
GET http://localhost:8000/api/v1/my/courses/{course_id}/progress
Authorization: Bearer {student_token}

# Expected Response:
{
  "success": true,
  "summary": {
    "completed_modules": 1,        // ← Module 1 done
    "completed_lessons": 4,
    "completion_percentage": 40.0, // ← 4/10 lessons
    "status": "in_progress"
  },
  "progress": [
    {
      "id": "...",
      "lesson_id": "...",
      "content_type": "lesson",
      "status": "completed",
      "completed_at": "...",
      "time_spent": 0
    },
    // ... more progress entries
  ]
}
```

**✅ Verify:**
- Summary shows correct counts
- Completion percentage calculated correctly
- Progress list shows all completed lessons

---

## 🎯 **TEST SCENARIO 5: Teacher Overrides Student Lock**

### **Scenario**
Student Ahmad wants to access Module 3 for exam preparation, but it's locked.
Teacher overrides the lock.

#### **Step 5.1: Before Override - Student View**
```bash
GET http://localhost:8000/api/v1/my/courses/{course_id}
Authorization: Bearer {ahmad_token}

# Module 3 status:
{
  "module_id": "module_3_id",
  "completed": false,
  "locked": true,           // ← Locked
  "accessible": false,      // ← Not accessible
  "override_unlocked": false
}
```

#### **Step 5.2: Teacher Adds Override**
```bash
POST http://localhost:8000/api/v1/course-assignments/{assignment_id}/overrides
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "student_id": "{ahmad_id}",
  "unlocked_modules": ["module_3_id"],
  "unlocked_lessons": [],
  "reason": "Student request untuk persiapan ujian"
}

# Expected Response:
{
  "success": true,
  "message": "Student override added successfully",
  "overrides": {
    "unlocked_modules": [],
    "student_overrides": [
      {
        "student_id": "...",
        "unlocked_modules": ["module_3_id"],
        "unlocked_lessons": [],
        "reason": "Student request untuk persiapan ujian",
        "overridden_by": "...",
        "created_at": "..."
      }
    ]
  }
}
```

**✅ Verify:**
- Override added to student_overrides array
- Reason saved
- overridden_by = teacher_id

#### **Step 5.3: After Override - Student View**
```bash
GET http://localhost:8000/api/v1/my/courses/{course_id}
Authorization: Bearer {ahmad_token}

# Module 3 status NOW:
{
  "module_id": "module_3_id",
  "completed": false,
  "locked": true,              // ← Still locked (sequential)
  "accessible": true,          // ← BUT NOW ACCESSIBLE!
  "override_unlocked": true    // ← Indicator
}
```

**✅ Verify:**
- Module 3 accessible = true
- override_unlocked = true
- Ahmad can now access Module 3 content

#### **Step 5.4: Remove Override**
```bash
DELETE http://localhost:8000/api/v1/course-assignments/{assignment_id}/overrides/{ahmad_id}
Authorization: Bearer {teacher_token}

# Expected Response:
{
  "success": true,
  "message": "Student override removed successfully"
}
```

**✅ Verify:**
- Override removed
- Student's next access shows Module 3 locked again

---

## 🎯 **TEST SCENARIO 6: Archive & Restore Assignment**

#### **Step 6.1: Archive Assignment**
```bash
DELETE http://localhost:8000/api/v1/course-assignments/{assignment_id}
Authorization: Bearer {teacher_token}

# Expected Response:
{
  "success": true,
  "message": "Assignment archived successfully"
}
```

**✅ Verify:**
- Assignment status = "archived"
- Not shown in active list
- Student can't access course

#### **Step 6.2: Student Access After Archive**
```bash
GET http://localhost:8000/api/v1/my/courses
Authorization: Bearer {student_token}

# Expected Response:
{
  "success": true,
  "total": 0,           // ← No active assignments
  "courses": []
}
```

#### **Step 6.3: Restore Assignment**
```bash
POST http://localhost:8000/api/v1/course-assignments/{assignment_id}/restore
Authorization: Bearer {teacher_token}

# Expected Response:
{
  "success": true,
  "message": "Assignment restored successfully",
  "assignment": {...}
}
```

**✅ Verify:**
- Assignment status = "active"
- Student can access course again
- Progress preserved (not deleted)

---

## 🎯 **TEST SCENARIO 7: Update Assignment Settings**

```bash
PUT http://localhost:8000/api/v1/course-assignments/{assignment_id}/settings
Authorization: Bearer {teacher_token}
Content-Type: application/json

{
  "end_date": "2024-07-31T00:00:00Z",
  "settings": {
    "allow_skip": true,
    "custom_setting": "value"
  }
}

# Expected Response:
{
  "success": true,
  "message": "Settings updated successfully",
  "assignment": {
    "end_date": "2024-07-31T00:00:00Z",
    "settings": {
      "allow_skip": true,
      "custom_setting": "value"
    }
  }
}
```

---

## 📊 **TEST CHECKLIST**

### **Teacher Endpoints**
- [ ] POST /course-assignments (assign)
- [ ] GET /course-assignments/{id} (details)
- [ ] GET /course-assignments/class/{class_id} (list by class)
- [ ] GET /course-assignments/course/{course_id} (list by course)
- [ ] PUT /course-assignments/{id}/settings (update)
- [ ] DELETE /course-assignments/{id} (archive)
- [ ] POST /course-assignments/{id}/restore
- [ ] POST /course-assignments/{id}/overrides (add override)
- [ ] DELETE /course-assignments/{id}/overrides/{student_id} (remove)

### **Student Endpoints**
- [ ] GET /my/courses (list)
- [ ] GET /my/courses/{id} (detail)
- [ ] POST /my/courses/{id}/lessons/{lesson_id}/next
- [ ] GET /my/courses/{id}/progress

### **Lock Logic**
- [ ] First module unlocked for new student
- [ ] Other modules locked (sequential)
- [ ] First lesson in module unlocked
- [ ] Other lessons locked until previous completed
- [ ] After complete lesson, next unlocks
- [ ] After complete module, next module unlocks
- [ ] Override unlocks despite locks
- [ ] Remove override re-locks content

### **Progress Tracking**
- [ ] Progress created on first complete
- [ ] Progress updated on subsequent completes
- [ ] Completion percentage calculated correctly
- [ ] Time spent tracked
- [ ] Status updated (not_started → in_progress → completed)

### **Authorization**
- [ ] Teacher can only assign to their classes
- [ ] Teacher can only manage their assignments
- [ ] Student can only access their class's courses
- [ ] Non-student can't access /my/courses
- [ ] Admin can access everything

---

## 🐛 **COMMON ISSUES & SOLUTIONS**

### **Issue 1: "Course not assigned to your class"**
**Cause:** Student's class_id doesn't match assignment
**Solution:** Check student.class_id in users collection

### **Issue 2: All modules locked**
**Cause:** Sequential logic bug or no progress
**Solution:** Check calculate_module_lock_status function

### **Issue 3: Override not working**
**Cause:** student_id mismatch or not checking overrides
**Solution:** Verify student_id in override matches exactly

### **Issue 4: Progress not saving**
**Cause:** ObjectId conversion issue
**Solution:** Check StudentProgress.to_mongo() conversion

---

## 📝 **TESTING NOTES**

**Record for each test:**
- [ ] Test passed ✅
- [ ] Test failed ❌
- [ ] Issue found & noted
- [ ] Response time (< 1s expected)
- [ ] Database state verified

**Bug Report Template:**
```
Test: [Scenario X Step Y]
Expected: [...]
Actual: [...]
Error: [...]
Request: [...]
Response: [...]
```

---

## 🚀 **NEXT STEPS AFTER TESTING**

1. Fix bugs found
2. Optimize slow queries
3. Add error handling improvements
4. Implement remaining features (Assessment, Auth)

---

**Ready to test!** Start with Scenario 1 and work through systematically. 🧪
