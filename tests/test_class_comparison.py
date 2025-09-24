#!/usr/bin/env python3
"""
Test script untuk memverifikasi class comparison calculation
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.crud.exam_analytics import exam_analytics_crud

async def test_class_comparison():
    """Test class comparison calculation"""
    print("=== Testing Class Comparison Calculation ===")
    
    # Test session ID dari user
    session_id = "68bb1b93b39c2a464c1819c4"
    
    try:
        # Generate analytics dengan force regenerate
        print(f"\\n1. Generating analytics for session: {session_id}")
        analytics = await exam_analytics_crud.generate_exam_analytics(
            exam_session_id=session_id,
            force_regenerate=True
        )
        
        if not analytics:
            print("❌ Failed to generate analytics")
            return False
            
        print("✅ Analytics generated successfully")
        
        # Extract class comparison data
        class_comparison = analytics.class_comparison
        
        print(f"\\n2. Class Comparison Results:")
        print(f"   📊 Total Participants: {class_comparison.total_participants}")
        print(f"   📊 Class Average: {class_comparison.class_average_score:.2f}")
        print(f"   📊 Class Highest: {class_comparison.class_highest_score:.2f}")
        print(f"   📊 Class Lowest: {class_comparison.class_lowest_score:.2f}")
        print(f"   📊 Student Rank: {class_comparison.student_rank}")
        print(f"   📊 Percentile: {class_comparison.percentile:.1f}%")
        print(f"   📊 Above Average: {class_comparison.above_average}")
        
        print(f"\\n3. Score Distribution:")
        for dist in class_comparison.score_distribution:
            print(f"   📈 {dist['range']}: {dist['count']} students ({dist['percentage']:.1f}%)")
        
        # Validate results
        print(f"\\n4. Validation:")
        
        # Check if total participants > 1 (should have 2 students)
        if class_comparison.total_participants >= 2:
            print("✅ Total participants looks correct (>=2)")
        else:
            print(f"❌ Total participants should be >= 2, got {class_comparison.total_participants}")
        
        # Check if class average makes sense 
        current_score = analytics.performance_metrics.score
        print(f"   📊 Current student score: {current_score:.2f}")
        
        if class_comparison.total_participants > 1:
            # If there are multiple students, average should be different from current score
            # unless all students have the same score
            if abs(class_comparison.class_average_score - current_score) > 0.01:
                print("✅ Class average is different from current student score (good!)")
            else:
                print("ℹ️  Class average equals current score - possible if all students have same score")
        
        # Check ranking logic
        if 1 <= class_comparison.student_rank <= class_comparison.total_participants:
            print("✅ Student rank is within valid range")
        else:
            print(f"❌ Student rank {class_comparison.student_rank} is outside valid range 1-{class_comparison.total_participants}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_direct_database_query():
    """Test direct database query to verify data"""
    print("\\n=== Direct Database Query Test ===")
    
    try:
        # Connect to database
        mongo_url = getattr(settings, 'MONGO_URL', 'mongodb://localhost:27017')
        db_name = getattr(settings, 'MONGO_DB', 'smart_study_hub')
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test exam ID from the session
        exam_id = ObjectId("68b5406b3c28dc76c69d0f45")
        
        # Query all sessions for this exam
        all_sessions = await db.exam_sessions.find({
            "exam_id": exam_id,
            "status": {"$in": ["submitted", "graded"]}
        }).to_list(length=None)
        
        print(f"\\n1. Found {len(all_sessions)} sessions for exam {exam_id}")
        
        for i, session in enumerate(all_sessions, 1):
            score = session.get("score", "No score")
            status = session.get("status", "No status") 
            student_id = session.get("student_id", "No student")
            print(f"   Session {i}: Student {student_id}, Score: {score}, Status: {status}")
        
        # Calculate manual average
        scores = [session.get("score", 0) for session in all_sessions if session.get("score") is not None]
        if scores:
            manual_average = sum(scores) / len(scores)
            print(f"\\n2. Manual calculation:")
            print(f"   📊 Valid scores: {scores}")
            print(f"   📊 Manual average: {manual_average:.2f}")
            print(f"   📊 Highest score: {max(scores):.2f}")
            print(f"   📊 Lowest score: {min(scores):.2f}")
        else:
            print("\\n2. No valid scores found!")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Testing Class Comparison Improvements")
    
    results = []
    
    # Test 1: Analytics generation
    try:
        result1 = await test_class_comparison()
        results.append(("Analytics Generation", result1))
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        results.append(("Analytics Generation", False))
    
    # Test 2: Direct database check
    try:
        result2 = await test_direct_database_query()
        results.append(("Database Query", result2))
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        results.append(("Database Query", False))
    
    # Summary
    print("\\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\\nOverall: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(main())
