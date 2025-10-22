# API Documentation: Update Module Endpoint

**Endpoint:** `PUT /api/v1/modules/{module_id}`  
**Authentication:** Required (Bearer Token)  
**Authorization:** Module creator or collaborators only

---

## 📋 Request Payload

### **Available Fields**

You can update any of the following fields. **All fields are optional** - only include the fields you want to update.

```typescript
{
  // Basic Information
  "title"?: string,                    // Module title (will auto-generate new slug)
  "description"?: string,              // Module description
  
  // Classification & Organization
  "topic_tags"?: string[],             // Array of topic tags
  "difficulty_level"?: string,         // "easy" | "medium" | "hard"
  
  // Learning Content
  "learning_objectives"?: string[],    // Array of learning objectives
  "prerequisites"?: string[],          // Array of prerequisites
  
  // Completion Rules
  "completion_criteria"?: {            // Module completion requirements
    "type": string,                    // "all_required" | "percentage" | "points" | "custom"
    "required_percentage": number,     // 0-100
    "minimum_score": number,           // 0-100
    "custom_rules": array              // Optional custom rules
  },
  
  // Visibility & Status
  "visibility"?: string,               // "public" | "private" | "shared"
  "status"?: string                    // "draft" | "published" | "archived"
}
```

---

## 📝 Field Descriptions

### **1. title** (string)
**Description:** Module title  
**Max Length:** 200 characters  
**Auto-effect:** Will automatically generate new slug  

**Example:**
```json
{
  "title": "Matematika Dasar Kelas 10"
}
```

---

### **2. description** (string)
**Description:** Detailed description of the module  
**Max Length:** 2000 characters  

**Example:**
```json
{
  "description": "Module ini membahas dasar-dasar matematika untuk kelas 10 termasuk aljabar, geometri, dan trigonometri."
}
```

---

### **3. topic_tags** (array of strings)
**Description:** Tags for categorization and search  
**Type:** Array of strings  

**Example:**
```json
{
  "topic_tags": ["aljabar", "geometri", "trigonometri", "matematika"]
}
```

**Empty array:**
```json
{
  "topic_tags": []
}
```

---

### **4. difficulty_level** (string)
**Description:** Overall difficulty of the module  
**Allowed Values:**
- `"easy"`
- `"medium"`
- `"hard"`

**Example:**
```json
{
  "difficulty_level": "medium"
}
```

---

### **5. learning_objectives** (array of strings)
**Description:** List of learning objectives/goals  
**Type:** Array of strings  

**Example:**
```json
{
  "learning_objectives": [
    "Memahami konsep dasar aljabar",
    "Menguasai operasi matematika dasar",
    "Mampu menyelesaikan soal cerita",
    "Memahami grafik fungsi linear"
  ]
}
```

**Empty array:**
```json
{
  "learning_objectives": []
}
```

---

### **6. prerequisites** (array of strings)
**Description:** Required prior knowledge or modules  
**Type:** Array of strings  

**Example:**
```json
{
  "prerequisites": [
    "Matematika Kelas 9",
    "Dasar-dasar Aljabar",
    "Operasi Bilangan"
  ]
}
```

**Empty array:**
```json
{
  "prerequisites": []
}
```

---

### **7. completion_criteria** (object)
**Description:** Rules untuk menentukan kapan siswa dianggap selesai menyelesaikan module  
**Type:** Object dengan structure khusus

**Structure:**
```json
{
  "type": "all_required | percentage | points | custom",
  "required_percentage": 0-100,
  "minimum_score": 0-100,
  "custom_rules": []
}
```

**Type Options:**
- `"all_required"` - Siswa harus selesaikan semua required lessons
- `"percentage"` - Siswa cukup selesaikan X% lessons
- `"points"` - Siswa harus kumpulkan X poin total
- `"custom"` - Aturan custom

**Example - Basic (No Grading):**
```json
{
  "completion_criteria": {
    "type": "all_required",
    "required_percentage": 100,
    "minimum_score": 0
  }
}
```

**Example - Graded Course:**
```json
{
  "completion_criteria": {
    "type": "all_required",
    "required_percentage": 100,
    "minimum_score": 75
  }
}
```
**Meaning:** Siswa harus selesaikan semua lessons dengan skor minimal 75.

**Example - Flexible:**
```json
{
  "completion_criteria": {
    "type": "percentage",
    "required_percentage": 80,
    "minimum_score": 70
  }
}
```
**Meaning:** Siswa cukup selesaikan 80% lessons dengan skor minimal 70.

**📚 For detailed guide:** See `docs/COMPLETION_CRITERIA_GUIDE.md`

---

### **8. visibility** (string)
**Description:** Who can see this module  
**Allowed Values:**
- `"public"` - Everyone can see
- `"private"` - Only creator can see
- `"shared"` - Creator and collaborators can see

**Example:**
```json
{
  "visibility": "public"
}
```

---

### **9. status** (string)
**Description:** Module lifecycle status  
**Allowed Values:**
- `"draft"` - Still being edited
- `"published"` - Available for use (sets `published_at`)
- `"archived"` - No longer active (sets `archived_at`)

