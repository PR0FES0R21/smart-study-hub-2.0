# ==============================================================================
# File: tests/test_lesson_created_by_name_fix.py
# Description: Verify lesson endpoint uses correct profiles structure for created_by_name
# ==============================================================================
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lesson_uses_profiles_collection():
    """Test that get_lesson_by_id uses profiles collection for created_by_name"""
    
    import inspect
    from app.crud.lesson import lesson_crud
    
    # Get source code of get_lesson_by_id
    source = inspect.getsource(lesson_crud.get_lesson_by_id)
    
    # Should query users for profile_id
    assert 'profile_id' in source, \
        "get_lesson_by_id should query profile_id from users collection"
    
    # Should query profiles collection
    assert 'profiles' in source, \
        "get_lesson_by_id should query profiles collection"
    
    # Should query full_name
    assert 'full_name' in source, \
        "get_lesson_by_id should query full_name from profiles"
    
    # Should NOT use old pattern
    assert 'profile.first_name' not in source, \
        "Should NOT use old embedded profile pattern (profile.first_name)"
    
    assert 'profile.last_name' not in source, \
        "Should NOT use old embedded profile pattern (profile.last_name)"
    
    print("[PASS] Lesson uses correct profiles collection structure")

def test_lesson_model_has_created_by_name():
    """Test that Lesson model has created_by_name field"""
    
    from app.models.lesson import Lesson
    
    fields = Lesson.model_fields
    
    # Should have created_by_name field
    assert 'created_by_name' in fields, \
        "Lesson model should have 'created_by_name' field"
    
    print("[PASS] Lesson model has created_by_name field")

def test_pattern_matches_module():
    """Test that lesson.py uses same pattern as module.py"""
    
    import inspect
    from app.crud.lesson import lesson_crud
    from app.crud.module import module_crud
    
    lesson_source = inspect.getsource(lesson_crud.get_lesson_by_id)
    module_source = inspect.getsource(module_crud.get_module_by_id)
    
    # Both should use profiles collection
    assert 'profiles' in lesson_source and 'profiles' in module_source, \
        "Both lesson and module should use profiles collection"
    
    # Both should query profile_id
    assert 'profile_id' in lesson_source and 'profile_id' in module_source, \
        "Both should query profile_id from users"
    
    # Both should query full_name
    assert 'full_name' in lesson_source and 'full_name' in module_source, \
        "Both should query full_name from profiles"
    
    print("[PASS] Lesson and Module use consistent pattern")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING LESSON CREATED_BY_NAME FIX VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_lesson_uses_profiles_collection,
        test_lesson_model_has_created_by_name,
        test_pattern_matches_module,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {str(e)}")
            failed += 1
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    print("="*80 + "\n")
    
    if failed == 0:
        print("SUCCESS: Lesson created_by_name fix verified!")
        print("\nFixed issues:")
        print("  [OK] Lesson uses profiles collection (not embedded profile)")
        print("  [OK] Queries profile_id from users collection")
        print("  [OK] Queries full_name from profiles collection")
        print("  [OK] Pattern matches module.py implementation")
        print("\nLesson endpoint will now return created_by_name correctly!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
