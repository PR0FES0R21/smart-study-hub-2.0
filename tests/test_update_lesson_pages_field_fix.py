# ==============================================================================
# File: tests/test_update_lesson_pages_field_fix.py
# Description: Verify update_lesson doesn't try to access non-existent pages field
# ==============================================================================
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_update_lesson_no_pages_access():
    """Test that update_lesson function does NOT access updates.pages field"""
    
    import inspect
    from app.crud.lesson import lesson_crud
    
    # Get source code of update_lesson
    source = inspect.getsource(lesson_crud.update_lesson)
    
    # Should NOT access updates.pages
    assert 'updates.pages' not in source, \
        "update_lesson should NOT access 'updates.pages' field (field removed from schema)"
    
    # Should NOT have the old validation check
    assert 'Pages cannot be updated via lesson update' not in source, \
        "Old validation error message should be removed"
    
    print("[PASS] update_lesson does not access updates.pages field")

def test_lesson_update_request_schema_no_pages():
    """Test that LessonUpdateRequest schema does NOT have pages field"""
    
    from app.schemas.lesson import LessonUpdateRequest
    
    fields = LessonUpdateRequest.model_fields
    
    # Should NOT have pages field
    assert 'pages' not in fields, \
        "LessonUpdateRequest should NOT have 'pages' field (strict separation)"
    
    # Verify it has other expected fields
    assert 'title' in fields, "Should have title field"
    assert 'description' in fields, "Should have description field"
    assert 'status' in fields, "Should have status field"
    
    print("[PASS] LessonUpdateRequest schema does not have 'pages' field")

def test_update_lesson_has_separation_comment():
    """Test that update_lesson has comment explaining separation"""
    
    import inspect
    from app.crud.lesson import lesson_crud
    
    source = inspect.getsource(lesson_crud.update_lesson)
    
    # Should have comment about separation
    has_separation_note = any(keyword in source for keyword in [
        'separate endpoints', 'strict separation', '/lessons/{id}/pages'
    ])
    
    assert has_separation_note, \
        "update_lesson should have comment explaining pages are managed separately"
    
    print("[PASS] update_lesson has explanatory comment about separation")

def test_lesson_create_request_schema_no_pages():
    """Test that LessonCreateRequest schema also does NOT have pages field"""
    
    from app.schemas.lesson import LessonCreateRequest
    
    fields = LessonCreateRequest.model_fields
    
    # Should NOT have pages field
    assert 'pages' not in fields, \
        "LessonCreateRequest should NOT have 'pages' field (strict separation)"
    
    print("[PASS] LessonCreateRequest schema does not have 'pages' field")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING UPDATE LESSON PAGES FIELD FIX VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_update_lesson_no_pages_access,
        test_lesson_update_request_schema_no_pages,
        test_update_lesson_has_separation_comment,
        test_lesson_create_request_schema_no_pages,
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
        print("SUCCESS: Update lesson fix verified!")
        print("\nFixed issues:")
        print("  [OK] Removed updates.pages access from update_lesson()")
        print("  [OK] LessonUpdateRequest has no 'pages' field")
        print("  [OK] LessonCreateRequest has no 'pages' field")
        print("  [OK] Explanatory comment added")
        print("\nNo more AttributeError: 'LessonUpdateRequest' object has no attribute 'pages'")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
