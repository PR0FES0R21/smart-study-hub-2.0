# REFACTOR PLAN: LMS Course System

## 📊 Current State Analysis

### Existing Collections & Models

#### 1. **courses** (Main Collection)
**File:** `app/models/course.py`

**Structure:**
```python
Course:
  - id, title, description, slug
  - subject_id, grade_level
  - coordinator_id, instructor_ids
  - module_refs: List[ModuleReference]
  - completion_criteria: Dict
  - assessments: List[CourseAssessment]
  - metadata: CourseMetadata (auto-calculated)
  - status: draft | published | active | archived
```

**ModuleReference:**
- module_id, order, required
- weight, unlock_condition
- module_snapshot (optional)

**CourseAssessment:**
- assessment_id, type, title
- required, weight
- prerequisite_modules

**Status:** ✅ Good foundation, needs minor updates

---

#### 2. **course_progress** (Progress Tracking)
**File:** `app/models/lesson_progress.py`, `app/crud/course_progress.py`

**Current Structure:**
```python
CourseProgress:
  - student_id, course_id
  - enrollment_id (optional)
  - status, completion_percentage
  - modules_completed, modules_total
```

**LessonProgress:**
- student_id, lesson_id, course_id, module_id
- status, completion_percentage
- page_progress: List[PageProgress]
- component_progress (quizzes, assignments)

**Status:** ⚠️ Needs refactoring to align with new design

---

#### 3. **Unused/Complex Files** (To Archive)
- `course_version.py` - Versioning (not needed)
- `course_pull_request.py` - PR system (not needed)
- `course_change_history.py` - Change tracking (not needed)

**Status:** ❌ Archive these files

---

## 🎯 Target Architecture (New Design)

### New Collections Needed

#### 1. **course_class_settings** (NEW)
**Purpose:** Link course to class with per-class overrides

```python
CourseClassSettings:
  - course_id (reference to courses)
  - class_id
  - teacher_id
  
  # Metadata per class
  - metadata:
      - total_students
      - started_students
      - completed_students
      - average_progress
  
  # Override unlocks
  - class_overrides:
      - unlocked_modules: List[str]
      - student_overrides: List[StudentOverride]
  
  # Settings
  - settings:
      - start_date, end_date
      - allow_skip
  
  - status: active | archived
```

---

#### 2. **student_progress** (Refactored from course_progress)
**Purpose:** Independent progress tracking per student

```python
StudentProgress:
  - student_id
  - course_class_setting_id (NOT course_id directly!)
  
  # Content identifier
  - module_id
  - lesson_id
  - page_number (optional)
  
  # Status
  - status: not_started | in_progress | completed
  - completed_at
  - time_spent
  
  # Score (if quiz/assignment)
  - score, max_score
  
  # Submission
  - submission: {...}
```

**Key Change:** Track by `course_class_setting_id` instead of `course_id`

---

#### 3. **assessment_submissions** (NEW)
**Purpose:** Track final assessment submissions

```python
AssessmentSubmission:
  - student_id
  - course_class_setting_id
  - assessment_id
  - question_set_id (reference to question bank)
  
  # Submission
  - submission:
      - submitted_at
      - answers: List[Answer]
  
  # Grading
  - score, max_score
  - passed (score >= passing_score)
  
  # Meta
  - attempt_number (always 1, no retake)
  - time_spent
  - started_at, completed_at
```

---

## 🔧 Refactoring Tasks

### Phase 1: Foundation (Models & Schemas)

#### Task 1.1: Review Existing Course Model ✅ (DONE)
- [x] Analyzed `app/models/course.py`
- [x] Identified what to keep
- [x] Documented current structure

#### Task 1.2: Create CourseClassSettings Model
**File:** `app/models/course_class_settings.py` (NEW)

**Changes needed:**
- Create new Pydantic model
- Define schema for overrides
- Add validation logic

#### Task 1.3: Refactor Progress Tracking
**Files to update:**
- `app/models/lesson_progress.py` - Rename/update CourseProgress
- `app/crud/course_progress.py` - Update CRUD logic

**Changes needed:**
- Rename CourseProgress → keep structure but adjust
- Update StudentProgress to track by course_class_setting_id
- Simplify structure (remove unnecessary fields)

#### Task 1.4: Update Course Model
**File:** `app/models/course.py`

**Changes needed:**
- Update CourseAssessment to include `question_set_id`
- Simplify completion_criteria
- Remove versioning-related fields (if any)

---

### Phase 2: CRUD Operations

#### Task 2.1: Create CourseClassSettings CRUD
**File:** `app/crud/course_class_settings.py` (NEW)

**Operations:**
- create_assignment (assign course to class)
- get_assignment
- update_assignment (override settings)
- archive_assignment (soft delete)
- add_student_override (teacher unlock)

#### Task 2.2: Update Course CRUD
**File:** Update existing CRUD files

**Changes:**
- Add coordination_assignment validation
- Update course creation to check coordinator permissions
- Simplify logic (remove versioning)

