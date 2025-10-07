# 📚 Smart Study Hub - LMS API Frontend Implementation Guide

**Comprehensive Guide for Frontend Developers**

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Authentication](#authentication)
4. [Quick Start Guide](#quick-start-guide)
5. [Lesson Management](#lesson-management)
6. [Module Management](#module-management)
7. [Course Management](#course-management)
8. [Progress Tracking](#progress-tracking)
9. [Complete User Flows](#complete-user-flows)
10. [Error Handling](#error-handling)
11. [Best Practices](#best-practices)

---

## 🎯 Overview

Smart Study Hub LMS menggunakan **Modular Architecture** dengan 3 level hierarki:

- **Lesson** - Unit pembelajaran terkecil (berisi pages)
- **Module** - Kumpulan lessons (references)
- **Course** - Kumpulan modules (references)

### Key Features:

- ✅ Reference-based (no embedding)
- ✅ Real-time progress tracking
- ✅ Multi-level analytics
- ✅ Progressive loading
- ✅ Collaborative content creation

---

## 🏗️ Architecture

```
Course (1)
├── Module Reference 1
│   ├── Lesson Reference 1 → Lesson (pages, components)
│   ├── Lesson Reference 2 → Lesson (pages, components)
│   └── Lesson Reference 3 → Lesson (pages, components)
├── Module Reference 2
│   └── ...
└── Module Reference 3

Progress Tracking:
Student → CourseProgress → ModuleProgress → LessonProgress → PageProgress
```

**Base URL:** `https://api.smartstudyhub.com/api/v1`

---

## 🔐 Authentication

All endpoints require authentication. Include JWT token in headers:

```javascript
const headers = {
  Authorization: `Bearer ${accessToken}`,
  "Content-Type": "application/json",
};
```

---

## 🚀 Quick Start Guide

### Step 1: Understand User Roles

```javascript
// User roles and permissions
const userRoles = {
  student: ["view_content", "track_progress", "submit_assignments"],
  teacher: ["create_lessons", "create_modules", "view_analytics"],
  coordinator: ["create_courses", "manage_enrollments", "view_all_analytics"],
  admin: ["full_access"],
};
```

### Step 2: Choose Your Starting Point

**For Teachers:**

1. Create Lessons → Create Modules → Share with Coordinators

**For Coordinators:**

1. Create Course → Add existing Modules → Enroll Students

**For Students:**

1. Enroll in Course → View Modules → Start Lessons → Track Progress

---

## 📄 Lesson Management

### 1. **Create Lesson** (Teacher)

**Endpoint:** `POST /lessons`

**When to use:** Teacher wants to create new learning content

**Request Body:**

```json
{
  "title": "Introduction to Algebra",
  "description": "Learn the basics of algebraic expressions",
  "subject_id": "507f1f77bcf86cd799439011",
  "grade_level": 10,
  "topic_tags": ["algebra", "mathematics", "fundamentals"],
  "difficulty_level": "medium",
  "learning_objectives": [
    "Understand algebraic notation",
    "Solve basic equations",
    "Apply algebra to real problems"
  ],
  "prerequisites": ["Basic arithmetic", "Number systems"],
  "visibility": "public",
  "pages": [
    {
      "title": "What is Algebra?",
      "content_markdown": "# Introduction\nAlgebra is...",
      "estimated_duration": 15,
      "difficulty_level": "easy",
      "learning_objectives": ["Define algebra"],
      "media_references": [
        {
          "media_key": "img_1",
          "file_name": "algebra_intro.png",
          "file_type": "image",
          "file_size": 245000,
          "url": "https://cdn.smartstudyhub.com/images/algebra_intro.png",
          "alt_text": "Algebra introduction diagram"
        }
      ],
      "embedded_components": [
        {
          "component_id": "quiz_1",
          "type": "quiz",
          "position": 1,
          "title": "Check Your Understanding",
          "required": true,
          "estimated_duration": 10,
          "data": {
            "questions": [
              {
                "id": "q1",
                "question": "What does the variable x represent?",
                "type": "multiple_choice",
                "options": [
                  "Unknown value",
                  "Constant",
                  "Function",
                  "Operator"
                ],
                "correct_answer": "Unknown value",
                "points": 10
              }
            ]
          }
        }
      ]
    },
    {
      "title": "Algebraic Expressions",
      "content_markdown": "## Expressions\nAn expression is...",
      "estimated_duration": 20,
      "difficulty_level": "medium",
      "learning_objectives": ["Create expressions", "Evaluate expressions"]
    }
  ]
}
```

**Response:**

```json
{
  "id": "507f1f77bcf86cd799439012",
  "title": "Introduction to Algebra",
  "description": "Learn the basics of algebraic expressions",
  "slug": "introduction-to-algebra-1234567890",
  "subject_id": "507f1f77bcf86cd799439011",
  "subject_name": "Mathematics",
  "grade_level": 10,
  "topic_tags": ["algebra", "mathematics", "fundamentals"],
  "pages": [...],
  "difficulty_level": "medium",
  "learning_objectives": [...],
  "prerequisites": [...],
  "visibility": "public",
  "created_by": "507f1f77bcf86cd799439010",
  "created_by_name": "John Doe",
  "collaborators": [],
  "metadata": {
    "total_pages": 2,
    "total_duration": 35,
    "total_components": 1,
    "total_media": 1,
    "component_breakdown": {"quiz": 1},
    "media_breakdown": {"image": 1},
    "difficulty_distribution": {"easy": 1, "medium": 1},
    "usage_count": 0,
    "completion_rate": 0.0,
    "rating": 0.0,
    "review_count": 0,
    "calculated_at": "2024-01-15T10:30:00Z"
  },
  "status": "draft",
  "published_at": null,
  "archived_at": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "can_edit": true,
  "can_delete": true,
  "can_collaborate": true,
  "usage_in_modules": null
}
```

**Next Steps:**

1. Review created lesson
2. Add more pages if needed: `POST /lessons/{lesson_id}/pages`
3. Publish lesson: `PUT /lessons/{lesson_id}` with `status: "published"`
4. Add to module: `POST /modules/{module_id}/lessons`

---

### 2. **List Lessons** (Teacher/Student)

**Endpoint:** `GET /lessons`

**When to use:** Browse available lessons, search for content

**Query Parameters:**

```
?page=1
&per_page=20
&subject_id=507f1f77bcf86cd799439011
&grade_level=10
&status=published
&visibility=public
&difficulty_level=medium
&topic_tags=algebra,mathematics
&search=introduction
&sort_by=updated_at
&sort_direction=desc
```

**Response:**

```json
{
  "items": [
    {
      "id": "507f1f77bcf86cd799439012",
      "title": "Introduction to Algebra",
      "description": "Learn the basics...",
      "slug": "introduction-to-algebra-1234567890",
      "subject_id": "507f1f77bcf86cd799439011",
      "subject_name": "Mathematics",
      "grade_level": 10,
      "topic_tags": ["algebra", "mathematics"],
      "total_pages": 2,
      "total_duration": 35,
      "difficulty_level": "medium",
      "created_by": "507f1f77bcf86cd799439010",
      "created_by_name": "John Doe",
      "visibility": "public",
      "status": "published",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "can_edit": true,
      "can_delete": true,
      "is_favorited": false
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20,
  "total_pages": 3,
  "has_next": true,
  "has_prev": false
}
```

**Frontend Implementation:**

```javascript
// Fetch lessons with filters
async function fetchLessons(filters = {}) {
  const params = new URLSearchParams({
    page: filters.page || 1,
    per_page: filters.perPage || 20,
    ...(filters.subjectId && { subject_id: filters.subjectId }),
    ...(filters.gradeLevel && { grade_level: filters.gradeLevel }),
    ...(filters.status && { status: filters.status }),
    ...(filters.search && { search: filters.search }),
    sort_by: filters.sortBy || "updated_at",
    sort_direction: filters.sortDirection || "desc",
  });

  const response = await fetch(`${API_BASE}/lessons?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  return await response.json();
}

// Usage in React component
function LessonList() {
  const [lessons, setLessons] = useState([]);
  const [pagination, setPagination] = useState({});
  const [filters, setFilters] = useState({ page: 1, perPage: 20 });

  useEffect(() => {
    fetchLessons(filters).then((data) => {
      setLessons(data.items);
      setPagination({
        total: data.total,
        page: data.page,
        totalPages: data.total_pages,
        hasNext: data.has_next,
        hasPrev: data.has_prev,
      });
    });
  }, [filters]);

  return (
    <div>
      {lessons.map((lesson) => (
        <LessonCard key={lesson.id} lesson={lesson} />
      ))}
      <Pagination
        {...pagination}
        onPageChange={(page) => setFilters({ ...filters, page })}
      />
    </div>
  );
}
```

---

### 3. **Get Lesson Details** (Teacher/Student)

**Endpoint:** `GET /lessons/{lesson_id}`

**When to use:** View complete lesson content before starting or editing

**Query Parameters:**

```
?include_usage=true  // Include where this lesson is used
```

**Response:**

```json
{
  "id": "507f1f77bcf86cd799439012",
  "title": "Introduction to Algebra",
  "description": "Learn the basics of algebraic expressions",
  "slug": "introduction-to-algebra-1234567890",
  "subject_id": "507f1f77bcf86cd799439011",
  "subject_name": "Mathematics",
  "grade_level": 10,
  "topic_tags": ["algebra", "mathematics", "fundamentals"],
  "pages": [
    {
      "page_number": 1,
      "title": "What is Algebra?",
      "content_markdown": "# Introduction\nAlgebra is a branch...",
      "media_references": [...],
      "embedded_components": [...],
      "estimated_duration": 15,
      "difficulty_level": "easy",
      "learning_objectives": ["Define algebra"],
      "is_published": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    },
    {
      "page_number": 2,
      "title": "Algebraic Expressions",
      "content_markdown": "## Expressions...",
      "media_references": [],
      "embedded_components": [],
      "estimated_duration": 20,
      "difficulty_level": "medium",
      "learning_objectives": ["Create expressions"],
      "is_published": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "difficulty_level": "medium",
  "learning_objectives": [...],
  "prerequisites": [...],
  "visibility": "public",
  "created_by": "507f1f77bcf86cd799439010",
  "created_by_name": "John Doe",
  "collaborators": [],
  "metadata": {...},
  "status": "published",
  "published_at": "2024-01-15T11:00:00Z",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "can_edit": true,
  "can_delete": true,
  "can_collaborate": true,
  "usage_in_modules": [
    {
      "module_id": "507f1f77bcf86cd799439020",
      "module_title": "Algebra Fundamentals",
      "order": 1
    }
  ]
}
```

---

### 4. **Get Lesson Library** (All Users)

**Endpoint:** `GET /lessons/library`

**When to use:** Display featured, popular, and recent lessons on homepage

**Response:**

```json
{
  "featured_lessons": [...],  // Top rated, high usage
  "recent_lessons": [...],     // Recently published
  "popular_lessons": [...],    // Most used
  "my_lessons": [...],         // Created by current user (if teacher)
  "subjects": [
    {"id": "507f1f77bcf86cd799439011", "name": "Mathematics"},
    {"id": "507f1f77bcf86cd799439013", "name": "Physics"}
  ],
  "grade_levels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "total_lessons": 1523,
  "total_creators": 45
}
```

**Frontend Implementation:**

```javascript
function LessonLibrary() {
  const [library, setLibrary] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/lessons/library`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then(setLibrary);
  }, []);

  if (!library) return <Loading />;

  return (
    <div>
      <section>
        <h2>Featured Lessons</h2>
        <LessonGrid lessons={library.featured_lessons} />
      </section>

      <section>
        <h2>Recent Additions</h2>
        <LessonGrid lessons={library.recent_lessons} />
      </section>

      <section>
        <h2>Most Popular</h2>
        <LessonGrid lessons={library.popular_lessons} />
      </section>

      {library.my_lessons.length > 0 && (
        <section>
          <h2>My Lessons</h2>
          <LessonGrid lessons={library.my_lessons} />
        </section>
      )}
    </div>
  );
}
```

---

### 5. **Update Lesson** (Teacher)

**Endpoint:** `PUT /lessons/{lesson_id}`

**When to use:** Edit lesson content, update pages, change settings

**Request Body (partial update):**

```json
{
  "title": "Advanced Algebra Introduction",
  "description": "Updated description",
  "difficulty_level": "hard",
  "status": "published",
  "pages": [...]  // Optional: full page replacement
}
```

---

### 6. **Add Page to Lesson** (Teacher)

**Endpoint:** `POST /lessons/{lesson_id}/pages`

**When to use:** Add new page to existing lesson

**Request Body:**

```json
{
  "page_number": 3, // Optional, auto-assigned if not provided
  "title": "Practice Problems",
  "content_markdown": "## Practice\nSolve these problems...",
  "estimated_duration": 25,
  "difficulty_level": "hard"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Page added successfully",
  "page": {
    "page_number": 3,
    "title": "Practice Problems",
    "content_markdown": "## Practice\nSolve...",
    "media_references": [],
    "embedded_components": [],
    "estimated_duration": 25,
    "difficulty_level": "hard",
    "learning_objectives": [],
    "is_published": true,
    "created_at": "2024-01-15T12:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  }
}
```

---

### 7. **Delete Lesson** (Teacher)

**Endpoint:** `DELETE /lessons/{lesson_id}`

**When to use:** Remove lesson permanently

**Safety Check:** Returns error if lesson is being used in modules

**Response:**

```json
{
  "success": true,
  "message": "Lesson deleted successfully",
  "lesson_id": "507f1f77bcf86cd799439012"
}
```

**Error Response (if used in modules):**

```json
{
  "detail": "Cannot delete lesson. It is being used in 3 modules. Remove from modules first."
}
```

---

## 📑 Module Management

### 1. **Create Module** (Teacher)

**Endpoint:** `POST /modules`

**When to use:** Teacher wants to group lessons into a module

**Request Body:**

```json
{
  "title": "Algebra Fundamentals",
  "description": "Complete introduction to algebraic concepts",
  "subject_id": "507f1f77bcf86cd799439011",
  "grade_level": 10,
  "topic_tags": ["algebra", "fundamentals", "mathematics"],
  "difficulty_level": "medium",
  "learning_objectives": [
    "Master basic algebra",
    "Solve complex equations",
    "Apply algebra to problems"
  ],
  "prerequisites": ["Basic arithmetic"],
  "visibility": "public",
  "completion_criteria": {
    "type": "all_required",
    "required_percentage": 100,
    "minimum_score": 70
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Module created successfully",
  "module": {
    "id": "507f1f77bcf86cd799439020",
    "title": "Algebra Fundamentals",
    "description": "Complete introduction to algebraic concepts",
    "slug": "algebra-fundamentals-1234567890",
    "subject_id": "507f1f77bcf86cd799439011",
    "grade_level": 10,
    "topic_tags": ["algebra", "fundamentals", "mathematics"],
    "lesson_refs": [],
    "difficulty_level": "medium",
    "learning_objectives": [...],
    "prerequisites": [...],
    "completion_criteria": {...},
    "assessments": [],
    "visibility": "public",
    "created_by": "507f1f77bcf86cd799439010",
    "collaborators": [],
    "metadata": {
      "total_lessons": 0,
      "total_duration": 0,
      "total_pages": 0,
      "total_components": 0,
      "difficulty_distribution": {},
      "component_summary": {},
      "sequential_lessons": 0,
      "optional_lessons": 0,
      "usage_count": 0,
      "completion_rate": 0.0,
      "rating": 0.0,
      "review_count": 0,
      "calculated_at": "2024-01-15T13:00:00Z"
    },
    "status": "draft",
    "created_at": "2024-01-15T13:00:00Z",
    "updated_at": "2024-01-15T13:00:00Z",
    "can_edit": true,
    "can_delete": true
  }
}
```

**Next Steps:**

1. Add lessons to module: `POST /modules/{module_id}/lessons`
2. Arrange lesson order: `PUT /modules/{module_id}/lessons/reorder`
3. Publish module: `PUT /modules/{module_id}` with `status: "published"`

---

### 2. **Add Lesson to Module** (Teacher)

**Endpoint:** `POST /modules/{module_id}/lessons`

**When to use:** Add a lesson reference to the module

**Request Body:**

```json
{
  "lesson_id": "507f1f77bcf86cd799439012",
  "config": {
    "order": 1,
    "required": true,
    "custom_title": null, // Override lesson title if needed
    "custom_description": null,
    "weight": 1.0, // For progress calculation
    "unlock_condition": "sequential", // sequential | immediate | conditional
    "unlock_requirements": []
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Lesson added to module successfully",
  "module_id": "507f1f77bcf86cd799439020",
  "lesson_id": "507f1f77bcf86cd799439012",
  "total_lessons": 1
}
```

**Frontend Implementation:**

```javascript
// Add multiple lessons to module
async function addLessonsToModule(moduleId, lessonIds) {
  const promises = lessonIds.map((lessonId, index) =>
    fetch(`${API_BASE}/modules/${moduleId}/lessons`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lesson_id: lessonId,
        config: {
          order: index + 1,
          required: true,
          unlock_condition: "sequential",
        },
      }),
    })
  );

  return await Promise.all(promises);
}

// Drag & drop lesson ordering
function ModuleLessonManager({ moduleId, lessons }) {
  const [orderedLessons, setOrderedLessons] = useState(lessons);

  const handleDragEnd = async (result) => {
    if (!result.destination) return;

    const items = Array.from(orderedLessons);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    setOrderedLessons(items);

    // Save new order to backend
    await fetch(`${API_BASE}/modules/${moduleId}/lessons/reorder`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lesson_ids: items.map((item) => item.lesson_id),
      }),
    });
  };

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Droppable droppableId="lessons">
        {(provided) => (
          <div {...provided.droppableProps} ref={provided.innerRef}>
            {orderedLessons.map((lesson, index) => (
              <Draggable
                key={lesson.lesson_id}
                draggableId={lesson.lesson_id}
                index={index}
              >
                {(provided) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                  >
                    <LessonCard lesson={lesson} order={index + 1} />
                  </div>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </DragDropContext>
  );
}
```

---

### 3. **Get Module with Lessons** (Teacher/Student)

**Endpoint:** `GET /modules/{module_id}?include_lessons=true`

**When to use:** View module structure with all lesson details

**Response:**

```json
{
  "module": {
    "id": "507f1f77bcf86cd799439020",
    "title": "Algebra Fundamentals",
    "description": "Complete introduction",
    "lesson_refs": [
      {
        "lesson_id": "507f1f77bcf86cd799439012",
        "order": 1,
        "required": true,
        "custom_title": null,
        "weight": 1.0,
        "unlock_condition": "sequential"
      },
      {
        "lesson_id": "507f1f77bcf86cd799439013",
        "order": 2,
        "required": true,
        "custom_title": null,
        "weight": 1.0,
        "unlock_condition": "sequential"
      }
    ],
    "metadata": {
      "total_lessons": 2,
      "total_duration": 85,
      "total_pages": 8,
      "total_components": 5
    }
  },
  "lessons": [
    {
      "lesson_id": "507f1f77bcf86cd799439012",
      "order": 1,
      "required": true,
      "custom_title": null,
      "weight": 1.0,
      "unlock_condition": "sequential",
      "title": "Introduction to Algebra",
      "description": "Learn the basics",
      "total_pages": 2,
      "total_duration": 35,
      "difficulty_level": "medium",
      "status": "published"
    },
    {
      "lesson_id": "507f1f77bcf86cd799439013",
      "order": 2,
      "required": true,
      "custom_title": null,
      "weight": 1.0,
      "unlock_condition": "sequential",
      "title": "Solving Equations",
      "description": "Master equation solving",
      "total_pages": 6,
      "total_duration": 50,
      "difficulty_level": "medium",
      "status": "published"
    }
  ],
  "total_lessons": 2,
  "total_duration": 85
}
```

---

### 4. **Reorder Lessons in Module** (Teacher)

**Endpoint:** `PUT /modules/{module_id}/lessons/reorder`

**When to use:** Change lesson sequence

**Request Body:**

```json
{
  "lesson_ids": [
    "507f1f77bcf86cd799439013", // Now first
    "507f1f77bcf86cd799439012" // Now second
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Lessons reordered successfully",
  "module_id": "507f1f77bcf86cd799439020",
  "new_order": ["507f1f77bcf86cd799439013", "507f1f77bcf86cd799439012"]
}
```

---

### 5. **Remove Lesson from Module** (Teacher)

**Endpoint:** `DELETE /modules/{module_id}/lessons/{lesson_id}`

**When to use:** Remove lesson reference from module (doesn't delete the lesson)

**Response:**

```json
{
  "success": true,
  "message": "Lesson removed from module successfully",
  "module_id": "507f1f77bcf86cd799439020",
  "lesson_id": "507f1f77bcf86cd799439012"
}
```

---

## 📚 Course Management

### 1. **Create Course** (Coordinator)

**Endpoint:** `POST /courses`

**When to use:** Coordinator wants to create a complete course

**Request Body:**

```json
{
  "title": "Mathematics Grade 10",
  "description": "Complete mathematics curriculum for grade 10",
  "course_code": "MATH-10-2024",
  "subject_id": "507f1f77bcf86cd799439011",
  "grade_level": 10,
  "instructor_ids": ["507f1f77bcf86cd799439010", "507f1f77bcf86cd799439015"],
  "difficulty_level": "medium",
  "learning_objectives": [
    "Master algebra",
    "Understand geometry",
    "Solve trigonometry problems"
  ],
  "prerequisites": ["Mathematics Grade 9"],
  "completion_criteria": {
    "type": "weighted_average",
    "minimum_score": 70,
    "required_modules": [],
    "optional_module_count": 0,
    "final_assessment_required": true
  },
  "auto_enroll_students": false,
  "allow_late_enrollment": true,
  "self_paced": false,
  "max_enrollments": 100,
  "course_start": "2024-02-01T00:00:00Z",
  "course_end": "2024-06-30T23:59:59Z",
  "enrollment_start": "2024-01-15T00:00:00Z",
  "enrollment_end": "2024-02-10T23:59:59Z",
  "visibility": "institutional"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Course created successfully",
  "course": {
    "id": "507f1f77bcf86cd799439030",
    "title": "Mathematics Grade 10",
    "description": "Complete mathematics curriculum",
    "slug": "mathematics-grade-10-1234567890",
    "course_code": "MATH-10-2024",
    "subject_id": "507f1f77bcf86cd799439011",
    "grade_level": 10,
    "coordinator_id": "507f1f77bcf86cd799439009",
    "instructor_ids": [...],
    "module_refs": [],
    "difficulty_level": "medium",
    "learning_objectives": [...],
    "prerequisites": [...],
    "completion_criteria": {...},
    "assessments": [],
    "auto_enroll_students": false,
    "allow_late_enrollment": true,
    "self_paced": false,
    "max_enrollments": 100,
    "enrollment_start": "2024-01-15T00:00:00Z",
    "enrollment_end": "2024-02-10T23:59:59Z",
    "course_start": "2024-02-01T00:00:00Z",
    "course_end": "2024-06-30T23:59:59Z",
    "visibility": "institutional",
    "featured": false,
    "metadata": {
      "total_modules": 0,
      "total_lessons": 0,
      "total_duration": 0,
      "enrolled_students": 0,
      "completion_rate": 0.0
    },
    "status": "draft",
    "created_at": "2024-01-15T14:00:00Z",
    "updated_at": "2024-01-15T14:00:00Z",
    "can_edit": true,
    "can_delete": true
  }
}
```

**Next Steps:**

1. Add modules: `POST /courses/{course_id}/modules`
2. Publish course: `PUT /courses/{course_id}` with `status: "published"`
3. Students can now enroll: `POST /progress/courses/{course_id}/enroll`

---

### 2. **Add Module to Course** (Coordinator)

**Endpoint:** `POST /courses/{course_id}/modules`

**When to use:** Add module reference to course

**Request Body:**

```json
{
  "module_id": "507f1f77bcf86cd799439020",
  "order": 1,
  "required": true,
  "custom_title": null,
  "weight": 1.0,
  "unlock_condition": "sequential"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Module added to course successfully",
  "course_id": "507f1f77bcf86cd799439030",
  "module_id": "507f1f77bcf86cd799439020",
  "total_modules": 1
}
```

---

### 3. **Get Course Details** (Student/Teacher/Coordinator)

**Endpoint:** `GET /courses/{course_id}?include_modules=true`

**When to use:** View complete course structure

**Response:**

```json
{
  "course": {
    "id": "507f1f77bcf86cd799439030",
    "title": "Mathematics Grade 10",
    "description": "Complete mathematics curriculum",
    "course_code": "MATH-10-2024",
    "subject_id": "507f1f77bcf86cd799439011",
    "grade_level": 10,
    "coordinator_id": "507f1f77bcf86cd799439009",
    "instructor_ids": [...],
    "module_refs": [...],
    "metadata": {
      "total_modules": 3,
      "total_lessons": 15,
      "total_duration": 900,
      "enrolled_students": 45,
      "estimated_weeks": 16
    },
    "status": "active",
    "course_start": "2024-02-01T00:00:00Z",
    "course_end": "2024-06-30T23:59:59Z",
    "can_edit": true,
    "can_delete": false,
    "can_enroll": true,
    "is_active": true
  },
  "modules": [
    {
      "module_id": "507f1f77bcf86cd799439020",
      "order": 1,
      "required": true,
      "custom_title": null,
      "weight": 1.0,
      "unlock_condition": "sequential",
      "title": "Algebra Fundamentals",
      "description": "Complete introduction",
      "total_lessons": 5,
      "total_duration": 300,
      "difficulty_level": "medium",
      "status": "published"
    },
    {
      "module_id": "507f1f77bcf86cd799439021",
      "order": 2,
      "required": true,
      "custom_title": null,
      "weight": 1.0,
      "unlock_condition": "sequential",
      "title": "Geometry Basics",
      "description": "Introduction to geometry",
      "total_lessons": 6,
      "total_duration": 350,
      "difficulty_level": "medium",
      "status": "published"
    }
  ]
}
```

**Frontend Implementation:**

```javascript
function CourseDetailPage({ courseId }) {
  const [course, setCourse] = useState(null);
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/courses/${courseId}?include_modules=true`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        setCourse(data.course);
        setModules(data.modules);
        setLoading(false);
      });
  }, [courseId]);

  if (loading) return <Loading />;

  return (
    <div>
      <CourseHeader course={course} />

      <CourseStats
        totalModules={course.metadata.total_modules}
        totalLessons={course.metadata.total_lessons}
        duration={course.metadata.total_duration}
        enrolledStudents={course.metadata.enrolled_students}
      />

      <ModuleList>
        {modules.map((module, index) => (
          <ModuleCard
            key={module.module_id}
            module={module}
            courseId={courseId}
            isLocked={!module.is_unlocked}
          />
        ))}
      </ModuleList>

      {course.can_enroll && <EnrollButton courseId={courseId} />}
    </div>
  );
}
```

---

## 📊 Progress Tracking

### Complete Student Learning Flow

```
1. Enroll in Course
   ↓
2. View Course Dashboard (modules, progress, recommendations)
   ↓
3. Start Module (initialize progress)
   ↓
4. View Module with Lessons (learning path)
   ↓
5. Start Lesson (page by page)
   ↓
6. Complete Pages & Components
   ↓
7. Progress auto-updates (Lesson → Module → Course)
   ↓
8. View analytics & completion certificate
```

---

### 1. **Enroll in Course** (Student)

**Endpoint:** `POST /progress/courses/{course_id}/enroll`

**When to use:** Student wants to join a course

**Request Body:**

```json
{
  "enrollment_metadata": {
    "enrollment_type": "self",
    "enrollment_reason": "Required course",
    "expectations": "Learn mathematics fundamentals"
  }
}
```

**Response:**

```json
{
  "id": "507f1f77bcf86cd799439040",
  "student_id": "507f1f77bcf86cd799439005",
  "course_id": "507f1f77bcf86cd799439030",
  "course_title": "Mathematics Grade 10",
  "course_description": "Complete mathematics curriculum",
  "enrollment_id": "507f1f77bcf86cd799439041",
  "status": "not_started",
  "completion_percentage": 0.0,
  "score": null,
  "grade": null,
  "total_modules": 3,
  "completed_modules": 0,
  "in_progress_modules": 0,
  "total_lessons": 15,
  "completed_lessons": 0,
  "in_progress_lessons": 0,
  "current_module_id": null,
  "current_lesson_id": null,
  "learning_path": [],
  "total_time_spent": 0,
  "average_quiz_score": 0.0,
  "average_assignment_score": 0.0,
  "login_count": 0,
  "active_days": 0,
  "streak_days": 0,
  "longest_streak": 0,
  "enrolled_at": "2024-01-15T15:00:00Z",
  "started_at": null,
  "completed_at": null,
  "last_activity": "2024-01-15T15:00:00Z",
  "created_at": "2024-01-15T15:00:00Z"
}
```

**Next Steps:**

1. View dashboard: `GET /progress/courses/{course_id}/dashboard`
2. Start first module: `POST /progress/modules/{module_id}/start`

---

### 2. **Get Course Dashboard** (Student)

**Endpoint:** `GET /progress/courses/{course_id}/dashboard`

**When to use:** Display student's course overview

**Response:**

```json
{
  "course_progress": {
    "id": "507f1f77bcf86cd799439040",
    "status": "in_progress",
    "completion_percentage": 35.5,
    "score": 78.5,
    "grade": "B",
    "total_modules": 3,
    "completed_modules": 1,
    "in_progress_modules": 1,
    "total_lessons": 15,
    "completed_lessons": 5,
    "in_progress_lessons": 2,
    "current_module_id": "507f1f77bcf86cd799439020",
    "current_lesson_id": "507f1f77bcf86cd799439013",
    "total_time_spent": 7200, // seconds
    "average_quiz_score": 82.5,
    "average_assignment_score": 75.0,
    "streak_days": 5,
    "longest_streak": 7
  },
  "course_info": {
    "title": "Mathematics Grade 10",
    "description": "Complete mathematics curriculum",
    "coordinator": "507f1f77bcf86cd799439009",
    "start_date": "2024-02-01T00:00:00Z",
    "end_date": "2024-06-30T23:59:59Z"
  },
  "module_progress": [
    {
      "module_id": "507f1f77bcf86cd799439020",
      "order": 1,
      "required": true,
      "progress": {
        "status": "completed",
        "completion_percentage": 100.0,
        "completed_lessons": 5,
        "total_lessons": 5
      },
      "lesson_summary": {
        "total_lessons": 5,
        "completed_lessons": 5,
        "next_lesson": null
      },
      "is_unlocked": true,
      "can_start": true
    },
    {
      "module_id": "507f1f77bcf86cd799439021",
      "order": 2,
      "required": true,
      "progress": {
        "status": "in_progress",
        "completion_percentage": 33.3,
        "completed_lessons": 2,
        "total_lessons": 6
      },
      "lesson_summary": {
        "total_lessons": 6,
        "completed_lessons": 2,
        "next_lesson": {
          "lesson_id": "507f1f77bcf86cd799439025",
          "title": "Triangles and Angles"
        }
      },
      "is_unlocked": true,
      "can_start": true
    },
    {
      "module_id": "507f1f77bcf86cd799439022",
      "order": 3,
      "required": true,
      "progress": {
        "status": "not_started",
        "completion_percentage": 0.0,
        "completed_lessons": 0,
        "total_lessons": 4
      },
      "is_unlocked": false,
      "can_start": false
    }
  ],
  "learning_path": [
    {
      "module_id": "507f1f77bcf86cd799439020",
      "order": 1,
      "status": "completed",
      "completion_percentage": 100.0,
      "is_unlocked": true,
      "is_next": false
    },
    {
      "module_id": "507f1f77bcf86cd799439021",
      "order": 2,
      "status": "in_progress",
      "completion_percentage": 33.3,
      "is_unlocked": true,
      "is_next": true
    },
    {
      "module_id": "507f1f77bcf86cd799439022",
      "order": 3,
      "status": "not_started",
      "completion_percentage": 0.0,
      "is_unlocked": false,
      "is_next": false
    }
  ],
  "next_steps": [
    {
      "type": "continue_lesson",
      "lesson_id": "507f1f77bcf86cd799439025",
      "title": "Continue: Triangles and Angles",
      "priority": "high"
    }
  ],
  "recent_activity": [
    {
      "type": "lesson_progress",
      "timestamp": "2024-01-15T14:30:00Z",
      "description": "Worked on: Introduction to Circles",
      "status": "in_progress",
      "completion_percentage": 60.0
    }
  ],
  "recommendations": [
    {
      "type": "engagement",
      "title": "Keep up your streak!",
      "description": "You've been consistent for 5 days",
      "priority": "low"
    },
    {
      "type": "performance",
      "title": "Great quiz scores!",
      "description": "Your average is 82.5%",
      "priority": "low"
    }
  ],
  "statistics": {
    "time_spent_today": 1800, // 30 minutes
    "streak_days": 5,
    "completion_prediction": "2024-05-15T00:00:00Z"
  }
}
```

**Frontend Implementation:**

```javascript
function CourseDashboard({ courseId }) {
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/progress/courses/${courseId}/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then(setDashboard);
  }, [courseId]);

  if (!dashboard) return <Loading />;

  return (
    <div className="course-dashboard">
      {/* Progress Overview */}
      <ProgressCard
        completion={dashboard.course_progress.completion_percentage}
        score={dashboard.course_progress.score}
        grade={dashboard.course_progress.grade}
        streak={dashboard.course_progress.streak_days}
      />

      {/* Next Steps */}
      <NextStepsCard steps={dashboard.next_steps} />

      {/* Module Progress */}
      <div className="modules-section">
        <h2>Your Learning Path</h2>
        {dashboard.module_progress.map((module) => (
          <ModuleProgressCard
            key={module.module_id}
            module={module}
            courseId={courseId}
          />
        ))}
      </div>

      {/* Statistics */}
      <StatisticsGrid
        timeToday={dashboard.statistics.time_spent_today}
        streak={dashboard.statistics.streak_days}
        prediction={dashboard.statistics.completion_prediction}
      />

      {/* Recent Activity */}
      <ActivityTimeline activities={dashboard.recent_activity} />

      {/* Recommendations */}
      <RecommendationsCard recommendations={dashboard.recommendations} />
    </div>
  );
}
```

---

### 3. **Start Lesson** (Student)

**Endpoint:** `POST /progress/lessons/{lesson_id}/start`

**When to use:** Student begins a lesson

**Request Body:**

```json
{
  "course_id": "507f1f77bcf86cd799439030",
  "module_id": "507f1f77bcf86cd799439020",
  "access_method": "via_course",
  "device_type": "desktop"
}
```

**Response:**

```json
{
  "id": "507f1f77bcf86cd799439050",
  "student_id": "507f1f77bcf86cd799439005",
  "lesson_id": "507f1f77bcf86cd799439012",
  "lesson_title": "Introduction to Algebra",
  "course_id": "507f1f77bcf86cd799439030",
  "module_id": "507f1f77bcf86cd799439020",
  "status": "not_started",
  "completion_percentage": 0.0,
  "score": null,
  "current_page": 1,
  "total_pages": 2,
  "page_progress": [
    {
      "page_number": 1,
      "status": "not_started",
      "time_spent": 0,
      "completion_percentage": 0.0,
      "component_progress": [
        {
          "component_id": "quiz_1",
          "component_type": "quiz",
          "status": "not_started",
          "score": null,
          "attempts": 0,
          "time_spent": 0
        }
      ],
      "started_at": null,
      "completed_at": null,
      "last_activity": "2024-01-15T15:30:00Z"
    },
    {
      "page_number": 2,
      "status": "not_started",
      "time_spent": 0,
      "completion_percentage": 0.0,
      "component_progress": [],
      "started_at": null,
      "completed_at": null,
      "last_activity": "2024-01-15T15:30:00Z"
    }
  ],
  "total_time_spent": 0,
  "access_method": "via_course",
  "device_type": "desktop",
  "started_at": "2024-01-15T15:30:00Z",
  "last_activity": "2024-01-15T15:30:00Z",
  "created_at": "2024-01-15T15:30:00Z"
}
```

**Next Steps:**

1. Get lesson content: `GET /lessons/{lesson_id}`
2. Display first page
3. Track activity: `POST /progress/lessons/{lesson_id}/activity`
4. Update page progress: `PUT /progress/lessons/{lesson_id}/pages/{page_number}/progress`

---

### 4. **Update Page Progress** (Student)

**Endpoint:** `PUT /progress/lessons/{lesson_id}/pages/{page_number}/progress`

**When to use:** Student reads a page or completes components

**Request Body:**

```json
{
  "status": "completed",
  "time_spent": 900, // 15 minutes in seconds
  "completion_percentage": 100.0,
  "component_progress": [
    {
      "component_id": "quiz_1",
      "status": "completed",
      "score": 90.0,
      "time_spent": 300,
      "attempts": 1,
      "responses": [
        {
          "question_id": "q1",
          "answer": "Unknown value",
          "is_correct": true,
          "points_earned": 10
        }
      ]
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Page progress updated successfully",
  "lesson_id": "507f1f77bcf86cd799439012",
  "page_number": 1,
  "completion_percentage": 50.0, // Overall lesson completion
  "next_page": 2
}
```

**Auto-triggers:**

- Lesson progress recalculation
- Module progress update
- Course progress update

---

### 5. **Complete Component** (Student)

**Endpoint:** `POST /progress/lessons/{lesson_id}/pages/{page_number}/components/{component_id}/complete`

**When to use:** Student finishes a quiz/assignment

**Request Body:**

```json
{
  "component_id": "quiz_1",
  "type": "quiz",
  "status": "completed",
  "score": 85.0,
  "time_spent": 450,
  "attempts": 2,
  "responses": [
    {
      "question_id": "q1",
      "question_type": "multiple_choice",
      "answer": "Unknown value",
      "is_correct": true,
      "points_earned": 10,
      "max_points": 10,
      "time_spent": 120
    },
    {
      "question_id": "q2",
      "question_type": "short_answer",
      "answer": "2x + 5",
      "is_correct": false,
      "points_earned": 0,
      "max_points": 15,
      "feedback": "Remember to simplify the expression",
      "time_spent": 180
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Component completed successfully",
  "component_id": "quiz_1",
  "score": 85.0,
  "lesson_progress": 75.0
}
```

**Frontend Implementation:**

```javascript
// Quiz Component
function QuizComponent({ lessonId, pageNumber, component }) {
  const [answers, setAnswers] = useState({});
  const [timeSpent, setTimeSpent] = useState(0);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeSpent((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleSubmit = async () => {
    setAttempts((prev) => prev + 1);

    // Calculate responses
    const responses = component.data.questions.map((q) => ({
      question_id: q.id,
      question_type: q.type,
      answer: answers[q.id],
      is_correct: answers[q.id] === q.correct_answer,
      points_earned: answers[q.id] === q.correct_answer ? q.points : 0,
      max_points: q.points,
      time_spent: timeSpent / component.data.questions.length,
    }));

    const score =
      (responses.reduce((sum, r) => sum + r.points_earned, 0) /
        responses.reduce((sum, r) => sum + r.max_points, 0)) *
      100;

    // Submit to API
    const result = await fetch(
      `${API_BASE}/progress/lessons/${lessonId}/pages/${pageNumber}/components/${component.component_id}/complete`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          component_id: component.component_id,
          type: component.type,
          status: "completed",
          score,
          time_spent: timeSpent,
          attempts,
          responses,
        }),
      }
    );

    const data = await result.json();

    // Show results
    showQuizResults(data);

    // Update lesson progress in parent component
    onComplete(data.lesson_progress);
  };

  return (
    <div className="quiz-component">
      <h3>{component.title}</h3>
      {component.data.questions.map((question) => (
        <QuestionItem
          key={question.id}
          question={question}
          answer={answers[question.id]}
          onAnswerChange={(answer) =>
            setAnswers({ ...answers, [question.id]: answer })
          }
        />
      ))}
      <button onClick={handleSubmit}>Submit Quiz</button>
      <div>Time: {formatTime(timeSpent)}</div>
      <div>Attempts: {attempts}</div>
    </div>
  );
}
```

---

### 6. **Track Activity** (Student)

**Endpoint:** `POST /progress/lessons/{lesson_id}/activity`

**When to use:** Track student engagement (send every 30 seconds or on page change)

**Request Body:**

```json
{
  "activity_type": "page_view",
  "time_spent": 30,
  "metadata": {
    "page_number": 1,
    "scroll_depth": 75,
    "interactions": 5
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Activity recorded successfully",
  "updated_progress": {
    "lesson_id": "507f1f77bcf86cd799439012",
    "total_time_spent": 1830
  }
}
```

**Frontend Implementation:**

```javascript
// Activity tracker hook
function useActivityTracker(lessonId) {
  const [sessionStart] = useState(Date.now());
  const [lastSync, setLastSync] = useState(Date.now());

  useEffect(() => {
    const syncActivity = async () => {
      const now = Date.now();
      const timeSpent = Math.floor((now - lastSync) / 1000);

      if (timeSpent >= 30) {
        await fetch(`${API_BASE}/progress/lessons/${lessonId}/activity`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            activity_type: "page_view",
            time_spent: timeSpent,
            metadata: {
              page_number: currentPage,
              scroll_depth: getScrollDepth(),
              interactions: getInteractionCount(),
            },
          }),
        });

        setLastSync(now);
      }
    };

    // Sync every 30 seconds
    const interval = setInterval(syncActivity, 30000);

    // Sync on page unload
    window.addEventListener("beforeunload", syncActivity);

    return () => {
      clearInterval(interval);
      window.removeEventListener("beforeunload", syncActivity);
      syncActivity(); // Final sync
    };
  }, [lessonId, lastSync]);
}

// Usage in Lesson component
function LessonViewer({ lessonId }) {
  useActivityTracker(lessonId);

  return <div>{/* Lesson content */}</div>;
}
```

---

### 7. **Get Student Progress List** (Student)

**Endpoint:** `GET /progress/students/me/lesson-progress`

**When to use:** Display all lessons student is working on

**Query Parameters:**

```
?page=1
&per_page=20
&course_id=507f1f77bcf86cd799439030
&module_id=507f1f77bcf86cd799439020
&status=in_progress
```

**Response:**

```json
{
  "items": [
    {
      "id": "507f1f77bcf86cd799439050",
      "lesson_id": "507f1f77bcf86cd799439012",
      "lesson_title": "Introduction to Algebra",
      "lesson_description": "Learn the basics",
      "status": "in_progress",
      "completion_percentage": 50.0,
      "score": 85.0,
      "current_page": 2,
      "total_pages": 2,
      "total_time_spent": 1800,
      "access_method": "via_course",
      "started_at": "2024-01-15T15:30:00Z",
      "last_activity": "2024-01-15T16:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 20,
  "total_pages": 1,
  "has_next": false,
  "has_prev": false
}
```

---

## 🔄 Complete User Flows

### Flow 1: Teacher Creates & Publishes Content

```javascript
// Step 1: Create Lesson
const lesson = await createLesson({
  title: "Introduction to Algebra",
  subject_id: subjectId,
  grade_level: 10,
  pages: [...]
});

// Step 2: Create Module
const module = await createModule({
  title: "Algebra Fundamentals",
  subject_id: subjectId,
  grade_level: 10
});

// Step 3: Add Lessons to Module
await addLessonToModule(module.id, lesson.id, {
  order: 1,
  required: true,
  unlock_condition: 'sequential'
});

// Step 4: Publish Module
await updateModule(module.id, {
  status: 'published'
});

// Step 5: Share with Coordinator
await shareModule(module.id, coordinatorIds);
```

---

### Flow 2: Coordinator Creates Course

```javascript
// Step 1: Create Course
const course = await createCourse({
  title: "Mathematics Grade 10",
  subject_id: subjectId,
  grade_level: 10,
  course_start: "2024-02-01T00:00:00Z",
  course_end: "2024-06-30T23:59:59Z",
});

// Step 2: Browse & Select Modules
const modules = await fetchModules({
  subject_id: subjectId,
  grade_level: 10,
  status: "published",
});

// Step 3: Add Modules to Course
for (const [index, module] of modules.entries()) {
  await addModuleToCourse(course.id, module.id, {
    order: index + 1,
    required: true,
    unlock_condition: "sequential",
  });
}

// Step 4: Publish Course
await updateCourse(course.id, {
  status: "published",
});

// Step 5: Notify Students
await notifyStudents(course.id, "New course available");
```

---

### Flow 3: Student Learns

```javascript
// Step 1: Enroll in Course
const enrollment = await enrollInCourse(courseId);

// Step 2: View Dashboard
const dashboard = await getCourseDashboard(courseId);

// Step 3: Start First Module
const firstModule = dashboard.module_progress[0];
await startModule(firstModule.module_id, courseId);

// Step 4: Get Module Details
const moduleDetail = await getModuleWithLessons(firstModule.module_id);

// Step 5: Start First Lesson
const firstLesson = moduleDetail.lessons[0];
const lessonProgress = await startLesson(firstLesson.lesson_id, {
  course_id: courseId,
  module_id: firstModule.module_id,
  access_method: 'via_course'
});

// Step 6: Get Lesson Content
const lessonContent = await getLesson(firstLesson.lesson_id);

// Step 7: Display First Page
displayPage(lessonContent.pages[0]);

// Step 8: Track Activity
startActivityTracking(firstLesson.lesson_id);

// Step 9: Complete Page
await updatePageProgress(firstLesson.lesson_id, 1, {
  status: 'completed',
  time_spent: 900,
  completion_percentage: 100
});

// Step 10: Complete Quiz
await completeComponent(firstLesson.lesson_id, 1, 'quiz_1', {
  score: 85,
  time_spent: 450,
  responses: [...]
});

// Step 11: Move to Next Page
const nextPageInfo = await getNextPage(firstLesson.lesson_id);
if (nextPageInfo.next_page) {
  displayPage(lessonContent.pages[nextPageInfo.next_page - 1]);
}

// Step 12: Refresh Progress
await refreshModuleProgress(firstModule.module_id);
await refreshCourseProgress(courseId);

// Step 13: View Updated Dashboard
const updatedDashboard = await getCourseDashboard(courseId);
```

---

## ⚠️ Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message here",
  "error_code": "LESSON_NOT_FOUND",
  "status_code": 404
}
```

### Common HTTP Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - No permission
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Error Handling Implementation

```javascript
async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error.detail, response.status, error.error_code);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      handleAPIError(error);
    } else {
      handleNetworkError(error);
    }
    throw error;
  }
}

class APIError extends Error {
  constructor(message, statusCode, errorCode) {
    super(message);
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

function handleAPIError(error) {
  switch (error.statusCode) {
    case 401:
      // Redirect to login
      redirectToLogin();
      break;
    case 403:
      // Show permission denied
      showToast("You do not have permission", "error");
      break;
    case 404:
      // Show not found
      showToast("Resource not found", "error");
      break;
    case 422:
      // Show validation errors
      showValidationErrors(error.message);
      break;
    default:
      // Show generic error
      showToast(error.message, "error");
  }
}
```

---

## 💡 Best Practices

### 1. **Progressive Loading**

Don't load everything at once. Load data as needed:

```javascript
// Good: Load course overview first
const courseOverview = await getCourse(courseId, { include_modules: false });
displayCourseHeader(courseOverview);

// Then load modules when user scrolls
const modules = await getCourseModules(courseId);
displayModules(modules);

// Load lesson details only when clicked
const lessonDetail = await getLesson(lessonId);
displayLesson(lessonDetail);
```

### 2. **Optimistic Updates**

Update UI immediately, then sync with server:

```javascript
function updatePageProgress(lessonId, pageNumber, progress) {
  // Update UI immediately
  setLocalProgress((prev) => ({
    ...prev,
    [pageNumber]: progress,
  }));

  // Sync with server
  apiCall(`/progress/lessons/${lessonId}/pages/${pageNumber}/progress`, {
    method: "PUT",
    body: JSON.stringify(progress),
  }).catch((error) => {
    // Revert on error
    setLocalProgress((prev) => ({
      ...prev,
      [pageNumber]: prevProgress,
    }));
    showToast("Failed to save progress", "error");
  });
}
```

### 3. **Caching**

Cache frequently accessed data:

```javascript
const cache = new Map();

async function getCachedLesson(lessonId, maxAge = 5 * 60 * 1000) {
  const cached = cache.get(lessonId);

  if (cached && Date.now() - cached.timestamp < maxAge) {
    return cached.data;
  }

  const data = await getLesson(lessonId);
  cache.set(lessonId, {
    data,
    timestamp: Date.now(),
  });

  return data;
}
```

### 4. **Polling for Progress Updates**

For collaborative features:

```javascript
function useProgressPolling(courseId, interval = 60000) {
  useEffect(() => {
    const poll = async () => {
      const progress = await getCourseProgress(courseId);
      updateProgress(progress);
    };

    poll(); // Initial load
    const timer = setInterval(poll, interval);

    return () => clearInterval(timer);
  }, [courseId, interval]);
}
```

### 5. **Batch Requests**

Group multiple requests:

```javascript
// Instead of multiple single requests
const lessons = await Promise.all(lessonIds.map((id) => getLesson(id)));

// Use batch endpoint if available
const lessons = await getLessons({ ids: lessonIds });
```

### 6. **Offline Support**

Store progress locally when offline:

```javascript
function saveProgressOffline(lessonId, pageNumber, progress) {
  const offline = JSON.parse(localStorage.getItem("offline_progress") || "[]");
  offline.push({
    lessonId,
    pageNumber,
    progress,
    timestamp: Date.now(),
  });
  localStorage.setItem("offline_progress", JSON.stringify(offline));
}

async function syncOfflineProgress() {
  const offline = JSON.parse(localStorage.getItem("offline_progress") || "[]");

  for (const item of offline) {
    try {
      await updatePageProgress(item.lessonId, item.pageNumber, item.progress);
    } catch (error) {
      console.error("Failed to sync:", item, error);
    }
  }

  localStorage.removeItem("offline_progress");
}

// Sync when online
window.addEventListener("online", syncOfflineProgress);
```

---

## 📱 Complete Example: Lesson Viewer Component

```javascript
import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

function LessonViewer() {
  const { lessonId, courseId, moduleId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [progress, setProgress] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLesson();
  }, [lessonId]);

  async function loadLesson() {
    try {
      // Load lesson content and progress in parallel
      const [lessonData, progressData] = await Promise.all([
        fetch(`${API_BASE}/lessons/${lessonId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.json()),

        fetch(`${API_BASE}/progress/lessons/${lessonId}/progress`, {
          headers: { Authorization: `Bearer ${token}` },
        })
          .then((res) => res.json())
          .catch(() => null),
      ]);

      setLesson(lessonData);

      // If no progress exists, start lesson
      if (!progressData) {
        const newProgress = await fetch(
          `${API_BASE}/progress/lessons/${lessonId}/start`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              course_id: courseId,
              module_id: moduleId,
              access_method: "via_course",
              device_type: getDeviceType(),
            }),
          }
        ).then((res) => res.json());

        setProgress(newProgress);
      } else {
        setProgress(progressData);
        setCurrentPage(progressData.current_page);
      }

      setLoading(false);
    } catch (error) {
      console.error("Failed to load lesson:", error);
      showToast("Failed to load lesson", "error");
    }
  }

  async function handlePageComplete(pageNumber, pageProgress) {
    try {
      const result = await fetch(
        `${API_BASE}/progress/lessons/${lessonId}/pages/${pageNumber}/progress`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(pageProgress),
        }
      ).then((res) => res.json());

      // Update local progress
      setProgress((prev) => ({
        ...prev,
        completion_percentage: result.completion_percentage,
      }));

      // Move to next page
      if (result.next_page) {
        setCurrentPage(result.next_page);
      } else {
        // Lesson completed
        showToast("Lesson completed!", "success");
        redirectToModule();
      }
    } catch (error) {
      console.error("Failed to save progress:", error);
      showToast("Failed to save progress", "error");
    }
  }

  if (loading) return <Loading />;

  const currentPageData = lesson.pages.find(
    (p) => p.page_number === currentPage
  );

  return (
    <div className="lesson-viewer">
      {/* Header */}
      <LessonHeader
        title={lesson.title}
        progress={progress.completion_percentage}
        currentPage={currentPage}
        totalPages={lesson.pages.length}
      />

      {/* Page Content */}
      <PageContent
        page={currentPageData}
        onComplete={(pageProgress) =>
          handlePageComplete(currentPage, pageProgress)
        }
      />

      {/* Navigation */}
      <LessonNavigation
        currentPage={currentPage}
        totalPages={lesson.pages.length}
        onPrevious={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
        onNext={() =>
          setCurrentPage((prev) => Math.min(lesson.pages.length, prev + 1))
        }
        canGoNext={
          progress.page_progress[currentPage - 1]?.status === "completed"
        }
      />
    </div>
  );
}

export default LessonViewer;
```

---

## 🎓 Summary

This guide covers the complete implementation of Smart Study Hub's LMS API. Key takeaways:

1. **Start Simple**: Teacher creates lessons → Module groups lessons → Course groups modules
2. **Progressive Loading**: Load data incrementally as needed
3. **Track Everything**: Activity, progress, engagement - all auto-calculated
4. **Error Handling**: Always handle errors gracefully
5. **Optimize**: Cache, batch requests, offline support

For questions or issues, contact the backend team or check the API documentation at `/api/v1/docs`.

---

**Last Updated:** January 15, 2024
**Version:** 1.0.0
**API Base URL:** `https://api.smartstudyhub.com/api/v1`
