# 📚 **Frontend Guide: Lesson Pages API (NEW)**

## 🎯 **OVERVIEW**

Sistem lesson telah diubah dari **embedded pages** menjadi **separated pages** untuk performa yang lebih baik.

### **Perubahan Utama:**

**SEBELUM (Old System - DEPRECATED):**
```typescript
// ❌ OLD: Load seluruh lesson + semua pages (250KB+)
GET /api/v1/lessons/{id}
→ Response: { id, title, pages: [...50 pages...] } // HEAVY!
```

**SEKARANG (New System - RECOMMENDED):**
```typescript
// ✅ NEW: Load metadata dulu (2KB), pages on-demand (5KB/page)
GET /api/v1/lessons/{id}                    // Metadata only
GET /api/v1/lessons/{id}/pages/{number}     // Single page
```

**Performance Improvement: 98% faster!** ⚡

---

## 📊 **ARCHITECTURE CHANGES**

### **Database Structure:**

**OLD:**
```javascript
// lessons collection (HEAVY)
{
  "_id": "lesson_123",
  "title": "Python Basics",
  "pages": [
    { page_number: 1, content_markdown: "...", ... },  // 5KB
    { page_number: 2, content_markdown: "...", ... },  // 5KB
    ... // 48 more pages = 250KB total!
  ]
}
```

**NEW:**
```javascript
// lessons collection (LIGHTWEIGHT)
{
  "_id": "lesson_123",
  "title": "Python Basics",
  "metadata": {
    "total_pages": 50,
    "total_duration": 300
  }
  // NO pages field! Separated!
}

// lesson_pages collection (SEPARATE)
{ "_id": "page_001", "lesson_id": "lesson_123", "page_number": 1, "content_markdown": "...", ... }
{ "_id": "page_002", "lesson_id": "lesson_123", "page_number": 2, "content_markdown": "...", ... }
...
```

---

## 🚀 **NEW API ENDPOINTS**

### **Summary Table:**

| Endpoint | Method | Purpose | Response Size |
|----------|--------|---------|---------------|
| `/lessons/{id}` | GET | Get lesson metadata | ~2KB |
| `/lessons/{id}/pages` | GET | List all pages (summary) | ~5KB |
| `/lessons/{id}/pages/{num}` | GET | Get single page | ~5-20KB |
| `/lessons/{id}/pages/batch` | GET | Get multiple pages | ~15-60KB |
| `/lessons/{id}/pages` | POST | Create new page | ~5KB |
| `/lessons/{id}/pages/{num}` | PUT | Update page | ~5KB |
| `/lessons/{id}/pages/reorder` | PUT | Reorder pages | ~1KB |
| `/lessons/{id}/pages/{num}` | DELETE | Delete page | ~1KB |

---

## 📖 **ENDPOINT DOCUMENTATION**

### **1. GET /lessons/{lesson_id}**

**Purpose:** Get lesson metadata (tanpa pages content)

**Request:**
```http
GET /api/v1/lessons/68e4567abc1234567890def
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": "68e4567abc1234567890def",
  "title": "Pemrograman Python Dasar",
  "description": "Belajar Python dari nol hingga mahir",
  "slug": "pemrograman-python-dasar",
  "subject_id": "68862590fdf3763352cda2b4",
  "grade_level": 10,
  "topic_tags": ["python", "programming", "basics"],
  "difficulty_level": "medium",
  "learning_objectives": [
    "Memahami syntax Python",
    "Membuat program sederhana"
  ],
  "prerequisites": ["Logika pemrograman dasar"],
  "visibility": "public",
  "created_by": "teacher_001",
  "collaborators": [],
  "metadata": {
    "total_pages": 15,
    "total_duration": 180,
    "total_components": 5,
    "total_media": 8,
    "calculated_at": "2025-01-07T10:30:00Z"
  },
  "status": "published",
  "published_at": "2025-01-07T09:00:00Z",
  "created_at": "2025-01-06T15:00:00Z",
  "updated_at": "2025-01-07T10:30:00Z"
}
```

**Notes:**
- ⚡ **Fast:** ~2KB response
- ✅ **Use this first** to show lesson info
- ❌ **NO pages content** - load pages separately

