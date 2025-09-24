#!/usr/bin/env python3
"""
Script untuk testing semua endpoint exam analytics
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "admin123"
}

def login():
    """Login dan dapatkan token"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    response = requests.post(login_url, data=ADMIN_CREDENTIALS)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_endpoint(url, headers, endpoint_name):
    """Test satu endpoint"""
    print(f"\n🔍 Testing {endpoint_name}:")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS - Status: {response.status_code}")
            data = response.json()
            print(f"   📊 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Non-dict response'}")
            return True
        else:
            print(f"   ❌ FAILED - Status: {response.status_code}")
            print(f"   📝 Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ⏰ TIMEOUT - Request took too long")
        return False
    except requests.exceptions.RequestException as e:
        print(f"   💥 ERROR - {str(e)}")
        return False

def main():
    print("🚀 Starting Exam Analytics Endpoint Tests")
    
    # Login
    print("\n🔐 Logging in...")
    token = login()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Test session ID (from the working logs)
    session_id = "68b73495b09dfc3016243c46"
    
    # List of endpoints to test
    endpoints = [
        {
            "name": "Get Exam Session Analytics",
            "url": f"{BASE_URL}/api/v1/exam-analytics/session/{session_id}",
        },
        {
            "name": "Get Exam Session Analytics (Force Regenerate)",
            "url": f"{BASE_URL}/api/v1/exam-analytics/session/{session_id}?force_regenerate=true",
        },
        {
            "name": "Get Exam Analytics Summary",
            "url": f"{BASE_URL}/api/v1/exam-analytics/session/{session_id}/summary",
        },
        {
            "name": "Get Learning Insights",
            "url": f"{BASE_URL}/api/v1/exam-analytics/session/{session_id}/learning-insights",
        },
        {
            "name": "Get Cheat Detection Report",
            "url": f"{BASE_URL}/api/v1/exam-analytics/session/{session_id}/cheat-detection",
        },
        {
            "name": "Analytics Health Check",
            "url": f"{BASE_URL}/api/v1/exam-analytics/health",
        }
    ]
    
    # Test semua endpoints
    results = []
    
    for endpoint in endpoints:
        success = test_endpoint(endpoint["url"], headers, endpoint["name"])
        results.append({
            "name": endpoint["name"],
            "success": success
        })
        
        # Jeda antar test
        time.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} - {result['name']}")
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed - check logs above")

if __name__ == "__main__":
    main()
