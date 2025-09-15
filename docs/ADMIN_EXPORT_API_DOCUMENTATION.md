# 🚀 Smart Study Hub - Admin Export System Documentation

## 🎯 Overview

**Admin Export System** adalah sistem export data yang sangat powerful dan fleksibel yang dirancang khusus untuk admin users. Sistem ini memungkinkan export data kompleks dengan nested joins unlimited depth, formatting profesional, dan kontrol penuh terhadap output data.

## 🌟 Apa yang Bisa Dilakukan dengan Export System Ini?

### 📊 **Export Data Kompleks**
- Export data dari multiple collections sekaligus
- Join data antar collections dengan unlimited depth
- Filter data di setiap level join
- Sort dan limit results
- Export ke format Excel, CSV, atau JSON

### 🔗 **Nested Joins Unlimited**
- Contoh: `users → profiles → classes → expertise_programs`
- Setiap level join bisa punya filter sendiri
- Support join types: `lookup` dan `unwind`
- Preserve atau skip empty data

### 🎨 **Professional Data Formatting**
- Field names dalam Bahasa Indonesia (user-friendly)
- Hide technical ObjectIDs
- Clean, readable column headers
- Smart data type formatting

### 🚀 **Performance & Scale**
- Async processing untuk data besar
- Progress tracking untuk long-running exports
- Query analysis dan performance insights
- Smart caching dan optimization

---

## 🆕 Fitur Lengkap yang Tersedia

### 1. **Advanced Query Builder**
- **Multiple Collection Joins**: Join unlimited collections
- **Complex Filtering**: Support semua MongoDB operators
- **Nested Filtering**: Filter di setiap level join
- **Sorting & Pagination**: Control output order dan size
- **Aggregation**: Group by, having, dan advanced operations

### 2. **Smart Field System**
- **Field Aliases**: Technical names → User-friendly names
- **Field Suggestions**: Smart recommendations berdasarkan collection
- **Field Categories**: Organized grouping (user_info, academic_info, etc.)
- **Field Validation**: Prevent invalid field references

### 3. **Export Formats & Options**
- **Multiple Formats**: Excel (.xlsx), CSV (.csv), JSON (.json)
- **Professional Styling**: Excel dengan formatting dan colors
- **Clean Headers**: Hide IDs, use aliases
- **Data Optimization**: Remove empty fields, flatten structures

### 4. **Computed Fields** ⚠️ *Limited*
- **Simple Concatenation**: Gabungkan fields dari main collection
- **Template System**: `"{field1} - {field2}"` format
- **⚠️ Limitation**: Hanya bekerja untuk main collection, nested fields belum support

### 5. **Performance & Monitoring**
- **Query Analysis**: Performance insights dan warnings
- **Async Processing**: Background processing untuk query berat
- **Progress Tracking**: Real-time status untuk long exports
- **Error Handling**: Comprehensive error reporting

### 6. **Security & Access Control**
- **Admin Only**: Semua endpoints require admin authentication
- **Collection Validation**: Prevent access to unauthorized collections
- **Field Validation**: Validate field existence dan relationships
- **Query Limits**: Prevent resource exhaustion

---

## 🌐 API Endpoints Lengkap

### Base URL: `/api/v1/admin/exports`

| Method | Endpoint | Fungsi | Kegunaan |
|--------|----------|--------|---------|
| `GET` | `/collections/relationships` | **Collection Discovery** | Melihat relasi antar collections, foreign keys, dan join possibilities |
| `GET` | `/fields/suggestions/{collection}` | **Smart Field Helper** | Mendapatkan field suggestions dengan aliases Bahasa Indonesia |
| `POST` | `/validate` | **Config Validator** | Validasi export configuration sebelum execute (recommended) |
| `POST` | `/execute` | **Main Export** | Eksekusi export dengan semua fitur advanced |
| `POST` | `/analyze` | **Performance Analyzer** | Analisis query complexity, execution time, dan optimization tips |

### 🎯 **Cara Kerja Complete Export Flow:**