**Example:**
```json
{
  "status": "published"
}
```

**Effects:**
- Setting to `"published"` → automatically sets `published_at` to current timestamp
- Setting to `"archived"` → automatically sets `archived_at` to current timestamp

---

## 🔍 Complete Examples

### **Example 1: Update Title Only**

**Request:**
```bash
PUT /api/v1/modules/68f8dad6a9717e5c6dc6b851
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "title": "Matematika Tingkat Lanjut Kelas 10"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module updated successfully",
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "title": "Matematika Tingkat Lanjut Kelas 10",
    "slug": "matematika-tingkat-lanjut-kelas-10",
    "description": "...",
    "updated_at": "2025-01-16T12:30:00.000Z",
    ...
  }
}
```

---

### **Example 2: Update Multiple Fields**

**Request:**
```bash
PUT /api/v1/modules/68f8dad6a9717e5c6dc6b851
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "title": "Matematika Dasar - Revisi 2025",
  "description": "Module matematika dasar yang telah diperbarui dengan materi terbaru",
  "difficulty_level": "medium",
  "topic_tags": ["matematika", "aljabar", "geometri"],
  "visibility": "public"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module updated successfully",
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "title": "Matematika Dasar - Revisi 2025",
    "slug": "matematika-dasar-revisi-2025",
    "description": "Module matematika dasar yang telah diperbarui dengan materi terbaru",
    "difficulty_level": "medium",
    "topic_tags": ["matematika", "aljabar", "geometri"],
    "visibility": "public",
    "updated_at": "2025-01-16T12:35:00.000Z",
    ...
  }
}
```

---

### **Example 3: Update Learning Content**

**Request:**
```bash
PUT /api/v1/modules/68f8dad6a9717e5c6dc6b851
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "learning_objectives": [
    "Memahami konsep matriks dan operasinya",
    "Menguasai determinan dan invers matriks",
    "Mampu menyelesaikan sistem persamaan linear",
    "Memahami aplikasi matriks dalam kehidupan sehari-hari"
  ],
  "prerequisites": [
    "Operasi Bilangan",
    "Aljabar Dasar",
    "Sistem Persamaan Linear"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module updated successfully",
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "learning_objectives": [
      "Memahami konsep matriks dan operasinya",
      "Menguasai determinan dan invers matriks",
      "Mampu menyelesaikan sistem persamaan linear",
      "Memahami aplikasi matriks dalam kehidupan sehari-hari"
    ],
    "prerequisites": [
      "Operasi Bilangan",
      "Aljabar Dasar",
      "Sistem Persamaan Linear"
    ],
    "updated_at": "2025-01-16T12:40:00.000Z",
    ...
  }
}
```

---

### **Example 4: Publish Module**

**Request:**
```bash
PUT /api/v1/modules/68f8dad6a9717e5c6dc6b851
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "status": "published",
  "visibility": "public"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module updated successfully",
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "status": "published",
    "visibility": "public",
    "published_at": "2025-01-16T12:45:00.000Z",
    "updated_at": "2025-01-16T12:45:00.000Z",
    ...
  }
}
```

---

### **Example 5: Archive Module**

**Request:**
```bash
PUT /api/v1/modules/68f8dad6a9717e5c6dc6b851
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "status": "archived"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module updated successfully",
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "status": "archived",
    "archived_at": "2025-01-16T12:50:00.000Z",
    "updated_at": "2025-01-16T12:50:00.000Z",
    ...
  }
}
```

---

### **Example 6: Clear Arrays (Set to Empty)**

**Request:**
```bash
PUT /api/v1/modules/68f8dad6a9717e5c6dc6b851
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "topic_tags": [],
  "learning_objectives": [],
  "prerequisites": []
}
```

**Response:**
```json
{
  "success": true,
  "message": "Module updated successfully",
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "topic_tags": [],
    "learning_objectives": [],
    "prerequisites": [],
    "updated_at": "2025-01-16T12:55:00.000Z",
    ...
  }
}
```

---

## ⚠️ Important Notes

### **Fields You CANNOT Update via This Endpoint:**

The following fields **cannot** be updated through this endpoint:

1. ❌ `subject_id` - Subject cannot be changed after creation
2. ❌ `grade_level` - Grade level cannot be changed after creation
3. ❌ `created_by` - Creator cannot be changed
4. ❌ `collaborators` - Use dedicated collaborator management endpoints
5. ❌ `lesson_refs` - Use dedicated lesson management endpoints:
   - `POST /modules/{id}/lessons` - Add lesson
   - `DELETE /modules/{id}/lessons/{lesson_id}` - Remove lesson
   - `PUT /modules/{id}/lessons/reorder` - Reorder lessons
6. ❌ `assessments` - Use dedicated assessment endpoints
7. ❌ `completion_criteria` - Not editable via this endpoint
8. ❌ `metadata` - Auto-calculated, cannot be manually updated

---

## 🚫 Error Responses

### **404 Not Found**

**When:** Module doesn't exist

```json
{
  "detail": "Module not found"
}
```

