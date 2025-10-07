# 📤 Media Upload Guide - Pre-signed URLs

## 🎯 **OVERVIEW**

Sistem upload media menggunakan **Pre-signed URLs** untuk upload langsung ke Cloudflare R2, **tanpa melalui backend server**.

**Benefits:**
- ⚡ Faster uploads (direct to R2)
- 💰 Lower server costs (no bandwidth usage)
- 📈 Scalable (handles thousands of concurrent uploads)
- 🔐 Secure (time-limited, single-use URLs)

---

## 🔄 **UPLOAD WORKFLOW**

```
1. Request pre-signed URL → Backend
2. Backend generate URL → Return to frontend
3. Upload file DIRECTLY to R2 using URL
4. Confirm upload → Backend (save metadata)
5. Use public_url in markdown content
```

---

## 📋 **SUPPORTED FILE TYPES**

### 🖼️ **Images** (Max 10MB)
- JPEG, JPG, PNG, GIF, WebP, SVG, BMP, TIFF
- Use: Lesson illustrations, diagrams, screenshots

### 🎬 **Videos** (Max 500MB)
- MP4, WebM, MOV, AVI, MKV
- Use: Video lectures, tutorials, demonstrations

### 🎵 **Audio** (Max 50MB)
- MP3, WAV, OGG, AAC, FLAC
- Use: Audio lessons, pronunciations, podcasts

### 📄 **Documents** (Max 20MB)
- PDF, DOC, DOCX, TXT, MD, HTML
- Use: Handouts, reading materials, references

### 📊 **Spreadsheets** (Max 10MB)
- XLS, XLSX, CSV
- Use: Data sets, templates, exercises

### 📑 **Presentations** (Max 50MB)
- PPT, PPTX
- Use: Slide decks, visual presentations

### 📦 **Archives** (Max 100MB)
- ZIP, RAR, 7Z
- Use: Resource packs, code samples, collections

---

## 🚀 **API ENDPOINTS**

### **1. Get Supported Types**
```http
GET /api/v1/media/supported-types
```

**Response:**
```json
{
  "categories": [
    {
      "category": "image",
      "mime_types": ["image/jpeg", "image/png", ...],
      "extensions": ["jpg", "png", ...],
      "max_size_mb": 10,
      "max_size_bytes": 10485760
    },
    ...
  ]
}
```

---

### **2. Get Pre-signed URL**
```http
POST /api/v1/media/presigned-url
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "filename": "diagram.png",
  "content_type": "image/png",
  "file_size": 245678,
  "category": "image",  // optional: auto-detected if not provided
  "context": "lesson_123",  // optional: for tracking
  "alt_text": "System architecture diagram"  // optional
}
```

**Response:**
```json
{
  "upload_url": "https://abc123.r2.cloudflarestorage.com/...",
  "file_key": "media/image/2025/01/uuid.png",
  "public_url": "https://cdn.example.com/media/image/2025/01/uuid.png",
  "category": "image",
  "expires_in": 3600,
  "max_file_size": 10485760
}
```

---

### **3. Upload File to R2**
```http
PUT {upload_url}
Content-Type: {content_type}
Body: {file_binary}
```

**JavaScript Example:**
```javascript
// Using fetch
const response = await fetch(upload_url, {
  method: 'PUT',
  headers: {
    'Content-Type': content_type
  },
  body: file  // File object from input
});

// Using axios
await axios.put(upload_url, file, {
  headers: {
    'Content-Type': content_type
  }
});
```

---

### **4. Confirm Upload**
```http
POST /api/v1/media/confirm-upload
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "file_key": "media/image/2025/01/uuid.png",
  "file_name": "diagram.png",
  "file_size": 245678,
  "content_type": "image/png",
  "category": "image",
  "context": "lesson_123",
  "alt_text": "System architecture diagram"
}
```

