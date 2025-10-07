# ==============================================================================
# File: tests/test_all_lesson_endpoints.py
# Description: Comprehensive test for ALL lesson endpoints to identify errors
# ==============================================================================
import requests
import json
from datetime import datetime
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_DATA = {
    "teacher_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ODgyMmYwNzk3OWNiYmEyM2U2ZGI5NTAiLCJleHAiOjc3NTk4NTkxNzd9.mlLTqtqz9Cnv0_jsEW6MK9xcC5QSZRHE7cdgVwQPHEg",
    "subject_id": "68b328329be3ef2464823bff",
    "lesson_id": "68e417bcfd89bb8eb15f09ad",
}

TESTS_PASSED = 0
TESTS_FAILED = 0
FAILED_TESTS = []

def print_header(title: str):
    print("\n" + "="*80)
    print(f"TEST: {title}")
    print("="*80)

def print_result(success: bool, test_name: str, message: str = ""):
    global TESTS_PASSED, TESTS_FAILED, FAILED_TESTS
    
    if success:
        print(f"[PASS] {test_name}")
        if message:
            print(f"       {message}")
        TESTS_PASSED += 1
    else:
        print(f"[FAIL] {test_name}")
        if message:
            print(f"       {message}")
        TESTS_FAILED += 1
        FAILED_TESTS.append({"test": test_name, "error": message})

def get_token() -> Optional[str]:
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": "guru.budi", "password": "password123"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            TEST_DATA["teacher_token"] = data["access_token"]
            print(f"[OK] Logged in successfully")
            return data["access_token"]
        else:
            print(f"[ERROR] Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return None

def setup_prerequisites():
    """Get subject ID"""
    token = TEST_DATA["teacher_token"]
    
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
        
        print("[ERROR] No subjects found")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

# ==================== TEST FUNCTIONS ====================

def test_create_lesson():
    """Test POST /lessons"""
    test_name = "POST /lessons (Create Lesson)"
    token = TEST_DATA["teacher_token"]
    subject_id = TEST_DATA["subject_id"]
    
    try:
        lesson_data = {
            "title": f"Test Lesson {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Test lesson description",
            "subject_id": subject_id,
            "grade_level": 10,
            "topic_tags": ["test"],
            "difficulty_level": "medium",
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
            print_result(True, test_name, f"Created lesson: {data['id']}")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_get_lesson_basic():
    """Test GET /lessons/{id}"""
    test_name = "GET /lessons/{id} (Basic)"
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not lesson_id:
        print_result(False, test_name, "No lesson_id available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Got lesson: {data['title']}")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_get_lesson_with_usage():
    """Test GET /lessons/{id}?include_usage=true"""
    test_name = "GET /lessons/{id}?include_usage=true"
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not lesson_id:
        print_result(False, test_name, "No lesson_id available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}?include_usage=true",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Got lesson with usage info")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:500]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_list_lessons():
    """Test GET /lessons"""
    test_name = "GET /lessons (List Lessons)"
    token = TEST_DATA["teacher_token"]
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons?page=1&per_page=10",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Got {len(data.get('items', []))} lessons")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_get_lesson_library():
    """Test GET /lessons/library"""
    test_name = "GET /lessons/library"
    token = TEST_DATA["teacher_token"]
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/library",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Got library data")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_list_lesson_pages():
    """Test GET /lessons/{id}/pages"""
    test_name = "GET /lessons/{id}/pages"
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not lesson_id:
        print_result(False, test_name, "No lesson_id available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}/pages",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Got {data.get('total_pages', 0)} pages")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_update_lesson():
    """Test PUT /lessons/{id}"""
    test_name = "PUT /lessons/{id} (Update Lesson)"
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not lesson_id:
        print_result(False, test_name, "No lesson_id available")
        return
    
    try:
        update_data = {
            "title": "Updated Test Lesson",
            "description": "Updated description"
        }
        
        response = requests.put(
            f"{BASE_URL}/lessons/{lesson_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Updated lesson")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_get_lesson_usage():
    """Test GET /lessons/{id}/usage"""
    test_name = "GET /lessons/{id}/usage"
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not lesson_id:
        print_result(False, test_name, "No lesson_id available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/lessons/{lesson_id}/usage",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, test_name, f"Used in {data.get('used_in_modules', 0)} modules")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

def test_delete_lesson():
    """Test DELETE /lessons/{id}"""
    test_name = "DELETE /lessons/{id}"
    token = TEST_DATA["teacher_token"]
    lesson_id = TEST_DATA["lesson_id"]
    
    if not lesson_id:
        print_result(False, test_name, "No lesson_id available")
        return
    
    try:
        response = requests.delete(
            f"{BASE_URL}/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            print_result(True, test_name, f"Lesson deleted")
        else:
            print_result(False, test_name, f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")

# ==================== MAIN ====================

def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE LESSON ENDPOINTS TEST")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Setup
    print("\n" + "="*80)
    print("SETUP")
    print("="*80)
    
    if not get_token():
        print("\n[FATAL] Could not login")
        return 1
    
    if not setup_prerequisites():
        print("\n[FATAL] Could not get subject")
        return 1
    
    # Run tests
    print("\n" + "="*80)
    print("RUNNING TESTS")
    print("="*80)
    
    test_create_lesson()
    test_get_lesson_basic()
    test_get_lesson_with_usage()  # THIS IS THE ONE THAT ERRORS
    test_list_lessons()
    test_get_lesson_library()
    test_list_lesson_pages()
    test_update_lesson()
    test_get_lesson_usage()
    test_delete_lesson()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed:  {TESTS_PASSED}")
    print(f"Failed:  {TESTS_FAILED}")
    print(f"Total:   {TESTS_PASSED + TESTS_FAILED}")
    
    if FAILED_TESTS:
        print("\n" + "="*80)
        print("FAILED TESTS DETAILS:")
        print("="*80)
        for failed in FAILED_TESTS:
            print(f"\n[FAIL] {failed['test']}")
            print(f"   Error: {failed['error']}")
    
    print("\n" + "="*80)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return 0 if TESTS_FAILED == 0 else 1

if __name__ == "__main__":
    exit(main())