---

### **403 Forbidden**

**When:** You don't have permission to edit (not creator or collaborator)

```json
{
  "detail": "Not authorized to edit this module"
}
```

---

### **400 Bad Request**

**When:** Invalid field values

```json
{
  "detail": "Invalid difficulty_level. Must be 'easy', 'medium', or 'hard'"
}
```

---

### **422 Validation Error**

**When:** Invalid data types

```json
{
  "detail": [
    {
      "loc": ["body", "topic_tags"],
      "msg": "value is not a valid list",
      "type": "type_error.list"
    }
  ]
}
```

---

## 💡 Best Practices

### **1. Update Only What Changed**

**❌ Don't:**
```json
{
  "title": "Same title",
  "description": "Same description",
  "topic_tags": ["same", "tags"],
  "status": "draft"
}
```

**✅ Do:**
```json
{
  "status": "published"
}
```

---

### **2. Validate Before Submitting**

```javascript
// Frontend validation example
const updates = {};

if (newTitle !== currentTitle) {
  updates.title = newTitle;
}

if (newDescription !== currentDescription) {
  updates.description = newDescription;
}

// Only send if something changed
if (Object.keys(updates).length > 0) {
  await updateModule(moduleId, updates);
}
```

---

### **3. Handle Status Changes Carefully**

**Publishing checklist:**
```javascript
// Before publishing, ensure:
const canPublish = (
  module.title &&
  module.description &&
  module.lesson_refs.length > 0 &&
  module.learning_objectives.length > 0
);

if (canPublish) {
  await updateModule(moduleId, { status: "published" });
} else {
  alert("Module incomplete. Cannot publish.");
}
```

---

### **4. Provide User Feedback**

```javascript
try {
  const response = await updateModule(moduleId, updates);
  
  if (response.success) {
    toast.success("Module updated successfully!");
    
    // Handle specific status changes
    if (updates.status === "published") {
      toast.info("Module is now public!");
    }
  }
} catch (error) {
  if (error.status === 403) {
    toast.error("You don't have permission to edit this module");
  } else {
    toast.error("Failed to update module");
  }
}
```

---

## 🔗 Related Endpoints

**Module Management:**
- `GET /api/v1/modules/{id}` - Get module details
- `POST /api/v1/modules` - Create new module
- `DELETE /api/v1/modules/{id}` - Delete module

**Lesson Management:**
- `POST /api/v1/modules/{id}/lessons` - Add lesson to module
- `DELETE /api/v1/modules/{id}/lessons/{lesson_id}` - Remove lesson
- `PUT /api/v1/modules/{id}/lessons/reorder` - Reorder lessons

**Collaborator Management:**
- (To be implemented)

---

## 📱 Frontend Integration Examples

### **React/Next.js Example**

```typescript
// api/modules.ts
export async function updateModule(
  moduleId: string,
  updates: {
    title?: string;
    description?: string;
    topic_tags?: string[];
    difficulty_level?: 'easy' | 'medium' | 'hard';
    learning_objectives?: string[];
    prerequisites?: string[];
    visibility?: 'public' | 'private' | 'shared';
    status?: 'draft' | 'published' | 'archived';
  }
) {
  const response = await fetch(`/api/v1/modules/${moduleId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`
    },
    body: JSON.stringify(updates)
  });
  
  if (!response.ok) {
    throw new Error('Failed to update module');
  }
  
  return response.json();
}

// Usage in component
const handleUpdate = async () => {
  try {
    const result = await updateModule(moduleId, {
      title: formData.title,
      description: formData.description,
      status: 'published'
    });
    
    console.log('Module updated:', result.module);
  } catch (error) {
    console.error('Update failed:', error);
  }
};
```

---

### **Vue.js Example**

```javascript
// composables/useModule.js
export function useModule() {
  const updateModule = async (moduleId, updates) => {
    try {
      const response = await $fetch(`/api/v1/modules/${moduleId}`, {
        method: 'PUT',
        body: updates,
        headers: {
          'Authorization': `Bearer ${authToken.value}`
        }
      });
      
      return response;
    } catch (error) {
      throw error;
    }
  };
  
  return { updateModule };
}

// In component
const { updateModule } = useModule();

const handleSave = async () => {
  await updateModule(props.moduleId, {
    title: title.value,
    difficulty_level: difficulty.value
  });
};
```

---

## ✅ Summary

**Endpoint:** `PUT /api/v1/modules/{module_id}`

**Updatable Fields:**
1. ✅ title
2. ✅ description
3. ✅ topic_tags
4. ✅ difficulty_level
5. ✅ learning_objectives
6. ✅ prerequisites
7. ✅ completion_criteria
8. ✅ visibility
9. ✅ status

**All fields optional** - only send what you want to update!

**Authorization:** Only creator or collaborators can update

**Auto-effects:**
- Updating `title` → generates new `slug`
- Setting `status` to `"published"` → sets `published_at`
- Setting `status` to `"archived"` → sets `archived_at`
- Any update → updates `updated_at` timestamp

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Status:** COMPLETE
