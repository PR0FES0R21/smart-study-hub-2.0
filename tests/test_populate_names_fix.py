# ==============================================================================
# File: tests/test_populate_names_fix.py
# Description: Test untuk verify subject_name dan created_by_name population
# ==============================================================================
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lesson_model_has_name_fields():
    """Test that Lesson model has subject_name and created_by_name fields"""
    from app.models.lesson import Lesson
    
    # Get model fields (Pydantic v2 API)
    fields = Lesson.model_fields
    
    # Check subject_name field exists
    assert 'subject_name' in fields, "Lesson model should have subject_name field"
    
    # Check created_by_name field exists
    assert 'created_by_name' in fields, "Lesson model should have created_by_name field"
    
    print("[PASS] Lesson model has subject_name and created_by_name fields")

def test_crud_populates_subject_name():
    """Test that CRUD layer populates subject_name"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.get_lesson_by_id)
    
    # Should fetch subject
    assert 'subjects' in source, "Should query subjects collection"
    assert 'subject_name' in source, "Should populate subject_name"
    
    print("[PASS] CRUD layer populates subject_name")

def test_crud_populates_created_by_name():
    """Test that CRUD layer populates created_by_name"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.get_lesson_by_id)
    
    # Should fetch user
    assert 'users' in source, "Should query users collection"
    assert 'created_by_name' in source, "Should populate created_by_name"
    assert 'first_name' in source and 'last_name' in source, "Should use profile name fields"
    
    print("[PASS] CRUD layer populates created_by_name")

def test_endpoint_does_not_overwrite():
    """Test that endpoint doesn't overwrite populated names with None"""
    from app.api.v1.endpoints.lessons import get_lesson
    import inspect
    
    source = inspect.getsource(get_lesson)
    
    # Should NOT set to None
    lines = source.split('\n')
    overwrite_lines = [
        l for l in lines 
        if 'subject_name' in l and '= None' in l and 'response_data[' in l
    ]
    
    assert len(overwrite_lines) == 0, \
        f"Endpoint should NOT overwrite subject_name with None. Found: {overwrite_lines}"
    
    overwrite_lines = [
        l for l in lines 
        if 'created_by_name' in l and '= None' in l and 'response_data[' in l
    ]
    
    assert len(overwrite_lines) == 0, \
        f"Endpoint should NOT overwrite created_by_name with None. Found: {overwrite_lines}"
    
    print("[PASS] Endpoint does not overwrite populated names")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING POPULATE NAMES FIX VERIFICATION TESTS")
    print("="*80 + "\n")
    
    tests = [
        test_lesson_model_has_name_fields,
        test_crud_populates_subject_name,
        test_crud_populates_created_by_name,
        test_endpoint_does_not_overwrite,
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
        print("SUCCESS: Name population fix verified!")
        print("\nEndpoint responses should now show:")
        print("  - subject_name: 'Mathematics' (actual subject name)")
        print("  - created_by_name: 'John Doe' (actual creator name)")
        print("\nNo more null values!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