---

### **2. GET /lessons/{lesson_id}/pages**

**Purpose:** List all pages (summary only - no content)

**Request:**
```http
GET /api/v1/lessons/68e4567abc1234567890def/pages?summary_only=true
Authorization: Bearer {token}
```

**Query Parameters:**
- `summary_only` (boolean, default: true) - Return summary or full content
- `status_filter` (string, optional) - Filter: "draft" | "published" | "archived"

**Response (200 OK):**
```json
{
  "lesson_id": "68e4567abc1234567890def",
  "lesson_title": "Pemrograman Python Dasar",
  "total_pages": 15,
  "pages": [
    {
      "page_number": 1,
      "title": "Pengenalan Python",
      "estimated_duration": 10,
      "difficulty_level": "easy",
      "status": "published",
      "has_media": true,
      "has_components": false,
      "media_count": 2,
      "component_count": 0,
      "created_at": "2025-01-06T15:00:00Z",
      "updated_at": "2025-01-06T15:00:00Z"
    },
    {
      "page_number": 2,
      "title": "Instalasi Python",
      "estimated_duration": 15,
      "difficulty_level": "easy",
      "status": "published",
      "has_media": true,
      "has_components": true,
      "media_count": 1,
      "component_count": 1,
      "created_at": "2025-01-06T15:10:00Z",
      "updated_at": "2025-01-06T15:10:00Z"
    }
    // ... 13 more pages
  ]
}
```

**Usage:**
```typescript
// Display table of contents / page navigator
const { data } = await api.get(`/lessons/${lessonId}/pages`);

// Render page list
data.pages.map(page => (
  <PageItem
    number={page.page_number}
    title={page.title}
    duration={page.estimated_duration}
    hasMedia={page.has_media}
  />
));
```

---

### **3. GET /lessons/{lesson_id}/pages/{page_number}**

**Purpose:** Get single page content (efficient!)

**Request:**
```http
GET /api/v1/lessons/68e4567abc1234567890def/pages/1
Authorization: Bearer {token}
```

**Path Parameters:**
- `page_number` (integer, required) - Page number to retrieve (1-based)

**Query Parameters:**
- `prefetch_next` (boolean, default: false) - Include next page data

**Response (200 OK):**
```json
{
  "lesson_id": "68e4567abc1234567890def",
  "lesson_title": "Pemrograman Python Dasar",
  "total_pages": 15,
  "current_page": 1,
  "has_previous": false,
  "has_next": true,
  "previous_page": null,
  "next_page": 2,
  "page": {
    "id": "68e4568abc1234567890xxx",
    "lesson_id": "68e4567abc1234567890def",
    "page_number": 1,
    "title": "Pengenalan Python",
    "content_markdown": "# Pengenalan Python\n\nPython adalah bahasa pemrograman yang mudah dipelajari...\n\n![Python Logo](https://cdn.example.com/media/image/2025/01/python-logo.png)\n\n## Mengapa Belajar Python?\n\n1. **Mudah dipelajari** - Syntax yang sederhana\n2. **Powerful** - Bisa untuk web, data science, AI\n3. **Populer** - Banyak job opportunities\n\n**Video Tutorial:**\n\n<video controls width=\"100%\">\n  <source src=\"https://cdn.example.com/media/video/2025/01/intro-python.mp4\" type=\"video/mp4\">\n</video>\n\n## Instalasi\n\nDownload Python dari [python.org](https://python.org)",
    "media_references": [
      {
        "media_key": "python_logo",
        "file_name": "python-logo.png",
        "file_type": "image",
        "file_size": 45678,
        "url": "https://cdn.example.com/media/image/2025/01/python-logo.png",
        "alt_text": "Logo Python Programming Language"
      },
      {
        "media_key": "intro_video",
        "file_name": "intro-python.mp4",
        "file_type": "video",
        "file_size": 12345678,
        "url": "https://cdn.example.com/media/video/2025/01/intro-python.mp4",
        "duration": 180
      }
    ],
    "embedded_components": [],
    "estimated_duration": 10,
    "difficulty_level": "easy",
    "learning_objectives": [
      "Memahami apa itu Python",
      "Mengenal kegunaan Python"
    ],
    "status": "published",
    "version": 1,
    "created_at": "2025-01-06T15:00:00Z",
    "updated_at": "2025-01-06T15:00:00Z",
    "created_by": "teacher_001"
  }
}
```

