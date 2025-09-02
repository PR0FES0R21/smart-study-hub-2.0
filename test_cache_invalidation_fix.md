# Cache Invalidation Fix - Test Documentation

## Problem yang Diperbaiki

Sebelumnya, ketika permission question set berubah (grant/revoke), cache tidak di-invalidate secara lengkap, menyebabkan:

1. **Grant Permission**: User yang diberi akses tidak bisa melihat question set sampai cache expired atau di-clear manual
2. **Revoke Permission**: User yang dicabut aksesnya masih bisa mengakses question set sampai cache expired

## Solusi yang Diimplementasikan

### 1. Method Baru: `_invalidate_permission_change_caches`

```python
async def _invalidate_permission_change_caches(
    self,
    question_set_id: ObjectId,
    target_user_id: ObjectId,
    requester_user_id: ObjectId
) -> None
```

**Yang di-invalidate:**

- ✅ Cache semua user yang terkait dengan question set
- ✅ Detail cache untuk question set specific
- ✅ List cache untuk semua user (aggressive tapi necessary)
- ✅ Teaching assignments cache untuk target user
- ✅ Creator cache

### 2. Updated `manage_permissions` Function

Menggunakan comprehensive cache invalidation instead of partial invalidation.

## Test Cases untuk Verifikasi

### Test Case 1: Grant Permission

**Setup:**

1. User A (Coordinator) membuat question set private
2. User B tidak punya akses

**Steps:**

1. Login sebagai User A
2. Buat question set baru (private)
3. Verify: User B tidak bisa lihat question set
4. Grant permission "can_view" ke User B
5. Login sebagai User B IMMEDIATELY
6. **Expected Result**: Question set langsung muncul di list User B
7. **Check Logs**: Harus ada log cache invalidation

### Test Case 2: Revoke Permission

**Setup:**

1. User A (Coordinator) punya question set
2. User B sudah punya permission can_view

**Steps:**

1. Login sebagai User B
2. Verify: User B bisa lihat question set
3. Login sebagai User A
4. Revoke permission "can_view" dari User B
5. Login sebagai User B IMMEDIATELY
6. **Expected Result**: Question set langsung hilang dari list User B
7. **Check Logs**: Harus ada log cache invalidation

### Test Case 3: Multiple Permission Grant

**Setup:**

1. User A (Coordinator) punya question set
2. User B tidak punya akses

**Steps:**

1. Grant multiple permissions sekaligus: ["can_view", "can_edit", "can_manage_questions"]
2. Login sebagai User B IMMEDIATELY
3. **Expected Result**:
   - Question set muncul di list
   - User B bisa edit question set
   - User B bisa manage questions

### Test Case 4: Cache Key Verification

**Steps:**

1. Check Redis keys sebelum permission change
2. Grant permission ke user
3. Check Redis keys setelah permission change
4. **Expected Result**:
   - Cache keys untuk target user harus hilang
   - Cache keys untuk question set detail harus hilang
   - Cache keys "question_sets:user:\*" harus hilang

## Monitoring Cache Invalidation

### Log Output yang Diharapkan

```
🔄 CACHE INVALIDATION START: question_set:68b5bf14cb2af8fe1c20115f
   Target user: 68822f07979cbba23e6db950
   Affected users: 3
   ✅ Invalidated caches for user: 688b56aaf64f8842d7361fe6
   ✅ Invalidated caches for user: 68822f07979cbba23e6db950
   ✅ Invalidated caches for user: 68b5bf14cb2af8fe1c20115f
   ✅ Invalidated detail caches for question_set: 68b5bf14cb2af8fe1c20115f
   ✅ Invalidated ALL question sets list caches
   ✅ Invalidated teaching cache for target user
🔄 CACHE INVALIDATION COMPLETE: 3 users affected
```

### Redis Key Check Commands

```bash
# Before permission change
redis-cli KEYS "question_sets:user:*"
redis-cli KEYS "question_set:detail:*"
redis-cli KEYS "user:teaching:*"

# After permission change
redis-cli KEYS "question_sets:user:*"  # Should be empty or reduced
redis-cli KEYS "question_set:detail:*"  # Should be empty or reduced
```

## Performance Impact

- **Cache Miss Rate**: Akan meningkat setelah permission changes (expected)
- **Response Time**: Sedikit lebih lambat untuk first request setelah permission change
- **Consistency**: 100% consistent permission state antar user
- **User Experience**: Immediate permission effect, no manual cache clearing needed

## Success Criteria

✅ Permission changes take effect immediately  
✅ No need for manual Redis cache clearing  
✅ Consistent state across all users  
✅ Comprehensive logging for debugging  
✅ No cache pollution between users

## Rollback Plan

Jika ada issue, bisa rollback dengan:

1. Revert `manage_permissions` function ke version lama
2. Remove `_invalidate_permission_change_caches` method
3. Use simple `_invalidate_question_set_caches` (partial invalidation)
