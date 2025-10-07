# 🚀 **Lesson Pages API - Quick Reference Card**

## 📋 **Cheat Sheet for Frontend Developers**

---

## 🎯 **THE BASICS**

### **Old Way (DEPRECATED):**
```typescript
// ❌ Don't use - loads all pages (250KB+)
const { data } = await api.get(`/lessons/${id}`);
const pages = data.pages;  // Won't work anymore!
```

### **New Way (USE THIS):**
```typescript
// ✅ Load metadata only (2KB)
const { data: lesson } = await api.get(`/lessons/${id}`);

// ✅ Load single page (5KB)
const { data: page } = await api.get(`/lessons/${id}/pages/1`);
```

---

## 📡 **API ENDPOINTS**

### **1. Get Lesson Metadata**
```http
GET /api/v1/lessons/{id}
→ { id, title, metadata: { total_pages, total_duration } }
```

### **2. List Pages (Summary)**
```http
GET /api/v1/lessons/{id}/pages?summary_only=true
→ { pages: [{ page_number, title, estimated_duration, ... }] }
```

### **3. Get Single Page**
```http
GET /api/v1/lessons/{id}/pages/{number}
→ { page: { content_markdown, ... }, has_next, has_previous }
```

### **4. Get Batch Pages**
```http
GET /api/v1/lessons/{id}/pages/batch?page_numbers=1,2,3
→ { pages: [...] }
```

### **5. Create Page**
```http
POST /api/v1/lessons/{id}/pages
Body: { page_number, title, content_markdown, ... }
```

### **6. Update Page**
```http
PUT /api/v1/lessons/{id}/pages/{number}
Body: { title?, content_markdown?, ... }
```

### **7. Reorder Pages**
```http
PUT /api/v1/lessons/{id}/pages/reorder
Body: { page_numbers: [3, 1, 2] }
```

### **8. Delete Page**
```http
DELETE /api/v1/lessons/{id}/pages/{number}
```

---

## 💻 **CODE SNIPPETS**

### **Load Lesson + First Page:**
```typescript
const loadLesson = async (lessonId: string) => {
  // Metadata
  const { data: lesson } = await api.get(`/lessons/${lessonId}`);
  
  // First page
  const { data: page1 } = await api.get(`/lessons/${lessonId}/pages/1`);
  
  return { lesson, page1 };
};
```

### **Navigate to Page:**
```typescript
const goToPage = async (pageNum: number) => {
  setLoading(true);
  const { data } = await api.get(`/lessons/${lessonId}/pages/${pageNum}`);
  setCurrentPage(data);
  setLoading(false);
};
```

### **Prefetch Next Page:**
```typescript
useEffect(() => {
  if (currentPage?.has_next) {
    // Prefetch in background
    api.get(`/lessons/${lessonId}/pages/${currentPage.next_page}`);
  }
}, [currentPage]);
```

### **Create New Page:**
```typescript
const createPage = async (pageData) => {
  const response = await api.post(`/lessons/${lessonId}/pages`, {
    page_number: pageData.number,
    title: pageData.title,
    content_markdown: pageData.content,
    estimated_duration: pageData.duration,
    difficulty_level: pageData.difficulty,
  });
  return response.data;
};
```

### **Update Page:**
```typescript
const updatePage = async (pageNum: number, updates) => {
  const response = await api.put(`/lessons/${lessonId}/pages/${pageNum}`, {
    title: updates.title,
    content_markdown: updates.content,
  });
  return response.data;
};
```

---

## 🎨 **REACT COMPONENTS**

### **Lesson Viewer:**
```tsx
function LessonViewer({ lessonId }) {
  const [lesson, setLesson] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageData, setPageData] = useState(null);
  
  useEffect(() => {
    // Load lesson metadata
    api.get(`/lessons/${lessonId}`).then(r => setLesson(r.data));
  }, [lessonId]);
  
  useEffect(() => {
    // Load current page
    api.get(`/lessons/${lessonId}/pages/${currentPage}`)
      .then(r => setPageData(r.data));
  }, [currentPage]);
  
  return (
    <div>
      <h1>{lesson?.title}</h1>
      <ReactMarkdown>{pageData?.page.content_markdown}</ReactMarkdown>
      
      <nav>
        <button 
          disabled={!pageData?.has_previous}
          onClick={() => setCurrentPage(p => p - 1)}
        >
          ← Previous
        </button>
        
        <span>{currentPage} / {lesson?.metadata.total_pages}</span>
        
        <button 
          disabled={!pageData?.has_next}
          onClick={() => setCurrentPage(p => p + 1)}
        >
          Next →
        </button>
      </nav>
    </div>
  );
}
```

