# Fix: Module ObjectId Serialization Error (500)

**Date:** 2025-01-16  
**Status:** ✅ FIXED  
**Severity:** HIGH - Endpoint completely broken (500 error)

---

## 📋 Problem

Module endpoint returning **500 Internal Server Error**:

```
GET /api/v1/modules/68f8dad6a9717e5c6dc6b851?include_lessons=false

Response: 500 Internal Server Error
```

**Error Message:**
```python
TypeError: 'ObjectId' object is not iterable
ValueError: [TypeError("'ObjectId' object is not iterable")]
```

---

## 🔍 Root Cause

**ObjectId in lesson_refs not converted to string before JSON serialization!**

### **The Flow:**

1. ✅ `module_crud.get_module_by_id()` returns Module model
2. ✅ `Module.from_mongo()` converts most ObjectIds to strings
3. ❌ **Endpoint converts some ObjectIds but missed `lesson_refs.lesson_id`**
4. 💥 FastAPI tries to serialize ObjectId → JSON → **ERROR!**

### **Problem Code:**

**File:** `app/api/v1/endpoints/modules.py` (line 132-144)

```python
# Convert module to dict and handle ObjectIds
module_dict = module.dict(by_alias=False)

# Convert ObjectId fields to strings
if "subject_id" in module_dict:
    module_dict["subject_id"] = str(module_dict["subject_id"])
if "created_by" in module_dict:
    module_dict["created_by"] = str(module_dict["created_by"])
if "collaborators" in module_dict:
    module_dict["collaborators"] = [str(c) for c in module_dict["collaborators"]]

# ❌ MISSING: lesson_refs still has ObjectId!
# lesson_refs = [
#     {"lesson_id": ObjectId("xxx"), ...},  ← Not converted!
#     {"lesson_id": ObjectId("yyy"), ...}
# ]
```

**What Happens:**
```python
# FastAPI tries to serialize
jsonable_encoder(module_dict)
→ Encounters ObjectId("xxx")
→ Tries: dict(ObjectId)  ❌ "ObjectId object is not iterable"
→ Tries: vars(ObjectId)  ❌ "vars() argument must have __dict__"
→ Raises ValueError
→ 500 Internal Server Error
```

---

## 🔧 Solution

**Add lesson_refs ObjectId conversion:**

### **Fixed Code:**

```python
# Convert module to dict and handle ObjectIds
module_dict = module.dict(by_alias=False)

# Convert ObjectId fields to strings
if "_id" in module_dict:
    module_dict["id"] = str(module_dict["_id"])
    del module_dict["_id"]
if "subject_id" in module_dict:
    module_dict["subject_id"] = str(module_dict["subject_id"])
if "created_by" in module_dict:
    module_dict["created_by"] = str(module_dict["created_by"])
if "collaborators" in module_dict:
    module_dict["collaborators"] = [str(c) for c in module_dict["collaborators"]]

# ✅ NEW: Convert lesson_refs ObjectIds to strings
if "lesson_refs" in module_dict:
    for ref in module_dict["lesson_refs"]:
        if "lesson_id" in ref and ref["lesson_id"]:
            ref["lesson_id"] = str(ref["lesson_id"])
```

**Now:**
```python
lesson_refs = [
    {"lesson_id": "68f0c913a46aa759e854c381", ...},  # ✅ String!
    {"lesson_id": "68e40c78253e7e2444e80483", ...}   # ✅ String!
]
→ JSON serialization works ✅
```

---

## ✅ Verification

### **Automated Tests: PASSED**

```bash
python tests/test_module_objectid_serialization.py
```

**Results:**
```
[PASS] get_module endpoint converts lesson_refs ObjectIds
[PASS] Module.from_mongo converts ObjectIds to strings
[PASS] get_module handles all ObjectId fields

Passed: 3/3 ✅
```

---

### **Expected Response After Fix:**

```bash
GET /api/v1/modules/68f8dad6a9717e5c6dc6b851?include_lessons=false
```

