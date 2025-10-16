# ==============================================================================
# File: tests/test_strict_separation.py
# Description: Verify strict separation of lessons and pages
# ==============================================================================
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lesson_create_request_has_no_pages_field():
    """Test that LessonCreateRequest does NOT have pages field"""
    from app.schemas.lesson import LessonCreateRequest
    
    # Get model fields
    fields = LessonCreateRequest.model_fields
    
    # Check that pages field does NOT exist
    assert 'pages' not in fields, \
        "LessonCreateRequest should NOT have 'pages' field. Use dedicated page endpoints instead."
    
    # Verify metadata fields exist
    assert 'title' in fields, "Should have title field"
    assert 'description' in fields, "Should have description field"
    assert 'subject_id' in fields, "Should have subject_id field"
    
    print("[PASS] LessonCreateRequest has NO pages field (strict separation)")

def test_lesson_update_request_has_no_pages_field():
    """Test that LessonUpdateRequest does NOT have pages field"""
    from app.schemas.lesson import LessonUpdateRequest
    
    fields = LessonUpdateRequest.model_fields
    
    # Check that pages field does NOT exist
    assert 'pages' not in fields, \
        "LessonUpdateRequest should NOT have 'pages' field"
    
    print("[PASS] LessonUpdateRequest has NO pages field")

def test_create_lesson_does_not_handle_pages():
    """Test that create_lesson CRUD does not handle pages"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.create_lesson)
    
    # Should NOT have page handling logic
    assert 'lesson_data.pages' not in source, \
        "create_lesson should NOT access lesson_data.pages"
    assert 'lesson_page_crud.create_page' not in source, \
        "create_lesson should NOT call lesson_page_crud.create_page"
    
    # Should have comment about separation
    assert 'NOT created here' in source or 'separate' in source.lower(), \
        "Should have comment explaining pages are created separately"
    
    print("[PASS] create_lesson does not handle pages")

def test_dedicated_page_endpoints_exist():
    """Test that dedicated page endpoints exist"""
    from app.api.v1.endpoints.lessons import router
    
    # Get all route paths
    route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
    
    # Check for page endpoints
    assert any('/{lesson_id}/pages' in path for path in route_paths), \
        "Should have dedicated page creation endpoint"
    
    assert any('/{lesson_id}/pages/{page_number}' in path for path in route_paths), \
        "Should have dedicated page update endpoint"
    
    print("[PASS] Dedicated page endpoints exist")

def test_collections_structure():
    """Test that we have proper collection structure"""
    
    # Verify model imports
    try:
        from app.models.lesson import Lesson
        from app.models.lesson_page import LessonPage
        print("[PASS] Both Lesson and LessonPage models exist")
    except ImportError as e:
        raise AssertionError(f"Missing model: {e}")
    
    # Verify CRUD imports
    try:
        from app.crud.lesson import lesson_crud
        from app.crud.lesson_page import lesson_page_crud
        print("[PASS] Both lesson_crud and lesson_page_crud exist")
    except ImportError as e:
        raise AssertionError(f"Missing CRUD: {e}")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING STRICT SEPARATION VERIFICATION TESTS")
    print("="*80 + "\n")
    
    tests = [
        test_lesson_create_request_has_no_pages_field,
        test_lesson_update_request_has_no_pages_field,
        test_create_lesson_does_not_handle_pages,
        test_dedicated_page_endpoints_exist,
        test_collections_structure,
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
        print("SUCCESS: Strict separation verified!")
        print("\nArchitecture:")
        print("  [OK] courses       -> Course metadata")
        print("  [OK] modules       -> Module metadata")
        print("  [OK] lessons       -> Lesson metadata (NO page content)")
        print("  [OK] lesson_pages  -> Page content (title, markdown, media)")
        print("\nClean separation achieved!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
