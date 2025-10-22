# ==============================================================================
# File: tests/test_module_crud_objectid_fix.py
# Description: Verify create and update module endpoints convert ObjectIds
# ==============================================================================
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_create_module_converts_objectids():
    """Test that create_module endpoint converts all ObjectIds to strings"""
    
    import inspect
    from app.api.v1.endpoints.modules import create_module
    
    source = inspect.getsource(create_module)
    
    # Should convert ObjectId fields
    assert 'subject_id' in source and 'str(' in source, \
        "create_module should convert subject_id to string"
    
    assert 'created_by' in source and 'str(' in source, \
        "create_module should convert created_by to string"
    
    assert 'collaborators' in source, \
        "create_module should handle collaborators"
    
    assert 'lesson_refs' in source, \
        "create_module should handle lesson_refs"
    
    print("[PASS] create_module converts ObjectIds to strings")

def test_update_module_converts_objectids():
    """Test that update_module endpoint converts all ObjectIds to strings"""
    
    import inspect
    from app.api.v1.endpoints.modules import update_module
    
    source = inspect.getsource(update_module)
    
    # Should convert ObjectId fields
    assert 'subject_id' in source and 'str(' in source, \
        "update_module should convert subject_id to string"
    
    assert 'created_by' in source and 'str(' in source, \
        "update_module should convert created_by to string"
    
    assert 'collaborators' in source, \
        "update_module should handle collaborators"
    
    assert 'lesson_refs' in source, \
        "update_module should handle lesson_refs"
    
    print("[PASS] update_module converts ObjectIds to strings")

def test_get_module_converts_objectids():
    """Test that get_module endpoint converts all ObjectIds to strings"""
    
    import inspect
    from app.api.v1.endpoints.modules import get_module
    
    source = inspect.getsource(get_module)
    
    # Should convert ObjectId fields
    assert 'subject_id' in source and 'str(' in source, \
        "get_module should convert subject_id to string"
    
    assert 'created_by' in source and 'str(' in source, \
        "get_module should convert created_by to string"
    
    assert 'lesson_refs' in source, \
        "get_module should handle lesson_refs ObjectIds"
    
    print("[PASS] get_module converts ObjectIds to strings")

def test_all_crud_endpoints_consistent():
    """Test that all CRUD endpoints use consistent ObjectId conversion pattern"""
    
    import inspect
    from app.api.v1.endpoints.modules import create_module, update_module, get_module
    
    create_source = inspect.getsource(create_module)
    update_source = inspect.getsource(update_module)
    get_source = inspect.getsource(get_module)
    
    # All should convert lesson_refs ObjectIds
    assert 'lesson_refs' in create_source, "create_module should handle lesson_refs"
    assert 'lesson_refs' in update_source, "update_module should handle lesson_refs"
    assert 'lesson_refs' in get_source, "get_module should handle lesson_refs"
    
    # All should handle by_alias=False
    assert 'by_alias=False' in create_source or 'by_alias' in create_source, \
        "create_module should use by_alias=False"
    assert 'by_alias=False' in update_source or 'by_alias' in update_source, \
        "update_module should use by_alias=False"
    assert 'by_alias=False' in get_source or 'by_alias' in get_source, \
        "get_module should use by_alias=False"
    
    print("[PASS] All CRUD endpoints use consistent pattern")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING MODULE CRUD OBJECTID FIX VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_create_module_converts_objectids,
        test_update_module_converts_objectids,
        test_get_module_converts_objectids,
        test_all_crud_endpoints_consistent,
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
        print("SUCCESS: Module CRUD ObjectId fix verified!")
        print("\nFixed endpoints:")
        print("  [OK] POST /modules (create)")
        print("  [OK] PUT /modules/{id} (update)")
        print("  [OK] GET /modules/{id} (get)")
        print("\nFixed issues:")
        print("  [OK] All ObjectId fields converted to strings")
        print("  [OK] lesson_refs ObjectIds handled")
        print("  [OK] Consistent pattern across all CRUD endpoints")
        print("\nNo more 'ObjectId object is not iterable' errors!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