**Before Fix:**
```
Status: 500 Internal Server Error
TypeError: 'ObjectId' object is not iterable
```

**After Fix:**
```
Status: 200 OK
{
  "module": {
    "id": "68f8dad6a9717e5c6dc6b851",
    "title": "...",
    "subject_id": "68b3265c961bd9dbdedaf0d0",      // ✅ String
    "created_by": "68822f07979cbba23e6db950",      // ✅ String
    "lesson_refs": [
      {
        "lesson_id": "68f0c913a46aa759e854c381",  // ✅ String (FIXED!)
        "order": 1,
        ...
      }
    ],
    ...
  },
  "lessons": [],
  "total_lessons": 3,
  "total_duration": 100
}
```

---

## 📊 Before vs After

### **Before:**
```python
lesson_refs = [
    {"lesson_id": ObjectId("xxx")}  # ❌ ObjectId
]
→ FastAPI jsonable_encoder fails
→ 500 error
```

### **After:**
```python
lesson_refs = [
    {"lesson_id": "xxx"}  # ✅ String
]
→ FastAPI jsonable_encoder succeeds
→ 200 OK with proper JSON
```

---

## 🎓 Lessons Learned

### **When Converting MongoDB Documents to JSON:**

**Rule:** ALL ObjectId fields MUST be converted to strings!

**Common ObjectId Locations:**
```python
# Direct fields
data["_id"] → str(data["_id"])
data["subject_id"] → str(data["subject_id"])
data["created_by"] → str(data["created_by"])

# Arrays of ObjectIds
data["collaborators"] → [str(c) for c in data["collaborators"]]

# Nested objects (OFTEN MISSED!)
for ref in data["lesson_refs"]:
    ref["lesson_id"] → str(ref["lesson_id"])  # ← Don't forget!

for item in data["items"]:
    item["user_id"] → str(item["user_id"])    # ← Check nested!
```

### **Checklist for API Endpoints:**

When returning MongoDB data:

- [ ] Convert `_id` to string `id`
- [ ] Convert all reference IDs (`subject_id`, `created_by`, etc)
- [ ] Convert arrays of IDs (`collaborators`, etc)
- [ ] **Check nested objects/arrays for ObjectIds!** ← Most common miss
- [ ] Test with actual data (not just mocks)

---

## 📝 Files Modified

1. ✅ `app/api/v1/endpoints/modules.py` (line 146-150)
   - Added lesson_refs ObjectId conversion

2. ✅ `tests/test_module_objectid_serialization.py` (NEW)
   - Verification tests (3/3 passing)

3. ✅ `docs/FIX_MODULE_OBJECTID_SERIALIZATION.md` (NEW)
   - This documentation

---

## 🔗 Related Issues

**Similar issues to watch for:**
- Any endpoint returning nested references
- Arrays of objects with ObjectId fields
- Aggregation pipeline results (already strings usually)
- Embedded documents with ObjectIds

**Prevention:**
- Always test endpoints with real data
- Add ObjectId serialization tests
- Use consistent conversion pattern across endpoints

---

## 🚀 Testing Checklist

After fix, verify:

- [x] Syntax valid
- [x] Tests passing (3/3)
- [ ] **Manual Test:** GET /modules/{id}?include_lessons=false → 200 OK ← **DO THIS!**
- [ ] **Manual Test:** Response is valid JSON ← **DO THIS!**
- [ ] **Manual Test:** lesson_refs has string IDs ← **DO THIS!**

---

## 💡 Key Takeaway

**ObjectId Serialization Rule:**

```
When converting MongoDB → JSON:
1. Convert ALL top-level ObjectIds ✅
2. Convert ALL array ObjectIds ✅
3. Convert ALL nested ObjectIds ✅ ← Don't forget!

If you see "ObjectId object is not iterable":
→ You missed converting an ObjectId somewhere!
→ Check nested objects and arrays!
```

**Always serialize completely before returning!**

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Status:** COMPLETE  
**Fix Verified:** ✅ Tests passing, ready for manual testing
