#!/usr/bin/env python3
# ==============================================================================
# File: test_student_statistics_endpoint.py
# Deskripsi: Test script untuk menguji endpoint student statistics baru
# ==============================================================================

import asyncio
import sys
import os
from datetime import datetime
from pprint import pprint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.crud.crud_score_analytics import get_combined_student_statistics

async def test_student_statistics():
    """Test the new student statistics functions"""
    
    print("🔍 Testing Student Statistics Implementation")
    print("=" * 60)
    
    # Connect to database
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Get a sample student and academic period from the database
        print("📋 Getting test data...")
        
        # Find an active academic period
        period = await db["academic_periods"].find_one({"status": "active"})
        if not period:
            print("❌ No active academic period found!")
            return False
        
        print(f"✅ Using academic period: {period['year']} {period['semester']}")
        
        # Find a student with exam sessions
        student_pipeline = [
            {"$match": {"roles": "student"}},
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
        
        print(f"✅ Testing with student ID: {student_id}")
        
        # Test the combined statistics function
        print("\n📊 Testing combined student statistics...")
        
        start_time = datetime.now()
        result = await get_combined_student_statistics(db, student_id, str(period["_id"]))
        end_time = datetime.now()
        
        print(f"⏱️  Query took: {(end_time - start_time).total_seconds():.2f} seconds")
        
        # Validate the response structure
        print("\n🔍 Validating response structure...")
        
        required_student_fields = [
            "overall_average_student",
            "best_score_student", 
            "latest_score_student",
            "participant_rate",
            "trend_scores_student",
            "score_distribution_student"
        ]
        
        required_class_fields = [
            "overall_average_class",
            "class_highest",
            "class_lowest", 
            "trend_scores_class",
            "score_distribution_class"
        ]
        
        # Check top-level structure
        if "student_statistics" not in result:
            print("❌ Missing 'student_statistics' in response")
            return False
        
        if "class_statistics" not in result:
            print("❌ Missing 'class_statistics' in response")
            return False
        
        print("✅ Top-level structure is correct")
        
        # Check student statistics fields
        student_stats = result["student_statistics"]
        for field in required_student_fields:
            if field not in student_stats:
                print(f"❌ Missing field '{field}' in student_statistics")
                return False
        
        print("✅ Student statistics fields are present")
        
        # Check class statistics fields  
        class_stats = result["class_statistics"]
        for field in required_class_fields:
            if field not in class_stats:
                print(f"❌ Missing field '{field}' in class_statistics")
                return False
        
        print("✅ Class statistics fields are present")
        
        # Validate data types and ranges
        print("\\n📈 Validating data values...")
        
        # Student statistics validation
        if not isinstance(student_stats["overall_average_student"], (int, float)):
            print("❌ overall_average_student should be a number")
            return False
        
        if not isinstance(student_stats["participant_rate"], (int, float)):
            print("❌ participant_rate should be a number") 
            return False
        
        if not (0 <= student_stats["participant_rate"] <= 100):
            print("❌ participant_rate should be between 0 and 100")
            return False
        
        if not isinstance(student_stats["trend_scores_student"], list):
            print("❌ trend_scores_student should be a list")
            return False
        
        if not isinstance(student_stats["score_distribution_student"], list):
            print("❌ score_distribution_student should be a list")
            return False
        
        # Validate score distribution structure
        for dist in student_stats["score_distribution_student"]:
            if not all(key in dist for key in ["range", "count", "percentage"]):
                print("❌ Score distribution items should have 'range', 'count', 'percentage'")
                return False
        
        print("✅ Student statistics data validation passed")
        
        # Class statistics validation
        if not isinstance(class_stats["overall_average_class"], (int, float)):
            print("❌ overall_average_class should be a number")
            return False
        
        if not isinstance(class_stats["trend_scores_class"], list):
            print("❌ trend_scores_class should be a list")
            return False
        
        print("✅ Class statistics data validation passed")
        
        # Print sample of the results
        print("\\n📄 Sample Response:")
        print("-" * 40)
        
        print("Student Statistics:")
        print(f"  Overall Average: {student_stats['overall_average_student']}")
        print(f"  Best Score: {student_stats['best_score_student']}")
        print(f"  Latest Score: {student_stats['latest_score_student']}")
        print(f"  Participation Rate: {student_stats['participant_rate']}%")
        print(f"  Trend Data Points: {len(student_stats['trend_scores_student'])}")
        print(f"  Distribution Ranges: {len(student_stats['score_distribution_student'])}")
        
        print("\\nClass Statistics:")
        print(f"  Class Average: {class_stats['overall_average_class']}")
        print(f"  Class Highest: {class_stats['class_highest']}")
        print(f"  Class Lowest: {class_stats['class_lowest']}")
        print(f"  Trend Data Points: {len(class_stats['trend_scores_class'])}")
        print(f"  Distribution Ranges: {len(class_stats['score_distribution_class'])}")
        
        # Test caching by running the same query again
        print("\\n💾 Testing caching...")
        cache_start = datetime.now()
        cached_result = await get_combined_student_statistics(db, student_id, str(period["_id"]))
        cache_end = datetime.now()
        
        cache_time = (cache_end - cache_start).total_seconds()
        print(f"⚡ Cached query took: {cache_time:.2f} seconds")
        
        if cache_time < 0.1:  # Should be much faster if cached
            print("✅ Caching appears to be working")
        else:
            print("⚠️  Caching might not be working optimally")
        
        print("\\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False
    
    finally:
        client.close()

async def main():
    """Main test function"""
    print("🚀 Starting Student Statistics Endpoint Test")
    print(f"🔗 Database: {settings.DATABASE_NAME}")
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = await test_student_statistics()
    
    print("\\n" + "=" * 60)
    if success:
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("🎯 The new student statistics endpoint should work correctly.")
        print("\\n📋 Next steps:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("2. Test the endpoint: GET /api/v1/score-analytics/student-statistics/{student_id}")
        print("3. Check authentication and authorization")
    else:
        print("❌ TEST FAILED!")
        print("🔧 Please fix the issues before deploying the endpoint.")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