**Usage:**
```typescript
// Load page when user navigates
const { data } = await api.get(`/lessons/${lessonId}/pages/${pageNumber}`);

// Display page content
<div>
  <h1>{data.page.title}</h1>
  
  {/* Render markdown */}
  <ReactMarkdown>{data.page.content_markdown}</ReactMarkdown>
  
  {/* Navigation buttons */}
  <div className="navigation">
    {data.has_previous && (
      <button onClick={() => goToPage(data.previous_page)}>
        ← Previous
      </button>
    )}
    
    <span>Page {data.current_page} of {data.total_pages}</span>
    
    {data.has_next && (
      <button onClick={() => goToPage(data.next_page)}>
        Next →
      </button>
    )}
  </div>
  
  {/* Progress bar */}
  <ProgressBar 
    current={data.current_page} 
    total={data.total_pages} 
  />
</div>
```

---

### **4. GET /lessons/{lesson_id}/pages/batch**

**Purpose:** Get multiple pages at once (for prefetching)

**Request:**
```http
GET /api/v1/lessons/68e4567abc1234567890def/pages/batch?page_numbers=1,2,3
Authorization: Bearer {token}
```

**Query Parameters:**
- `page_numbers` (string, required) - Comma-separated page numbers (e.g., "1,2,3")

**Response (200 OK):**
```json
{
  "lesson_id": "68e4567abc1234567890def",
  "page_numbers": [1, 2, 3],
  "pages": [
    {
      "id": "68e4568abc...",
      "lesson_id": "68e4567abc...",
      "page_number": 1,
      "title": "Pengenalan Python",
      "content_markdown": "...",
      // ... full page data
    },
    {
      "id": "68e4569bcd...",
      "lesson_id": "68e4567abc...",
      "page_number": 2,
      "title": "Instalasi Python",
      "content_markdown": "...",
      // ... full page data
    },
    {
      "id": "68e456acde...",
      "lesson_id": "68e4567abc...",
      "page_number": 3,
      "title": "Hello World",
      "content_markdown": "...",
      // ... full page data
    }
  ]
}
```

**Usage:**
```typescript
// Prefetch next pages for smooth navigation
useEffect(() => {
  if (currentPage < totalPages) {
    const nextPages = [currentPage + 1, currentPage + 2, currentPage + 3]
      .filter(p => p <= totalPages)
      .join(',');
    
    // Background prefetch (don't await)
    api.get(`/lessons/${lessonId}/pages/batch?page_numbers=${nextPages}`)
      .then(response => {
        // Cache pages
        response.data.pages.forEach(page => {
          cacheStore.set(`page_${page.page_number}`, page);
        });
      });
  }
}, [currentPage]);
```

---

### **5. POST /lessons/{lesson_id}/pages**

**Purpose:** Create new page

**Request:**
```http
POST /api/v1/lessons/68e4567abc1234567890def/pages
Authorization: Bearer {token}
Content-Type: application/json

{
  "page_number": 16,
  "title": "Advanced Topics",
  "content_markdown": "# Advanced Topics\n\nNow let's explore advanced Python concepts...\n\n## Topics:\n\n- Decorators\n- Generators\n- Context managers",
  "media_references": [],
  "embedded_components": [],
  "estimated_duration": 20,
  "difficulty_level": "hard",
  "learning_objectives": [
    "Master advanced Python features"
  ],
  "status": "published"
}
```

**Request Body Schema:**
```typescript
interface CreatePageRequest {
  page_number: number;           // Required, must be unique, >= 1
  title: string;                  // Required, 1-200 chars
  content_markdown: string;       // Required, markdown format
  media_references?: MediaReference[];  // Optional
  embedded_components?: EmbeddedComponent[];  // Optional
  estimated_duration?: number;    // Optional, default: 10 (minutes)
  difficulty_level?: 'easy' | 'medium' | 'hard';  // Optional, default: 'medium'
  learning_objectives?: string[]; // Optional
  status?: 'draft' | 'published' | 'archived';  // Optional, default: 'published'
}

interface MediaReference {
  media_key: string;
  file_name: string;
  file_type: 'image' | 'video' | 'audio' | 'document';
  file_size: number;
  url: string;
  alt_text?: string;
  duration?: number;
}
```

