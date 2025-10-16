# Lesson Management System - Frontend Integration Guide

**Version:** 2.0  
**Last Updated:** 2025-01-16  
**API Base URL:** `/api/v1`  
**Authentication:** Bearer Token (JWT)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core Concepts](#core-concepts)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Data Models](#data-models)
6. [UI/UX Implementation Patterns](#uiux-implementation-patterns)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Common Workflows](#common-workflows)

---

## Overview

### System Architecture

Lesson Management System menggunakan **separated storage architecture**:
- **Lessons Collection**: Menyimpan metadata lesson (title, description, settings, etc.)
- **Lesson Pages Collection**: Menyimpan page content secara terpisah
- **Relasi**: One-to-Many (1 lesson → N pages)

**Key Benefits:**
- ✅ Performance: Load metadata tanpa full content
- ✅ Scalability: Large lessons tidak bottleneck
- ✅ Concurrent editing: Multiple pages bisa diedit simultan
- ✅ Versioning: Per-page version tracking

### Key Features

- ✅ CRUD operations untuk lessons dan pages
- ✅ Permission-based access (creator, collaborator, public)
- ✅ Draft/Published status management
- ✅ Page ordering dengan transaction-safe reordering
- ✅ Usage tracking (lessons used in modules/courses)
- ✅ Media references dan embedded components
- ✅ Markdown content support

---

## Authentication

### Required Header

Semua API requests memerlukan JWT token:

```
Authorization: Bearer <jwt_token>
```

### User Roles

- **admin**: Full access ke semua lessons
- **teacher**: Create, edit own lessons, view public lessons
- **student**: View public lessons dan enrolled courses

### Permission Logic

| Action | Creator | Collaborator | Other Teachers | Students |
|--------|---------|--------------|----------------|----------|
| View (public) | ✅ | ✅ | ✅ | ✅ |
| View (private) | ✅ | ✅ | ❌ | ❌ |
| Edit | ✅ | ✅ | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ❌ |
| Publish | ✅ | ✅ | ❌ | ❌ |

---

## Core Concepts

### Lesson Lifecycle

```
draft → published → archived
  ↓         ↓
edit     edit (version++)
```

### Page Management

- **Pages** stored separately dari lesson document
- **Page numbers** start from 1 (sequential)
- **Reordering** uses transaction to prevent conflicts
- **Deletion** auto-renumbers remaining pages

### Metadata Auto-Calculation

System automatically calculates:
- `total_pages`: Count of pages
- `total_duration`: Sum of page durations
- `total_components`: Count of embedded components
- `total_media`: Count of media references

**Note:** Frontend TIDAK perlu calculate ini manually. Backend handles automatically saat pages created/updated/deleted.

---

## API Endpoints Reference

### 1. Lesson CRUD Operations

#### 1.1 Create Lesson

**Endpoint:** `POST /lessons`

**Description:** Create new lesson dengan atau tanpa pages. Recommended: Create dengan basic info saja, add pages later.

**Request Body:**
```json
{
  "title": "string (required, max 200 chars)",
  "description": "string (required, max 2000 chars)",
  "subject_id": "string (required, ObjectId)",
  "grade_level": "integer (required, 1-12)",
  "topic_tags": ["string array (optional)"],
  "difficulty_level": "string (optional, default: 'medium', values: easy|medium|hard)",
  "learning_objectives": ["string array (optional)"],
  "prerequisites": ["string array (optional)"],
  "visibility": "string (optional, default: 'public', values: public|private|shared)",
  "status": "string (optional, default: 'draft', values: draft|published|archived)"
}
```

**IMPORTANT:** Pages are NOT created via this endpoint. After creating a lesson, use `POST /lessons/{id}/pages` to add pages. This ensures clean separation between lesson metadata and page content.
```

**Response:** `201 Created`
```json
{
  "id": "68e417bcfd89bb8eb15f09ad",
  "title": "Introduction to Algebra",
  "description": "Learn basic algebra concepts",
  "slug": "introduction-to-algebra-1234567890",
  "subject_id": "68b328329be3ef2464823bff",
  "subject_name": null,
  "grade_level": 10,
  "topic_tags": ["algebra", "mathematics"],
  "difficulty_level": "medium",
  "learning_objectives": ["Understand variables", "Solve equations"],
  "prerequisites": [],
  "visibility": "private",
  "status": "draft",
  "created_by": "68822f07979cbba23e6db950",
  "created_by_name": null,
  "collaborators": [],
  "metadata": {
    "total_pages": 0,
    "total_duration": 0,
    "total_components": 0,
    "total_media": 0,
    "component_breakdown": {},
    "media_breakdown": {},
    "difficulty_distribution": {},
    "usage_count": 0,
    "completion_rate": 0.0,
    "rating": 0.0,
    "review_count": 0,
    "calculated_at": "2025-01-16T10:30:00Z"
  },
  "pages": [],
  "can_edit": true,
  "can_delete": true,
  "can_collaborate": true,
  "usage_in_modules": null,
  "published_at": null,
  "archived_at": null,
  "created_at": "2025-01-16T10:30:00Z",
  "updated_at": "2025-01-16T10:30:00Z"
}
```

**Validation Rules:**
- `subject_id` must exist in database (akan di-validate oleh backend)
- `grade_level` must be 1-12
- `visibility` must be: public, private, atau shared
- `status` must be: draft, published, atau archived
- `difficulty_level` must be: easy, medium, atau hard

---

#### 1.2 List Lessons

**Endpoint:** `GET /lessons`

**Description:** Retrieve paginated list of lessons dengan filtering dan sorting.

**Query Parameters:**
```
page=1                      (integer, default: 1, min: 1)
per_page=20                 (integer, default: 20, min: 1, max: 100)
subject_id=<ObjectId>       (optional)
grade_level=<1-12>          (optional)
created_by=<ObjectId>       (optional)
visibility=<public|private|shared> (optional)
status=<draft|published|archived> (optional)
difficulty_level=<easy|medium|hard> (optional)
topic_tags=<tag1,tag2>      (optional, comma-separated)
search=<query>              (optional, searches title, description, tags)
sort_by=<field>             (optional, default: updated_at)
sort_direction=<asc|desc>   (optional, default: desc)
```

**Available sort fields:**
- `title`, `created_at`, `updated_at`, `grade_level`, `difficulty_level`, `status`

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "68e417bcfd89bb8eb15f09ad",
      "title": "Introduction to Algebra",
      "description": "Learn basic algebra concepts",
      "slug": "introduction-to-algebra-1234567890",
      "subject_id": "68b328329be3ef2464823bff",
      "subject_name": "Mathematics",
      "grade_level": 10,
      "topic_tags": ["algebra"],
      "total_pages": 5,
      "total_duration": 75,
      "difficulty_level": "medium",
      "created_by": "68822f07979cbba23e6db950",
      "created_by_name": "John Doe",
      "visibility": "public",
      "status": "published",
      "can_edit": true,
      "can_delete": true,
      "is_favorited": false,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-16T10:30:00Z"
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

**Permission Behavior:**
- Teachers: See public lessons + own lessons + shared lessons
- Students: See public lessons only
- Admin: See all lessons

---

#### 1.3 Get Lesson by ID

**Endpoint:** `GET /lessons/{lesson_id}`

**Query Parameters:**
```
include_usage=<true|false>  (optional, default: false)
```

**Description:** Get detailed lesson information. Set `include_usage=true` to get modules/courses using this lesson.

**Response:** `200 OK`
```json
{
  "id": "68e417bcfd89bb8eb15f09ad",
  "title": "Introduction to Algebra",
  "description": "Learn basic algebra concepts",
  "slug": "introduction-to-algebra-1234567890",
  "subject_id": "68b328329be3ef2464823bff",
  "subject_name": null,
  "grade_level": 10,
  "topic_tags": ["algebra"],
  "difficulty_level": "medium",
  "learning_objectives": ["Understand variables"],
  "prerequisites": [],
  "visibility": "public",
  "status": "published",
  "created_by": "68822f07979cbba23e6db950",
  "created_by_name": null,
  "collaborators": [],
  "metadata": {
    "total_pages": 5,
    "total_duration": 75,
    "total_components": 3,
    "total_media": 2,
    "usage_count": 2,
    "completion_rate": 78.5,
    "rating": 4.2,
    "review_count": 8
  },
  "pages": [],
  "can_edit": true,
  "can_delete": true,
  "can_collaborate": true,
  "usage_in_modules": [
    {
      "id": "module_id_1",
      "title": "Algebra Basics Module",
      "status": "published"
    }
  ],
  "usage_in_courses": [
    {
      "id": "course_id_1",
      "title": "Mathematics Grade 10",
      "status": "published"
    }
  ],
  "published_at": "2025-01-15T12:00:00Z",
  "archived_at": null,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-16T10:30:00Z"
}
```

**Notes:**
- `pages` array ALWAYS empty (pages loaded separately)
- `usage_in_modules` dan `usage_in_courses` only populated if `include_usage=true`
- `subject_name` dan `created_by_name` currently null (TODO: will be populated in future)

**Error Responses:**
- `404`: Lesson not found
- `403`: Not authorized to view this lesson

---

#### 1.4 Update Lesson

**Endpoint:** `PUT /lessons/{lesson_id}`

**Description:** Update lesson metadata. **CANNOT update pages via this endpoint** - use page endpoints instead.

**Request Body:** (All fields optional)
```json
{
  "title": "string (max 200 chars)",
  "description": "string (max 2000 chars)",
  "topic_tags": ["string array"],
  "difficulty_level": "string (easy|medium|hard)",
  "learning_objectives": ["string array"],
  "prerequisites": ["string array"],
  "visibility": "string (public|private|shared)",
  "status": "string (draft|published|archived)"
}
```

**Response:** `200 OK` (same structure as Get Lesson)

**Important Notes:**
- ❌ **CANNOT send `pages` field** - will return 400 error
- ✅ Use `/lessons/{id}/pages` endpoints to manage pages
- Status changes: `draft→published` sets `published_at`, `*→archived` sets `archived_at`

**Error Responses:**
- `400`: Invalid data or attempting to update pages
- `403`: Not authorized to edit this lesson
- `404`: Lesson not found

---

#### 1.5 Delete Lesson

**Endpoint:** `DELETE /lessons/{lesson_id}`

**Description:** Delete lesson and all its pages (cascade delete). Will fail if lesson is used in modules.

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Lesson deleted successfully",
  "lesson_id": "68e417bcfd89bb8eb15f09ad"
}
```

**Error Responses:**
- `400`: Lesson is being used in X modules (cannot delete)
- `403`: Not authorized to delete this lesson (must be creator)
- `404`: Lesson not found

**Cascade Behavior:**
- ✅ All pages deleted automatically
- ✅ Progress data deleted
- ✅ Transaction-safe operation

---

#### 1.6 Get Lesson Library

**Endpoint:** `GET /lessons/library`

**Description:** Get curated collections of lessons (featured, popular, recent).

**Response:** `200 OK`
```json
{
  "featured_lessons": [
    {
      "id": "...",
      "title": "...",
      "description": "...",
      "rating": 4.5,
      "usage_count": 50
    }
  ],
  "recent_lessons": [...],
  "popular_lessons": [...],
  "my_lessons": [...],
  "subjects": [
    {
      "id": "subject_id",
      "name": "Mathematics"
    }
  ],
  "grade_levels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "total_lessons": 156,
  "total_creators": 23
}
```

**Use Cases:**
- Dashboard/home page
- Browse/discovery page
- Quick access to popular content

---

#### 1.7 Get Lesson Usage

**Endpoint:** `GET /lessons/{lesson_id}/usage`

**Description:** Get detailed information about where lesson is being used.

**Response:** `200 OK`
```json
{
  "lesson_id": "68e417bcfd89bb8eb15f09ad",
  "used_in_modules": 2,
  "used_in_courses": 1,
  "modules": [
    {
      "id": "module_id_1",
      "title": "Algebra Basics",
      "status": "published"
    },
    {
      "id": "module_id_2",
      "title": "Advanced Math",
      "status": "draft"
    }
  ],
  "courses": [
    {
      "id": "course_id_1",
      "title": "Mathematics Grade 10",
      "status": "published"
    }
  ]
}
```

**Use Cases:**
- Before deletion: Show warning if lesson is used
- Impact analysis: See where lesson is referenced
- Usage tracking: Monitor lesson adoption

---

### 2. Page Management Operations

#### 2.1 List Lesson Pages

**Endpoint:** `GET /lessons/{lesson_id}/pages`

**Query Parameters:**
```
status_filter=<draft|published|archived> (optional)
summary_only=<true|false>                (optional, default: true)
```

**Description:** Get all pages for a lesson. Default returns summary without full content for performance.

**Response (summary_only=true):** `200 OK`
```json
{
  "lesson_id": "68e417bcfd89bb8eb15f09ad",
  "lesson_title": "Introduction to Algebra",
  "total_pages": 5,
  "pages": [
    {
      "page_number": 1,
      "title": "Introduction",
      "estimated_duration": 15,
      "difficulty_level": "easy",
      "status": "published",
      "has_media": true,
      "has_components": false,
      "media_count": 2,
      "component_count": 0,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    },
    {
      "page_number": 2,
      "title": "Basic Concepts",
      "estimated_duration": 20,
      "difficulty_level": "medium",
      "status": "published",
      "has_media": false,
      "has_components": true,
      "media_count": 0,
      "component_count": 1,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Response (summary_only=false):** Returns full page objects dengan `content_markdown` dan semua details.

**Performance Notes:**
- `summary_only=true`: Fast, lightweight (~5KB per page)
- `summary_only=false`: Slower, full content (~50KB+ per page)
- **Recommendation:** Use summary untuk list views, full untuk editor

---

#### 2.2 Get Single Page

**Endpoint:** `GET /lessons/{lesson_id}/pages/{page_number}`

**Query Parameters:**
```
prefetch_next=<true|false>  (optional, default: false)
```

**Description:** Get single page content dengan navigation info.

**Response:** `200 OK`
```json
{
  "lesson_id": "68e417bcfd89bb8eb15f09ad",
  "lesson_title": "Introduction to Algebra",
  "total_pages": 5,
  "current_page": 2,
  "has_previous": true,
  "has_next": true,
  "previous_page": 1,
  "next_page": 3,
  "page": {
    "id": "page_id_123",
    "lesson_id": "68e417bcfd89bb8eb15f09ad",
    "page_number": 2,
    "title": "Basic Concepts",
    "content_markdown": "# Variables and Constants\n\nA **variable** is...",
    "media_references": [
      {
        "media_key": "img_001",
        "file_name": "variable-diagram.png",
        "file_type": "image",
        "file_size": 245678,
        "url": "https://storage.example.com/...",
        "alt_text": "Variable diagram",
        "duration": null
      }
    ],
    "embedded_components": [
      {
        "component_id": "quiz_001",
        "type": "quiz",
        "position": 1,
        "title": "Variables Quiz",
        "required": true,
        "estimated_duration": 10,
        "data": {
          "quiz_id": "quiz_obj_id",
          "passing_score": 70
        }
      }
    ],
    "estimated_duration": 20,
    "difficulty_level": "medium",
    "learning_objectives": ["Understand variables", "Identify constants"],
    "status": "published",
    "version": 3,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-16T09:00:00Z",
    "published_at": "2025-01-15T12:00:00Z",
    "created_by": "user_id",
    "updated_by": "user_id"
  }
}
```

**Use Cases:**
- Student viewing lesson page by page
- Teacher previewing content
- Sequential navigation

**Performance:** ~5-20KB per page (vs ~250KB+ if loading full lesson)

---

#### 2.3 Get Multiple Pages (Batch)

**Endpoint:** `GET /lessons/{lesson_id}/pages/batch`

**Query Parameters:**
```
page_numbers=<1,2,3>  (required, comma-separated integers)
```

**Description:** Get multiple pages at once for prefetching.

**Response:** `200 OK`
```json
{
  "lesson_id": "68e417bcfd89bb8eb15f09ad",
  "page_numbers": [1, 2, 3],
  "pages": [
    {
      "id": "...",
      "page_number": 1,
      "title": "...",
      "content_markdown": "..."
    },
    {
      "id": "...",
      "page_number": 2,
      "title": "...",
      "content_markdown": "..."
    }
  ]
}
```

**Use Cases:**
- Prefetch next 2-3 pages untuk smooth navigation
- Offline mode preparation
- Preload for sequential reading

**Example:** User on page 1, prefetch pages 2 and 3: `?page_numbers=2,3`

---

#### 2.4 Create Page

**Endpoint:** `POST /lessons/{lesson_id}/pages`

**Description:** Add new page to lesson.

**Request Body:**
```json
{
  "page_number": 1,
  "title": "Introduction",
  "content_markdown": "# Welcome\n\nThis is the first page...",
  "media_references": [
    {
      "media_key": "img_001",
      "file_name": "intro.png",
      "file_type": "image",
      "file_size": 123456,
      "url": "https://storage.example.com/intro.png",
      "alt_text": "Introduction image",
      "duration": null
    }
  ],
  "embedded_components": [
    {
      "component_id": "quiz_001",
      "type": "quiz",
      "position": 1,
      "title": "Quick Quiz",
      "required": true,
      "estimated_duration": 5,
      "data": {
        "quiz_id": "quiz_obj_id",
        "question_count": 5
      }
    }
  ],
  "estimated_duration": 10,
  "difficulty_level": "easy",
  "learning_objectives": ["Understand course structure"],
  "status": "published"
}
```

**Field Requirements:**
- `page_number`: Must be unique, will fail if exists
- `title`: Required, max 200 chars
- `content_markdown`: Required, markdown format
- `media_references`: Optional array
- `embedded_components`: Optional array
- `estimated_duration`: Optional, default 10 minutes
- `difficulty_level`: Optional, default "medium"
- `status`: Optional, default "published"

**Response:** `201 Created`
```json
{
  "id": "page_id_123",
  "lesson_id": "68e417bcfd89bb8eb15f09ad",
  "page_number": 1,
  "title": "Introduction",
  "content_markdown": "# Welcome...",
  "media_references": [...],
  "embedded_components": [...],
  "estimated_duration": 10,
  "difficulty_level": "easy",
  "learning_objectives": ["..."],
  "status": "published",
  "version": 1,
  "created_at": "2025-01-16T10:30:00Z",
  "updated_at": "2025-01-16T10:30:00Z",
  "created_by": "user_id",
  "updated_by": null
}
```

**Side Effects:**
- Lesson metadata automatically updated (total_pages, total_duration, etc.)
- Page number collision will return 400 error

**Error Responses:**
- `400`: Page number already exists, invalid data
- `403`: Not authorized to edit this lesson
- `404`: Lesson not found

---

#### 2.5 Update Page

**Endpoint:** `PUT /lessons/{lesson_id}/pages/{page_number}`

**Description:** Update existing page content.

**Request Body:** (All fields optional)
```json
{
  "title": "Updated Title",
  "content_markdown": "# Updated Content...",
  "media_references": [...],
  "embedded_components": [...],
  "estimated_duration": 15,
  "difficulty_level": "medium",
  "learning_objectives": ["Updated objectives"],
  "status": "published"
}
```

**Response:** `200 OK` (same structure as Create Page)

**Versioning:**
- `version` field auto-incremented when `content_markdown` changes
- Other field changes don't increment version

**Side Effects:**
- Lesson metadata automatically updated
- `updated_at` and `updated_by` fields updated

**Error Responses:**
- `403`: Not authorized to edit
- `404`: Lesson or page not found

---

#### 2.6 Reorder Pages

**Endpoint:** `PUT /lessons/{lesson_id}/pages/reorder`

**Description:** Change page order. **Transaction-safe** to prevent concurrent conflicts.

**Request Body:**
```json
{
  "page_numbers": [3, 1, 2, 4, 5]
}
```

**Explanation:**
- Array represents new order
- Example: `[3, 1, 2, 4, 5]` means:
  - Old page 3 → New position 1
  - Old page 1 → New position 2
  - Old page 2 → New position 3
  - Old page 4 → New position 4
  - Old page 5 → New position 5

**Validation:**
- Array length must equal total pages
- Must be permutation of 1 to N (no duplicates, no missing numbers)

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Pages reordered successfully",
  "new_order": [3, 1, 2, 4, 5]
}
```

**Technical Implementation:**
Uses MongoDB transaction dengan two-phase commit:
1. Set all page_numbers to negative (avoid collisions)
2. Update to new page_numbers atomically

**Error Responses:**
- `400`: Invalid order (wrong count, duplicates, missing numbers)
- `403`: Not authorized
- `404`: Lesson not found

---

#### 2.7 Delete Page

**Endpoint:** `DELETE /lessons/{lesson_id}/pages/{page_number}`

**Description:** Delete page and auto-renumber remaining pages.

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Page 2 deleted successfully"
}
```

**Side Effects:**
- Remaining pages automatically renumbered (sequential from 1)
- Example: Delete page 2 dari [1,2,3,4,5] → Result [1,2,3,4]
- Lesson metadata updated

**Error Responses:**
- `403`: Not authorized
- `404`: Lesson or page not found

---

### 3. Additional Endpoints

#### 3.1 Get Lesson Analytics

**Endpoint:** `GET /lessons/{lesson_id}/analytics`

**Description:** Get detailed analytics and performance metrics.

**Response:** `200 OK`
```json
{
  "lesson_id": "68e417bcfd89bb8eb15f09ad",
  "total_views": 1234,
  "unique_students": 89,
  "times_used_in_modules": 5,
  "average_completion_time": 65.5,
  "completion_rate": 78.3,
  "average_score": 82.5,
  "component_performance": {
    "quiz_001": 85.2,
    "assignment_001": 78.9
  },
  "difficulty_feedback": {
    "too_easy": 5,
    "just_right": 45,
    "too_hard": 12
  },
  "page_views": [
    {
      "page_number": 1,
      "views": 120
    }
  ],
  "drop_off_points": [
    {
      "page_number": 3,
      "drop_off_rate": 15.2
    }
  ],
  "most_popular_components": [],
  "peak_usage_hours": [14, 15, 16],
  "usage_by_day": {},
  "student_ratings": [4, 5, 3, 5, 4],
  "teacher_reviews": []
}
```

**Authorization:** Only creator, collaborators, atau admin

**Use Cases:**
- Teacher dashboard
- Content improvement insights
- Performance tracking

---

## Data Models

### Lesson Model

```typescript
interface Lesson {
  id: string;                           // MongoDB ObjectId
  title: string;                        // Max 200 chars
  description: string;                  // Max 2000 chars
  slug: string | null;                  // Auto-generated URL-friendly
  subject_id: string;                   // Foreign key to subjects
  subject_name: string | null;          // Populated (currently null)
  grade_level: number;                  // 1-12
  topic_tags: string[];                 // Array of tags
  difficulty_level: "easy" | "medium" | "hard";
  learning_objectives: string[];
  prerequisites: string[];
  visibility: "public" | "private" | "shared";
  status: "draft" | "published" | "archived";
  created_by: string;                   // User ID
  created_by_name: string | null;       // Populated (currently null)
  collaborators: string[];              // Array of user IDs
  metadata: LessonMetadata;
  pages: [];                            // Always empty (deprecated field)
  can_edit: boolean;                    // Permission flag
  can_delete: boolean;                  // Permission flag
  can_collaborate: boolean;             // Permission flag
  usage_in_modules: Module[] | null;   // Only if include_usage=true
  usage_in_courses: Course[] | null;   // Only if include_usage=true
  published_at: string | null;          // ISO datetime
  archived_at: string | null;           // ISO datetime
  created_at: string;                   // ISO datetime
  updated_at: string;                   // ISO datetime
}
```

### Lesson Metadata

```typescript
interface LessonMetadata {
  total_pages: number;                  // Auto-calculated
  total_duration: number;               // Minutes, auto-calculated
  total_components: number;             // Auto-calculated
  total_media: number;                  // Auto-calculated
  component_breakdown: Record<string, number>;  // By type
  media_breakdown: Record<string, number>;      // By type
  difficulty_distribution: Record<string, number>; // By difficulty
  usage_count: number;                  // Times used in modules
  average_completion_time: number | null;
  completion_rate: number;              // 0-100
  rating: number;                       // 0-5
  review_count: number;
  calculated_at: string;                // ISO datetime
}
```

### Page Model

```typescript
interface Page {
  id: string;                           // MongoDB ObjectId
  lesson_id: string;                    // Foreign key
  page_number: number;                  // Sequential, starts at 1
  title: string;                        // Max 200 chars
  content_markdown: string;             // Markdown format
  media_references: MediaReference[];
  embedded_components: EmbeddedComponent[];
  estimated_duration: number;           // Minutes
  difficulty_level: "easy" | "medium" | "hard";
  learning_objectives: string[];
  status: "draft" | "published" | "archived";
  version: number;                      // Auto-incremented on content change
  created_at: string;                   // ISO datetime
  updated_at: string;                   // ISO datetime
  published_at: string | null;
  created_by: string | null;            // User ID
  updated_by: string | null;            // User ID
}
```

### Media Reference

```typescript
interface MediaReference {
  media_key: string;                    // Unique key for content reference
  file_name: string;                    // Original filename
  file_type: "image" | "video" | "audio" | "document";
  file_size: number;                    // Bytes
  url: string;                          // Full URL to file
  alt_text: string | null;              // For accessibility
  duration: number | null;              // Seconds (for video/audio)
}
```

### Embedded Component

```typescript
interface EmbeddedComponent {
  component_id: string;                 // Unique identifier
  type: "quiz" | "assignment" | "interactive" | "survey" | "reflection" | "discussion";
  position: number;                     // Position in content
  title: string;
  required: boolean;                    // Required for completion
  estimated_duration: number;           // Minutes
  data: Record<string, any>;           // Component-specific config
}
```

---

## UI/UX Implementation Patterns

**Important:** Ini adalah **saran optional**. Frontend team bebas implement dengan approach apapun yang paling comfortable dan sesuai dengan design system mereka.

### Pattern A: Multi-Step Wizard (Recommended)

**Suggested User Flow:**
1. Step 1: Basic lesson info form → `POST /lessons` (status: draft)
2. Step 2: Add pages iteratively → `POST /lessons/{id}/pages`
3. Step 3: Review & reorder → `GET /lessons/{id}/pages`, `PUT /lessons/{id}/pages/reorder`
4. Step 4: Publish → `PUT /lessons/{id}` (status: published)

**Technical Requirements:**
- State management (Redux, Zustand, Context, etc.)
- Form handling dengan validation
- Draft auto-save mechanism
- Progress persistence (localStorage atau backend)

**Advantages:**
- ✅ Guided experience
- ✅ Can save progress
- ✅ Less overwhelming
- ✅ Good for first-time users

**Disadvantages:**
- ❌ More complex state management
- ❌ Longer user flow

---

### Pattern B: Create-Then-Manage (Alternative)

**Suggested User Flow:**
1. Quick create form → `POST /lessons` (basic info only)
2. Redirect to detail/manage page
3. Add/edit pages from manage interface

**Technical Requirements:**
- Single-page application routing
- Modal atau sidebar-based page editor
- Inline editing capabilities
- Drag-and-drop for reordering

**Advantages:**
- ✅ Faster initial creation
- ✅ Simpler state management
- ✅ Direct manipulation
- ✅ Good for experienced users

**Disadvantages:**
- ❌ Can be overwhelming
- ❌ Less guided

---

### Pattern C: Hybrid Approach (Most Flexible)

Combine both patterns:
- New users → Wizard flow
- Existing lessons → Direct management
- Quick create option for experienced users

**Implementation Suggestions:**
- Two entry points: "Create with Wizard" vs "Quick Create"
- User preference setting
- Context-aware UI (show wizard for empty lessons)

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Common HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 400 | Bad Request | Validation error, invalid data |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | No permission for action |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Backend error |

### Error Handling Recommendations

**Client-Side Validation:**
- Validate required fields before API call
- Check field lengths (title max 200, description max 2000)
- Validate enum values (status, visibility, difficulty)
- Validate page_number uniqueness

**User-Friendly Error Messages:**
```
Backend: "Subject not found"
Frontend: "The selected subject is no longer available. Please choose another."

Backend: "Not authorized to edit this lesson"
Frontend: "You don't have permission to edit this lesson. Contact the lesson creator to request access."

Backend: "Cannot delete lesson. It is being used in 3 modules."
Frontend: "This lesson is used in 3 modules. Remove it from those modules before deleting."
```

**Retry Logic:**
- Implement exponential backoff for 500 errors
- Don't retry 400/403/404 errors
- Show retry option to user

**Offline Handling:**
- Queue API calls saat offline
- Sync when connection restored
- Show offline indicator

---

## Best Practices

### 1. Performance Optimization

**Pagination:**
```
Always use pagination for lists
Recommended per_page: 20-50
Max per_page: 100
```

**Lazy Loading:**
```
Use summary_only=true untuk list views
Load full content only when needed
Implement infinite scroll atau load more
```

**Prefetching:**
```
Prefetch next page saat user baca current page
Use batch endpoint untuk multiple pages
Cache frequently accessed data
```

**Image Optimization:**
```
Lazy load images in markdown content
Use progressive JPEGs
Implement responsive images
```

### 2. State Management

**Recommendations:**
- Use global state untuk current lesson being edited
- Local state untuk form inputs
- Cache lesson list dengan timestamp
- Invalidate cache on mutations

**Optimistic Updates:**
```
Update UI immediately (optimistic)
Send API request
Rollback if error
Show success/error feedback
```

### 3. Content Editing

**Markdown Editor:**
- Implement live preview
- Support toolbar untuk common formatting
- Auto-save drafts every N seconds
- Warn before navigate away dengan unsaved changes

**Media Upload:**
- Show upload progress
- Validate file types dan sizes client-side
- Generate thumbnails untuk images
- Store media URLs in media_references array

**Component Embedding:**
- Visual picker untuk component types
- Inline preview of embedded components
- Drag-and-drop positioning
- Validate component data before save

### 4. Permission Handling

**Check Permissions Before Actions:**
```
if (lesson.can_edit) {
  // Show edit button
}

if (lesson.can_delete) {
  // Show delete button
}
```

**Hide vs Disable:**
- Hide actions user definitely can't do
- Disable actions user might be able to do (with explanation)
- Show permission upgrade options if applicable

### 5. User Experience

**Loading States:**
- Skeleton screens untuk content loading
- Spinners untuk actions
- Progress bars untuk uploads
- Disable buttons during API calls

**Feedback:**
- Toast notifications untuk success/error
- Inline validation messages
- Confirmation dialogs untuk destructive actions
- Undo option untuk accidental actions (jika possible)

**Navigation:**
- Breadcrumbs untuk context
- Back button behavior
- Deep linking support
- Save scroll position

---

## Common Workflows

### Workflow 1: Create New Lesson with Pages

```
1. POST /lessons
   - Send lesson metadata only (NO pages)
   - Receive lesson_id
   
   Example:
   {
     "title": "Introduction to Algebra",
     "description": "...",
     "subject_id": "...",
     "grade_level": 10,
     "status": "draft"
   }

2. POST /lessons/{lesson_id}/pages (for each page)
   - Create pages one by one
   - Pages auto-numbered sequentially
   
   Example:
   {
     "page_number": 1,
     "title": "Page 1",
     "content_markdown": "# Content here..."
   }

3. GET /lessons/{lesson_id}/pages?summary_only=true
   - Review all pages
   - Verify order

4. Optional: PUT /lessons/{lesson_id}/pages/reorder
   - Reorder if needed

5. PUT /lessons/{lesson_id}
   - Change status to "published"
   - Change visibility to "public" (if desired)
   
   Example:
   {
     "status": "published",
     "visibility": "public"
   }

6. Navigate to lesson detail atau list
```

### Workflow 2: Edit Existing Lesson

```
1. GET /lessons/{lesson_id}
   - Load lesson metadata
   - Check can_edit permission

2. GET /lessons/{lesson_id}/pages
   - Load all pages (summary)

3. To edit page:
   GET /lessons/{lesson_id}/pages/{page_number}
   - Load full page content
   
   PUT /lessons/{lesson_id}/pages/{page_number}
   - Update page content

4. To add new page:
   POST /lessons/{lesson_id}/pages
   - With appropriate page_number

5. To delete page:
   DELETE /lessons/{lesson_id}/pages/{page_number}
   - Remaining pages auto-renumber

6. To update lesson metadata:
   PUT /lessons/{lesson_id}
   - Update title, description, etc.
```

### Workflow 3: Student Views Lesson

```
1. GET /lessons
   - List available lessons (filtered by permission)

2. User selects lesson
   GET /lessons/{lesson_id}
   - Load lesson metadata
   - Check can_view permission

3. GET /lessons/{lesson_id}/pages/{page_number}
   - Start with page 1
   - Use navigation info for prev/next

4. Optional: GET /lessons/{lesson_id}/pages/batch?page_numbers=2,3
   - Prefetch next pages for smooth navigation

5. Track progress (separate progress tracking API)
```

### Workflow 4: Check Before Delete

```
1. User clicks delete button

2. GET /lessons/{lesson_id}/usage
   - Check if lesson is used anywhere

3. If used_in_modules > 0:
   - Show warning modal dengan list
   - Prevent deletion
   - Show option to remove from modules first

4. If used_in_modules === 0:
   - Show confirmation dialog
   - "Are you sure? This will delete X pages."

5. If confirmed:
   DELETE /lessons/{lesson_id}
   - Cascade deletes all pages
   - Remove from list/navigate away
```

### Workflow 5: Reorder Pages

```
1. GET /lessons/{lesson_id}/pages?summary_only=true
   - Load page list

2. Implement drag-and-drop interface
   - Reorder pages in UI
   - Track new order in state

3. PUT /lessons/{lesson_id}/pages/reorder
   - Send new order array
   - Wait for confirmation

4. On success:
   - Show success feedback
   - Update UI to reflect new order

5. On error:
   - Rollback UI to previous order
   - Show error message
   - Allow retry
```

---

## Additional Notes

### Metadata Fields Currently NULL

These fields are marked for future implementation:
- `subject_name`: Will be populated via lookup join
- `created_by_name`: Will be populated via user lookup

**Current Workaround:** Frontend can fetch separately jika needed atau wait for backend update.

### Favorites Feature

`is_favorited` field exists di response tapi currently always `false`. Feature belum implemented.

**Future Implementation:**
```
POST /lessons/{lesson_id}/favorite    (add to favorites)
DELETE /lessons/{lesson_id}/favorite  (remove from favorites)
GET /lessons/favorites                (list user's favorites)
```

### Collaboration Feature

`collaborators` array exists dan functional tapi no dedicated endpoints yet untuk manage collaborators.

**Future Implementation:**
```
POST /lessons/{lesson_id}/collaborators
DELETE /lessons/{lesson_id}/collaborators/{user_id}
GET /lessons/{lesson_id}/collaborators
```

### Page Versioning

Pages have `version` field yang auto-increments on content changes. Currently tidak ada version history atau rollback feature.

**Future Implementation:**
```
GET /lessons/{lesson_id}/pages/{page_number}/history
POST /lessons/{lesson_id}/pages/{page_number}/restore/{version}
```

---

## Support & Questions

### Technical Support

Jika ada pertanyaan atau menemukan issues:
1. Check error response details
2. Verify authentication token
3. Validate request payload against schema
4. Check permission requirements
5. Review this documentation

### API Changes

API ini stable tapi might evolve. Breaking changes akan dikomunikasikan melalui:
- Version bumps (v1 → v2)
- Deprecation notices
- Migration guides

### Feedback

Frontend team feedback sangat appreciated:
- Missing endpoints atau features
- Response format issues
- Performance concerns
- UX/DX improvements

---

## Version History

### v2.0 (2025-01-16)
- ✅ Separated pages architecture implemented
- ✅ Permission system fixed (can_edit, can_delete)
- ✅ Transaction-safe page reordering
- ✅ Cascade delete implemented
- ✅ Subject validation added
- ✅ Usage tracking enhanced

### v1.0 (Initial)
- Basic CRUD operations
- Embedded pages architecture (deprecated)

---

**End of Documentation**

For the latest updates, refer to: `/docs/FIXES_APPLIED_LESSON_LMS.md` and `/docs/PERMISSION_FIX.md`
