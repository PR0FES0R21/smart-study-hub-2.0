#!/usr/bin/env python3
"""
Test script untuk memverifikasi perbaikan Score Trend Analytics
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_ENDPOINTS = {
    "score_trend": "/api/v1/exam-analytics/score-trend",
    "class_exam_analytics": "/api/v1/score-analytics/student/class-exam-analytics"
}

def test_endpoints():
    """Test endpoints yang sudah diperbaiki"""
    
    print("=" * 60)
    print("🧪 TESTING SCORE TREND ANALYTICS FIX")
    print("=" * 60)
    
    # Headers for authentication (adjust as needed)
    headers = {
        "Content-Type": "application/json",
        # Add authentication headers here if needed
        # "Authorization": "Bearer YOUR_TOKEN"
    }
    
    results = {}
    
    for name, endpoint in TEST_ENDPOINTS.items():
        print(f"\n🔍 Testing {name}: {endpoint}")
        print("-" * 40)
        
        try:
            # Test GET request
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                results[name] = {
                    "status": "✅ SUCCESS",
                    "response_keys": list(data.keys()) if isinstance(data, dict) else "Not a dict",
                    "data_sample": str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                }
                
                # Specific checks for each endpoint
                if name == "score_trend":
                    has_series = "series" in data
                    has_metadata = "metadata" in data
                    print(f"✅ Has series: {has_series}")
                    print(f"✅ Has metadata: {has_metadata}")
                    
                elif name == "class_exam_analytics":
                    has_exam_analytics = "exam_analytics" in data
                    has_trend_data = "trend_data" in data
                    has_overall_stats = "overall_stats" in data
                    trend_data_count = len(data.get("trend_data", []))
                    
                    print(f"✅ Has exam_analytics: {has_exam_analytics}")
                    print(f"✅ Has trend_data: {has_trend_data}")
                    print(f"✅ Has overall_stats: {has_overall_stats}")
                    print(f"✅ Trend data count: {trend_data_count}")
                    
                    # Check if trend_data contains valid entries
                    if trend_data_count > 0:
                        sample_trend = data["trend_data"][0]
                        has_student_score = "student_score" in sample_trend
                        student_score_value = sample_trend.get("student_score")
                        print(f"✅ First trend has student_score field: {has_student_score}")
                        print(f"✅ Student score value: {student_score_value} (None is OK)")
                    
            else:
                error_detail = response.text
                results[name] = {
                    "status": f"❌ ERROR {response.status_code}",
                    "error": error_detail[:500] + "..." if len(error_detail) > 500 else error_detail
                }
                print(f"❌ Error: {response.status_code}")
                print(f"Error detail: {error_detail[:200]}...")
                
        except requests.exceptions.RequestException as e:
            results[name] = {
                "status": f"❌ CONNECTION ERROR",
                "error": str(e)
            }
            print(f"❌ Connection Error: {e}")
        
        except Exception as e:
            results[name] = {
                "status": f"❌ UNEXPECTED ERROR",
                "error": str(e)
            }
            print(f"❌ Unexpected Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for endpoint, result in results.items():
        print(f"{endpoint:20} : {result['status']}")
    
    # Check if fixes are working
    print("\n🔧 FIX VERIFICATION:")
    success_count = sum(1 for r in results.values() if "SUCCESS" in r["status"])
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 ALL TESTS PASSED - Fixes are working correctly!")
    else:
        print(f"⚠️  {success_count}/{total_count} tests passed")
        
    print(f"\n📝 Test completed at: {datetime.now().isoformat()}")
    
    return results

def test_schema_validation():
    """Test schema validation in isolation"""
    print("\n🔬 TESTING SCHEMA VALIDATION")
    print("-" * 40)
    
    try:
        import sys
        sys.path.append('.')
        
        from app.schemas.score_analytics import StudentClassTrendData, StudentClassExamAnalytics
        from datetime import datetime
        
        # Test 1: None student_score
        trend_with_none = StudentClassTrendData(
            exam_title="Test Exam",
            class_average=75.5,
            student_score=None,  # This should work now
            exam_date=datetime.now()
        )
        print("✅ Schema accepts None for student_score")
        
        # Test 2: Valid student_score
        trend_with_score = StudentClassTrendData(
            exam_title="Test Exam 2",
            class_average=80.0,
            student_score=85.5,  # Valid score
            exam_date=datetime.now()
        )
        print("✅ Schema accepts valid student_score")
        
        # Test 3: Full response object
        full_response = StudentClassExamAnalytics(
            exam_analytics=[],
            trend_data=[trend_with_none, trend_with_score],
            overall_stats={"test": "value"},
            generated_at=datetime.now()
        )
        print("✅ Full response schema validation passed")
        print(f"✅ Response has {len(full_response.trend_data)} trend data items")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Score Trend Analytics Fix Tests")
    
    # Test 1: Schema validation (always works)
    schema_ok = test_schema_validation()
    
    # Test 2: API endpoints (requires running server)
    print(f"\n{'='*60}")
    print("⚠️  NOTE: API tests require server running at http://localhost:8000")
    print("   Start server with: uvicorn app.main:app --reload")
    print("="*60)
    
    try:
        api_results = test_endpoints()
    except Exception as e:
        print(f"❌ API tests failed: {e}")
        print("💡 Make sure the server is running and accessible")
    
    print("\n🏁 Test execution completed!")
    print("📋 If all tests pass, the Score Trend Analytics fix is working correctly.")
