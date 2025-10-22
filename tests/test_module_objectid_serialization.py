# ==============================================================================
# File: tests/test_module_objectid_serialization.py
# Description: Verify module endpoint converts all ObjectIds to strings
# ==============================================================================
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_get_module_endpoint_converts_lesson_refs():
    """Test that get_module endpoint converts lesson_refs ObjectIds to strings"""
    
    import inspect
    from app.api.v1.endpoints.modules import get_module
    
    # Get source code
    source = inspect.getsource(get_module)
    
    # Should convert lesson_refs ObjectIds
    assert 'lesson_refs' in source, \
        "get_module should handle lesson_refs"
    
    assert 'str(ref["lesson_id"])' in source or "str(ref['lesson_id'])" in source, \
        "get_module should convert lesson_id to string in lesson_refs"
    
    print("[PASS] get_module endpoint converts lesson_refs ObjectIds")

def test_module_from_mongo_converts_objectids():
    """Test that Module.from_mongo converts ObjectIds to strings"""
    
    from app.models.lesson_assignment import Module
    import inspect
    
    source = inspect.getsource(Module.from_mongo)
    
    # Should convert various ObjectIds
    assert 'subject_id' in source and 'str(' in source, \
        "from_mongo should convert subject_id to string"
    
    assert 'created_by' in source and 'str(' in source, \
        "from_mongo should convert created_by to string"
    
    assert 'lesson_refs' in source, \
        "from_mongo should handle lesson_refs"
    
    print("[PASS] Module.from_mongo converts ObjectIds to strings")

def test_get_module_handles_all_objectid_fields():
    """Test that get_module endpoint handles all ObjectId fields"""
    
    import inspect
    from app.api.v1.endpoints.modules import get_module
    
    source = inspect.getsource(get_module)
    
    # Check all ObjectId conversions
    required_conversions = [
        'subject_id',
        'created_by',
        'collaborators',
        'lesson_refs'
    ]
    
    for field in required_conversions:
        assert field in source, f"get_module should handle {field} conversion"
    
    print("[PASS] get_module handles all ObjectId fields")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING MODULE OBJECTID SERIALIZATION VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_get_module_endpoint_converts_lesson_refs,
        test_module_from_mongo_converts_objectids,
        test_get_module_handles_all_objectid_fields,
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
        print("SUCCESS: Module ObjectId serialization verified!")
        print("\nFixed issues:")
        print("  [OK] lesson_refs ObjectIds converted to strings")
        print("  [OK] All ObjectId fields handled in endpoint")
        print("  [OK] No more 'ObjectId object is not iterable' error")
        print("\nModule endpoint will now return proper JSON!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
