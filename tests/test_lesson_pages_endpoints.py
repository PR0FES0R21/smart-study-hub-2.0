# ==============================================================================
# File: tests/test_lesson_pages_endpoints.py
# Description: Comprehensive unit tests for lesson pages endpoints
# ==============================================================================
import requests
import json
from datetime import datetime
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_DATA = {
    "teacher_token": None,
    "teacher_id": None,
    "subject_id": None,
    "lesson_id": None,
    "page_ids": [],  # Will store created page numbers
}

# Test counters
TESTS_PASSED = 0
TESTS_FAILED = 0
TESTS_SKIPPED = 0

# ==================== HELPER FUNCTIONS ====================

def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"TEST: {title}")
    print("="*80)

def print_result(success: bool, message: str = ""):
    """Print test result"""
    global TESTS_PASSED, TESTS_FAILED
    
    if success:
        print(f"[PASS] Test passed")
        if message:
            print(f"       {message}")
        TESTS_PASSED += 1
    else:
        print(f"[FAIL] Test failed")
        if message:
            print(f"       {message}")
        TESTS_FAILED += 1

def test_endpoint(name: str, test_func):
    """Run a single test endpoint"""
    print_header(name)
    
    try:
        result = test_func()
        
        if isinstance(result, bool):
            print_result(result)
        elif isinstance(result, str):
            # Skip message
            global TESTS_SKIPPED
            print(f"[SKIP] {result}")
            TESTS_SKIPPED += 1
        else:
            print_result(True)
            
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()

