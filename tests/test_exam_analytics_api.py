# ==============================================================================
# File: test_exam_analytics_api.py
# Deskripsi: Test script untuk exam analytics API endpoints
# ==============================================================================

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from bson import ObjectId

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import db
from app.api.v1.deps import get_database

async def create_test_exam_session():
    """Create a simple test exam session"""
    print("🔧 Creating test exam session...")
    
    # Create test subject
    subject_id = ObjectId()
    await db.subjects.insert_one({
        "_id": subject_id,
        "name": "Test Subject",
        "code": "TEST",
        "description": "Test subject for analytics"
    })
    
    # Create test teacher
    teacher_id = ObjectId()
    await db.users.insert_one({
        "_id": teacher_id,
        "login_id": f"teacher_test_{teacher_id}",
        "email": f"teacher_test_{teacher_id}@test.com",
        "first_name": "Test",
        "last_name": "Teacher",
        "roles": ["teacher"],
        "hashed_password": "test",
        "is_active": True
    })
    
    # Create test student
    student_id = ObjectId()
    await db.users.insert_one({
        "_id": student_id,
        "login_id": f"student_test_{student_id}",
        "email": f"student_test_{student_id}@test.com", 
        "first_name": "Test",
        "last_name": "Student",
        "roles": ["student"],
        "hashed_password": "test",
        "is_active": True
    })
    
    # Create test class
    class_id = ObjectId()
    await db.classes.insert_one({
        "_id": class_id,
        "name": "Test Class",
        "students": [student_id]
    })
    
    # Create test question
    question_id = ObjectId()
    await db.questions.insert_one({
        "_id": question_id,
        "question_text": "What is 2 + 2?",
        "type": "multiple_choice",
        "difficulty": "easy",
        "subject_id": subject_id,
        "options": [
            {
                "_id": ObjectId(),
                "text": "3",
                "is_correct": False
            },
            {
                "_id": ObjectId(),
                "text": "4", 
                "is_correct": True
            },
            {
                "_id": ObjectId(),
                "text": "5",
                "is_correct": False
            }
        ]
    })
    
    # Create test exam
    exam_id = ObjectId()
    await db.exams.insert_one({
        "_id": exam_id,
        "title": "Test Exam",
        "description": "Test exam for analytics",
        "teacher_id": teacher_id,
        "subject_id": subject_id,
        "class_id": class_id,
        "duration": 30,  # 30 minutes
        "questions": [{
            "question_id": question_id,
            "position": 1,
            "points": 10,
            "original_position": 1
        }],
        "students": [student_id],
        "status": "active",
        "exam_type": "regular",
        "academic_period": "2024-1"
    })
    
    # Create test exam session
    session_id = ObjectId()
    start_time = datetime.utcnow() - timedelta(hours=1)
    submit_time = start_time + timedelta(minutes=15)
    
    # Get the correct answer option
    question = await db.questions.find_one({"_id": question_id})
    correct_option = next(opt for opt in question["options"] if opt["is_correct"])
    
    await db.exam_sessions.insert_one({
        "_id": session_id,
        "exam_id": exam_id,
        "student_id": student_id,
        "started_at": start_time,
        "submitted_at": submit_time,
        "status": "submitted",
        "answers": [{
            "question_id": question_id,
            "selected_option": str(correct_option["_id"]),
            "is_correct": True,
            "answered_at": start_time + timedelta(minutes=5),
            "time_spent": 120,  # 2 minutes
            "position": 1,
            "points_earned": 10,
            "change_count": 0
        }],
        "violations": [{
            "violation_type": "tab_switch",
            "severity": "low",
            "detected_at": start_time + timedelta(minutes=10),
            "description": "Student switched browser tab"
        }],
        "score": 10,
        "client_info": {
            "browser": "Chrome",
            "os": "Windows"
        }
    })
    
    print(f"✅ Test exam session created: {session_id}")
    return {
        "session_id": str(session_id),
        "student_id": str(student_id),
        "teacher_id": str(teacher_id),
        "exam_id": str(exam_id),
        "subject_id": str(subject_id),
        "class_id": str(class_id),
        "question_id": str(question_id)
    }