**Response:**
```json
{
  "id": "67890...",
  "file_key": "media/image/2025/01/uuid.png",
  "file_name": "diagram.png",
  "file_size": 245678,
  "content_type": "image/png",
  "category": "image",
  "public_url": "https://cdn.example.com/media/image/2025/01/uuid.png",
  "uploaded_by": "user_id",
  "uploaded_at": "2025-01-07T10:30:00Z",
  "context": "lesson_123",
  "alt_text": "System architecture diagram"
}
```

---

### **5. Get My Uploads**
```http
GET /api/v1/media/my-uploads?category=image&page=1&per_page=20
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [...],
  "total": 45,
  "page": 1,
  "per_page": 20
}
```

---

### **6. Delete Media**
```http
DELETE /api/v1/media/{file_key}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "message": "Media file deleted successfully"
}
```

---

## 💻 **FRONTEND IMPLEMENTATION**

### **React/TypeScript Example:**

```typescript
// 1. Upload Hook
import { useState } from 'react';
import axios from 'axios';

interface UploadProgress {
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  url?: string;
  error?: string;
}

export const useMediaUpload = () => {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  
  const uploadFile = async (file: File, context?: string) => {
    const uploadId = Date.now().toString();
    
    try {
      // Add to upload queue
      setUploads(prev => [...prev, {
        filename: file.name,
        progress: 0,
        status: 'uploading'
      }]);
      
      // Step 1: Get pre-signed URL
      const { data: presigned } = await axios.post('/api/v1/media/presigned-url', {
        filename: file.name,
        content_type: file.type,
        file_size: file.size,
        context
      });
      
      // Update progress
      setUploads(prev => prev.map(u => 
        u.filename === file.name 
          ? { ...u, progress: 10 } 
          : u
      ));
      
      // Step 2: Upload to R2
      await axios.put(presigned.upload_url, file, {
        headers: {
          'Content-Type': file.type
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 90) / (progressEvent.total || 1)
          ) + 10; // 10-100%
          
          setUploads(prev => prev.map(u => 
            u.filename === file.name 
              ? { ...u, progress: percentCompleted } 
              : u
          ));
        }
      });
      
      // Update status
      setUploads(prev => prev.map(u => 
        u.filename === file.name 
          ? { ...u, status: 'processing' } 
          : u
      ));
      
      // Step 3: Confirm upload
      const { data: confirmed } = await axios.post('/api/v1/media/confirm-upload', {
        file_key: presigned.file_key,
        file_name: file.name,
        file_size: file.size,
        content_type: file.type,
        category: presigned.category,
        context
      });
      
      // Complete
      setUploads(prev => prev.map(u => 
        u.filename === file.name 
          ? { 
              ...u, 
              progress: 100, 
              status: 'completed',
              url: confirmed.public_url
            } 
          : u
      ));
      
      return confirmed.public_url;
      
    } catch (error) {
      setUploads(prev => prev.map(u => 
        u.filename === file.name 
          ? { 
              ...u, 
              status: 'error',
              error: error.message
            } 
          : u
      ));
      
      throw error;
    }
  };
  
  return { uploads, uploadFile };
};
```

---

### **Usage in Component:**

```typescript
import { useMediaUpload } from './hooks/useMediaUpload';

function LessonEditor() {
  const { uploads, uploadFile } = useMediaUpload();
  const [markdown, setMarkdown] = useState('');
  
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      const url = await uploadFile(file, 'lesson_123');
      
      // Insert markdown with uploaded image URL
      const imageMarkdown = `\n![${file.name}](${url})\n`;
      setMarkdown(prev => prev + imageMarkdown);
      
    } catch (error) {
      alert('Upload failed: ' + error.message);
    }
  };
  
  return (
    <div>
      <input 
        type="file" 
        accept="image/*" 
        onChange={handleImageUpload}
      />
      
      {uploads.map(upload => (
        <div key={upload.filename}>
          <p>{upload.filename}</p>
          <progress value={upload.progress} max={100} />
          <span>{upload.status}</span>
        </div>
      ))}
      
      <textarea 
        value={markdown}
        onChange={(e) => setMarkdown(e.target.value)}
        placeholder="Write your lesson content..."
      />
    </div>
  );
}
```

---

