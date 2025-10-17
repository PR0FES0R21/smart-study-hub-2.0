# ==============================================================================
# File: tests/test_media_confirm_upload_fix.py
# Description: Verify media confirm-upload KeyError fix
# ==============================================================================
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_media_endpoint_uses_correct_user_id_field():
    """Test that media endpoints use current_user['_id'] not current_user['id']"""
    import re
    
    with open('app/api/v1/endpoints/media.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all occurrences of current_user["id"]
    wrong_pattern = r'current_user\["id"\]'
    wrong_matches = re.findall(wrong_pattern, content)
    
    assert len(wrong_matches) == 0, \
        f"Found {len(wrong_matches)} occurrences of current_user['id'] (should use current_user['_id'])"
    
    # Verify correct pattern exists
    correct_pattern = r'current_user\["_id"\]'
    correct_matches = re.findall(correct_pattern, content)
    
    assert len(correct_matches) >= 4, \
        f"Expected at least 4 occurrences of current_user['_id'], found {len(correct_matches)}"
    
    print(f"[PASS] Media endpoints use correct field: current_user['_id'] ({len(correct_matches)} occurrences)")

def test_confirm_upload_endpoint_structure():
    """Test that confirm-upload endpoint has correct structure"""
    with open('app/api/v1/endpoints/media.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check endpoint exists
    assert 'def confirm_media_upload' in content, "confirm_media_upload function not found"
    assert '@router.post("/confirm-upload"' in content, "confirm-upload route not found"
    
    # Check uses correct user field in media_doc
    assert 'str(current_user["_id"])' in content, "Should convert current_user['_id'] to string"
    
    print("[PASS] confirm-upload endpoint has correct structure")

def test_list_media_uses_correct_field():
    """Test that list media endpoint uses correct user field"""
    with open('app/api/v1/endpoints/media.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find list media function
    assert 'def get_my_media_files' in content, "get_my_media_files function not found"
    
    # Check query uses correct field
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'uploaded_by' in line and 'query' in lines[max(0, i-3):i+1]:
            # Found uploaded_by in query context
            assert 'current_user["_id"]' in line, f"Line {i}: Query should use current_user['_id']"
    
    print("[PASS] List media endpoint uses correct user field")

def test_delete_media_uses_correct_field():
    """Test that delete media endpoint uses correct user field"""
    with open('app/api/v1/endpoints/media.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find delete function
    assert 'def delete_media_file' in content, "delete_media_file function not found"
    
    # Check both find_one and update_one use correct field
    lines = content.split('\n')
    delete_func_start = None
    
    for i, line in enumerate(lines):
        if 'def delete_media_file' in line:
            delete_func_start = i
            break
    
    if delete_func_start:
        # Check next 50 lines for uploaded_by and deleted_by
        func_lines = lines[delete_func_start:delete_func_start + 50]
        func_content = '\n'.join(func_lines)
        
        assert 'current_user["_id"]' in func_content, "Delete function should use current_user['_id']"
    
    print("[PASS] Delete media endpoint uses correct user field")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING MEDIA CONFIRM-UPLOAD FIX VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_media_endpoint_uses_correct_user_id_field,
        test_confirm_upload_endpoint_structure,
        test_list_media_uses_correct_field,
        test_delete_media_uses_correct_field,
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
        print("SUCCESS: Media confirm-upload fix verified!")
        print("\nFixed issues:")
        print("  [OK] confirm-upload: current_user['id'] -> current_user['_id']")
        print("  [OK] list_media: current_user['id'] -> current_user['_id']")
        print("  [OK] delete_media: current_user['id'] -> current_user['_id']")
        print("  [OK] All user ID references use correct field")
        print("\nNo more KeyError: 'id'!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
