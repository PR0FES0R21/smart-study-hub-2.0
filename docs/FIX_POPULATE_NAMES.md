# Fix: Populate subject_name and created_by_name

**Date:** 2025-01-16  
**Status:** ✅ FIXED  
**Severity:** MEDIUM - Missing data in responses

---

## Problem

Endpoint `GET /api/v1/lessons/{id}?include_usage=true` returning:
```json
{
  "subject_id": "68b328329be3ef2464823bff",
  "subject_name": null,              // ❌ Should show "Mathematics"
  "created_by": "68822f07979cbba23e6db950",
  "created_by_name": null            // ❌ Should show "John Doe"
}
```

---

## Root Cause

**Three Issues:**

1. **Missing Model Fields**: `Lesson` model didn't have `subject_name` and `created_by_name` fields
2. **No Data Population**: CRUD layer didn't fetch and populate these fields
3. **Endpoint Overwrites**: Endpoint explicitly set values to `None`, overwriting any populated data

---

## Solution

### 1. Added Fields to Model

**File:** `app/models/lesson.py`

```python
class Lesson(BaseModel):
    # Academic classification
    subject_id: PyObjectId
    subject_name: Optional[str] = Field(None, description="Subject name (populated from lookup)")
    
    # Sharing dan visibility
    created_by: PyObjectId
    created_by_name: Optional[str] = Field(None, description="Creator name (populated from lookup)")
```

### 2. Populate Data in CRUD Layer

**File:** `app/crud/lesson.py`

```python
async def get_lesson_by_id(...):
    lesson_data = await db["lessons"].find_one({"_id": ObjectId(lesson_id)})
    
    # Populate subject_name
    if "subject_id" in lesson_data and lesson_data["subject_id"]:
        subject = await db["subjects"].find_one(
            {"_id": ObjectId(lesson_data["subject_id"])},
            {"name": 1}
        )
        lesson_data["subject_name"] = subject["name"] if subject else None
    
    # Populate created_by_name
    if "created_by" in lesson_data and lesson_data["created_by"]:
        creator = await db["users"].find_one(
            {"_id": ObjectId(lesson_data["created_by"])},
            {"profile.first_name": 1, "profile.last_name": 1}
        )
        if creator and "profile" in creator:
            first_name = creator["profile"].get("first_name", "")
            last_name = creator["profile"].get("last_name", "")
            lesson_data["created_by_name"] = f"{first_name} {last_name}".strip()
    
    return Lesson.from_mongo(lesson_data)
```

### 3. Remove Overwrites in Endpoint

**File:** `app/api/v1/endpoints/lessons.py`

```python
# BEFORE (BAD):
response_data["subject_name"] = None  # Overwrites populated value!
response_data["created_by_name"] = None

# AFTER (GOOD):
# Note: subject_name and created_by_name are now populated by CRUD layer
# Don't overwrite with None - they should already be set
```

---

## Changes Summary

### Modified Files

1. **`app/models/lesson.py`**
   - Added `subject_name: Optional[str]` field
   - Added `created_by_name: Optional[str]` field

2. **`app/crud/lesson.py`**
   - Added subject lookup to populate `subject_name`
   - Added user lookup to populate `created_by_name`
   - Handles missing/null gracefully

3. **`app/api/v1/endpoints/lessons.py`**
   - Removed lines that overwrote with `None`
   - Added clarifying comment

4. **`tests/test_populate_names_fix.py`** (NEW)
   - Created verification tests
   - All 4 tests passing

---

## Verification

### Automated Tests

```bash
python tests/test_populate_names_fix.py
```

**Result:**
```
[PASS] Lesson model has subject_name and created_by_name fields
[PASS] CRUD layer populates subject_name
[PASS] CRUD layer populates created_by_name
[PASS] Endpoint does not overwrite populated names

Passed: 4/4 ✅
```

### Manual Testing

**Test Case:**
```bash
GET /api/v1/lessons/68f0c913a46aa759e854c381?include_usage=true
Authorization: Bearer <token>

# Expected Response:
{
  "id": "68f0c913a46aa759e854c381",
  "subject_id": "68b328329be3ef2464823bff",
  "subject_name": "Mathematics",            // ✅ NOW POPULATED
  "created_by": "68822f07979cbba23e6db950",
  "created_by_name": "John Doe",            // ✅ NOW POPULATED
  ...
}
```

---

## Performance Considerations

### Additional Queries

This fix adds **2 extra database queries** per `get_lesson_by_id()` call:
1. Subject lookup: `O(1)` - indexed by `_id`
2. User lookup: `O(1)` - indexed by `_id`

**Impact:** Minimal - both queries are fast (indexed lookups)

### Optimization Options (Future)

If performance becomes a concern:

1. **Caching**
   ```python
   # Cache subject names (rarely change)
   subject_name = await redis.get(f"subject:{subject_id}:name")
   if not subject_name:
       subject = await db["subjects"].find_one(...)
       subject_name = subject["name"]
       await redis.setex(f"subject:{subject_id}:name", 3600, subject_name)
   ```

2. **Aggregation Pipeline** (for list endpoints)
   ```python
   # Use $lookup in aggregation for batch efficiency
   pipeline = [
       {"$match": {...}},
       {"$lookup": {
           "from": "subjects",
           "localField": "subject_id",
           "foreignField": "_id",
           "as": "subject_info"
       }}
   ]
   ```

3. **Denormalization** (if needed)
   - Store `subject_name` directly in lesson document
   - Update when subject name changes (rare)
   - Trade-off: More storage, faster reads

**Current Decision:** Keep current implementation (clean, maintainable, good enough performance)

---

## Impact

### Before Fix
```
❌ subject_name: null
❌ created_by_name: null
❌ Frontend shows IDs instead of names
❌ Poor user experience
```

### After Fix
```
✅ subject_name: "Mathematics"
✅ created_by_name: "John Doe"
✅ Frontend shows readable names
✅ Better user experience
```

---

## Related Fixes

- include_usage fix: `docs/FIX_INCLUDE_USAGE_500_ERROR.md`
- Permission fix: `docs/PERMISSION_FIX.md`
- Main fixes: `docs/FIXES_APPLIED_LESSON_LMS.md`
- Frontend guide: `docs/FRONTEND_LESSON_API_GUIDE.md`

---

**Document Version:** 1.0  
**Status:** COMPLETE  
**Fix Verified:** ✅ All tests passing