### **MDEditor Integration (react-markdown-editor-lite):**

```typescript
import MdEditor from 'react-markdown-editor-lite';
import 'react-markdown-editor-lite/lib/index.css';

function MarkdownLessonEditor() {
  const { uploadFile } = useMediaUpload();
  
  const handleImageUpload = async (file: File) => {
    const url = await uploadFile(file, 'lesson_123');
    return url;
  };
  
  return (
    <MdEditor
      style={{ height: '500px' }}
      renderHTML={(text) => mdParser.render(text)}
      onImageUpload={handleImageUpload}
      imageAccept=".jpg,.png,.gif,.webp"
    />
  );
}
```

---

## 🔒 **SECURITY FEATURES**

1. **Time-limited URLs**: Expire after 1 hour
2. **File size validation**: Per-category limits
3. **Content type validation**: Only allowed MIME types
4. **Authentication required**: Bearer token needed
5. **Filename sanitization**: Remove dangerous characters
6. **Soft delete**: Files marked as deleted, not immediately removed

---

## 🏗️ **FILE ORGANIZATION IN R2**

```
media/
  ├── image/
  │   └── 2025/
  │       └── 01/
  │           ├── uuid1.jpg
  │           └── uuid2.png
  ├── video/
  │   └── 2025/01/
  ├── audio/
  │   └── 2025/01/
  ├── document/
  │   └── 2025/01/
  └── ...
```

---

## ⚠️ **ERROR HANDLING**

### **Common Errors:**

```javascript
// File too large
{
  "detail": "File too large. Maximum size for image is 10MB"
}

// Invalid file type
{
  "detail": "Invalid content type for image. Allowed: image/jpeg, image/png, ..."
}

// Upload failed
{
  "detail": "Failed to generate pre-signed URL: ..."
}

// File not found after upload
{
  "detail": "File not found in storage"
}
```

---

## 📊 **USAGE IN LESSONS**

### **Example Lesson with Multiple Media:**

```markdown
# Lesson: Introduction to Web Development

## Overview
This lesson covers the basics of HTML, CSS, and JavaScript.

![Web Stack](https://cdn.example.com/media/image/2025/01/web-stack.png)

## Video Tutorial
Watch this introduction video:

<video controls>
  <source src="https://cdn.example.com/media/video/2025/01/intro.mp4" type="video/mp4">
</video>

## Practice Files
Download the starter template:
[Download ZIP](https://cdn.example.com/media/archive/2025/01/starter.zip)

## Reference Materials
- [HTML Guide (PDF)](https://cdn.example.com/media/document/2025/01/html-guide.pdf)
- [CSS Cheat Sheet (PDF)](https://cdn.example.com/media/document/2025/01/css-cheat.pdf)
```

---

## 🎨 **BEST PRACTICES**

1. **Optimize before upload**: Compress images, videos
2. **Use descriptive filenames**: `lesson-1-diagram.png` vs `image.png`
3. **Add alt text**: For accessibility
4. **Set context**: Link media to lessons for tracking
5. **Clean up**: Delete unused media files
6. **Use appropriate formats**:
   - Images: WebP for photos, PNG for graphics
   - Videos: MP4 for compatibility
   - Documents: PDF for portability

---

## 🧪 **TESTING**

```bash
# Test upload with curl
curl -X POST http://localhost:8000/api/v1/media/presigned-url \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.png",
    "content_type": "image/png",
    "file_size": 12345
  }'

# Upload to R2
curl -X PUT "PRESIGNED_URL" \
  -H "Content-Type: image/png" \
  --data-binary @test.png

# Confirm upload
curl -X POST http://localhost:8000/api/v1/media/confirm-upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_key": "media/image/2025/01/uuid.png",
    "file_name": "test.png",
    "file_size": 12345,
    "content_type": "image/png",
    "category": "image"
  }'
```

---

## 📞 **SUPPORT**

For issues or questions:
- Check error messages in API response
- Verify file size and type limits
- Ensure proper authentication
- Check R2 configuration in `.env`

---

**Happy Uploading! 🚀**
