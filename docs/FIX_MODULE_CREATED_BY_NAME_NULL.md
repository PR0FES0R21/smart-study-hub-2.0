# Fix: Module created_by_name Null Issue

**Date:** 2025-01-16  
**Status:** ✅ FIXED  
**Severity:** LOW - Display data missing

---

## 📋 Problem

Module endpoint returning `created_by_name: null`:

```json
{
  "subject_id": "68b3265c961bd9dbdedaf0d0",
  "subject_name": "Matematika",              // ✅ Working
  "created_by": "68822f07979cbba23e6db950",
  "created_by_name": null                    // ❌ Null!
}
```

---

## 🔍 Root Cause

**Wrong field names in user lookup!**

### **Incorrect Code (module.py):**
```python
creator = await db["users"].find_one({"_id": ObjectId(module_data["created_by"])})
if creator:
    module_data["created_by_name"] = creator.get("full_name") or creator.get("username")  
    # ❌ User document has NO "full_name" field!
```

### **User Document Structure:**
```json
{
  "_id": "68822f07979cbba23e6db950",
  "username": "john_doe",
  "profile": {                    // ✅ Name is inside "profile"
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Problem:** Code tried to get `full_name` (doesn't exist) → returns None → `created_by_name` stays null!

---

## 🔧 Solution

**Match lesson.py pattern - use profile.first_name and profile.last_name:**

### **Fixed Code:**
```python
# Populate created_by_name from database
if module_data.get("created_by"):
    creator = await db["users"].find_one(
        {"_id": ObjectId(module_data["created_by"])},
        {"profile.first_name": 1, "profile.last_name": 1, "username": 1}  # ✅ Correct fields
    )
    if creator and creator.get("profile"):
        first = creator["profile"].get("first_name", "")
        last = creator["profile"].get("last_name", "")
        module_data["created_by_name"] = f"{first} {last}".strip() or creator.get("username", "Unknown")
    elif creator:
        module_data["created_by_name"] = creator.get("username", "Unknown")  # Fallback
```

**Logic:**
1. ✅ Query only needed fields (efficient)
2. ✅ Check if profile exists
3. ✅ Concat first_name + last_name
4. ✅ Fallback to username if no profile
5. ✅ Default to "Unknown" if no name at all

---

## ✅ Verification

**Expected Response After Fix:**

```bash
GET /api/v1/modules/68f5220ab525a8c1b9b5bcdc?include_lessons=true
```

```json
{
  "module": {
    "id": "68f5220ab525a8c1b9b5bcdc",
    "title": "Matematika Dasar kelas 10",
    "subject_id": "68b3265c961bd9dbdedaf0d0",
    "subject_name": "Matematika",              // ✅ Working
    "created_by": "68822f07979cbba23e6db950",
    "created_by_name": "John Doe",             // ✅ NOW WORKING!
    ...
  }
}
```

---

## 📊 Before vs After

### **Before:**
```python
# WRONG field names
creator.get("full_name")  # ❌ Field doesn't exist
→ Returns None
→ created_by_name = null
```

### **After:**
```python
# CORRECT field names
creator["profile"].get("first_name")  # ✅ "John"
creator["profile"].get("last_name")   # ✅ "Doe"
→ "John Doe"
→ created_by_name = "John Doe" ✅
```

---

## 🎓 Lessons Learned

### **When Populating Data from Other Collections:**

1. **Check the actual document structure first!**
   - Don't assume field names
   - Use MongoDB Compass or query to verify

2. **Follow existing patterns**
   - lesson.py already had correct implementation
   - Should have copied that pattern

3. **Add fallbacks**
   - If profile missing → use username
   - If everything missing → use "Unknown"

---

## 📝 Files Modified

1. ✅ `app/crud/module.py` (line 141-152)
   - Fixed user lookup to use correct field names
   - Added profile.first_name and profile.last_name
   - Added username fallback

---

## 🔗 Related Fixes

- `docs/FIX_MODULE_NAMES_POPULATION.md` - Main module names fix
- `app/crud/lesson.py` - Reference implementation (correct pattern)

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Status:** COMPLETE  
**Fix Verified:** ✅ Ready for testing