**Response (201 Created):**
```json
{
  "id": "68e456def...",
  "lesson_id": "68e4567abc...",
  "page_number": 16,
  "title": "Advanced Topics",
  "content_markdown": "...",
  "media_references": [],
  "embedded_components": [],
  "estimated_duration": 20,
  "difficulty_level": "hard",
  "learning_objectives": ["Master advanced Python features"],
  "status": "published",
  "version": 1,
  "created_at": "2025-01-07T11:00:00Z",
  "updated_at": "2025-01-07T11:00:00Z",
  "created_by": "teacher_001"
}
```

**Usage:**
```typescript
// Create new page
const createPage = async (pageData) => {
  try {
    const response = await api.post(
      `/lessons/${lessonId}/pages`,
      pageData
    );
    
    toast.success('Page created successfully!');
    return response.data;
  } catch (error) {
    if (error.response?.status === 400) {
      toast.error('Page number already exists!');
    }
    throw error;
  }
};
```

---

### **6. PUT /lessons/{lesson_id}/pages/{page_number}**

**Purpose:** Update page content

**Request:**
```http
PUT /api/v1/lessons/68e4567abc1234567890def/pages/1
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Pengenalan Python (Updated)",
  "content_markdown": "# Pengenalan Python (UPDATED)\n\nContent has been updated with new information...",
  "estimated_duration": 15
}
```

**Request Body Schema:**
```typescript
interface UpdatePageRequest {
  title?: string;                 // Optional
  content_markdown?: string;      // Optional
  media_references?: MediaReference[];  // Optional
  embedded_components?: EmbeddedComponent[];  // Optional
  estimated_duration?: number;    // Optional
  difficulty_level?: 'easy' | 'medium' | 'hard';  // Optional
  learning_objectives?: string[]; // Optional
  status?: 'draft' | 'published' | 'archived';  // Optional
}
```

**Response (200 OK):**
```json
{
  "id": "68e4568abc...",
  "lesson_id": "68e4567abc...",
  "page_number": 1,
  "title": "Pengenalan Python (Updated)",
  "content_markdown": "...",
  "estimated_duration": 15,
  "version": 2,  // Version incremented!
  "updated_at": "2025-01-07T11:30:00Z",
  "updated_by": "teacher_001"
}
```

**Notes:**
- ✅ **Version auto-incremented** when content changes
- ✅ **Only specified fields updated** (partial update)
- ✅ **Lesson metadata auto-updated** (total duration, etc.)

---

### **7. PUT /lessons/{lesson_id}/pages/reorder**

**Purpose:** Reorder pages (change page numbers)

**Request:**
```http
PUT /api/v1/lessons/68e4567abc1234567890def/pages/reorder
Authorization: Bearer {token}
Content-Type: application/json

{
  "page_numbers": [3, 1, 2, 4, 5]
}
```

**Request Body:**
```typescript
interface ReorderPagesRequest {
  page_numbers: number[];  // New order of page numbers
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Pages reordered successfully",
  "new_order": [3, 1, 2, 4, 5]
}
```

**Usage:**
```typescript
// Drag & drop reorder
const handleDragEnd = async (result) => {
  const newOrder = reorderArray(pages, result);
  const pageNumbers = newOrder.map(p => p.page_number);
  
  await api.put(`/lessons/${lessonId}/pages/reorder`, {
    page_numbers: pageNumbers
  });
  
  // Refresh page list
  refreshPages();
};
```

---

### **8. DELETE /lessons/{lesson_id}/pages/{page_number}**

**Purpose:** Delete a page

**Request:**
```http
DELETE /api/v1/lessons/68e4567abc1234567890def/pages/3
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Page 3 deleted successfully"
}
```