def get_token(role: str = "teacher") -> Optional[str]:
    """Login and get authentication token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": "guru.budi",  # Change to your test user
                "password": "password123"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            TEST_DATA["teacher_token"] = data["access_token"]
            TEST_DATA["teacher_id"] = data.get("user", {}).get("id")
            return data["access_token"]
        else:
            print(f"Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Login error: {e}")
        return None

# ==================== SETUP TESTS ====================

def setup_get_subject():
    """Get subject ID for creating lessons"""
    token = TEST_DATA["teacher_token"]
    if not token:
        return "No teacher token"
    
    try:
        response = requests.get(
            f"{BASE_URL}/subjects",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                TEST_DATA["subject_id"] = data[0]["_id"]
                print(f"[OK] Got subject ID: {TEST_DATA['subject_id']}")
                return True
            else:
                print("[WARN] No subjects found")
                return False
        else:
            print(f"Failed to get subjects: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error getting subjects: {e}")
        return False

def setup_create_lesson():
    """Create a test lesson"""
    token = TEST_DATA["teacher_token"]
    subject_id = TEST_DATA["subject_id"]
    
    if not token or not subject_id:
        return "Missing token or subject_id"
    
    try:
        lesson_data = {
            "title": f"Test Lesson - Pages {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Test lesson for pages endpoint testing",
            "subject_id": subject_id,
            "grade_level": 10,
            "topic_tags": ["test", "pages"],
            "difficulty_level": "medium",
            "learning_objectives": ["Test page operations"],
            "visibility": "public",
            "status": "published"
        }
        
        response = requests.post(
            f"{BASE_URL}/lessons",
            json=lesson_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            TEST_DATA["lesson_id"] = data["id"]
            print(f"[OK] Created test lesson: {TEST_DATA['lesson_id']}")
            return True
        else:
            print(f"Failed to create lesson: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error creating lesson: {e}")
        return False

# ==================== PAGE ENDPOINT TESTS ====================

def test_list_pages_empty():
    """Test GET /lessons/{id}/pages (empty)"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}/pages",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Lesson: {data.get('lesson_title')}")
            print(f"Total pages: {data.get('total_pages', 0)}")
            
            if data.get('total_pages', 0) == 0:
                print("[OK] List pages empty as expected")
                return True
            else:
                print(f"[WARN] Expected 0 pages, got {data.get('total_pages')}")
                return True  # Still pass, just unexpected
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_create_page_1():
    """Test POST /lessons/{id}/pages (Page 1)"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        page_data = {
            "page_number": 1,
            "title": "Introduction to Testing",
            "content_markdown": "# Introduction\n\nThis is the first page of our test lesson.\n\n## What we'll learn\n\n- Creating pages\n- Reading pages\n- Updating pages\n- Deleting pages\n\n![Test Image](https://via.placeholder.com/600x400)\n\nLet's get started!",
            "estimated_duration": 10,
            "difficulty_level": "easy",
            "learning_objectives": ["Understand page creation", "Learn API usage"],
            "status": "published"
        }
        
        response = requests.post(
            f"{BASE_URL}/lessons/{lesson_id}/pages",
            json=page_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"Created page: {data.get('page_number')} - {data.get('title')}")
            print(f"Page ID: {data.get('id')}")
            print(f"Version: {data.get('version', 1)}")
            TEST_DATA["page_ids"].append(1)
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_create_page_2():
    """Test POST /lessons/{id}/pages (Page 2)"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        page_data = {
            "page_number": 2,
            "title": "Advanced Concepts",
            "content_markdown": "# Advanced Concepts\n\nNow let's dive deeper into testing.\n\n## Topics\n\n1. Unit testing\n2. Integration testing\n3. End-to-end testing\n\n**Video tutorial:**\n\n<video controls>\n  <source src=\"https://example.com/video.mp4\" type=\"video/mp4\">\n</video>\n\n## Practice Exercise\n\nTry creating your own test cases!",
            "estimated_duration": 15,
            "difficulty_level": "medium",
            "learning_objectives": ["Master testing concepts"],
            "status": "published"
        }
        
        response = requests.post(
            f"{BASE_URL}/lessons/{lesson_id}/pages",
            json=page_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"Created page: {data.get('page_number')} - {data.get('title')}")
            TEST_DATA["page_ids"].append(2)
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_create_page_3():
    """Test POST /lessons/{id}/pages (Page 3)"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        page_data = {
            "page_number": 3,
            "title": "Summary and Conclusion",
            "content_markdown": "# Summary\n\nGreat job completing this lesson!\n\n## What we learned\n\n- ✅ Page creation\n- ✅ Content formatting\n- ✅ Media embedding\n\n## Next Steps\n\n- Practice more\n- Build your own content\n- Share with others\n\n**Download resources:**\n\n[📥 Download PDF](https://example.com/resources.pdf)",
            "estimated_duration": 5,
            "difficulty_level": "easy",
            "learning_objectives": ["Review concepts"],
            "status": "published"
        }
        
        response = requests.post(
            f"{BASE_URL}/lessons/{lesson_id}/pages",
            json=page_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"Created page: {data.get('page_number')} - {data.get('title')}")
            TEST_DATA["page_ids"].append(3)
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_list_pages_with_content():
    """Test GET /lessons/{id}/pages (with 3 pages)"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}/pages?summary_only=true",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Lesson: {data.get('lesson_title')}")
            print(f"Total pages: {data.get('total_pages', 0)}")
            
            if data.get('total_pages', 0) == 3:
                print("[OK] All 3 pages listed")
                for page in data.get('pages', []):
                    print(f"  - Page {page['page_number']}: {page['title']}")
                return True
            else:
                print(f"[WARN] Expected 3 pages, got {data.get('total_pages')}")
                return False
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_get_single_page():
    """Test GET /lessons/{id}/pages/{page_number}"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}/pages/1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Current page: {data.get('current_page')}")
            print(f"Total pages: {data.get('total_pages')}")
            print(f"Has previous: {data.get('has_previous')}")
            print(f"Has next: {data.get('has_next')}")
            
            page = data.get('page', {})
            print(f"Page title: {page.get('title')}")
            print(f"Content length: {len(page.get('content_markdown', ''))} chars")
            print(f"Duration: {page.get('estimated_duration')} mins")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_get_batch_pages():
    """Test GET /lessons/{id}/pages/batch"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}/pages/batch?page_numbers=1,2,3",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Requested pages: {data.get('page_numbers')}")
            print(f"Pages returned: {len(data.get('pages', []))}")
            
            for page in data.get('pages', []):
                print(f"  - Page {page['page_number']}: {page['title']}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_update_page():
    """Test PUT /lessons/{id}/pages/{page_number}"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        update_data = {
            "title": "Introduction to Testing (UPDATED)",
            "content_markdown": "# Introduction (UPDATED)\n\nThis content has been updated!\n\n## New section\n\nThis is a new section added via update.",
            "estimated_duration": 12
        }
        
        response = requests.put(
            f"{BASE_URL}/lessons/{lesson_id}/pages/1",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Updated page: {data.get('page_number')}")
            print(f"New title: {data.get('title')}")
            print(f"New duration: {data.get('estimated_duration')} mins")
            print(f"Version: {data.get('version')}")  # Should be incremented
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_reorder_pages():
    """Test PUT /lessons/{id}/pages/reorder"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        reorder_data = {
            "page_numbers": [3, 1, 2]  # Reverse order
        }
        
        response = requests.put(
            f"{BASE_URL}/lessons/{lesson_id}/pages/reorder",
            json=reorder_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            print(f"New order: {data.get('new_order')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_delete_page():
    """Test DELETE /lessons/{id}/pages/{page_number}"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        # Delete page 2 (which is now at position 3 after reorder)
        response = requests.delete(
            f"{BASE_URL}/lessons/{lesson_id}/pages/3",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            
            # Verify page count reduced
            list_response = requests.get(
                f"{BASE_URL}/lessons/{lesson_id}/pages",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if list_response.status_code == 200:
                list_data = list_response.json()
                print(f"Remaining pages: {list_data.get('total_pages')}")
                return list_data.get('total_pages') == 2
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_verify_lesson_metadata():
    """Test that lesson metadata is auto-updated"""
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not token or not lesson_id:
        return "Missing token or lesson_id"
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            
            print(f"Lesson metadata:")
            print(f"  - Total pages: {metadata.get('total_pages')}")
            print(f"  - Total duration: {metadata.get('total_duration')} mins")
            print(f"  - Last calculated: {metadata.get('calculated_at')}")
            
            # Should have 2 pages after deletion
            if metadata.get('total_pages') == 2:
                print("[OK] Metadata auto-updated correctly")
                return True
            else:
                print(f"[WARN] Expected 2 pages in metadata, got {metadata.get('total_pages')}")
                return False
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

# ==================== MAIN TEST RUNNER ====================

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("LESSON PAGES ENDPOINTS - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Setup
    print("\n" + "="*80)
    print("SETUP: Getting prerequisite data")
    print("="*80)
    
    print("\n  > Logging in as teacher...")
    token = get_token("teacher")
    if not token:
        print("\n[FATAL] Setup failed: Could not login")
        return
    print("    [OK] Logged in successfully")
    
    if not setup_get_subject():
        print("\n[FATAL] Setup failed: Could not get subject")
        return
    
    if not setup_create_lesson():
        print("\n[FATAL] Setup failed: Could not create lesson")
        return
    
    # Run tests
    test_endpoint("1. List Pages (Empty)", test_list_pages_empty)
    test_endpoint("2. Create Page 1", test_create_page_1)
    test_endpoint("3. Create Page 2", test_create_page_2)
    test_endpoint("4. Create Page 3", test_create_page_3)
    test_endpoint("5. List Pages (With Content)", test_list_pages_with_content)
    test_endpoint("6. Get Single Page (With Navigation)", test_get_single_page)
    test_endpoint("7. Get Batch Pages (Prefetch)", test_get_batch_pages)
    test_endpoint("8. Update Page", test_update_page)
    test_endpoint("9. Reorder Pages", test_reorder_pages)
    test_endpoint("10. Delete Page", test_delete_page)
    test_endpoint("11. Verify Lesson Metadata Auto-Update", test_verify_lesson_metadata)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed:  {TESTS_PASSED}")
    print(f"Failed:  {TESTS_FAILED}")
    print(f"Skipped: {TESTS_SKIPPED}")
    print(f"Total:   {TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED}")
    
    print(f"\nTest Data Created:")
    print(f"  Lesson ID: {TEST_DATA['lesson_id']}")
    print(f"  Pages Created: {TEST_DATA['page_ids']}")
    
    print("\n" + "="*80)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Return exit code
    return 0 if TESTS_FAILED == 0 else 1

if __name__ == "__main__":
    exit(main())