#### Task 2.3: Update Progress CRUD
**File:** `app/crud/course_progress.py`

**Changes:**
- Update to work with course_class_setting_id
- Simplify enrollment logic
- Add sequential lock calculation

---

### Phase 3: Business Logic

#### Task 3.1: Sequential Lock Logic
**File:** `app/utils/course_locks.py` (NEW)

**Functions:**
```python
async def calculate_lock_status(
    course: Course,
    student_progress: List[StudentProgress],
    class_overrides: Dict
) -> List[ModuleWithLockStatus]

async def get_next_unlocked_content(...)

async def check_can_access(...)
```

#### Task 3.2: Next Button Logic
**File:** `app/utils/course_navigation.py` (NEW)

**Functions:**
```python
async def handle_next_button(
    student_id: str,
    current_lesson_id: str
) -> NextResult

async def mark_content_completed(...)
```

#### Task 3.3: Assessment Logic
**File:** `app/crud/assessment_submissions.py` (NEW)

**Operations:**
- start_assessment
- submit_assessment
- get_results
- check_course_completion

---

### Phase 4: API Endpoints

#### Task 4.1: Update Course Endpoints
**File:** `app/api/v1/endpoints/courses.py`

**Changes:**
- Add coordination_assignment validation to create
- Update list to show class assignments
- Add bulk operations

#### Task 4.2: Create Assignment Endpoints
**File:** `app/api/v1/endpoints/course_assignments.py` (NEW)

**Endpoints:**
```
POST   /courses/{id}/assign-to-class
GET    /course-class-settings/{id}
PUT    /course-class-settings/{id}/settings
DELETE /course-class-settings/{id}  (archive)
POST   /course-class-settings/{id}/overrides
GET    /course-class-settings/{id}/analytics
```

#### Task 4.3: Update Student Endpoints
**File:** `app/api/v1/endpoints/my/courses.py`

**Endpoints:**
```
GET    /my/courses
GET    /my/courses/{id}  (with lock status)
POST   /my/courses/{id}/lessons/{lesson_id}/next
GET    /my/courses/{id}/progress
```

#### Task 4.4: Create Assessment Endpoints
**File:** `app/api/v1/endpoints/assessments.py` (NEW)

**Endpoints:**
```
# Student
POST   /my/assessments/{id}/start
POST   /my/assessments/{id}/submit
GET    /my/assessments/{id}/results

# Teacher
GET    /course-class-settings/{id}/assessments/{assessment_id}/results
GET    /course-class-settings/{id}/assessments/{assessment_id}/submissions
```

---

### Phase 5: Authorization & Middleware

#### Task 5.1: Update Authorization
**File:** `app/api/v1/deps.py`

**Add:**
```python
async def get_coordinator_assignment(...)
async def check_teacher_class_permission(...)
async def check_student_course_access(...)
```

---

### Phase 6: Testing & Documentation

#### Task 6.1: Archive Unused Files
Move to `app/models/deprecated/`:
- course_version.py
- course_pull_request.py
- course_change_history.py

#### Task 6.2: Create Tests
**Files:** `tests/test_course_refactor.py`

Test scenarios:
- Coordinator creates course
- Teacher assigns to class
- Student accesses with sequential locks
- Teacher overrides unlock
- Assessment flow

#### Task 6.3: Update Documentation
- API documentation
- Model documentation
- Migration guide (if needed)

---

## 🚦 Implementation Order

### Story 1: Foundation (Week 1)
1. ✅ Review existing structure (DONE)
2. Create CourseClassSettings model
3. Refactor StudentProgress
4. Update Course model (assessments)

### Story 2: Coordinator Features (Week 1-2)
5. Create CourseClassSettings CRUD
6. Update Course CRUD with validation
7. Update Course API endpoints
8. Add authorization checks

### Story 3: Teacher Features (Week 2)
9. Create Assignment API endpoints
10. Add override unlock system
11. Add analytics endpoints

### Story 4: Student Features (Week 3)
12. Update Student Course Access API
13. Implement sequential lock logic
14. Implement Next button logic
15. Update progress tracking

### Story 5: Assessment System (Week 3-4)
16. Create AssessmentSubmission model
17. Create Assessment CRUD
18. Create Assessment API endpoints
19. Integrate with question bank

### Story 6: Cleanup & Testing (Week 4)
20. Archive unused files
21. Create comprehensive tests
22. Update documentation

---

## 📝 Notes

### Key Design Decisions
- Course = Stateless/Reusable template
- Progress tracking = Separate, independent
- Calculate locks on-the-fly (no stored state)
- Track by course_class_setting_id (not course_id)
- No retake allowed for assessments
- Teacher can override unlock per student

### Breaking Changes
- Progress tracking structure changes
- Course assignment requires course_class_settings
- Student access requires class assignment
- Assessment submission structure new

### Migration Strategy (if needed)
If there's existing data:
1. Create migration script
2. Move course_progress → student_progress
3. Create course_class_settings for existing enrollments
4. Update references

---

**Status:** Ready for implementation
**Last Updated:** 2025-10-23