### **Table of Contents:**
```tsx
function TableOfContents({ lessonId }) {
  const [pages, setPages] = useState([]);
  
  useEffect(() => {
    api.get(`/lessons/${lessonId}/pages?summary_only=true`)
      .then(r => setPages(r.data.pages));
  }, [lessonId]);
  
  return (
    <ul>
      {pages.map(page => (
        <li key={page.page_number}>
          <a href={`#page-${page.page_number}`}>
            {page.page_number}. {page.title}
            <span>({page.estimated_duration} min)</span>
          </a>
        </li>
      ))}
    </ul>
  );
}
```

---

## 🔄 **MIGRATION CHECKLIST**

- [ ] Remove `data.pages` references
- [ ] Update lesson loading to use `/lessons/{id}` (metadata only)
- [ ] Update page loading to use `/lessons/{id}/pages/{num}`
- [ ] Add loading states for page transitions
- [ ] Implement caching (React Query recommended)
- [ ] Add prefetching for smooth UX
- [ ] Test navigation (Previous/Next buttons)
- [ ] Test on mobile devices
- [ ] Test with slow network (throttling)

---

## 📊 **RESPONSE STRUCTURES**

### **Lesson Metadata:**
```typescript
interface Lesson {
  id: string;
  title: string;
  description: string;
  metadata: {
    total_pages: number;
    total_duration: number;
    total_media: number;
    total_components: number;
  };
  status: 'draft' | 'published' | 'archived';
  created_at: string;
  updated_at: string;
}
```

### **Page Data:**
```typescript
interface PageResponse {
  lesson_id: string;
  lesson_title: string;
  total_pages: number;
  current_page: number;
  has_previous: boolean;
  has_next: boolean;
  previous_page: number | null;
  next_page: number | null;
  page: {
    id: string;
    page_number: number;
    title: string;
    content_markdown: string;
    media_references: MediaReference[];
    embedded_components: EmbeddedComponent[];
    estimated_duration: number;
    difficulty_level: 'easy' | 'medium' | 'hard';
    status: 'draft' | 'published' | 'archived';
    version: number;
    created_at: string;
    updated_at: string;
  };
}
```

---

## ⚡ **PERFORMANCE TIPS**

### **1. Use React Query:**
```typescript
import { useQuery } from '@tanstack/react-query';

const { data } = useQuery({
  queryKey: ['lesson', lessonId, 'page', pageNum],
  queryFn: () => api.get(`/lessons/${lessonId}/pages/${pageNum}`),
  staleTime: 5 * 60 * 1000, // Cache 5 mins
});
```

### **2. Prefetch Next Pages:**
```typescript
// Prefetch next 3 pages
useEffect(() => {
  const nextPages = [currentPage + 1, currentPage + 2, currentPage + 3]
    .filter(p => p <= totalPages)
    .join(',');
  
  api.get(`/lessons/${lessonId}/pages/batch?page_numbers=${nextPages}`);
}, [currentPage]);
```

### **3. Lazy Load Images:**
```typescript
import { LazyLoadImage } from 'react-lazy-load-image-component';

<LazyLoadImage src={url} alt={alt} effect="blur" />
```

---

## 🐛 **COMMON ERRORS**

### **"pages field not found"**
**Fix:** Update to new endpoint
```typescript
// ❌ Old
const pages = lesson.pages;

// ✅ New
const { data } = await api.get(`/lessons/${id}/pages`);
```

### **"404 Not Found"**
**Fix:** Check server restarted after migration
```bash
uvicorn app.main:app --reload
```

### **"Slow loading"**
**Fix:** Implement caching + prefetching

---

## 📱 **MOBILE SUPPORT**

### **Swipe Gestures:**
```typescript
import { useSwipeable } from 'react-swipeable';

const handlers = useSwipeable({
  onSwipedLeft: () => goToPage(currentPage + 1),
  onSwipedRight: () => goToPage(currentPage - 1),
});

<div {...handlers}>
  {/* Content */}
</div>
```

### **Keyboard Navigation:**
```typescript
useEffect(() => {
  const handleKey = (e) => {
    if (e.key === 'ArrowLeft') goToPage(currentPage - 1);
    if (e.key === 'ArrowRight') goToPage(currentPage + 1);
  };
  
  window.addEventListener('keydown', handleKey);
  return () => window.removeEventListener('keydown', handleKey);
}, [currentPage]);
```

---

## 📚 **FULL DOCUMENTATION**

**Main Guide:**  
`docs/FRONTEND_LESSON_PAGES_API_GUIDE.md`

**Changelog:**  
`docs/LESSON_PAGES_CHANGELOG.md`

**API Docs:**  
http://localhost:8000/docs

---

## ✅ **SUCCESS INDICATORS**

After migration:
- ✅ Initial load: <500ms (was 3-5s)
- ✅ Page nav: <200ms
- ✅ Bandwidth: -95%
- ✅ Mobile: Smooth experience

---

**Need help? Check full documentation!** 📖
