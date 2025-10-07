# 🚀 **QUICK START: Lesson Pages Migration**

## ⚠️ **IMPORTANT: READ BEFORE RUNNING!**

This migration will **restructure your lesson data** for better performance.

---

## 📋 **CHECKLIST BEFORE MIGRATION:**

- [ ] **Backup your database** (CRITICAL!)
- [ ] Server is NOT in production use
- [ ] You have 5-10 minutes for migration
- [ ] MongoDB is running and accessible

---

## 1️⃣ **BACKUP DATABASE (MANDATORY)**

### **Option A: MongoDB Dump (Recommended)**
```bash
mongodump --db smart_study_hub --out backup_$(date +%Y%m%d)
```

### **Option B: MongoDB Compass**
1. Open MongoDB Compass
2. Connect to database
3. Export collections:
   - `lessons`
   - `modules`
   - `courses`

---

## 2️⃣ **RUN MIGRATION**

```bash
# Navigate to project directory
cd "C:\Users\sayog\OneDrive\Dokumen\code\SMART STUDY HUB 2.2\smart-study-hub-2.0"

# Run migration
python scripts/migrate_lessons_to_separate_pages.py
```

**Expected output:**
```
================================================================================
MIGRATION: Separating Lesson Pages
================================================================================

⚠️  IMPORTANT: This migration will restructure your lessons data!
   Make sure you have a backup before proceeding.

Do you want to continue? (yes/no): yes

[1/5] Fetching lessons with embedded pages...
   Found 15 lessons to migrate

[2/5] Creating indexes for lesson_pages collection...
   ✅ Indexes created

[3/5] Migrating pages to lesson_pages collection...
   
   Lesson: Python Basics (abc123...)
   Pages to migrate: 10
   ✅ Migrated 10 pages
   
   ... (more lessons) ...
   
   Total pages migrated: 150

[4/5] Updating lessons collection (removing embedded pages)...
   ✅ Updated 15 lessons

[5/5] Verifying migration...
   Lessons still with embedded pages: 0
   Total pages in lesson_pages collection: 150

================================================================================
✅ MIGRATION COMPLETED SUCCESSFULLY!
================================================================================

Summary:
  - Lessons migrated: 15
  - Pages extracted: 150
  - New lesson_pages documents: 150

Next steps:
  1. Test new endpoints: GET /lessons/{id}/pages
  2. Update frontend to use new endpoints
  3. Monitor performance improvements

Database connection closed.
```

---

## 3️⃣ **VERIFY MIGRATION**

### **Check in MongoDB:**
```javascript
// Connect to MongoDB
use smart_study_hub

// Check lessons collection (should have no 'pages' field)
db.lessons.findOne()
// Should NOT have 'pages' array

// Check lesson_pages collection (should have all pages)
db.lesson_pages.countDocuments()
// Should show total number of pages

// Check one page
db.lesson_pages.findOne()
// Should have: lesson_id, page_number, content_markdown, etc.
```

### **Check via API:**
```bash
# Get lesson (should return metadata only, no pages)
curl http://localhost:8000/api/v1/lessons/{lesson_id}

# Get pages list
curl http://localhost:8000/api/v1/lessons/{lesson_id}/pages

# Get single page
curl http://localhost:8000/api/v1/lessons/{lesson_id}/pages/1
```

---

## 4️⃣ **RESTART SERVER**

```bash
# Stop current server (Ctrl+C)

# Restart
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Check server logs:**
- Should start without errors
- New endpoints should be loaded

---

## 5️⃣ **TEST NEW ENDPOINTS**

### **Using Swagger UI:**
1. Open: http://localhost:8000/docs
2. Find **"LMS - Lessons"** section
3. Look for new endpoints:
   - `GET /lessons/{id}/pages`
   - `POST /lessons/{id}/pages`
   - `GET /lessons/{id}/pages/{page_number}`
   - etc.

### **Using curl:**
```bash
# List pages
curl -X GET "http://localhost:8000/api/v1/lessons/YOUR_LESSON_ID/pages" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get single page
curl -X GET "http://localhost:8000/api/v1/lessons/YOUR_LESSON_ID/pages/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ✅ **SUCCESS INDICATORS:**

After migration, you should see:

1. ✅ **Lessons collection:**
   - No `pages` field
   - Has `metadata.total_pages`
   - Has `migrated_at` timestamp

2. ✅ **lesson_pages collection:**
   - All pages extracted
   - Each page has `lesson_id` reference
   - Properly indexed

3. ✅ **API endpoints:**
   - Old `/lessons/{id}` returns metadata only
   - New `/lessons/{id}/pages` works
   - New `/lessons/{id}/pages/{number}` works

4. ✅ **Performance:**
   - Lesson metadata loads fast (~2KB)
   - Single page loads fast (~5KB)
   - No more 250KB+ responses

---

## 🐛 **TROUBLESHOOTING:**

### **Problem: Migration script won't run**
```bash
# Check Python path
python --version  # Should be 3.8+

# Check dependencies
pip install motor pymongo

# Check MongoDB connection
python -c "from motor.motor_asyncio import AsyncIOMotorClient; print('OK')"
```

### **Problem: "No lessons to migrate"**
**Possible reasons:**
1. Lessons already migrated
2. No lessons in database
3. Lessons don't have 'pages' field

**Check:**
```javascript
// In MongoDB
db.lessons.findOne({pages: {$exists: true}})
```

### **Problem: Server won't start**
```bash
# Check for syntax errors
python -c "from app.api.v1.endpoints import lessons; print('OK')"

# Check imports
python -c "from app.crud.lesson_page import lesson_page_crud; print('OK')"
```

### **Problem: 404 on new endpoints**
1. Check server restarted
2. Check in Swagger UI: http://localhost:8000/docs
3. Check router registered in `app/api/v1/api.py`

---

## 🔄 **ROLLBACK (If Needed)**

**If something goes wrong:**

### **Option 1: Restore from backup**
```bash
# Restore MongoDB dump
mongorestore --db smart_study_hub backup_YYYYMMDD/smart_study_hub
```

### **Option 2: Manual revert**
```javascript
// NOT recommended, but if needed:
// 1. Copy pages back to lessons
// 2. Delete lesson_pages collection
// 3. Remove migrated_at field from lessons

// This is complex - better to restore from backup!
```

---

## 📊 **MONITOR PERFORMANCE:**

### **Before Migration:**
```bash
# Check response size
curl -w "\nSize: %{size_download} bytes\n" \
  http://localhost:8000/api/v1/lessons/{id}
# Expected: 200KB - 500KB
```

### **After Migration:**
```bash
# Lesson metadata
curl -w "\nSize: %{size_download} bytes\n" \
  http://localhost:8000/api/v1/lessons/{id}
# Expected: 2KB - 5KB ✅

# Single page
curl -w "\nSize: %{size_download} bytes\n" \
  http://localhost:8000/api/v1/lessons/{id}/pages/1
# Expected: 5KB - 20KB ✅
```

**Performance improvement: 90-98%!** 🚀

---

## 📞 **NEED HELP?**

1. Check migration logs for errors
2. Check MongoDB logs
3. Check server logs
4. Verify all files created correctly
5. Check documentation: `PHASE_1_2_IMPLEMENTATION_COMPLETE.md`

---

## ✨ **READY TO GO!**

Your LMS is now **production-ready** with:
- ✅ Scalable architecture
- ✅ 98% performance improvement
- ✅ Industry-standard separation
- ✅ Future-proof design

**Happy teaching! 🎓**
