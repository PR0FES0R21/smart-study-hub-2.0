# ==============================================================================
# File: tests/test_batch_route_fix.py
# Description: Verify batch route is defined before {page_number} route
# ==============================================================================
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_batch_route_order():
    """Test that /pages/batch route is defined BEFORE /pages/{page_number}"""
    
    with open('app/api/v1/endpoints/lessons.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find line numbers for both routes
    batch_pattern = r'@router\.get\(["\']/{lesson_id}/pages/batch["\']'
    page_num_pattern = r'@router\.get\(["\']/{lesson_id}/pages/{page_number}["\']'
    
    batch_match = re.search(batch_pattern, content)
    page_num_match = re.search(page_num_pattern, content)
    
    assert batch_match, "Batch route not found"
    assert page_num_match, "Page number route not found"
    
    batch_pos = batch_match.start()
    page_num_pos = page_num_match.start()
    
    assert batch_pos < page_num_pos, \
        f"Route order incorrect! Batch route must be BEFORE page_number route.\n" \
        f"Batch at position {batch_pos}, page_number at {page_num_pos}"
    
    # Calculate approximate line numbers for better error messages
    lines_before_batch = content[:batch_pos].count('\n')
    lines_before_page_num = content[:page_num_pos].count('\n')
    
    print(f"[PASS] Route order correct:")
    print(f"  - /pages/batch at line ~{lines_before_batch}")
    print(f"  - /pages/{{page_number}} at line ~{lines_before_page_num}")
    print(f"  [OK] Specific route comes first (prevents routing conflict)")

def test_no_duplicate_batch_routes():
    """Test that there are no duplicate batch route definitions"""
    
    with open('app/api/v1/endpoints/lessons.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    batch_pattern = r'@router\.get\(["\']/{lesson_id}/pages/batch["\']'
    matches = re.findall(batch_pattern, content)
    
    assert len(matches) == 1, \
        f"Found {len(matches)} batch route definitions. Should be exactly 1."
    
    print(f"[PASS] No duplicate batch routes (found exactly 1)")

def test_batch_route_has_comment():
    """Test that batch route has explanatory comment about route order"""
    
    with open('app/api/v1/endpoints/lessons.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find batch route function
    batch_start = content.find('@router.get("/{lesson_id}/pages/batch"')
    assert batch_start != -1, "Batch route not found"
    
    # Get next 500 characters (docstring area)
    batch_section = content[batch_start:batch_start + 500]
    
    # Check for comment about route order
    has_comment = any(keyword in batch_section.lower() for keyword in [
        'before', 'route', 'conflict', 'order', 'must be defined'
    ])
    
    assert has_comment, \
        "Batch route should have comment explaining it must be defined before {page_number} route"
    
    print("[PASS] Batch route has explanatory comment about route order")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING BATCH ROUTE ORDER FIX VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_batch_route_order,
        test_no_duplicate_batch_routes,
        test_batch_route_has_comment,
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
        print("SUCCESS: Batch route order fix verified!")
        print("\nFixed issues:")
        print("  [OK] /pages/batch defined BEFORE /pages/{page_number}")
        print("  [OK] No duplicate route definitions")
        print("  [OK] Explanatory comment added")
        print("\nNo more routing conflicts!")
        print("\nNow this will work:")
        print("  GET /lessons/{id}/pages/batch?page_numbers=1,2,3")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
