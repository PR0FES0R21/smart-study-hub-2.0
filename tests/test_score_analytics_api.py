#!/usr/bin/env python3
"""
Test script untuk menguji API endpoints score analytics via HTTP calls.
"""
import requests
import json
import sys
import os

# Base URL untuk API
BASE_URL = "http://localhost:8000/api/v1"

def get_auth_token():
    """Get authentication token"""
    # You'll need to implement this based on your auth system
    # For now, return None to test without auth
    return None

def test_endpoint(endpoint, method="GET", headers=None, data=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"  {method} {endpoint}")
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    print(f"    Response keys: {list(json_data.keys())}")
                elif isinstance(json_data, list):
                    print(f"    Response items: {len(json_data)}")
                print("    ✅ SUCCESS")
                return True
            except json.JSONDecodeError:
                print("    ⚠️  Non-JSON response")
                return True
        else:
            print(f"    Error: {response.text[:100]}...")
            print("    ❌ FAILED")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"    Connection error: {e}")
        print("    ❌ CONNECTION FAILED")
        return False

def main():
    """Main test function"""
    print("TESTING SCORE ANALYTICS API ENDPOINTS")
    print("=" * 50)
    print("Note: This test assumes the FastAPI server is running on localhost:8000")
    print("If you need authentication, please implement get_auth_token() function")
    print()
    
    # Get auth token (if needed)
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # Define endpoints to test
    endpoints = [
        # Health check
        ("/score-analytics/health", "GET"),
        
        # Admin endpoints (will fail without proper auth)
        ("/score-analytics/admin/dashboard", "GET"),
        ("/score-analytics/admin/global-stats", "GET"),
        ("/score-analytics/admin/grade-performances", "GET"),
        ("/score-analytics/admin/major-performances", "GET"),
        ("/score-analytics/admin/subject-rankings", "GET"),
        ("/score-analytics/admin/score-trends", "GET"),
        
        # Teacher endpoints (will fail without proper auth)
        ("/score-analytics/teacher/dashboard", "GET"),
        ("/score-analytics/teacher/class-statistics", "GET"),
        ("/score-analytics/teacher/student-performances", "GET"),
        ("/score-analytics/teacher/students-attention", "GET"),
        
        # Student endpoints (will fail without proper auth)
        ("/score-analytics/student/dashboard", "GET"),
        ("/score-analytics/student/subject-performances", "GET"),
        ("/score-analytics/student/exam-history", "GET"),
        ("/score-analytics/student/class-comparison", "GET"),
        ("/score-analytics/student/improvement-suggestions", "GET"),
        
        # Common endpoints
        ("/score-analytics/metadata", "GET"),
    ]
    
    results = []
    
    for endpoint, method in endpoints:
        print(f"\n[TEST] {endpoint}")
        result = test_endpoint(endpoint, method, headers)
        results.append(result)
    
    print("\n" + "=" * 50)
    print("API TEST SUMMARY:")
    
    for i, (endpoint, method) in enumerate(endpoints):
        status = "[PASS]" if results[i] else "[FAIL]"
        print(f"   {status} {method} {endpoint}")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nAPI Test Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 50:  # Lower threshold since auth might not be configured
        print("✅ Most endpoints are accessible!")
        print("\nNOTE:")
        print("   - Some endpoints may fail due to authentication requirements")
        print("   - Configure authentication in get_auth_token() for full testing")
    else:
        print("❌ Many endpoints failed - check if server is running")
        print("   Start server with: uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()
