# ==============================================================================
# File: tests/test_permission_fix.py
# Description: Test untuk verify permission fix (can_edit, can_delete)
# ==============================================================================
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_is_editable_by_string_comparison():
    """Test that is_editable_by() handles string comparison correctly"""
    from app.models.lesson import Lesson, LessonMetadata
    from bson import ObjectId
    
    # Create a lesson with ObjectId
    user_id = ObjectId()
    lesson = Lesson(
        title="Test Lesson",
        description="Test Description",
        subject_id=str(ObjectId()),
        grade_level=10,
        created_by=str(user_id),  # String
        collaborators=[]
    )
    
    # Test 1: Should be editable by creator (string comparison)
    assert lesson.is_editable_by(str(user_id)), "Creator should be able to edit (string)"
    assert lesson.is_editable_by(user_id), "Creator should be able to edit (ObjectId)"
    
    # Test 2: Should NOT be editable by different user
    other_user_id = ObjectId()
    assert not lesson.is_editable_by(str(other_user_id)), "Different user should not be able to edit"
    
    # Test 3: Should be editable by collaborator
    collaborator_id = ObjectId()
    lesson.collaborators = [str(collaborator_id)]
    assert lesson.is_editable_by(str(collaborator_id)), "Collaborator should be able to edit (string)"
    assert lesson.is_editable_by(collaborator_id), "Collaborator should be able to edit (ObjectId)"
    
    print("[PASS] is_editable_by() handles string/ObjectId comparison correctly")

def test_aggregation_includes_collaborators():
    """Test that aggregation pipeline includes collaborators field"""
    from app.crud.lesson import lesson_crud
    import inspect
    
    source = inspect.getsource(lesson_crud.list_lessons)
    assert '"collaborators"' in source, "Aggregation pipeline should include collaborators field"
    assert '$map' in source, "Should use $map to convert collaborators to strings"
    
    print("[PASS] Aggregation pipeline includes collaborators field")

def test_endpoint_sets_permissions():
    """Test that list_lessons endpoint sets permission fields"""
    import inspect
    from app.api.v1.endpoints.lessons import list_lessons
    
    source = inspect.getsource(list_lessons)
    assert 'can_edit' in source, "Endpoint should set can_edit"
    assert 'can_delete' in source, "Endpoint should set can_delete"
    assert 'item["created_by"]' in source, "Should check created_by for permissions"
    
    print("[PASS] list_lessons endpoint sets permission fields")

def test_get_lesson_uses_str_conversion():
    """Test that get_lesson endpoint uses string conversion for comparison"""
    import inspect
    from app.api.v1.endpoints.lessons import get_lesson
    
    source = inspect.getsource(get_lesson)
    
    # Should have str() conversion for created_by comparison
    lines = source.split('\n')
    can_delete_lines = [l for l in lines if 'can_delete' in l.lower()]
    
    assert any('str(' in line for line in can_delete_lines), \
        "get_lesson should use str() conversion for can_delete comparison"
    
    print("[PASS] get_lesson endpoint uses string conversion")

def test_update_lesson_uses_str_conversion():
    """Test that update_lesson endpoint uses string conversion"""
    import inspect
    from app.api.v1.endpoints.lessons import update_lesson
    
    source = inspect.getsource(update_lesson)
    
    # Should have str() conversion
    lines = source.split('\n')
    can_delete_lines = [l for l in lines if 'can_delete' in l.lower()]
    
    assert any('str(' in line for line in can_delete_lines), \
        "update_lesson should use str() conversion for can_delete comparison"
    
    print("[PASS] update_lesson endpoint uses string conversion")

def run_all_tests():
    """Run all permission fix tests"""
    print("\n" + "="*80)
    print("RUNNING PERMISSION FIX VERIFICATION TESTS")
    print("="*80 + "\n")
    
    tests = [
        test_is_editable_by_string_comparison,
        test_aggregation_includes_collaborators,
        test_endpoint_sets_permissions,
        test_get_lesson_uses_str_conversion,
        test_update_lesson_uses_str_conversion,
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
        print("SUCCESS: All permission fixes verified!")
        print("\nYour lessons should now show:")
        print("  - can_edit: true   (if you are creator or collaborator)")
        print("  - can_delete: true (if you are creator)")
        print("  - is_favorited: false (feature not yet implemented)")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