**Notes:**
- ✅ **Remaining pages auto-renumbered** (page 4 becomes 3, etc.)
- ✅ **Lesson metadata auto-updated**

**Usage:**
```typescript
const deletePage = async (pageNumber) => {
  if (!confirm('Are you sure you want to delete this page?')) {
    return;
  }
  
  try {
    await api.delete(`/lessons/${lessonId}/pages/${pageNumber}`);
    toast.success('Page deleted successfully');
    
    // Refresh page list
    refreshPages();
  } catch (error) {
    toast.error('Failed to delete page');
  }
};
```

---

## 💻 **FRONTEND IMPLEMENTATION EXAMPLES**

### **Example 1: Lesson Viewer Component (React)**

```typescript
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from './api';

interface LessonViewerProps {
  lessonId: string;
}

export const LessonViewer: React.FC<LessonViewerProps> = ({ lessonId }) => {
  const [lesson, setLesson] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Load lesson metadata
  useEffect(() => {
    const loadLesson = async () => {
      const { data } = await api.get(`/lessons/${lessonId}`);
      setLesson(data);
    };
    loadLesson();
  }, [lessonId]);
  
  // Load current page
  useEffect(() => {
    const loadPage = async () => {
      setLoading(true);
      try {
        const { data } = await api.get(
          `/lessons/${lessonId}/pages/${currentPage}`
        );
        setPageData(data);
      } finally {
        setLoading(false);
      }
    };
    
    if (lessonId && currentPage) {
      loadPage();
    }
  }, [lessonId, currentPage]);
  
  // Prefetch next page
  useEffect(() => {
    if (pageData?.has_next) {
      api.get(`/lessons/${lessonId}/pages/${pageData.next_page}`);
    }
  }, [pageData]);
  
  if (!lesson || !pageData) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="lesson-viewer">
      {/* Header */}
      <header>
        <h1>{lesson.title}</h1>
        <div className="meta">
          <span>Page {pageData.current_page} of {pageData.total_pages}</span>
          <span>{pageData.page.estimated_duration} mins</span>
        </div>
      </header>
      
      {/* Progress Bar */}
      <div className="progress">
        <div 
          className="progress-bar"
          style={{ 
            width: `${(pageData.current_page / pageData.total_pages) * 100}%` 
          }}
        />
      </div>
      
      {/* Page Content */}
      <article className="page-content">
        <h2>{pageData.page.title}</h2>
        
        {loading ? (
          <div>Loading page...</div>
        ) : (
          <ReactMarkdown>
            {pageData.page.content_markdown}
          </ReactMarkdown>
        )}
      </article>
      
      {/* Navigation */}
      <nav className="page-navigation">
        <button
          disabled={!pageData.has_previous}
          onClick={() => setCurrentPage(pageData.previous_page)}
        >
          ← Previous
        </button>
        
        <span>
          Page {currentPage} / {pageData.total_pages}
        </span>
        
        <button
          disabled={!pageData.has_next}
          onClick={() => setCurrentPage(pageData.next_page)}
        >
          Next →
        </button>
      </nav>
    </div>
  );
};
```

---

### **Example 2: Page List / Table of Contents**

```typescript
import React, { useState, useEffect } from 'react';

export const LessonTableOfContents: React.FC<{ lessonId: string }> = ({ 
  lessonId 
}) => {
  const [pages, setPages] = useState([]);
  
  useEffect(() => {
    const loadPages = async () => {
      const { data } = await api.get(
        `/lessons/${lessonId}/pages?summary_only=true`
      );
      setPages(data.pages);
    };
    loadPages();
  }, [lessonId]);
  
  return (
    <div className="table-of-contents">
      <h3>Table of Contents</h3>
      
      <ul>
        {pages.map((page) => (
          <li key={page.page_number}>
            <a href={`#page-${page.page_number}`}>
              <span className="page-number">{page.page_number}</span>
              <span className="page-title">{page.title}</span>
              <span className="page-duration">
                {page.estimated_duration} mins
              </span>
              
              {/* Icons */}
              {page.has_media && <span>🖼️</span>}
              {page.has_components && <span>📝</span>}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
};
```

---

### **Example 3: Page Editor (Teacher)**

```typescript
import React, { useState } from 'react';
import MDEditor from '@uiw/react-md-editor';