1. **Discovery Phase** → `GET /collections/relationships`
   - Explore available collections dan relationships
   - Understand data structure untuk planning

2. **Planning Phase** → `GET /fields/suggestions/{collection}`
   - Get field recommendations dengan aliases
   - Build form untuk user selection

3. **Validation Phase** → `POST /validate`
   - Validate configuration sebelum execution
   - Get warnings dan performance estimates

4. **Execution Phase** → `POST /execute`
   - Execute actual export
   - Handle sync atau async processing

5. **Monitoring Phase** → `POST /analyze` (optional)
   - Analyze query untuk optimization
   - Get performance insights

---

## 📊 Data Structures

### 1. **Advanced Export Request**

```typescript
interface AdvancedExportRequest {
  config: AdvancedExportConfig;
  format: 'excel' | 'csv' | 'json';
  filename?: string;
  async_export?: boolean;
  explain?: boolean;
  dry_run?: boolean;
  formatting?: ExportFormattingOptions;
}
```

### 2. **Export Configuration**

```typescript
interface AdvancedExportConfig {
  main_collection: string;
  fields?: string[];
  exclude_fields?: string[];
  filters?: AdvancedFilterCondition[];
  joins?: AdvancedJoinConfig[];
  group_by?: string[];
  having?: AdvancedFilterCondition[];
  sort?: Record<string, 1 | -1>;
  skip?: number;
  limit?: number;
  allow_disk_use?: boolean;
  max_time_ms?: number;
}
```

### 3. **Join Configuration**

```typescript
interface AdvancedJoinConfig {
  collection: string;
  local_field: string;
  foreign_field: string;
  alias?: string;
  join_type: 'lookup' | 'unwind';
  fields?: string[];
  exclude_fields?: string[];
  filters?: AdvancedFilterCondition[];
  joins?: AdvancedJoinConfig[]; // Nested joins support!
  preserve_null_and_empty_arrays?: boolean;
  limit?: number;
  sort?: Record<string, 1 | -1>;
}
```

### 4. **Filter Conditions**

```typescript
interface AdvancedFilterCondition {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'nin' | 'exists' | 'regex';
  value: any;
  options?: string; // untuk regex options
}
```

### 5. **Formatting Options**

```typescript
interface ExportFormattingOptions {
  exclude_ids?: boolean; // default: true
  use_aliases?: boolean; // default: true  
  flatten_nested?: boolean; // default: true
  include_empty_fields?: boolean; // default: false
}
```

---

## 🎨 Use Cases Lengkap & Format Data

### 📈 **1. Export Data Students Complete**

**Kebutuhan:** Export semua data siswa dengan info kelas dan jurusan

```typescript
const exportStudentsComplete = {
  config: {
    main_collection: 'users',
    fields: ['email', 'login_id', 'profile'], // Must include 'profile' for joins!
    filters: [
      { field: 'roles', operator: 'eq', value: 'student' },
      { field: 'is_active', operator: 'eq', value: true }
    ],
    joins: [
      {
        collection: 'profiles',
        local_field: 'profile_id',
        foreign_field: '_id',
        alias: 'profile',
        join_type: 'lookup',
        fields: ['full_name', 'gender', 'birth_date', 'phone_number', 'class_detail'],
        joins: [
          {
            collection: 'classes',
            local_field: 'class_id',
            foreign_field: '_id',
            alias: 'class_detail',
            join_type: 'lookup',
            fields: ['name', 'grade_level', 'academic_year', 'expertise'],
            joins: [
              {
                collection: 'expertise_programs',
                local_field: 'expertise_id',
                foreign_field: '_id',
                alias: 'expertise',
                join_type: 'lookup',
                fields: ['name', 'abbreviation']
              }
            ]
          }
        ]
      }
    ],
    sort: { 'login_id': 1 },
    limit: 1000
  },
  format: 'excel',
  filename: 'data_siswa_lengkap',
  formatting: {
    exclude_ids: true,
    use_aliases: true,
    flatten_nested: true,
    include_empty_fields: false
  }
};
```

