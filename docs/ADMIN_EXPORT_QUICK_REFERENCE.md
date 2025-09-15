# 🚀 Smart Study Hub - Admin Export System Quick Reference

## 📋 Complete Export System Cheat Sheet

### 🌐 Base URL
```
/api/v1/admin/exports
```

### 🔑 Authentication
```typescript
headers: {
  'Authorization': `Bearer ${adminToken}`,
  'Content-Type': 'application/json'
}
```

### 🎯 **What Can You Export?**
- **Students** with class and expertise info
- **Teachers** with teaching assignments
- **Exam results** with student details  
- **Any collection** with unlimited nested joins
- **Custom data combinations** dengan complex filtering

### ⚡ **Key Features:**
- 🔗 **Unlimited nested joins** (users → profiles → classes → expertise)
- 🎨 **Indonesian field names** (user-friendly headers)
- 📊 **Multiple formats** (Excel, CSV, JSON)
- 🚀 **Async processing** untuk large datasets
- ⚠️ **Computed fields** (main collection only)

---

## ⚡ Common Use Cases

### 1. **Export All Students**
```typescript
const exportAllStudents = {
  config: {
    main_collection: 'users',
    fields: ['email', 'login_id', 'profile'],
    filters: [{ field: 'roles', operator: 'eq', value: 'student' }],
    joins: [{
      collection: 'profiles',
      local_field: 'profile_id', 
      foreign_field: '_id',
      alias: 'profile',
      join_type: 'lookup',
      fields: ['full_name', 'gender']
    }]
  },
  format: 'excel',
  formatting: { exclude_ids: true, use_aliases: true }
};
```

### 2. **Export Students with Class Info** ❗ **Critical Pattern**
```typescript
const exportStudentsWithClass = {
  config: {
    main_collection: 'users',
    // ❗ CRITICAL: Must include join aliases in main fields!
    fields: ['email', 'login_id', 'profile'], // 'profile' must be here for joins to work!
    filters: [{ field: 'roles', operator: 'eq', value: 'student' }],
    joins: [{
      collection: 'profiles',
      local_field: 'profile_id',
      foreign_field: '_id', 
      alias: 'profile', // This alias MUST be in fields above!
      join_type: 'lookup',
      fields: ['full_name', 'gender', 'class_detail'], // Include nested alias here too
      joins: [{
        collection: 'classes',
        local_field: 'class_id',
        foreign_field: '_id',
        alias: 'class_detail', // This alias MUST be in parent fields!
        join_type: 'lookup',
        fields: ['name', 'grade_level', 'expertise'],
        joins: [{
          collection: 'expertise_programs',
          local_field: 'expertise_id',
          foreign_field: '_id',
          alias: 'expertise',
          join_type: 'lookup', 
          fields: ['name', 'abbreviation']
        }]
      }]
    }]
  },
  format: 'excel',
  formatting: { exclude_ids: true, use_aliases: true }
};
```

