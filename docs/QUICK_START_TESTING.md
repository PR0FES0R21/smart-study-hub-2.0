# QUICK START: Testing New Course System

## 🚀 **GET STARTED IN 5 MINUTES**

---

## **STEP 1: Setup Test Data** (2 minutes)

```bash
# Pastikan server tidak running
# Pastikan MongoDB connected

# Run setup script
python scripts/setup_test_data_course_system.py
```

**Output yang diharapkan:**
```
✅ TEST DATA SETUP COMPLETE!
📋 TEST CREDENTIALS:
   Teacher: teacher.test@school.com / password123
   Student 1: student1.test@school.com / password123
   Student 2: student2.test@school.com / password123

📚 TEST DATA IDs:
   Course ID: 673f1a2b3c4d5e6f7a8b9c0d
   Class ID: 673f1a2b3c4d5e6f7a8b9c0e
   ...
```

**⚠️ SAVE IDs ini! Akan dipakai di testing.**

---

## **STEP 2: Start Server** (30 seconds)

```bash
# Development mode
uvicorn main:app --reload --port 8000

# Or
python main.py
```

**Verify server running:**
```
http://localhost:8000/docs
```

---

## **STEP 3: Test with Postman/REST Client** (2 minutes)

### **Option A: VS Code REST Client**

1. Install extension: [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
2. Open: `docs/API_TEST_COLLECTION.http`
3. **REPLACE** placeholders dengan IDs dari Step 1:
   ```
   @courseId = <PASTE_YOUR_COURSE_ID>
   @classId = <PASTE_YOUR_CLASS_ID>
   @student1Id = <PASTE_YOUR_STUDENT1_ID>
   @lessonId = <PASTE_YOUR_FIRST_LESSON_ID>
   ```
4. Click "Send Request" pada setiap endpoint

### **Option B: Postman**

1. Import `docs/API_TEST_COLLECTION.http` as raw text
2. Replace placeholders dengan IDs
3. Send requests

### **Option C: curl**

Lihat contoh di bawah.

---

## **STEP 4: Run Basic Test Flow** (1 minute)

### **Test 1: Login as Teacher**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher.test@school.com",
    "password": "password123"
  }'
```

**Save token dari response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

---

### **Test 2: Assign Course to Class**

```bash
curl -X POST http://localhost:8000/api/v1/course-assignments \
  -H "Authorization: Bearer YOUR_TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "YOUR_COURSE_ID",
    "class_id": "YOUR_CLASS_ID",
    "start_date": "2024-01-10T00:00:00Z",
    "end_date": "2024-06-30T00:00:00Z"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Course assigned to class successfully",
  "assignment": {
    "id": "...",
    "course_title": "Test Course: Matematika Kelas 10",
    "class_name": "10A Test",
    ...
  }
}
```

**✅ SUCCESS:** Assignment created!

---

### **Test 3: Student Lists Courses**

```bash
# Login as student first
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student1.test@school.com",
    "password": "password123"
  }'

# List courses
curl -X GET http://localhost:8000/api/v1/my/courses \
  -H "Authorization: Bearer YOUR_STUDENT_TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "total": 1,
  "courses": [
    {
      "course": {
        "id": "...",
        "title": "Test Course: Matematika Kelas 10"
      },
      "progress": {
        "completion_percentage": 0.0,
        "completed_modules": 0,
        "status": "not_started"
      },
      "modules": [
        {
          "module_id": "...",
          "order": 1,
          "completed": false,
          "locked": false,      // ← First module unlocked!
          "accessible": true
        },
        {
          "module_id": "...",
          "order": 2,
          "completed": false,
          "locked": true,       // ← Locked (sequential)
          "accessible": false
        }
      ]
    }
  ]
}
```

**✅ SUCCESS:** Student sees course with lock status!

---

### **Test 4: Student Completes Lesson**

```bash
# Get course detail first to get lesson_id
curl -X GET http://localhost:8000/api/v1/my/courses/YOUR_COURSE_ID \
  -H "Authorization: Bearer YOUR_STUDENT_TOKEN"

# Find first lesson ID from response, then:
curl -X POST http://localhost:8000/api/v1/my/courses/YOUR_COURSE_ID/lessons/FIRST_LESSON_ID/next \
  -H "Authorization: Bearer YOUR_STUDENT_TOKEN"
```

**Expected Response:**
```json
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
    "content_id": "...",     // ← Next lesson!
    "module_id": "..."
  },
  "has_next": true,
  "course_completed": false
}
```

**✅ SUCCESS:** Progress tracked, next lesson unlocked!

---

## **STEP 5: Verify in Database** (Optional)

```bash
# Connect to MongoDB
mongo

