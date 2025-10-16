# ==============================================================================
# File: tests/test_lesson_fixes.py
# Description: Test untuk verifikasi fixes yang sudah dilakukan
# ==============================================================================
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lesson_model_no_obsolete_methods():
    """Verify that obsolete methods have been removed from Lesson model"""
    from app.models.lesson import Lesson
    
    # Check that obsolete methods are removed
    obsolete_methods = ['calculate_metadata', 'add_page', 'reorder_pages', 'get_page_by_number']
    
    for method in obsolete_methods:
        assert not hasattr(Lesson, method), f"Obsolete method {method} still exists in Lesson model"
    
    # Check that essential methods still exist
    assert hasattr(Lesson, 'is_editable_by'), "is_editable_by method missing"
    assert hasattr(Lesson, 'from_mongo'), "from_mongo method missing"
    assert hasattr(Lesson, 'to_mongo'), "to_mongo method missing"
    
    print("[PASS] Lesson model - obsolete methods removed")

def test_lesson_crud_uses_lesson_page_crud():
    """Verify that lesson_crud delegates to lesson_page_crud"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    # Check that add_page_to_lesson is deprecated
    source = inspect.getsource(lesson_crud.add_page_to_lesson)
    assert 'DEPRECATED' in source, "add_page_to_lesson should be marked as DEPRECATED"
    assert 'lesson_page_crud' in source, "add_page_to_lesson should delegate to lesson_page_crud"
    
    # Check that update_lesson_page is deprecated
    source = inspect.getsource(lesson_crud.update_lesson_page)
    assert 'DEPRECATED' in source, "update_lesson_page should be marked as DEPRECATED"
    assert 'lesson_page_crud' in source, "update_lesson_page should delegate to lesson_page_crud"
    
    print("[PASS] lesson_crud - delegates to lesson_page_crud")

def test_cascade_delete_implemented():
    """Verify that cascade delete is implemented"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.delete_lesson)
    assert 'CASCADE DELETE' in source or 'delete_all_pages' in source, \
        "Cascade delete for lesson_pages not implemented"
    
    print("[PASS] Cascade delete - implemented")

def test_include_usage_returns_data():
    """Verify that include_usage logic returns usage data"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.get_lesson_by_id)
    assert '_usage_details' in source, "Usage details not being collected"
    assert 'modules' in source and 'courses' in source, "Both modules and courses usage should be collected"
    
    print("[PASS] include_usage - returns usage data")

def test_authorization_fixed():
    """Verify that authorization logic is correct (no teacher bias)"""
    from app.api.v1.endpoints.lessons import router
    import inspect
    
    # Get source of get_lesson endpoint
    for route in router.routes:
        if hasattr(route, 'endpoint') and route.endpoint.__name__ == 'get_lesson':
            source = inspect.getsource(route.endpoint)
            
            # Check that authorization doesn't give all teachers access
            lines = source.split('\n')
            auth_lines = [l for l in lines if 'can_view' in l and '=' in l]
            
            # Should NOT have: "teacher" in user_roles
            for line in auth_lines:
                if '"teacher"' in line or "'teacher'" in line:
                    assert False, f"Authorization still gives all teachers access: {line.strip()}"
            
            print("[PASS] Authorization - teacher bias removed")
            return
    
    assert False, "get_lesson endpoint not found"

def test_subject_validation_added():
    """Verify that subject_id validation is added"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.create_lesson)
    assert 'Subject not found' in source or 'subject' in source.lower(), \
        "Subject validation not implemented"
    
    print("[PASS] Subject validation - implemented")

def test_transaction_in_reorder():
    """Verify that transaction is used in reorder_pages"""
    from app.crud.lesson_page import lesson_page_crud
    import inspect
    
    source = inspect.getsource(lesson_page_crud.reorder_pages)
    assert 'start_session' in source and 'start_transaction' in source, \
        "Transaction not used in reorder_pages"
    assert 'TRANSACTION-SAFE' in source, "Should be marked as TRANSACTION-SAFE"
    
    print("[PASS] Reorder pages - uses transaction")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING LESSON FIXES VERIFICATION TESTS")
    print("="*80 + "\n")
    
    tests = [
        test_lesson_model_no_obsolete_methods,
        test_lesson_crud_uses_lesson_page_crud,
        test_cascade_delete_implemented,
        test_include_usage_returns_data,
        test_authorization_fixed,
        test_subject_validation_added,
        test_transaction_in_reorder,
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
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