async def test_analytics_endpoint():
    """Test the analytics endpoint directly"""
    try:
        # Create test data
        test_data = await create_test_exam_session()
        session_id = test_data["session_id"]
        
        print(f"\n📊 Testing analytics generation for session: {session_id}")
        
        # Test the CRUD function directly (simulating what the endpoint does)
        from app.crud.exam_analytics import exam_analytics_crud
        
        # Generate analytics
        analytics = await exam_analytics_crud.generate_exam_analytics(session_id)
        
        print("✅ Analytics generated successfully!")
        print(f"   - Exam Title: {analytics.exam_title}")
        print(f"   - Student Score: {analytics.performance_metrics.score}")
        print(f"   - Accuracy: {analytics.performance_metrics.accuracy_percentage:.1f}%")
        print(f"   - Total Violations: {analytics.violation_analytics.total_violations}")
        print(f"   - Risk Level: {analytics.violation_analytics.risk_level}")
        
        # Test caching
        print("\n🔄 Testing cached retrieval...")
        cached_analytics = await exam_analytics_crud.get_cached_analytics(session_id)
        
        if cached_analytics:
            print("✅ Cache retrieval successful!")
        else:
            print("❌ Cache retrieval failed!")
            
        # Test summary
        print("\n📋 Testing analytics summary...")
        summary = await exam_analytics_crud.get_analytics_summary(session_id)
        
        if summary:
            print("✅ Summary generation successful!")
            print(f"   - Student: {summary.student_name}")
            print(f"   - Score: {summary.score}")
            print(f"   - Flagged: {summary.is_flagged}")
        else:
            print("❌ Summary generation failed!")
        
        # Test permission check function
        print("\n🔐 Testing permission checks...")
        from app.api.v1.routes.exam_analytics import _check_analytics_permission
        
        # Create a mock student user
        student_user = {
            "_id": ObjectId(test_data["student_id"]),
            "roles": ["student"]
        }
        
        try:
            await _check_analytics_permission(session_id, student_user, get_database())
            print("✅ Student permission check passed!")
        except Exception as e:
            print(f"❌ Student permission check failed: {e}")
        
        # Test with wrong student
        wrong_student = {
            "_id": ObjectId(),
            "roles": ["student"]
        }
        
        try:
            await _check_analytics_permission(session_id, wrong_student, get_database())
            print("❌ Wrong student permission check should have failed!")
        except PermissionError:
            print("✅ Wrong student correctly denied access!")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        print(f"\n✅ All tests completed!")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        await cleanup_test_data(test_data)
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def cleanup_test_data(test_data):
    """Clean up test data"""
    try:
        # Delete in reverse order of creation
        await db.exam_sessions.delete_many({"_id": ObjectId(test_data["session_id"])})
        await db.exams.delete_many({"_id": ObjectId(test_data["exam_id"])})
        await db.questions.delete_many({"_id": ObjectId(test_data["question_id"])})
        await db.classes.delete_many({"_id": ObjectId(test_data["class_id"])})
        await db.users.delete_many({
            "_id": {
                "$in": [ObjectId(test_data["teacher_id"]), ObjectId(test_data["student_id"])]
            }
        })
        await db.subjects.delete_many({"_id": ObjectId(test_data["subject_id"])})
        await db.exam_analytics.delete_many({"exam_session_id": ObjectId(test_data["session_id"])})
        
        print("✅ Test data cleaned up successfully!")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")

async def main():
    """Main test function"""
    print("🚀 Starting Exam Analytics API Test")
    print("=" * 50)
    
    await test_analytics_endpoint()
    
    print("\n" + "=" * 50)
    print("🎉 API Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