**Output Excel:**
| Email | NIS/NIP | Nama Lengkap | Jenis Kelamin | Tanggal Lahir | Nomor Telepon | Nama Kelas | Tingkat Kelas | Tahun Akademik | Nama Jurusan | Singkatan Jurusan |
|-------|---------|--------------|---------------|---------------|---------------|------------|---------------|----------------|--------------|-------------------|
| alex@gmail.com | 79111967 | Alexander Grahambel | Laki Laki | 15/09/2005 | 0812-3456-7890 | 2 | 12 | 2025/2026 | Teknik Komputer dan Jaringan | TKJ |

### 🏆 **2. Export Data Exam Results**

**Kebutuhan:** Export hasil ujian dengan info siswa dan mata pelajaran

```typescript
const exportExamResults = {
  config: {
    main_collection: 'exam_sessions',
    fields: ['score', 'started_at', 'submitted_at', 'time_spent_minutes', 'student', 'exam'],
    filters: [
      { field: 'status', operator: 'eq', value: 'graded' },
      { field: 'score', operator: 'gte', value: 0 }
    ],
    joins: [
      {
        collection: 'users',
        local_field: 'student_id',
        foreign_field: '_id',
        alias: 'student',
        join_type: 'lookup',
        fields: ['login_id', 'email', 'student_profile'],
        filters: [{ field: 'roles', operator: 'eq', value: 'student' }],
        joins: [
          {
            collection: 'profiles',
            local_field: 'profile_id',
            foreign_field: '_id',
            alias: 'student_profile',
            join_type: 'lookup',
            fields: ['full_name']
          }
        ]
      },
      {
        collection: 'exams',
        local_field: 'exam_id',
        foreign_field: '_id',
        alias: 'exam',
        join_type: 'lookup',
        fields: ['title', 'exam_type', 'duration_minutes']
      }
    ],
    sort: { 'score': -1 }, // Sort by score descending
    limit: 500
  },
  format: 'excel',
  filename: 'hasil_ujian_lengkap'
};
```

**Output Excel:**
| Skor | Waktu Mulai | Waktu Submit | Durasi (Menit) | NIS/NIP | Email | Nama Lengkap | Judul Ujian | Jenis Ujian |
|------|-------------|--------------|----------------|---------|-------|--------------|-------------|-------------|
| 95.5 | 15/09/2025 08:00 | 15/09/2025 09:30 | 90 | 79111967 | alex@gmail.com | Alexander Grahambel | UTS Matematika | official_uts |

### 📅 **3. Export Data Teachers dengan Teaching Assignments**

```typescript
const exportTeachers = {
  config: {
    main_collection: 'users',
    fields: ['email', 'login_id', 'profile'],
    filters: [{ field: 'roles', operator: 'eq', value: 'teacher' }],
    joins: [
      {
        collection: 'profiles',
        local_field: 'profile_id',
        foreign_field: '_id',
        alias: 'profile',
        join_type: 'lookup',
        fields: ['full_name', 'phone_number']
      }
    ]
  },
  format: 'csv',
  formatting: { use_aliases: true, exclude_ids: true }
};
```

### 🧾 **4. Computed Fields Usage** ⚠️ *Limited Support*

**⚠️ IMPORTANT LIMITATION:** Computed fields saat ini **hanya bekerja untuk main collection fields**. Nested joined fields belum support!

```typescript
// ✅ WORKS - Main collection fields only
const computedFieldsWorking = {
  config: {
    main_collection: 'users',
    fields: ['email', 'login_id'], // Main collection fields
    filters: [{ field: 'roles', operator: 'eq', value: 'student' }],
    limit: 100
  },
  format: 'excel',
  formatting: {
    exclude_ids: true,
    use_aliases: true,
    computed_fields: [
      {
        name: 'student_info',
        alias: 'Info Siswa',
        template: '{nis} - {email}', // ✅ Works because both are main collection fields
        fields: ['login_id', 'email']
      }
    ]
  }
};

// ❌ DOESN'T WORK - Nested fields
const computedFieldsNotWorking = {
  config: {
    main_collection: 'users',
    fields: ['email', 'login_id', 'profile'],
    joins: [{
      collection: 'profiles',
      local_field: 'profile_id',
      foreign_field: '_id',
      alias: 'profile',
      join_type: 'lookup',
      fields: ['full_name']
    }]
  },
  format: 'excel',
  formatting: {
    computed_fields: [
      {
        name: 'full_identity',
        alias: 'Identitas Lengkap',
        template: '{nis} - {nama}', // ❌ Won't work - 'nama' from nested field
        fields: ['login_id', 'profile.full_name'] // ❌ profile.full_name won't extract
      }
    ]
  }
};
```