export const PageEditor: React.FC<{ lessonId: string }> = ({ lessonId }) => {
  const [pageData, setPageData] = useState({
    page_number: 1,
    title: '',
    content_markdown: '',
    estimated_duration: 10,
    difficulty_level: 'medium' as const,
  });
  
  const [saving, setSaving] = useState(false);
  
  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await api.post(
        `/lessons/${lessonId}/pages`,
        pageData
      );
      
      toast.success('Page created successfully!');
      // Navigate to new page or reset form
    } catch (error) {
      toast.error('Failed to create page');
    } finally {
      setSaving(false);
    }
  };
  
  const handleImageUpload = async (file: File) => {
    // Upload to media endpoint
    const { data: presigned } = await api.post('/media/presigned-url', {
      filename: file.name,
      content_type: file.type,
      file_size: file.size
    });
    
    // Upload to R2
    await fetch(presigned.upload_url, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type }
    });
    
    // Confirm upload
    await api.post('/media/confirm-upload', {
      file_key: presigned.file_key,
      file_name: file.name,
      file_size: file.size,
      content_type: file.type,
      category: 'image'
    });
    
    // Return URL for markdown
    return presigned.public_url;
  };
  
  return (
    <div className="page-editor">
      <h2>Create New Page</h2>
      
      <form onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
        {/* Page Number */}
        <div className="form-group">
          <label>Page Number</label>
          <input
            type="number"
            min="1"
            value={pageData.page_number}
            onChange={(e) => setPageData({
              ...pageData,
              page_number: parseInt(e.target.value)
            })}
            required
          />
        </div>
        
        {/* Title */}
        <div className="form-group">
          <label>Title</label>
          <input
            type="text"
            value={pageData.title}
            onChange={(e) => setPageData({
              ...pageData,
              title: e.target.value
            })}
            required
          />
        </div>
        
        {/* Content (Markdown Editor) */}
        <div className="form-group">
          <label>Content</label>
          <MDEditor
            value={pageData.content_markdown}
            onChange={(value) => setPageData({
              ...pageData,
              content_markdown: value || ''
            })}
            height={500}
            onImageUpload={handleImageUpload}
          />
        </div>
        
        {/* Duration */}
        <div className="form-group">
          <label>Estimated Duration (minutes)</label>
          <input
            type="number"
            min="1"
            value={pageData.estimated_duration}
            onChange={(e) => setPageData({
              ...pageData,
              estimated_duration: parseInt(e.target.value)
            })}
          />
        </div>
        
        {/* Difficulty */}
        <div className="form-group">
          <label>Difficulty Level</label>
          <select
            value={pageData.difficulty_level}
            onChange={(e) => setPageData({
              ...pageData,
              difficulty_level: e.target.value as any
            })}
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        
        {/* Submit */}
        <button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Create Page'}
        </button>
      </form>
    </div>
  );
};
```

---

## 🔄 **MIGRATION GUIDE (Old → New)**

### **Step 1: Update Lesson Loading**

**OLD CODE (REMOVE):**
```typescript
// ❌ DON'T USE ANYMORE
const loadLesson = async (lessonId) => {
  const { data } = await api.get(`/lessons/${lessonId}`);
  
  // data.pages has all 50 pages embedded - HEAVY!
  setLesson(data);
  setPages(data.pages);  // All pages at once
};
```

**NEW CODE (USE THIS):**
```typescript
// ✅ USE THIS
const loadLesson = async (lessonId) => {
  // Step 1: Load metadata
  const { data: lesson } = await api.get(`/lessons/${lessonId}`);
  setLesson(lesson);
  
  // Step 2: Load pages summary (optional - for TOC)
  const { data: pagesList } = await api.get(`/lessons/${lessonId}/pages`);
  setPagesSummary(pagesList.pages);
  
  // Step 3: Load first page
  const { data: firstPage } = await api.get(`/lessons/${lessonId}/pages/1`);
  setCurrentPageData(firstPage);
};
```

---

### **Step 2: Update Page Navigation**

**OLD CODE:**
```typescript
// ❌ OLD: Pages already loaded
const goToPage = (pageNumber) => {
  const page = pages.find(p => p.page_number === pageNumber);
  setCurrentPage(page);
};
```

**NEW CODE:**
```typescript
// ✅ NEW: Load page on-demand
const goToPage = async (pageNumber) => {
  setLoading(true);
  try {
    const { data } = await api.get(
      `/lessons/${lessonId}/pages/${pageNumber}`
    );
    setCurrentPageData(data);
    setCurrentPageNumber(pageNumber);
  } finally {
    setLoading(false);
  }
};
```

---

### **Step 3: Add Prefetching (Optional but Recommended)**

```typescript
// Prefetch next page for smooth UX
useEffect(() => {
  if (currentPageData?.has_next) {
    // Prefetch in background
    api.get(`/lessons/${lessonId}/pages/${currentPageData.next_page}`)
      .then(response => {
        // Cache for instant load
        pageCache.set(currentPageData.next_page, response.data);
      });
  }
}, [currentPageData]);

