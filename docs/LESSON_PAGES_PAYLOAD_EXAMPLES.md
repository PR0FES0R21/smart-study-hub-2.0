# Lesson Pages API - Payload Examples

**Complete Request/Response Examples for All Page Operations**

**Base URL:** `http://localhost:8000/api/v1`  
**Auth Required:** Yes (Bearer token in header)

---

## 📋 Table of Contents

1. [List Pages](#1-list-pages)
2. [Create Page](#2-create-page)
3. [Get Single Page](#3-get-single-page)
4. [Update Page](#4-update-page)
5. [Delete Page](#5-delete-page)
6. [Reorder Pages](#6-reorder-pages)
7. [Batch Get Pages](#7-batch-get-pages)

---

## 1. List Pages

### **GET /lessons/{lesson_id}/pages**

**Purpose:** Get list of all pages for a lesson

### Request Examples:

#### A. Summary Only (Default - Fast)
```http
GET /api/v1/lessons/68f0c913a46aa759e854c381/pages?summary_only=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### B. Full Content (Slower)
```http
GET /api/v1/lessons/68f0c913a46aa759e854c381/pages?summary_only=false
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### C. Filter by Status
```http
GET /api/v1/lessons/68f0c913a46aa759e854c381/pages?status_filter=published
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response Example (Summary):

```json
{
  "lesson_id": "68f0c913a46aa759e854c381",
  "lesson_title": "Introduction to Python Programming",
  "total_pages": 5,
  "pages": [
    {
      "page_number": 1,
      "title": "Welcome to Python",
      "estimated_duration": 15,
      "difficulty_level": "easy",
      "status": "published",
      "has_media": true,
      "has_components": false,
      "media_count": 2,
      "component_count": 0
    },
    {
      "page_number": 2,
      "title": "Variables and Data Types",
      "estimated_duration": 20,
      "difficulty_level": "medium",
      "status": "published",
      "has_media": false,
      "has_components": true,
      "media_count": 0,
      "component_count": 1
    }
  ]
}
```

---

## 2. Create Page

### **POST /lessons/{lesson_id}/pages**

**Purpose:** Add new page to lesson

### Request Example (Minimal):

```http
POST /api/v1/lessons/68f0c913a46aa759e854c381/pages
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "page_number": 1,
  "title": "Introduction to Python",
  "content_markdown": "# Welcome to Python\n\nPython is a versatile programming language..."
}
```

### Request Example (Full - With Media & Components):

```http
POST /api/v1/lessons/68f0c913a46aa759e854c381/pages
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "page_number": 2,
  "title": "Variables and Data Types",
  "content_markdown": "# Variables in Python\n\n## What is a Variable?\n\nA variable is a container for storing data...\n\n![Python Variables](media:img_variables)\n\nTry the interactive quiz below!",
  "media_references": [
    {
      "media_key": "img_variables",
      "file_name": "python-variables.png",
      "file_type": "image",
      "file_size": 245678,
      "url": "https://storage.example.com/media/python-variables.png",
      "alt_text": "Diagram showing Python variable assignment"
    },
    {
      "media_key": "video_intro",
      "file_name": "variables-intro.mp4",
      "file_type": "video",
      "file_size": 5242880,
      "url": "https://storage.example.com/media/variables-intro.mp4",
      "alt_text": "Introduction to Python variables",
      "duration": 180
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
        "quiz_id": "68f123abc456def789012345",
        "passing_score": 70,
        "max_attempts": 3
      }
    }
  ],
  "estimated_duration": 25,
  "difficulty_level": "medium",
  "learning_objectives": [
    "Understand what variables are",
    "Learn how to declare variables in Python",
    "Practice variable naming conventions"
  ],
  "status": "published"
}
```

### Response Example:

```json
{
  "id": "68f0c999a46aa759e854c388",
  "lesson_id": "68f0c913a46aa759e854c381",
  "page_number": 2,
  "title": "Variables and Data Types",
  "content_markdown": "# Variables in Python\n\n## What is a Variable?...",
  "media_references": [
    {
      "media_key": "img_variables",
      "file_name": "python-variables.png",
      "file_type": "image",
      "file_size": 245678,
      "url": "https://storage.example.com/media/python-variables.png",
      "alt_text": "Diagram showing Python variable assignment",
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
        "quiz_id": "68f123abc456def789012345",
        "passing_score": 70,
        "max_attempts": 3
      }
    }
  ],
  "estimated_duration": 25,
  "difficulty_level": "medium",
  "learning_objectives": [
    "Understand what variables are",
    "Learn how to declare variables in Python",
    "Practice variable naming conventions"
  ],
  "status": "published",
  "version": 1,
  "created_at": "2025-01-16T10:30:00.000Z",
  "updated_at": "2025-01-16T10:30:00.000Z",
  "created_by": "68822f07979cbba23e6db950",
  "updated_by": null
}
```

**Status:** `201 Created`

---

## 3. Get Single Page

### **GET /lessons/{lesson_id}/pages/{page_number}**

**Purpose:** Get full content of specific page

### Request Example:

```http
GET /api/v1/lessons/68f0c913a46aa759e854c381/pages/2
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response Example:

```json
{
  "lesson_id": "68f0c913a46aa759e854c381",
  "lesson_title": "Introduction to Python Programming",
  "total_pages": 5,
  "current_page": 2,
  "has_previous": true,
  "has_next": true,
  "previous_page": 1,
  "next_page": 3,
  "page": {
    "id": "68f0c999a46aa759e854c388",
    "lesson_id": "68f0c913a46aa759e854c381",
    "page_number": 2,
    "title": "Variables and Data Types",
    "content_markdown": "# Variables in Python\n\n## What is a Variable?\n\nA variable is a container...",
    "media_references": [
      {
        "media_key": "img_variables",
        "file_name": "python-variables.png",
        "file_type": "image",
        "file_size": 245678,
        "url": "https://storage.example.com/media/python-variables.png",
        "alt_text": "Diagram showing Python variable assignment",
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
          "quiz_id": "68f123abc456def789012345",
          "passing_score": 70,
          "max_attempts": 3
        }
      }
    ],
    "estimated_duration": 25,
    "difficulty_level": "medium",
    "learning_objectives": [
      "Understand what variables are",
      "Learn how to declare variables in Python"
    ],
    "status": "published",
    "version": 1,
    "created_at": "2025-01-16T10:30:00.000Z",
    "updated_at": "2025-01-16T10:30:00.000Z",
    "created_by": "68822f07979cbba23e6db950",
    "updated_by": null
  }
}
```

**Status:** `200 OK`

---

## 4. Update Page

### **PUT /lessons/{lesson_id}/pages/{page_number}**

**Purpose:** Update existing page content

### Request Example (Partial Update):

```http
PUT /api/v1/lessons/68f0c913a46aa759e854c381/pages/2
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Variables and Data Types - Updated",
  "content_markdown": "# Variables in Python (Updated)\n\nNew content here..."
}
```

### Request Example (Full Update):

```http
PUT /api/v1/lessons/68f0c913a46aa759e854c381/pages/2
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Variables and Data Types - Revised",
  "content_markdown": "# Variables in Python\n\nCompletely revised content...",
  "media_references": [
    {
      "media_key": "img_new",
      "file_name": "new-diagram.png",
      "file_type": "image",
      "file_size": 156789,
      "url": "https://storage.example.com/media/new-diagram.png",
      "alt_text": "Updated diagram"
    }
  ],
  "embedded_components": [],
  "estimated_duration": 30,
  "difficulty_level": "hard",
  "learning_objectives": [
    "Master variable concepts",
    "Apply best practices"
  ],
  "status": "published"
}
```

### Response Example:

```json
{
  "id": "68f0c999a46aa759e854c388",
  "lesson_id": "68f0c913a46aa759e854c381",
  "page_number": 2,
  "title": "Variables and Data Types - Revised",
  "content_markdown": "# Variables in Python\n\nCompletely revised content...",
  "media_references": [
    {
      "media_key": "img_new",
      "file_name": "new-diagram.png",
      "file_type": "image",
      "file_size": 156789,
      "url": "https://storage.example.com/media/new-diagram.png",
      "alt_text": "Updated diagram",
      "duration": null
    }
  ],
  "embedded_components": [],
  "estimated_duration": 30,
  "difficulty_level": "hard",
  "learning_objectives": [
    "Master variable concepts",
    "Apply best practices"
  ],
  "status": "published",
  "version": 2,
  "created_at": "2025-01-16T10:30:00.000Z",
  "updated_at": "2025-01-16T11:45:00.000Z",
  "created_by": "68822f07979cbba23e6db950",
  "updated_by": "68822f07979cbba23e6db950"
}
```

**Status:** `200 OK`

**Note:** `version` field incremented from 1 to 2

---

## 5. Delete Page

### **DELETE /lessons/{lesson_id}/pages/{page_number}**

**Purpose:** Delete a page (remaining pages auto-renumber)

### Request Example:

```http
DELETE /api/v1/lessons/68f0c913a46aa759e854c381/pages/3
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response Example:

```json
{
  "message": "Page 3 deleted successfully",
  "lesson_id": "68f0c913a46aa759e854c381",
  "deleted_page_number": 3,
  "remaining_pages": 4
}
```

**Status:** `200 OK`

**Important:** Pages after deleted page are automatically renumbered:
- Before: [1, 2, 3, 4, 5]
- Delete page 3
- After: [1, 2, 3, 4] (old page 4 becomes 3, old page 5 becomes 4)

---

## 6. Reorder Pages

### **PUT /lessons/{lesson_id}/pages/reorder**

**Purpose:** Change the order of pages

### Request Example:

```http
PUT /api/v1/lessons/68f0c913a46aa759e854c381/pages/reorder
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "page_numbers": [3, 1, 2, 5, 4]
}
```

**Explanation:**
- Current order: [1, 2, 3, 4, 5]
- New order: [3, 1, 2, 5, 4]
- Page 3 becomes page 1
- Page 1 becomes page 2
- Page 2 becomes page 3
- Page 5 becomes page 4
- Page 4 becomes page 5

### Response Example:

```json
{
  "message": "Pages reordered successfully",
  "lesson_id": "68f0c913a46aa759e854c381",
  "total_pages": 5,
  "new_order": [3, 1, 2, 5, 4]
}
```

**Status:** `200 OK`

### Validation Rules:

```json
// ❌ INVALID - Duplicate numbers
{
  "page_numbers": [1, 2, 2, 3, 4]  // Error: duplicates not allowed
}

// ❌ INVALID - Missing pages
{
  "page_numbers": [1, 2, 4, 5]  // Error: must include all pages
}

// ❌ INVALID - Wrong count
{
  "page_numbers": [1, 2, 3]  // Error: lesson has 5 pages, not 3
}

// ✅ VALID
{
  "page_numbers": [5, 4, 3, 2, 1]  // Reverse order - OK
}
```

---

## 7. Batch Get Pages

### **GET /lessons/{lesson_id}/pages/batch**

**Purpose:** Get multiple pages in one request (prefetching)

### Request Example:

```http
GET /api/v1/lessons/68f0c913a46aa759e854c381/pages/batch?page_numbers=1,2,3
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response Example:

```json
{
  "lesson_id": "68f0c913a46aa759e854c381",
  "lesson_title": "Introduction to Python Programming",
  "total_pages": 5,
  "requested_pages": [1, 2, 3],
  "pages": [
    {
      "id": "68f0c999a46aa759e854c387",
      "page_number": 1,
      "title": "Welcome to Python",
      "content_markdown": "# Welcome...",
      "media_references": [],
      "embedded_components": [],
      "estimated_duration": 15,
      "difficulty_level": "easy",
      "status": "published",
      "version": 1,
      "created_at": "2025-01-16T10:00:00.000Z",
      "updated_at": "2025-01-16T10:00:00.000Z"
    },
    {
      "id": "68f0c999a46aa759e854c388",
      "page_number": 2,
      "title": "Variables and Data Types",
      "content_markdown": "# Variables...",
      "media_references": [],
      "embedded_components": [],
      "estimated_duration": 20,
      "difficulty_level": "medium",
      "status": "published",
      "version": 1,
      "created_at": "2025-01-16T10:15:00.000Z",
      "updated_at": "2025-01-16T10:15:00.000Z"
    },
    {
      "id": "68f0c999a46aa759e854c389",
      "page_number": 3,
      "title": "Control Flow",
      "content_markdown": "# If-Else...",
      "media_references": [],
      "embedded_components": [],
      "estimated_duration": 25,
      "difficulty_level": "medium",
      "status": "published",
      "version": 1,
      "created_at": "2025-01-16T10:30:00.000Z",
      "updated_at": "2025-01-16T10:30:00.000Z"
    }
  ]
}
```

**Status:** `200 OK`

**Use Case:** Prefetch next 2-3 pages for smooth navigation

---

## 📝 Field Descriptions

### Page Fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page_number` | integer | ✅ Yes | Page number (must be unique per lesson) |
| `title` | string | ✅ Yes | Page title (max 200 chars) |
| `content_markdown` | string | ❌ No | Page content in markdown format |
| `media_references` | array | ❌ No | Array of media files used in page |
| `embedded_components` | array | ❌ No | Array of interactive components (quiz, assignment, etc) |
| `estimated_duration` | integer | ❌ No | Reading/completion time in minutes (default: 10) |
| `difficulty_level` | string | ❌ No | `easy` \| `medium` \| `hard` (default: medium) |
| `learning_objectives` | array | ❌ No | Array of learning objectives for this page |
| `status` | string | ❌ No | `draft` \| `published` \| `archived` (default: published) |

### Media Reference Fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `media_key` | string | ✅ Yes | Unique key to reference in markdown (e.g., `![Alt](media:key)`) |
| `file_name` | string | ✅ Yes | Original file name |
| `file_type` | string | ✅ Yes | `image` \| `video` \| `audio` \| `document` |
| `file_size` | integer | ✅ Yes | File size in bytes |
| `url` | string | ✅ Yes | Full URL to media file |
| `alt_text` | string | ❌ No | Alt text for accessibility |
| `duration` | integer | ❌ No | Duration in seconds (for video/audio) |

### Embedded Component Fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `component_id` | string | ✅ Yes | Unique component identifier |
| `type` | string | ✅ Yes | `quiz` \| `assignment` \| `interactive` \| `survey` \| `reflection` \| `discussion` |
| `position` | integer | ✅ Yes | Position in page content |
| `title` | string | ✅ Yes | Component title |
| `required` | boolean | ❌ No | Is completion required? (default: true) |
| `estimated_duration` | integer | ❌ No | Completion time in minutes (default: 10) |
| `data` | object | ✅ Yes | Component-specific configuration |

---

## 🚀 Quick Start Examples

### Example 1: Create Lesson with 3 Pages

```javascript
// Step 1: Create lesson
const lesson = await fetch('/api/v1/lessons', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: "Python Basics",
    description: "Learn Python fundamentals",
    subject_id: "68b328329be3ef2464823bff",
    grade_level: 10
  })
}).then(r => r.json());

// Step 2: Create pages
const pages = [
  {
    page_number: 1,
    title: "Introduction",
    content_markdown: "# Welcome to Python\n\nLet's get started..."
  },
  {
    page_number: 2,
    title: "Variables",
    content_markdown: "# Variables\n\nVariables store data..."
  },
  {
    page_number: 3,
    title: "Functions",
    content_markdown: "# Functions\n\nFunctions are reusable..."
  }
];

for (const page of pages) {
  await fetch(`/api/v1/lessons/${lesson.id}/pages`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(page)
  });
}

// Step 3: Publish
await fetch(`/api/v1/lessons/${lesson.id}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ status: "published" })
});
```

### Example 2: Update Page Content

```javascript
// Update page 2
await fetch('/api/v1/lessons/68f0c913a46aa759e854c381/pages/2', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: "Variables - Updated",
    content_markdown: "# Variables in Python\n\nNew improved content..."
  })
});
```

### Example 3: Reorder Pages

```javascript
// Move page 3 to be first
await fetch('/api/v1/lessons/68f0c913a46aa759e854c381/pages/reorder', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    page_numbers: [3, 1, 2, 4, 5]  // New order
  })
});
```

---

## ⚠️ Common Errors

### 1. Page Number Already Exists

**Request:**
```json
POST /lessons/68f0c913a46aa759e854c381/pages
{
  "page_number": 2,
  "title": "Duplicate Page"
}
```

**Response:** `400 Bad Request`
```json
{
  "detail": "Page 2 already exists for this lesson"
}
```

**Solution:** Use different page number or update existing page

### 2. Invalid Difficulty Level

**Request:**
```json
{
  "difficulty_level": "extreme"
}
```

**Response:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "loc": ["body", "difficulty_level"],
      "msg": "Difficulty must be one of ['easy', 'medium', 'hard']",
      "type": "value_error"
    }
  ]
}
```

### 3. Missing Required Fields

**Request:**
```json
{
  "title": "Missing Page Number"
}
```

**Response:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "loc": ["body", "page_number"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 4. Unauthorized

**Request:**
```http
POST /lessons/68f0c913a46aa759e854c381/pages
// No Authorization header
```

**Response:** `401 Unauthorized`
```json
{
  "detail": "Not authenticated"
}
```

### 5. Forbidden (Not Lesson Owner)

**Request:**
```http
POST /lessons/68f0c913a46aa759e854c381/pages
Authorization: Bearer <other_user_token>
```

**Response:** `403 Forbidden`
```json
{
  "detail": "You don't have permission to edit this lesson"
}
```

---

## 📚 Related Documentation

- **API Guide:** `docs/FRONTEND_LESSON_API_GUIDE.md`
- **Breaking Changes:** `docs/BREAKING_CHANGE_STRICT_SEPARATION.md`
- **ObjectId Fix:** `docs/FIX_LESSON_PAGE_OBJECTID_ERROR.md`

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Status:** Complete & Ready to Use