**Result computed fields yang bekerja:**
| Email | NIS/NIP | Info Siswa |
|-------|---------|------------|
| alex@gmail.com | 79111967 | 79111967 - alex@gmail.com |

### 📄 **5. Export Format Options Lengkap**

#### **Excel Format (.xlsx)**
- **Professional styling** dengan colors dan formatting
- **Auto-width columns** sesuai content
- **Header formatting** dengan background color
- **Data type formatting** (dates, numbers, etc.)

#### **CSV Format (.csv)**  
- **UTF-8 encoding** untuk support karakter Indonesia
- **Configurable delimiter** (default: comma)
- **Header row included**
- **Clean data** tanpa styling

#### **JSON Format (.json)**
- **Raw data structure** preserved
- **Nested objects maintained**
- **Array structures intact**
- **Perfect untuk API integration**

---

## 📋 Field Suggestions API

### Request

```http
GET /api/v1/admin/exports/fields/suggestions/users
Authorization: Bearer {admin_token}
```

### Response

```typescript
interface FieldSuggestionsResponse {
  collection: string;
  available_fields: FieldInfo[];
  smart_suggestions: SmartSuggestions;
  total_fields: number;
}

interface FieldInfo {
  field: string;          // "login_id"
  alias: string;          // "NIS/NIP"
  category: string;       // "user_info"
}

interface SmartSuggestions {
  recommended: string[];  // Fields yang sering digunakan
  optional: string[];     // Fields opsional
  advanced: string[];     // Fields untuk advanced users
}
```

### Example Response

```json
{
  "collection": "users",
  "available_fields": [
    {
      "field": "login_id",
      "alias": "NIS/NIP",
      "category": "user_info"
    },
    {
      "field": "email",
      "alias": "Email",
      "category": "user_info"
    },
    {
      "field": "profile.full_name",
      "alias": "Nama Lengkap",
      "category": "profile_info"
    },
    {
      "field": "profile.class_detail.name",
      "alias": "Nama Kelas",
      "category": "academic_info"
    }
  ],
  "smart_suggestions": {
    "recommended": ["login_id", "email", "profile.full_name"],
    "optional": ["profile.gender", "profile.birth_date"],
    "advanced": ["is_active", "created_at"]
  },
  "total_fields": 25
}
```

---

## 🎯 Export Response

### Successful Response

```typescript
interface AdvancedExportResponse {
  success: boolean;
  message: string;
  task_id?: string;           // untuk async exports
  file_url?: string;          // untuk sync exports
  record_count?: number;
  execution_time_ms?: number;
  estimated_file_size?: string;
  pipeline_stages?: number;
  warnings?: string[];
}
```

### Example Response

```json
{
  "success": true,
  "message": "Advanced export completed successfully. 150 records exported.",
  "file_url": "/api/v1/exports/download/students_20250915_140759.xlsx",
  "record_count": 150,
  "execution_time_ms": 2340,
  "estimated_file_size": "45.2 KB",
  "pipeline_stages": 6,
  "warnings": [
    "Complex query: 3 joins with max depth 3"
  ]
}
```

---

## 📈 Field Aliases Mapping

### Users Collection
| Technical Field | Display Alias | Category |
|----------------|---------------|----------|
| `_id` | `ID` | technical |
| `login_id` | `NIS/NIP` | user_info |
| `email` | `Email` | user_info |
| `roles` | `Peran` | user_info |
| `is_active` | `Status Aktif` | user_info |