# Switch to database
use smart_study_hub

# Check course_class_settings
db.course_class_settings.find().pretty()

# Check student_progress
db.student_progress.find().pretty()

# Expected:
# - 1 course_class_settings document (assignment)
# - 1 student_progress document (completed lesson)
```

---

## 🎯 **WHAT TO TEST**

### **Critical Paths (Must Work)**

1. ✅ **Teacher assigns course**
   - POST /course-assignments
   - Verify assignment created

2. ✅ **Student sees course**
   - GET /my/courses
   - Verify lock status correct

3. ✅ **Student views course detail**
   - GET /my/courses/{id}
   - Verify modules & lessons with locks

4. ✅ **Student completes lesson**
   - POST /my/courses/{id}/lessons/{lesson_id}/next
   - Verify progress saved
   - Verify next lesson unlocked

5. ✅ **Teacher overrides lock**
   - POST /course-assignments/{id}/overrides
   - Verify student can access locked module

### **Edge Cases (Should Handle Correctly)**

6. ⚠️ **Assign duplicate**
   - Try assign same course to same class twice
   - Should return error

7. ⚠️ **Invalid permissions**
   - Student tries to assign course
   - Should return 403

8. ⚠️ **Invalid IDs**
   - Access non-existent course
   - Should return 404

9. ⚠️ **Archive & restore**
   - Archive assignment
   - Verify student can't access
   - Restore
   - Verify student can access again

---

## 🐛 **DEBUGGING TIPS**

### **Issue: 401 Unauthorized**
- Token expired? Login again
- Token correct format? `Bearer <token>`

### **Issue: 404 Not Found**
- IDs correct? Check database
- Endpoint URL correct?

### **Issue: 403 Forbidden**
- User has correct role? (teacher/student)
- Teacher has teaching_assignment?
- Student in correct class?

### **Issue: 500 Internal Server Error**
- Check server logs
- Check MongoDB connection
- Check ObjectId format

### **Issue: Lock logic not working**
- Check sequential_mode = true in course
- Check student_progress documents
- Check calculate_module_lock_status function

---

## 📊 **EXPECTED RESULTS**

After completing all tests:

**Database State:**
```
course_class_settings: 1 document
  - course_id linked to test course
  - class_id linked to test class
  - status: "active"

student_progress: ~1-5 documents
  - One per completed lesson
  - content_type: "lesson"
  - status: "completed"
```

**Student View:**
```
- Course visible in /my/courses
- Module 1 accessible
- First lesson completed
- Second lesson now accessible
- Module 2 still locked (if not all Module 1 done)
```

---

## ✅ **SUCCESS CRITERIA**

**Core Features Working:**
- [x] Teacher can assign course
- [x] Student can list courses
- [x] Student sees correct lock status
- [x] Student can complete lesson
- [x] Progress tracked correctly
- [x] Sequential locks working
- [x] Teacher can override locks
- [x] Archive/restore working

**No Errors:**
- [ ] No 500 errors
- [ ] No data corruption
- [ ] No ObjectId conversion errors
- [ ] No authorization bypasses

---

## 🚨 **IF SOMETHING FAILS**

1. **Check server logs** for detailed error
2. **Check database** for data state
3. **Verify test data** setup correctly
4. **Note the bug** for fixing phase
5. **Continue testing** other scenarios

---

## 📝 **TESTING CHECKLIST**

Copy this to track your testing:

```
[ ] Test data setup successful
[ ] Server running without errors
[ ] Teacher login works
[ ] Teacher can assign course
[ ] Student login works
[ ] Student sees assigned course
[ ] Lock status calculated correctly
[ ] Student can complete lesson
[ ] Progress saved to database
[ ] Next lesson unlocks automatically
[ ] Teacher can add override
[ ] Override works for student
[ ] Archive assignment works
[ ] Student can't access archived
[ ] Restore assignment works
[ ] Error cases handled correctly
```

---

## 🎉 **READY TO TEST!**

**Estimated Time:** 15-30 minutes untuk complete testing

**Priority Order:**
1. Basic flow (assign → access → complete)
2. Lock logic verification
3. Override system
4. Error handling

**Let's go!** 🚀

---

**Next Steps After Testing:**
- Document any bugs found
- Fix bugs (Option A)
- Continue implementation (Assessment, Auth)
- Deploy to test environment (Option C)