// Use cached data if available
const goToPage = async (pageNumber) => {
  // Check cache first
  const cached = pageCache.get(pageNumber);
  if (cached) {
    setCurrentPageData(cached);
    return;
  }
  
  // Otherwise fetch
  const { data } = await api.get(`/lessons/${lessonId}/pages/${pageNumber}`);
  setCurrentPageData(data);
};
```

---

## 🎨 **UI/UX RECOMMENDATIONS**

### **1. Loading States**

```typescript
// Show skeleton while loading
{loading ? (
  <div className="skeleton">
    <div className="skeleton-title"></div>
    <div className="skeleton-text"></div>
    <div className="skeleton-text"></div>
  </div>
) : (
  <ReactMarkdown>{pageData.page.content_markdown}</ReactMarkdown>
)}
```

### **2. Progress Indicator**

```typescript
<div className="lesson-progress">
  <div className="progress-bar">
    <div 
      className="progress-fill"
      style={{ width: `${(currentPage / totalPages) * 100}%` }}
    />
  </div>
  <span className="progress-text">
    Page {currentPage} of {totalPages} ({Math.round((currentPage / totalPages) * 100)}% complete)
  </span>
</div>
```

### **3. Navigation Controls**

```typescript
<nav className="page-nav">
  {/* Previous button */}
  <button
    disabled={!pageData.has_previous}
    onClick={() => goToPage(pageData.previous_page)}
    className="btn-nav"
  >
    <span>←</span> Previous
  </button>
  
  {/* Page indicator */}
  <div className="page-dots">
    {Array.from({ length: totalPages }).map((_, i) => (
      <span
        key={i}
        className={i + 1 === currentPage ? 'dot active' : 'dot'}
        onClick={() => goToPage(i + 1)}
      />
    ))}
  </div>
  
  {/* Next button */}
  <button
    disabled={!pageData.has_next}
    onClick={() => goToPage(pageData.next_page)}
    className="btn-nav btn-primary"
  >
    Next <span>→</span>
  </button>
</nav>
```

### **4. Keyboard Navigation**

```typescript
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' && pageData.has_previous) {
      goToPage(pageData.previous_page);
    } else if (e.key === 'ArrowRight' && pageData.has_next) {
      goToPage(pageData.next_page);
    }
  };
  
  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, [pageData]);
```

---

## ⚡ **PERFORMANCE TIPS**

### **1. Implement Caching**

```typescript
// Use React Query for automatic caching
import { useQuery } from '@tanstack/react-query';

const usePage = (lessonId: string, pageNumber: number) => {
  return useQuery({
    queryKey: ['lesson', lessonId, 'page', pageNumber],
    queryFn: () => api.get(`/lessons/${lessonId}/pages/${pageNumber}`),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    cacheTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });
};
```

### **2. Lazy Load Images**

```typescript
import { LazyLoadImage } from 'react-lazy-load-image-component';

<LazyLoadImage
  src={imageUrl}
  alt={altText}
  effect="blur"
  threshold={100}