### Profiles Collection  
| Technical Field | Display Alias | Category |
|----------------|---------------|----------|
| `profile.full_name` | `Nama Lengkap` | profile_info |
| `profile.gender` | `Jenis Kelamin` | profile_info |
| `profile.birth_date` | `Tanggal Lahir` | profile_info |
| `profile.phone_number` | `Nomor Telepon` | profile_info |

### Classes & Expertise (Nested)
| Technical Field | Display Alias | Category |
|----------------|---------------|----------|
| `profile.class_detail.name` | `Nama Kelas` | academic_info |
| `profile.class_detail.grade_level` | `Tingkat Kelas` | academic_info |
| `profile.class_detail.expertise.name` | `Nama Jurusan` | academic_info |
| `profile.class_detail.expertise.abbreviation` | `Singkatan Jurusan` | academic_info |

---

## 🛠️ Frontend Implementation Tips

### 1. **Form Builder Integration**

```typescript
// Gunakan field suggestions untuk dynamic form
const buildExportForm = async (collection: string) => {
  const suggestions = await fetchFieldSuggestions(collection);
  
  // Kategorisasi fields untuk better UX
  const fieldCategories = {
    recommended: suggestions.smart_suggestions.recommended,
    optional: suggestions.smart_suggestions.optional,
    advanced: suggestions.smart_suggestions.advanced
  };
  
  // Build form sections berdasarkan category
  return buildFormSections(fieldCategories);
};
```

### 2. **Export Configuration Builder**

```typescript
// Helper untuk build export config
const buildExportConfig = (formData: FormData): AdvancedExportRequest => {
  return {
    config: {
      main_collection: formData.collection,
      fields: formData.selectedFields,
      filters: buildFilters(formData.filters),
      joins: buildJoins(formData.joins),
      limit: formData.limit || 1000
    },
    format: formData.format,
    formatting: {
      exclude_ids: formData.hideIds ?? true,
      use_aliases: formData.useAliases ?? true,
      flatten_nested: true,
      include_empty_fields: formData.showEmpty ?? false
    }
  };
};
```

### 3. **Progress Tracking untuk Async Exports**

```typescript
// Track async export progress
const trackExportProgress = async (taskId: string) => {
  const pollInterval = setInterval(async () => {
    const status = await fetchExportStatus(taskId);
    
    switch (status.status) {
      case 'processing':
        updateProgressBar(status.progress);
        break;
      case 'completed':
        clearInterval(pollInterval);
        downloadFile(status.file_url);
        break;
      case 'failed':
        clearInterval(pollInterval);
        showError(status.error_details);
        break;
    }
  }, 2000);
};
```

---

## ⚠️ Error Handling

### Common Error Responses

```typescript
// Validation Error
{
  "detail": "Invalid advanced export configuration: Collection 'invalid' not found"
}

// Permission Error  
{
  "detail": "Admin access required for advanced export functionality"
}

// Query Error
{
  "detail": "Failed to execute advanced export"
}
```

### Frontend Error Handling

```typescript
const handleExportError = (error: ApiError) => {
  switch (error.status) {
    case 400:
      showValidationError(error.detail);
      break;
    case 403:
      redirectToLogin();
      break;
    case 422:
      showFormErrors(error.detail);
      break;
    case 500:
      showServerError();
      break;
  }
};
```

---

## 🎯 Best Practices Complete Export System

### 1. **🚀 Performance & Scalability**
- **Always use `limit`** untuk dataset besar (recommended: 1000-5000 records)
- **Set `async_export: true`** untuk queries dengan >3 joins atau >1000 records
- **Use `dry_run: true`** untuk preview dan validation sebelum actual export
- **Monitor metrics**: `pipeline_stages`, `execution_time_ms`, `estimated_records`
- **Implement timeout**: Set reasonable timeout untuk avoid hanging requests

