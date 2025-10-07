"""
Comprehensive Unit Tests for LMS Endpoints
Tests all endpoints: Lessons, Modules, Courses, Progress Tracking

Usage:
    python tests/test_lms_endpoints.py

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
    "course_id": None,
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
# LESSON ENDPOINTS TESTS
# ============================================================================

def test_list_lessons():
    """Test GET /lessons"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    
    response = requests.get(
        f"{BASE_URL}/lessons",
        params={"page": 1, "per_page": 20},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Returned: {len(data.get('items', []))} lessons")
        print(f"Total: {data.get('total', 0)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_create_lesson():
    """Test POST /lessons"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    
    # First get a subject ID
    subjects_response = requests.get(
        f"{BASE_URL}/subjects",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if subjects_response.status_code == 200:
        subjects = subjects_response.json()
        if subjects.get("data") and len(subjects["data"]) > 0:
            # Subject endpoint returns "_id" not "id"
            subject = subjects["data"][0]
            TEST_DATA["subject_id"] = str(subject.get("_id") or subject.get("id"))
    
    if not TEST_DATA["subject_id"]:
        return "No subject available"
    
    lesson_data = {
        "title": f"Test Lesson - {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Automated test lesson",
        "subject_id": TEST_DATA["subject_id"],
        "grade_level": 10,
        "topic_tags": ["test", "automated"],
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
    
    response = requests.post(
        f"{BASE_URL}/lessons",
        json=lesson_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        TEST_DATA["lesson_id"] = data.get("id")
        print(f"Created lesson ID: {TEST_DATA['lesson_id']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_lesson_detail():
    """Test GET /lessons/{id}"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    if not TEST_DATA["lesson_id"]:
        return "No lesson created"
    
    response = requests.get(
        f"{BASE_URL}/lessons/{TEST_DATA['lesson_id']}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Lesson: {data.get('title')}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_lesson_library():
    """Test GET /lessons/library"""
    token = get_token("teacher")
    if not token:
        return "No teacher token"
    
    response = requests.get(
        f"{BASE_URL}/lessons/library",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Featured: {len(data.get('featured_lessons', []))}")
        print(f"Recent: {len(data.get('recent_lessons', []))}")
        return True
    else:
        print(f"Error: {response.text}")
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
        print(f"Returned: {len(data.get('items', []))} modules")
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
        "topic_tags": ["test"],
        "difficulty_level": "medium",
        "learning_objectives": ["Test objective"],
        "estimated_duration": 60,
        "visibility": "public"
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
        TEST_DATA["module_id"] = data.get("module", {}).get("id")
        print(f"Created module ID: {TEST_DATA['module_id']}")
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
        return "No lesson created"
    
    lesson_config = {
        "lesson_id": TEST_DATA["lesson_id"],
        "order": 1,
        "required": True,
        "unlock_condition": "sequential",
        "estimated_duration": 30
    }
    
    response = requests.post(
        f"{BASE_URL}/modules/{TEST_DATA['module_id']}/lessons",
        json=lesson_config,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Added lesson to module")
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
        params={"include_lessons": True},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Module: {data.get('title')}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


# ============================================================================
# COURSE ENDPOINTS TESTS
# ============================================================================

def test_list_courses():
    """Test GET /courses"""
    token = get_token("coordinator")
    if not token:
        return "No coordinator token"
    
    response = requests.get(
        f"{BASE_URL}/courses",
        params={"page": 1, "per_page": 20},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Returned: {len(data.get('items', []))} courses")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_create_course():
    """Test POST /courses"""
    token = get_token("coordinator")
    if not token:
        return "No coordinator token"
    if not TEST_DATA["subject_id"]:
        return "No subject available"
    
    course_data = {
        "title": f"Test Course - {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Automated test course",
        "subject_id": TEST_DATA["subject_id"],
        "grade_level": 10,
        "difficulty_level": "medium",
        "learning_objectives": ["Test objective"],
        "prerequisites": [],
        "visibility": "institutional"
    }
    
    response = requests.post(
        f"{BASE_URL}/courses",
        json=course_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        TEST_DATA["course_id"] = data.get("course", {}).get("id")
        print(f"Created course ID: {TEST_DATA['course_id']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_add_module_to_course():
    """Test POST /courses/{id}/modules"""
    token = get_token("coordinator")
    if not token:
        return "No coordinator token"
    if not TEST_DATA["course_id"]:
        return "No course created"
    if not TEST_DATA["module_id"]:
        return "No module created"
    
    module_config = {
        "module_id": TEST_DATA["module_id"],
        "order": 1,
        "required": True,
        "unlock_condition": "sequential"
    }
    
    response = requests.post(
        f"{BASE_URL}/courses/{TEST_DATA['course_id']}/modules",
        json=module_config,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Added module to course")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_course_detail():
    """Test GET /courses/{id}"""
    token = get_token("coordinator")
    if not token:
        return "No coordinator token"
    if not TEST_DATA["course_id"]:
        return "No course created"
    
    response = requests.get(
        f"{BASE_URL}/courses/{TEST_DATA['course_id']}",
        params={"include_modules": True},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Course: {data.get('title')}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


# ============================================================================
# PROGRESS TRACKING TESTS
# ============================================================================

def test_enroll_in_course():
    """Test POST /progress/courses/{id}/enroll"""
    token = get_token("student")
    if not token:
        return "No student token"
    if not TEST_DATA["course_id"]:
        return "No course created"
    
    response = requests.post(
        f"{BASE_URL}/progress/courses/{TEST_DATA['course_id']}/enroll",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Enrolled in course")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_get_course_dashboard():
    """Test GET /progress/courses/{id}/dashboard"""
    token = get_token("student")
    if not token:
        return "No student token"
    if not TEST_DATA["course_id"]:
        return "No course created"
    
    response = requests.get(
        f"{BASE_URL}/progress/courses/{TEST_DATA['course_id']}/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Progress: {data.get('overall_progress', {}).get('completion_percentage', 0)}%")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_start_lesson():
    """Test POST /progress/lessons/{id}/start"""
    token = get_token("student")
    if not token:
        return "No student token"
    if not TEST_DATA["lesson_id"]:
        return "No lesson created"
    
    start_data = {
        "course_id": TEST_DATA["course_id"],
        "module_id": TEST_DATA["module_id"],
        "access_method": "via_course"
    }
    
    response = requests.post(
        f"{BASE_URL}/progress/lessons/{TEST_DATA['lesson_id']}/start",
        json=start_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Started lesson")
        return True
    else:
        print(f"Error: {response.text}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("\n")
    print("=" * 80)
    print("LMS ENDPOINTS COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Run tests in order
    tests = [
        # Lesson tests
        ("List Lessons", test_list_lessons),
        ("Create Lesson", test_create_lesson),
        ("Get Lesson Detail", test_get_lesson_detail),
        ("Get Lesson Library", test_get_lesson_library),
        
        # Module tests
        ("List Modules", test_list_modules),
        ("Create Module", test_create_module),
        ("Add Lesson to Module", test_add_lesson_to_module),
        ("Get Module Detail", test_get_module_detail),
        
        # Course tests
        ("List Courses", test_list_courses),
        ("Create Course", test_create_course),
        ("Add Module to Course", test_add_module_to_course),
        ("Get Course Detail", test_get_course_detail),
        
        # Progress tests
        ("Enroll in Course", test_enroll_in_course),
        ("Get Course Dashboard", test_get_course_dashboard),
        ("Start Lesson", test_start_lesson),
    ]
    
    for name, func in tests:
        test_endpoint(name, func)
    
    # Print summary
    print("\n")
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Passed:  {TEST_RESULTS['passed']}")
    print(f"Failed:  {TEST_RESULTS['failed']}")
    print(f"Skipped: {TEST_RESULTS['skipped']}")
    print(f"Total:   {sum([TEST_RESULTS['passed'], TEST_RESULTS['failed'], TEST_RESULTS['skipped']])}")
    
    if TEST_RESULTS["errors"]:
        print("\nERRORS:")
        for error in TEST_RESULTS["errors"]:
            print(f"  - {error}")
    
    print("\nTest Data Created:")
    print(f"  Subject ID: {TEST_DATA.get('subject_id', 'N/A')}")
    print(f"  Lesson ID:  {TEST_DATA.get('lesson_id', 'N/A')}")
    print(f"  Module ID:  {TEST_DATA.get('module_id', 'N/A')}")
    print(f"  Course ID:  {TEST_DATA.get('course_id', 'N/A')}")
    
    print("\n" + "=" * 80)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    return 0 if TEST_RESULTS["failed"] == 0 else 1


if __name__ == "__main__":
    exit(main())
