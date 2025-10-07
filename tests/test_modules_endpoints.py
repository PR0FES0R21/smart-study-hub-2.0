"""
Comprehensive Unit Tests for Modules Endpoints
Tests all module-related endpoints

Usage:
    python tests/test_modules_endpoints.py

Requirements:
    - Server must be running on localhost:8000
    - Test accounts must exist (teacher, student, coordinator)
"""
import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"

# Test credentials - UPDATE THESE WITH REAL TEST ACCOUNTS FROM YOUR DB
TEST_CREDENTIALS = {
    "teacher": {"username": "202507001", "password": "202507001"},
    "student": {"username": "79111967", "password": "79111967"},
    "coordinator": {"username": "202507001", "password": "202507001"}
}

# Test data storage
TEST_DATA = {
    "tokens": {},
    "subject_id": None,
    "lesson_id": None,
    "module_id": None,
}

# Test results
TEST_RESULTS = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": []
}


def get_token(role):
    """Get auth token for a role"""
    if role in TEST_DATA["tokens"]:
        return TEST_DATA["tokens"][role]
    
    try:
        print(f"  > Logging in as {role}...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=TEST_CREDENTIALS[role],  # OAuth2 expects form data, not JSON
            timeout=5
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            TEST_DATA["tokens"][role] = token
            print(f"    [OK] Logged in successfully")
            return token
        else:
            print(f"    [FAIL] Login failed: {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"    [ERROR] Login error: {str(e)}")
    return None


def test_endpoint(name, func):
    """Wrapper for test execution"""
    try:
        print(f"\n{'='*80}")
        print(f"TEST: {name}")
        print(f"{'='*80}")
        result = func()
        if result is True:
            TEST_RESULTS["passed"] += 1
            print(f"[PASS] Test passed")
        elif result is False:
            TEST_RESULTS["failed"] += 1
            print(f"[FAIL] Test failed")
        else:
            TEST_RESULTS["skipped"] += 1
            print(f"[SKIP] Test skipped: {result}")
    except Exception as e:
        TEST_RESULTS["failed"] += 1
        TEST_RESULTS["errors"].append(f"{name}: {str(e)}")
        print(f"[ERROR] {str(e)}")


# ============================================================================
# SETUP - Get prerequisite data
# ============================================================================

def setup_test_data():
    """Setup prerequisite data for tests"""
    print("\n" + "="*80)
    print("SETUP: Getting prerequisite data")
    print("="*80)
    
    token = get_token("teacher")
    if not token:
        print("[ERROR] Cannot get teacher token")
        return False
    
    # Get subject ID
    subjects_response = requests.get(
        f"{BASE_URL}/subjects",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if subjects_response.status_code == 200:
        subjects = subjects_response.json()
        if subjects.get("data") and len(subjects["data"]) > 0:
            subject = subjects["data"][0]
            TEST_DATA["subject_id"] = str(subject.get("_id") or subject.get("id"))
            print(f"[OK] Got subject ID: {TEST_DATA['subject_id']}")
    
    if not TEST_DATA["subject_id"]:
        print("[ERROR] No subject available")
        return False
    
    # Create a lesson for testing
    lesson_data = {
        "title": f"Test Lesson for Modules - {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Automated test lesson for module testing",
        "subject_id": TEST_DATA["subject_id"],
        "grade_level": 10,
        "topic_tags": ["test", "modules"],
        "pages": [
            {
                "title": "Introduction",
                "content_markdown": "# Test Content\n\nThis is a test.",
                "media_references": [],
                "embedded_components": [],
                "estimated_duration": 10,
                "difficulty_level": "easy",
                "learning_objectives": ["Test objective"]
            }
        ],
        "difficulty_level": "medium",
        "learning_objectives": ["Test learning"],
        "prerequisites": [],
        "visibility": "public"
    }
    
    lesson_response = requests.post(
        f"{BASE_URL}/lessons",
        json=lesson_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if lesson_response.status_code == 201:
        data = lesson_response.json()
        TEST_DATA["lesson_id"] = data.get("id")
        print(f"[OK] Created test lesson: {TEST_DATA['lesson_id']}")
        return True
    else:
        print(f"[ERROR] Failed to create test lesson: {lesson_response.status_code}")
        print(f"Response: {lesson_response.text}")
        return False


# ============================================================================
# MODULE ENDPOINTS TESTS
# ============================================================================

def test_list_modules():
    """Test GET /modules"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    
    response = requests.get(
        f"{BASE_URL}/modules",
        params={"page": 1, "per_page": 20},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response type: {type(data)}")
        print(f"Response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        if isinstance(data, dict):
            items = data.get("items", data.get("data", []))
            total = data.get("total", data.get("total_items", 0))
            print(f"Returned: {len(items)} modules")
            print(f"Total: {total}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_create_module():
    """Test POST /modules"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["subject_id"]:
        return "No subject available"
    
    module_data = {
        "title": f"Test Module - {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Automated test module",
        "subject_id": TEST_DATA["subject_id"],
        "grade_level": 10,
        "topic_tags": ["test", "automated"],
        "difficulty_level": "medium",
        "learning_objectives": ["Test objective 1", "Test objective 2"],
        "prerequisites": [],
        "visibility": "public",
        "estimated_duration": 120
    }
    
    response = requests.post(
        f"{BASE_URL}/modules",
        json=module_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        # Response format: {"success": true, "message": "...", "module": {...}}
        module = data.get("module", {})
        TEST_DATA["module_id"] = module.get("id") or module.get("_id") or data.get("id")
        print(f"Created module ID: {TEST_DATA['module_id']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_module_detail():
    """Test GET /modules/{id}"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    
    response = requests.get(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        module = data.get("module", data)
        print(f"Module: {module.get('title', 'Unknown')}")
        print(f"Total lessons: {data.get('total_lessons', 0)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_add_lesson_to_module():
    """Test POST /modules/{id}/lessons"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    if not TEST_DATA["lesson_id"]:
        return "No lesson available"
    
    lesson_ref_data = {
        "lesson_id": TEST_DATA["lesson_id"],
        "order": 1,
        "is_required": True
    }
    
    response = requests.post(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}/lessons",
        json=lesson_ref_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_update_module():
    """Test PUT /modules/{id}"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    
    update_data = {
        "description": "Updated description from test",
        "topic_tags": ["test", "updated"]
    }
    
    response = requests.put(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Updated module: {data.get('title', 'Unknown')}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_module_with_lessons():
    """Test GET /modules/{id}?include_lessons=true"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    
    response = requests.get(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}",
        params={"include_lessons": True},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        lessons = data.get("lessons", [])
        print(f"Module has {len(lessons)} lessons")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_remove_lesson_from_module():
    """Test DELETE /modules/{id}/lessons/{lesson_id}"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    if not TEST_DATA["lesson_id"]:
        return "No lesson available"
    
    response = requests.delete(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}/lessons/{TEST_DATA['lesson_id']}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 204]:
        print(f"Lesson removed successfully")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_module_usage():
    """Test GET /modules/{id}/usage"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    
    response = requests.get(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}/usage",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Used in {data.get('used_in_courses', 0)} courses")
        print(f"Total students: {data.get('total_students_affected', 0)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_delete_module():
    """Test DELETE /modules/{id}"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["module_id"]:
        return "No module created"
    
    response = requests.delete(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 204]:
        print(f"Module deleted successfully")
        return True
    else:
        print(f"Error: {response.text}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all module endpoint tests"""
    print("\n" + "="*80)
    print("MODULE ENDPOINTS COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Setup
    if not setup_test_data():
        print("\n[FATAL] Setup failed. Cannot continue tests.")
        return
    
    # Run tests
    test_endpoint("List Modules", test_list_modules)
    test_endpoint("Create Module", test_create_module)
    test_endpoint("Get Module Detail", test_get_module_detail)
    test_endpoint("Add Lesson to Module", test_add_lesson_to_module)
    test_endpoint("Get Module with Lessons", test_get_module_with_lessons)
    test_endpoint("Update Module", test_update_module)
    test_endpoint("Get Module Usage", test_get_module_usage)
    test_endpoint("Remove Lesson from Module", test_remove_lesson_from_module)
    test_endpoint("Delete Module", test_delete_module)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed:  {TEST_RESULTS['passed']}")
    print(f"Failed:  {TEST_RESULTS['failed']}")
    print(f"Skipped: {TEST_RESULTS['skipped']}")
    print(f"Total:   {TEST_RESULTS['passed'] + TEST_RESULTS['failed'] + TEST_RESULTS['skipped']}")
    
    if TEST_RESULTS['errors']:
        print(f"\nERRORS:")
        for error in TEST_RESULTS['errors']:
            print(f"  - {error}")
    
    print(f"\nTest Data Created:")
    print(f"  Subject ID: {TEST_DATA['subject_id']}")
    print(f"  Lesson ID:  {TEST_DATA['lesson_id']}")
    print(f"  Module ID:  {TEST_DATA['module_id']}")
    
    print("\n" + "="*80)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == "__main__":
    run_all_tests()