### 2. **📄 Data Quality & Formatting**
- **Always use `formatting` section** dengan options:
  ```typescript
  formatting: {
    exclude_ids: true,        // Hide technical ObjectIDs
    use_aliases: true,        // Use Bahasa Indonesia headers
    flatten_nested: true,     // Flatten nested structures
    include_empty_fields: false  // Skip empty data
  }
  ```
- **Include alias in main fields**: `fields: ['email', 'profile']` bukan hanya `['email']`
- **Use proper field selection**: Jangan request semua fields, pilih yang dibutuhkan saja

### 3. **🔗 Join Configuration Best Practices**
- **Critical**: Must include join alias dalam main collection fields!
  ```typescript
  // ✅ CORRECT
  fields: ['email', 'login_id', 'profile'],  // Include 'profile' for joins to work
  joins: [{
    collection: 'profiles',
    alias: 'profile'  // This alias must be in main fields!
  }]
  
  // ❌ WRONG
  fields: ['email', 'login_id'],  // Missing 'profile' = joins won't show data
  ```
- **Use meaningful aliases**: `alias: 'student_profile'` bukan generic names
- **Filter at appropriate level**: Put filters as close to source as possible
- **Preserve nulls wisely**: Use `preserve_null_and_empty_arrays: true` untuk optional data

### 4. **⚠️ Computed Fields Limitations**
- **Only works for main collection fields** - nested fields tidak support
- **Test carefully**: Validate computed field output sebelum production
- **Simple templates only**: Avoid complex logic dalam templates

### 5. **📱 Frontend UX Guidelines**
- **Progressive disclosure**: Start dengan basic options, show advanced on demand
- **Field suggestions**: Use `/fields/suggestions/{collection}` untuk dynamic forms
- **Validation first**: Always call `/validate` sebelum `/execute`
- **Progress tracking**: Implement proper loading states dan progress bars
- **Error handling**: Show meaningful error messages kepada users

### 6. **🔒 Security & Access Control**
- **Admin authentication required**: Semua endpoints butuh admin token
- **Validate on frontend**: Check user permissions sebelum show export options
- **Log export activities**: Track who exports what untuk audit trails
- **Rate limiting**: Implement proper rate limits pada frontend

### 7. **📦 File Management**
- **Unique filenames**: Use timestamps atau UUIDs untuk avoid conflicts
- **Cleanup old files**: Implement file cleanup untuk avoid storage bloat
- **Download handling**: Use proper download triggers dan error handling
- **File size warnings**: Warn users untuk large exports

---

## 🚀 Complete Working Example

### 📐 **Full Student Export Implementation**

