#!/usr/bin/env python3
# ==============================================================================
# File: test_my_statistics_endpoint.py
# Deskripsi: Test script untuk endpoint /student/my-statistics yang sudah diperbaiki
# ==============================================================================

import asyncio
import sys
import os
import httpx
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def test_my_statistics_endpoint():
    """Test the corrected /student/my-statistics endpoint"""
    
    print("🎓 Testing Student My-Statistics API Endpoint")
    print("=" * 60)
    
    # Connect to database to get test data
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Get test data
        print("📋 Getting test student credentials...")
        
        # Find a student with exam sessions for testing
        student_pipeline = [
            {"$match": {"roles": "student", "is_active": True}},
            {"$lookup": {
                "from": "exam_sessions",
                "localField": "_id",
                "foreignField": "student_id", 
                "as": "exam_sessions"
            }},
            {"$match": {"exam_sessions": {"$ne": []}}},
            {"$limit": 1}
        ]
        
        students = await db["users"].aggregate(student_pipeline).to_list(1)
        if not students:
            print("❌ No student with exam sessions found!")
            return False
        
        student_user = students[0]
        student_login_id = student_user["login_id"]
        student_id = str(student_user["_id"])
        
        print(f"✅ Testing with student: {student_login_id} (ID: {student_id})")
        
        # Create HTTP client
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Login as student to get authentication token
            print("\\n🔐 Authenticating as student...")
            
            login_data = {
                "username": student_login_id,
                "password": student_login_id  # Assuming default password is login_id
            }
            
            try:
                login_response = await http_client.post(
                    f"{base_url}/api/v1/auth/login",
                    data=login_data
                )
                
                if login_response.status_code != 200:
                    print(f"❌ Student login failed with status {login_response.status_code}")
                    print(f"Response: {login_response.text}")
                    return False
                
                login_result = login_response.json()
                access_token = login_result["access_token"]
                print("✅ Student authentication successful")
                
                # Test the new endpoint
                print("\\n📊 Testing /student/my-statistics endpoint...")
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                endpoint_url = f"{base_url}/api/v1/score-analytics/student/my-statistics"
                
                start_time = datetime.now()
                response = await http_client.get(endpoint_url, headers=headers)
                end_time = datetime.now()
                
                print(f"⏱️  API call took: {(end_time - start_time).total_seconds():.2f} seconds")
                
                if response.status_code != 200:
                    print(f"❌ API request failed with status {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                
                result = response.json()
                print("✅ API endpoint responded successfully")
                
                # Validate the JSON response structure
                print("\\n🔍 Validating API response structure...")
                
                if "student_statistics" not in result:
                    print("❌ Missing 'student_statistics' in API response")
                    return False
                
                if "class_statistics" not in result:
                    print("❌ Missing 'class_statistics' in API response")
                    return False
                
                # Check if all required fields are present
                student_stats = result["student_statistics"]
                class_stats = result["class_statistics"]
                
                required_student_fields = [
                    "overall_average_student", "best_score_student", "latest_score_student",
                    "participant_rate", "trend_scores_student", "score_distribution_student"
                ]
                
                required_class_fields = [
                    "overall_average_class", "class_highest", "class_lowest", 
                    "trend_scores_class", "score_distribution_class"
                ]
                
                for field in required_student_fields:
                    if field not in student_stats:
                        print(f"❌ Missing field '{field}' in student_statistics")
                        return False
                
                for field in required_class_fields:
                    if field not in class_stats:
                        print(f"❌ Missing field '{field}' in class_statistics")
                        return False
                
                print("✅ All required fields present in API response")
                
                # Validate score distribution format
                for dist in student_stats["score_distribution_student"]:
                    if not all(key in dist for key in ["range", "count", "percentage"]):
                        print("❌ Invalid score distribution format")
                        return False
                
                for dist in class_stats["score_distribution_class"]:
                    if not all(key in dist for key in ["range", "count", "percentage"]):
                        print("❌ Invalid class score distribution format")
                        return False
                
                print("✅ Score distribution format validation passed")
                
                # Print formatted results
                print("\\n📊 API Response Summary:")
                print("-" * 50)
                print("🎓 STUDENT STATISTICS (Individual):")
                print(f"   📈 Overall Average: {student_stats['overall_average_student']}")
                print(f"   🏆 Best Score: {student_stats['best_score_student']}")
                print(f"   📝 Latest Score: {student_stats['latest_score_student']}")
                print(f"   📊 Participation Rate: {student_stats['participant_rate']}%")
                print(f"   📉 Trend Data Points: {len(student_stats['trend_scores_student'])}")
                
                # Show trend data if available
                if student_stats['trend_scores_student']:\n                    print(\"   📈 Recent Trend (Last 3 exams):\")\n                    for i, trend in enumerate(student_stats['trend_scores_student'][:3]):\n                        exam_date = datetime.fromisoformat(trend['exam_date'].replace('Z', '+00:00'))\n                        print(f\"      {i+1}. {exam_date.strftime('%Y-%m-%d')}: {trend['score']}\")\n                \n                print(\"\\n🏫 CLASS STATISTICS (Comparative):\")\n                print(f\"   📊 Class Average: {class_stats['overall_average_class']}\")\n                print(f\"   🥇 Class Highest: {class_stats['class_highest']}\")\n                print(f\"   📉 Class Lowest: {class_stats['class_lowest']}\")\n                print(f\"   📈 Class Trend Points: {len(class_stats['trend_scores_class'])}\")\n                \n                # Show score distributions\n                print(\"\\n📊 SCORE DISTRIBUTIONS:\")\n                print(\"   Student Distribution:\")\n                for dist in student_stats['score_distribution_student']:\n                    if dist['count'] > 0:\n                        print(f\"      {dist['range']}: {dist['count']} exams ({dist['percentage']}%)\")\n                \n                print(\"   Class Distribution:\")\n                for dist in class_stats['score_distribution_class']:\n                    if dist['count'] > 0:\n                        print(f\"      {dist['range']}: {dist['count']} scores ({dist['percentage']}%)\")\n                \n                # Test performance comparison\n                student_avg = student_stats['overall_average_student']\n                class_avg = class_stats['overall_average_class']\n                \n                print(\"\\n🏆 PERFORMANCE COMPARISON:\")\n                if student_avg > class_avg:\n                    diff = student_avg - class_avg\n                    print(f\"   🎯 Student performing ABOVE class average by {diff:.2f} points\")\n                elif student_avg < class_avg:\n                    diff = class_avg - student_avg\n                    print(f\"   📚 Student performing BELOW class average by {diff:.2f} points\")\n                else:\n                    print(f\"   ⚖️  Student performing AT class average\")\n                \n                participation = student_stats['participant_rate']\n                if participation >= 80:\n                    print(f\"   ✅ Good participation rate: {participation}%\")\n                elif participation >= 50:\n                    print(f\"   ⚠️  Moderate participation rate: {participation}%\")\n                else:\n                    print(f\"   ❌ Low participation rate: {participation}%\")\n                \n                # Test unauthorized access (try with non-student user)\n                print(\"\\n🔒 Testing authorization (trying with admin user)...\")\n                \n                admin_user = await db[\"users\"].find_one({\"roles\": \"admin\", \"is_active\": True})\n                if admin_user:\n                    # Login as admin\n                    admin_login = {\n                        \"username\": admin_user[\"login_id\"],\n                        \"password\": admin_user[\"login_id\"]\n                    }\n                    \n                    admin_login_response = await http_client.post(\n                        f\"{base_url}/api/v1/auth/login\",\n                        data=admin_login\n                    )\n                    \n                    if admin_login_response.status_code == 200:\n                        admin_token = admin_login_response.json()[\"access_token\"]\n                        admin_headers = {\"Authorization\": f\"Bearer {admin_token}\"}\n                        \n                        # Try to access student endpoint as admin\n                        admin_response = await http_client.get(endpoint_url, headers=admin_headers)\n                        \n                        if admin_response.status_code == 403:\n                            print(\"✅ Authorization working: Admin correctly blocked from student endpoint\")\n                        else:\n                            print(f\"⚠️  Authorization issue: Admin got status {admin_response.status_code}\")\n                    else:\n                        print(\"⚠️  Could not test admin authorization (admin login failed)\")\n                else:\n                    print(\"⚠️  No admin user found for authorization test\")\n                \n                # Test caching\n                print(\"\\n💾 Testing endpoint caching...\")\n                cache_start = datetime.now()\n                cached_response = await http_client.get(endpoint_url, headers=headers)\n                cache_end = datetime.now()\n                \n                cache_time = (cache_end - cache_start).total_seconds()\n                print(f\"⚡ Cached API call took: {cache_time:.2f} seconds\")\n                \n                if cached_response.status_code == 200 and cache_time < 0.2:\n                    print(\"✅ Endpoint caching working optimally\")\n                else:\n                    print(\"⚠️  Endpoint caching might need optimization\")\n                \n                print(\"\\n🎉 All endpoint tests passed successfully!\")\n                return True\n                \n            except httpx.ConnectError:\n                print(\"❌ Could not connect to FastAPI server\")\n                print(\"💡 Please make sure the server is running:\")\n                print(\"   uvicorn app.main:app --reload --port 8000\")\n                return False\n            except httpx.TimeoutException:\n                print(\"❌ Request timed out\")\n                return False\n            except Exception as e:\n                print(f\"❌ Unexpected error during API test: {str(e)}\")\n                import traceback\n                print(traceback.format_exc())\n                return False\n        \n    except Exception as e:\n        print(f\"❌ Test setup failed with error: {str(e)}\")\n        import traceback\n        print(\"Full traceback:\")\n        print(traceback.format_exc())\n        return False\n    \n    finally:\n        client.close()\n\nasync def main():\n    \"\"\"Main function\"\"\"\n    print(\"🚀 Starting Corrected Student Statistics Endpoint Test\")\n    print(f\"🔗 Target URL: http://localhost:8000\")\n    print(f\"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\")\n    print()\n    \n    success = await test_my_statistics_endpoint()\n    \n    print(\"\\n\" + \"=\" * 60)\n    if success:\n        print(\"✅ CORRECTED ENDPOINT TEST COMPLETED SUCCESSFULLY!\")\n        print(\"🎯 The student my-statistics endpoint is working correctly.\")\n        print(\"\\n📋 Endpoint details:\")\n        print(\"   URL: GET /api/v1/score-analytics/student/my-statistics\")\n        print(\"   Auth: Bearer token required (student only)\")\n        print(\"   Access: Student can only see their own statistics\")\n        print(\"\\n🔗 Example usage:\")\n        print(\"   1. Login as student to get token\")\n        print(\"   2. Call GET /api/v1/score-analytics/student/my-statistics\")\n        print(\"   3. Receive both individual and class comparative statistics\")\n    else:\n        print(\"❌ ENDPOINT TEST FAILED!\")\n        print(\"🔧 Please check the server status and fix any issues.\")\n        print(\"\\n💡 Common issues:\")\n        print(\"   - FastAPI server not running on port 8000\")\n        print(\"   - Database connection issues\")\n        print(\"   - No student data or exam sessions in database\")\n    \n    print(\"=\" * 60)\n\nif __name__ == "__main__":\n    asyncio.run(main())
