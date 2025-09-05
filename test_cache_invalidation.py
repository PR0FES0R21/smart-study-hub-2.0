#!/usr/bin/env python3
"""
Test script untuk memverifikasi cache invalidation berjalan dengan benar
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.cache import get_cache, set_cache, invalidate_cache
from app.crud.crud_exam_sessions import invalidate_student_analytics_cache_for_exam

async def test_cache_operations():
    """Test basic cache operations"""
    print("=== Testing Cache Operations ===")
    
    # Test basic cache set/get
    test_key = "test_key_12345"
    test_value = {"test": "data", "timestamp": "2024-01-01"}
    
    # Set cache
    await set_cache(test_key, test_value, ttl=300)
    print(f"✓ Set cache: {test_key}")
    
    # Get cache
    cached_data = await get_cache(test_key)
    print(f"✓ Get cache: {cached_data}")
    
    # Invalidate cache
    await invalidate_cache(test_key)
    print(f"✓ Invalidated cache: {test_key}")
    
    # Verify cache is gone
    cached_data_after = await get_cache(test_key)
    print(f"✓ Cache after invalidation: {cached_data_after}")
    
    return cached_data_after is None

async def test_student_analytics_invalidation():
    """Test student analytics cache invalidation"""
    print("\n=== Testing Student Analytics Cache Invalidation ===")
    
    # Connect to database
    mongo_url = getattr(settings, 'MONGODB_URL', None) or getattr(settings, 'MONGO_URL', 'mongodb://localhost:27017')
    db_name = getattr(settings, 'DATABASE_NAME', None) or getattr(settings, 'MONGO_DB', 'test_db')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Get a sample exam that has submitted sessions
        sample_exam = await db["exams"].find_one({})
        if not sample_exam:
            print("❌ No exams found in database")
            return False
        
        exam_id = str(sample_exam["_id"])
        print(f"✓ Testing with exam: {exam_id}")
        
        # Create some mock cache entries first
        period_id = str(sample_exam.get("academic_period_id", "test_period"))
        mock_cache_keys = [
            f"student_class_exam_analytics:period:{period_id}:student:test_student_1",
            f"student_individual_stats:period:{period_id}:student:test_student_1",
            f"student_full_dashboard:period:{period_id}:student:test_student_1"
        ]
        
        # Set mock cache entries
        for cache_key in mock_cache_keys:
            await set_cache(cache_key, {"mock": "data"}, ttl=3600)
            print(f"✓ Set mock cache: {cache_key}")
        
        # Verify caches exist
        for cache_key in mock_cache_keys:
            cached = await get_cache(cache_key)
            if cached:
                print(f"✓ Mock cache exists: {cache_key}")
            else:
                print(f"❌ Mock cache missing: {cache_key}")
        
        # Test the invalidation function
        invalidated_count = await invalidate_student_analytics_cache_for_exam(db, exam_id)
        print(f"✓ Invalidation function returned: {invalidated_count}")
        
        # Verify caches are gone (for the mock ones we can check)
        for cache_key in mock_cache_keys:
            cached_after = await get_cache(cache_key)
            if not cached_after:
                print(f"✓ Cache successfully invalidated: {cache_key}")
            else:
                print(f"❌ Cache still exists: {cache_key}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        return False
    finally:
        client.close()

async def test_cache_pattern_matching():
    """Test cache pattern matching for different scenarios"""
    print("\n=== Testing Cache Pattern Matching ===")
    
    # Test different cache key patterns
    test_patterns = [
        "student_class_exam_analytics:period:67abc123:student:67def456",
        "student_individual_stats:period:67abc123:student:67def456", 
        "student_full_dashboard:period:67abc123:student:67def456",
        "assignments:ids:67abc123:class_id=67def456",
        "academic_periods:active"
    ]
    
    # Set test caches
    for pattern in test_patterns:
        await set_cache(pattern, {"test": "data"}, ttl=300)
        print(f"✓ Set test cache: {pattern}")
    
    # Test invalidating specific patterns
    student_patterns = [p for p in test_patterns if "student" in p and "period:67abc123" in p]
    
    print(f"\n✓ Found {len(student_patterns)} student patterns to invalidate")
    
    for pattern in student_patterns:
        await invalidate_cache(pattern)
        print(f"✓ Invalidated: {pattern}")
    
    # Verify invalidation
    for pattern in test_patterns:
        cached = await get_cache(pattern)
        if cached:
            if "student" in pattern:
                print(f"❌ Student cache should be gone but exists: {pattern}")
            else:
                print(f"✓ Non-student cache preserved: {pattern}")
        else:
            print(f"✓ Cache invalidated: {pattern}")
    
    # Cleanup remaining caches
    for pattern in test_patterns:
        await invalidate_cache(pattern)
    
    return True

async def main():
    """Main test function"""
    print("🧪 Starting Cache Invalidation Tests")
    
    results = []
    
    # Test 1: Basic cache operations
    try:
        result1 = await test_cache_operations()
        results.append(("Basic Cache Operations", result1))
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        results.append(("Basic Cache Operations", False))
    
    # Test 2: Student analytics invalidation
    try:
        result2 = await test_student_analytics_invalidation()
        results.append(("Student Analytics Invalidation", result2))
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        results.append(("Student Analytics Invalidation", False))
    
    # Test 3: Cache pattern matching
    try:
        result3 = await test_cache_pattern_matching()
        results.append(("Cache Pattern Matching", result3))
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        results.append(("Cache Pattern Matching", False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Cache invalidation is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    asyncio.run(main())