```typescript
// Complete working example dengan semua best practices
class AdminExportService {
  private adminToken: string;
  
  constructor(token: string) {
    this.adminToken = token;
  }

  // 1. Get field suggestions untuk build form
  async getFieldSuggestions(collection: string) {
    const response = await fetch(`/api/v1/admin/exports/fields/suggestions/${collection}`, {
      headers: { 'Authorization': `Bearer ${this.adminToken}` }
    });
    return await response.json();
  }

  // 2. Validate configuration sebelum export
  async validateExport(config: AdvancedExportConfig) {
    const response = await fetch('/api/v1/admin/exports/validate', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ config })
    });
    
    if (!response.ok) {
      throw new Error(`Validation failed: ${response.statusText}`);
    }
    
    return await response.json();
  }

  // 3. Execute export dengan complete configuration
  async executeExport(): Promise<void> {
    try {
      // Build complete export configuration
      const exportRequest = {
        config: {
          main_collection: 'users',
          fields: ['email', 'login_id', 'profile'], // ❗ CRITICAL: Include 'profile' for joins!
          filters: [
            { field: 'roles', operator: 'eq', value: 'student' },
            { field: 'is_active', operator: 'eq', value: true }
          ],
          joins: [
            {
              collection: 'profiles',
              local_field: 'profile_id',
              foreign_field: '_id',
              alias: 'profile', // Must match field in main fields!
              join_type: 'lookup',
              fields: ['full_name', 'gender', 'birth_date', 'class_detail'],
              joins: [
                {
                  collection: 'classes',
                  local_field: 'class_id',
                  foreign_field: '_id',
                  alias: 'class_detail',
                  join_type: 'lookup',
                  fields: ['name', 'grade_level', 'expertise'],
                  joins: [
                    {
                      collection: 'expertise_programs',
                      local_field: 'expertise_id',
                      foreign_field: '_id',
                      alias: 'expertise',
                      join_type: 'lookup',
                      fields: ['name', 'abbreviation']
                    }
                  ]
                }
              ]
            }
          ],
          sort: { 'login_id': 1 },
          limit: 1000
        },
        format: 'excel',
        filename: 'data_siswa_lengkap',
        formatting: {
          exclude_ids: true,
          use_aliases: true,
          flatten_nested: true,
          include_empty_fields: false
        }
      };

      // Step 1: Validate first
      console.log('Validating export configuration...');
      const validation = await this.validateExport(exportRequest.config);
      
      if (!validation.valid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }

      console.log(`Validation passed. Estimated records: ${validation.estimated_records}`);
      if (validation.warnings?.length > 0) {
        console.warn('Warnings:', validation.warnings);
      }

      // Step 2: Execute export
      console.log('Executing export...');
      const exportResponse = await fetch('/api/v1/admin/exports/execute', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.adminToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(exportRequest)
      });

      if (!exportResponse.ok) {
        throw new Error(`Export failed: ${exportResponse.statusText}`);
      }

      const result = await exportResponse.json();
      
      // Step 3: Handle result
      if (result.task_id) {
        // Async export - track progress
        console.log(`Async export started. Task ID: ${result.task_id}`);
        await this.trackExportProgress(result.task_id);
      } else if (result.file_url) {
        // Sync export - download immediately
        console.log(`Export completed! Records: ${result.record_count}`);
        console.log(`Execution time: ${result.execution_time_ms}ms`);
        this.downloadFile(result.file_url, exportRequest.filename || 'export.xlsx');
      }

    } catch (error) {
      console.error('Export failed:', error);
      this.handleExportError(error);
    }
  }

  // Helper: Track async export progress
  private async trackExportProgress(taskId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/v1/exports/status/${taskId}`, {
            headers: { 'Authorization': `Bearer ${this.adminToken}` }
          });
          
          const status = await statusResponse.json();
          
          console.log(`Export progress: ${status.progress}% - ${status.message}`);
          
          if (status.status === 'completed') {
            clearInterval(interval);
            console.log('Export completed!');
            this.downloadFile(status.file_url, 'export.xlsx');
            resolve();
          } else if (status.status === 'failed') {
            clearInterval(interval);
            reject(new Error(status.error_details || 'Export failed'));
          }
        } catch (error) {
          clearInterval(interval);
          reject(error);
        }
      }, 2000);
    });
  }

  // Helper: Download file
  private downloadFile(url: string, filename: string): void {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
  }

  // Helper: Error handling
  private handleExportError(error: any): void {
    if (error.status === 403) {
      alert('Admin access required. Please login as admin.');
    } else if (error.status === 422) {
      alert('Invalid export configuration. Please check your settings.');
    } else {
      alert(`Export failed: ${error.message}`);
    }
  }
}

// Usage
const exportService = new AdminExportService(adminToken);
exportService.executeExport();
```

### 📋 **Expected Output Excel:**
| Email | NIS/NIP | Nama Lengkap | Jenis Kelamin | Tanggal Lahir | Nama Kelas | Tingkat Kelas | Nama Jurusan | Singkatan Jurusan |
|-------|---------|--------------|---------------|---------------|------------|---------------|--------------|-------------------|
| alex@gmail.com | 79111967 | Alexander Grahambel | Laki Laki | 15/09/2005 | 2 | 12 | Teknik Komputer dan Jaringan | TKJ |
| sarah@gmail.com | 79111968 | Sarah Wijaya | Perempuan | 20/08/2005 | 1 | 12 | Akuntansi | AK |

---

## 📞 Support

Untuk pertanyaan teknis atau bug reports terkait Admin Export API, silakan contact backend team atau create issue di repository project.

---

**Happy Coding! 🚀**