/>
```

### **3. Batch Prefetch**

```typescript
// Prefetch next 3 pages
useEffect(() => {
  if (currentPage < totalPages - 2) {
    const nextPages = [currentPage + 1, currentPage + 2, currentPage + 3]
      .filter(p => p <= totalPages)
      .join(',');
    
    api.get(`/lessons/${lessonId}/pages/batch?page_numbers=${nextPages}`);
  }
}, [currentPage]);
```

---

## 🐛 **ERROR HANDLING**

```typescript
const loadPage = async (pageNumber: number) => {
  setLoading(true);
  setError(null);
  
  try {
    const { data } = await api.get(
      `/lessons/${lessonId}/pages/${pageNumber}`
    );
    setPageData(data);
  } catch (error) {
    if (error.response?.status === 404) {
      setError('Page not found');
    } else if (error.response?.status === 403) {
      setError('You don\'t have access to this lesson');
    } else {
      setError('Failed to load page. Please try again.');
    }
  } finally {
    setLoading(false);
  }
};

// Display error
{error && (
  <div className="error-message">
    <span>⚠️</span> {error}
    <button onClick={() => loadPage(currentPage)}>
      Retry
    </button>
  </div>
)}
```

---

## 📱 **MOBILE OPTIMIZATION**

```typescript
// Swipe gestures for mobile
import { useSwipeable } from 'react-swipeable';

const handlers = useSwipeable({
  onSwipedLeft: () => {
    if (pageData.has_next) {
      goToPage(pageData.next_page);
    }
  },
  onSwipedRight: () => {
    if (pageData.has_previous) {
      goToPage(pageData.previous_page);
    }
  },
  preventScrollOnSwipe: true,
  trackMouse: true,
});

<div {...handlers} className="lesson-content">
  {/* Page content */}
</div>
```

---

## 📊 **ANALYTICS TRACKING**

```typescript
// Track page views
useEffect(() => {
  if (pageData) {
    // Send analytics event
    analytics.track('page_view', {
      lesson_id: lessonId,
      page_number: pageData.current_page,
      page_title: pageData.page.title,
      timestamp: new Date().toISOString(),
    });
    
    // Track time spent
    const startTime = Date.now();
    
    return () => {
      const timeSpent = Math.floor((Date.now() - startTime) / 1000);
      
      analytics.track('page_time_spent', {
        lesson_id: lessonId,
        page_number: pageData.current_page,
        time_spent: timeSpent,
      });
    };
  }
}, [pageData]);
```

---

## ✅ **CHECKLIST FOR FRONTEND IMPLEMENTATION**

- [ ] Update lesson loading to use new endpoints
- [ ] Implement page navigation
- [ ] Add loading states and skeletons
- [ ] Implement caching (React Query recommended)
- [ ] Add prefetching for smooth UX
- [ ] Handle errors gracefully
- [ ] Add keyboard navigation (arrow keys)
- [ ] Add mobile swipe gestures
- [ ] Implement progress tracking
- [ ] Add analytics tracking
- [ ] Test on mobile devices
- [ ] Test with slow network (throttling)
- [ ] Add accessibility features (ARIA labels)

---

## 🎯 **SUMMARY**

### **Key Changes:**
1. ✅ Lessons now return **metadata only** (no embedded pages)
2. ✅ Pages loaded **on-demand** via separate endpoints
3. ✅ **98% performance improvement**
4. ✅ **Better UX** with prefetching and caching
5. ✅ **Scalable** architecture for large lessons

### **Performance Benefits:**
- ⚡ Initial load: **2KB** (was 250KB+)
- ⚡ Page load: **5KB** (was 250KB+)
- ⚡ Mobile data savings: **95%+**
- ⚡ Faster navigation: **instant** with caching

### **Developer Benefits:**
- 💻 Cleaner code
- 🎯 Better separation of concerns
- 🚀 Easier to maintain
- 📈 Scalable for growth

---

## 📞 **SUPPORT**

**Questions?** Contact backend team or check:
- API Documentation: http://localhost:8000/docs
- Test File: `tests/test_lesson_pages_endpoints.py`
- Migration Guide: `QUICK_START_MIGRATION.md`

---

**Happy Coding! 🚀**
