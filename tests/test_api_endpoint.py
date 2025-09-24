#!/usr/bin/env python3
# ==============================================================================
# File: test_api_endpoint.py
# Deskripsi: Test script untuk menguji API endpoint student statistics
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

async def test_api_endpoint():
    """Test the API endpoint with a real HTTP request"""
    
    print("🌐 Testing Student Statistics API Endpoint")
    print("=" * 60)
    
    # Connect to database to get test data
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Get test data
        print("📋 Getting test credentials...")
        
        # Find an admin user for authentication
        admin_user = await db["users"].find_one({"roles": "admin", "is_active": True})
        if not admin_user:
            print("❌ No active admin user found!")
            return False
        
        # Find a student with exam sessions
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
        
        student = students[0]
        student_id = str(student["_id"])
        
        print(f"✅ Using admin: {admin_user['login_id']}")
        print(f"✅ Testing with student ID: {student_id}")
        
        # Create HTTP client
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First, login to get authentication token
            print("\\n🔐 Authenticating...")
            
            login_data = {
                "username": admin_user["login_id"],
                "password": admin_user["login_id"]  # Assuming default password is login_id
            }
            
            try:
                login_response = await http_client.post(
                    f"{base_url}/api/v1/auth/login",
                    data=login_data
                )
                
                if login_response.status_code != 200:
                    print(f"❌ Login failed with status {login_response.status_code}")
                    print(f"Response: {login_response.text}")
                    return False
                
                login_result = login_response.json()
                access_token = login_result["access_token"]
                print("✅ Authentication successful")
                
                # Test the new endpoint
                print("\\n📊 Testing student statistics endpoint...")
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                endpoint_url = f"{base_url}/api/v1/score-analytics/student-statistics/{student_id}"
                
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
                print("\\n🔍 Validating API response...")
                
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
                
                # Print formatted results
                print("\\n📊 API Response Summary:")
                print("-" * 40)
                print("Student Statistics:")
                print(f"  Overall Average: {student_stats['overall_average_student']}")
                print(f"  Best Score: {student_stats['best_score_student']}")
                print(f"  Latest Score: {student_stats['latest_score_student']}")
                print(f"  Participation Rate: {student_stats['participant_rate']}%")
                print(f"  Trend Data Points: {len(student_stats['trend_scores_student'])}")
                
                print("\\nClass Statistics:")
                print(f"  Class Average: {class_stats['overall_average_class']}")
                print(f"  Class Highest: {class_stats['class_highest']}")
                print(f"  Class Lowest: {class_stats['class_lowest']}")
                print(f"  Trend Data Points: {len(class_stats['trend_scores_class'])}")
                
                # Test caching by making another request
                print("\\n💾 Testing API caching...")
                cache_start = datetime.now()
                cached_response = await http_client.get(endpoint_url, headers=headers)
                cache_end = datetime.now()
                
                cache_time = (cache_end - cache_start).total_seconds()
                print(f"⚡ Cached API call took: {cache_time:.2f} seconds")
                
                if cached_response.status_code == 200 and cache_time < 0.5:
                    print("✅ API caching appears to be working")
                else:
                    print("⚠️  API caching might not be optimal")
                
                print("\\n🎉 API endpoint test passed successfully!")
                return True
                
            except httpx.ConnectError:
                print("❌ Could not connect to FastAPI server")
                print("💡 Please make sure the server is running:")
                print("   uvicorn app.main:app --reload --port 8000")
                return False
            except httpx.TimeoutException:
                print("❌ Request timed out")
                return False
            except Exception as e:
                print(f"❌ Unexpected error during API test: {str(e)}")
                return False
        
    except Exception as e:
        print(f"❌ Test setup failed with error: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False
    
    finally:
        client.close()

async def main():
    """Main function"""
    print("🚀 Starting API Endpoint Test")
    print(f"🔗 Target URL: http://localhost:8000")
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = await test_api_endpoint()
    
    print("\\n" + "=" * 60)
    if success:
        print("✅ API ENDPOINT TEST COMPLETED SUCCESSFULLY!")
        print("🎯 The student statistics endpoint is working correctly.")
        print("\\n📋 Endpoint details:")
        print("   URL: GET /api/v1/score-analytics/student-statistics/{student_id}")
        print("   Auth: Bearer token required")
        print("   Roles: student (own data), teacher/admin (any student)")
    else:
        print("❌ API ENDPOINT TEST FAILED!")
        print("🔧 Please check the server status and fix any issues.")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
