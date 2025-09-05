#!/usr/bin/env python3
"""
Manual test untuk memverifikasi cache invalidation bekerja
"""

import asyncio
import sys
import os

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.cache import get_cache, set_cache, invalidate_cache

async def test_manual_cache():
    """Test manual cache operations"""
    print("=== Manual Cache Test ===")
    
    # Test cache keys yang mirip dengan yang ada di sistem
    test_cache_keys = [
        "student_class_exam_analytics:period:6878bebc5084cc17176782a5:student:688477a78a56906f19d02551",
        "student_class_exam_analytics:period:6878bebc5084cc17176782a5:student:68b2dcbdcccc321f815ea3f5", 
        "assignments:ids:6878bebc5084cc17176782a5:class_id=687e01044593234141867820",
        "academic_periods:active"
    ]
    
    print("\\n1. Setting test cache entries...")
    for cache_key in test_cache_keys:
        await set_cache(cache_key, {"test": "data", "timestamp": "2024-01-01"}, ttl=3600)
        print(f"✓ Set: {cache_key}")
    
    print("\\n2. Verifying cache entries exist...")
    for cache_key in test_cache_keys:
        cached = await get_cache(cache_key)
        if cached:
            print(f"✓ Exists: {cache_key}")
        else:
            print(f"❌ Missing: {cache_key}")
    
    print("\\n3. Invalidating student analytics caches...")
    student_cache_keys = [k for k in test_cache_keys if "student_class_exam_analytics" in k]
    for cache_key in student_cache_keys:
        await invalidate_cache(cache_key)
        print(f"✓ Invalidated: {cache_key}")
    
    print("\\n4. Verifying selective invalidation...")
    for cache_key in test_cache_keys:
        cached = await get_cache(cache_key)
        if "student_class_exam_analytics" in cache_key:
            if not cached:
                print(f"✅ Correctly invalidated: {cache_key}")
            else:
                print(f"❌ Should be invalidated: {cache_key}")
        else:
            if cached:
                print(f"✅ Correctly preserved: {cache_key}")
            else:
                print(f"❌ Should be preserved: {cache_key}")
    
    print("\\n5. Cleanup remaining caches...")
    for cache_key in test_cache_keys:
        await invalidate_cache(cache_key)
    
    print("\\n✅ Manual test completed!")

if __name__ == "__main__":
    asyncio.run(test_manual_cache())