### ⚠️ **CRITICAL JOIN RULE:**
```typescript
// ✅ CORRECT - Include join alias in parent fields
fields: ['email', 'profile'],  // Include 'profile' here
joins: [{ alias: 'profile' }]   // Matches alias above

// ❌ WRONG - Missing alias in fields = NO DATA!
fields: ['email'],              // Missing 'profile' = joins won't work
joins: [{ alias: 'profile' }]   // Data won't appear in export!
```
```

### 3. **Export with Filtering**
```typescript
const exportFilteredStudents = {
  config: {
    main_collection: 'users',
    fields: ['email', 'login_id', 'profile'],
    filters: [
      { field: 'roles', operator: 'eq', value: 'student' },
      { field: 'is_active', operator: 'eq', value: true }
    ],
    joins: [{
      collection: 'profiles',
      local_field: 'profile_id',
      foreign_field: '_id',
      alias: 'profile', 
      join_type: 'lookup',
      fields: ['full_name', 'gender'],
      filters: [
        { field: 'gender', operator: 'eq', value: 'Laki Laki' }
      ]
    }],
    limit: 100
  },
  format: 'excel'
};
```

---

## 🎯 Field Mapping Reference

| Collection | Technical Field | Display Name | Type |
|------------|----------------|--------------|------|
| **Users** | `login_id` | `NIS/NIP` | string |
| | `email` | `Email` | string |
| | `roles` | `Peran` | array |
| | `is_active` | `Status Aktif` | boolean |
| **Profiles** | `profile.full_name` | `Nama Lengkap` | string |
| | `profile.gender` | `Jenis Kelamin` | string |
| | `profile.birth_date` | `Tanggal Lahir` | date |
| | `profile.phone_number` | `Nomor Telepon` | string |
| **Classes** | `profile.class_detail.name` | `Nama Kelas` | string |
| | `profile.class_detail.grade_level` | `Tingkat Kelas` | number |
| **Expertise** | `profile.class_detail.expertise.name` | `Nama Jurusan` | string |
| | `profile.class_detail.expertise.abbreviation` | `Singkatan Jurusan` | string |

---

## 🔧 Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `{ field: 'roles', operator: 'eq', value: 'student' }` |
| `ne` | Not equals | `{ field: 'is_active', operator: 'ne', value: false }` |
| `gt` | Greater than | `{ field: 'grade_level', operator: 'gt', value: 10 }` |
| `gte` | Greater than or equal | `{ field: 'grade_level', operator: 'gte', value: 11 }` |
| `lt` | Less than | `{ field: 'grade_level', operator: 'lt', value: 12 }` |
| `lte` | Less than or equal | `{ field: 'grade_level', operator: 'lte', value: 11 }` |
| `in` | In array | `{ field: 'roles', operator: 'in', value: ['student', 'teacher'] }` |
| `nin` | Not in array | `{ field: 'status', operator: 'nin', value: ['deleted', 'banned'] }` |
| `exists` | Field exists | `{ field: 'profile_id', operator: 'exists', value: true }` |
| `regex` | Regex match | `{ field: 'email', operator: 'regex', value: '@gmail.com' }` |

---

## 📱 Frontend Helper Functions

### 1. **Build Export Request**
```typescript
const buildExportRequest = (
  collection: string,
  selectedFields: string[],
  filters: any[],
  format: string = 'excel'
): AdvancedExportRequest => {
  return {
    config: {
      main_collection: collection,
      fields: selectedFields,
      filters: filters,
      limit: 1000
    },
    format: format as any,
    formatting: {
      exclude_ids: true,
      use_aliases: true,
      flatten_nested: true,
      include_empty_fields: false
    }
  };
};
```

### 2. **Execute Export**
```typescript
const executeExport = async (request: AdvancedExportRequest) => {
  const response = await fetch('/api/v1/admin/exports/execute', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getAdminToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) {
    throw new Error(`Export failed: ${response.statusText}`);
  }
  
  return await response.json();
};
```

### 3. **Get Field Suggestions**
```typescript
const getFieldSuggestions = async (collection: string) => {
  const response = await fetch(`/api/v1/admin/exports/fields/suggestions/${collection}`, {
    headers: {
      'Authorization': `Bearer ${getAdminToken()}`
    }
  });
  
  return await response.json();
};
```

### 4. **Download Export File**
```typescript
const downloadExport = (fileUrl: string, filename: string) => {
  const link = document.createElement('a');
  link.href = fileUrl;
  link.download = filename;
  link.click();
};
```

---

## 🚨 Error Handling

### Common Errors & Solutions

| Status | Error | Solution |
|--------|-------|----------|
| `400` | Invalid configuration | Check payload structure |
| `403` | Admin access required | Verify admin token |
| `422` | Validation failed | Check field names and filters |
| `500` | Server error | Contact backend team |

### Error Handler
```typescript
const handleExportError = (error: any) => {
  switch (error.status) {
    case 400:
      alert('Invalid export configuration. Please check your settings.');
      break;
    case 403:
      alert('Admin access required. Please login as admin.');
      break;
    case 422:
      alert('Validation failed. Please check field names and filters.');
      break;
    case 500:
      alert('Server error. Please try again later.');
      break;
    default:
      alert('Unknown error occurred.');
  }
};
```

---

## 🎯 Best Practices Checklist

- [ ] Always validate config before execute
- [ ] Use `limit` for large datasets
- [ ] Set `async_export: true` for complex queries
- [ ] Handle async export progress tracking
- [ ] Use field suggestions API for dynamic forms
- [ ] Implement proper error handling
- [ ] Show loading states during export
- [ ] Cache field suggestions to reduce API calls

---

## 🧪 Testing Payloads

### Minimal Test
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["email", "login_id"],
    "filters": [{"field": "roles", "operator": "eq", "value": "student"}],
    "limit": 5
  },
  "format": "excel"
}
```

### Full Featured Test
```json
{
  "config": {
    "main_collection": "users",
    "fields": ["email", "login_id", "profile"],
    "filters": [{"field": "roles", "operator": "eq", "value": "student"}],
    "joins": [{
      "collection": "profiles",
      "local_field": "profile_id",
      "foreign_field": "_id",
      "alias": "profile",
      "join_type": "lookup",
      "fields": ["full_name", "gender"]
    }],
    "limit": 10
  },
  "format": "excel",
  "formatting": {
    "exclude_ids": true,
    "use_aliases": true,
    "flatten_nested": true,
    "include_empty_fields": false
  }
}
```

---

**Need help? Contact the backend team! 🚀**
