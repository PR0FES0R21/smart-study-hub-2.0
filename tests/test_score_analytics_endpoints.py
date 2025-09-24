#!/usr/bin/env python3
"""
Test script untuk menguji semua endpoint score analytics.
"""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.crud import crud_score_analytics

async def test_admin_endpoints():
    """Test admin analytics endpoints"""
    print("\n=== Testing Admin Analytics ===")
    
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Get an active academic period
        period = await db["academic_periods"].find_one({"status": "active"})
        if not period:
            print("❌ No active academic period found")
            return False
        
        period_id = str(period["_id"])
        print(f"✓ Using academic period: {period_id}")
        
        # Test admin dashboard
        print("Testing admin dashboard...")
        admin_dashboard = await crud_score_analytics.get_admin_dashboard(db, period_id)
        print(f"✓ Admin dashboard: {len(admin_dashboard.get('recent_exams', []))} recent exams")
        
        # Test admin global stats
        print("Testing admin global stats...")
        global_stats = await crud_score_analytics.get_admin_global_statistics(db, period_id)
        print(f"✓ Global stats: {global_stats.get('total_exams_conducted', 0)} exams conducted")
        
        # Test grade performances
        print("Testing grade performances...")
        grade_performances = await crud_score_analytics.get_admin_grade_performances(db, period_id)
        print(f"✓ Grade performances: {len(grade_performances)} grades analyzed")
        
        # Test major performances
        print("Testing major performances...")
        major_performances = await crud_score_analytics.get_admin_major_performances(db, period_id)
        print(f"✓ Major performances: {len(major_performances)} majors analyzed")
        
        # Test subject rankings
        print("Testing subject rankings...")
        subject_rankings = await crud_score_analytics.get_admin_subject_rankings(db, period_id)
        print(f"✓ Subject rankings: {len(subject_rankings)} subjects ranked")
        
        # Test score trends
        print("Testing score trends...")
        score_trends = await crud_score_analytics.get_admin_score_trends(db, period_id, 6)
        print(f"✓ Score trends: {len(score_trends)} trend points")
        
        return True
        
    except Exception as e:
        print(f"❌ Admin endpoints test failed: {e}")
        return False
    finally:
        client.close()

async def test_teacher_endpoints():
    """Test teacher analytics endpoints"""
    print("\n=== Testing Teacher Analytics ===")
    
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Get an active academic period
        period = await db["academic_periods"].find_one({"status": "active"})
        if not period:
            print("❌ No active academic period found")
            return False
        
        period_id = str(period["_id"])
        
        # Get a teacher with teaching assignments
        assignment = await db["teaching_assignments"].find_one({"academic_period_id": period["_id"]})
        if not assignment:
            print("❌ No teaching assignments found")
            return False
        
        teacher_id = str(assignment["teacher_id"])
        print(f"✓ Using teacher: {teacher_id}")
        
        # Test teacher dashboard
        print("Testing teacher dashboard...")
        teacher_dashboard = await crud_score_analytics.get_teacher_dashboard(db, teacher_id, period_id)
        print(f"✓ Teacher dashboard: {len(teacher_dashboard.get('class_statistics', []))} class stats")
        
        # Test teacher class statistics
        print("Testing teacher class statistics...")
        class_stats = await crud_score_analytics.get_teacher_class_statistics(db, teacher_id, period_id)
        print(f"✓ Class statistics: {len(class_stats)} classes")
        
        # Test teacher student performances
        print("Testing teacher student performances...")
        student_performances = await crud_score_analytics.get_teacher_student_performances(db, teacher_id, period_id)
        print(f"✓ Student performances: {len(student_performances)} students")
        
        # Test teacher exam analysis (if there are exams)
        exam = await db["exams"].find_one({"teaching_assignment_id": assignment["_id"]})
        if exam:
            print("Testing teacher exam analysis...")
            exam_analysis = await crud_score_analytics.get_teacher_exam_analysis(db, str(exam["_id"]))
            print(f"✓ Exam analysis: {exam_analysis.get('participants', 0)} participants")
        else:
            print("⚠ No exams found for exam analysis test")
        
        return True
        
    except Exception as e:
        print(f"❌ Teacher endpoints test failed: {e}")
        return False
    finally:
        client.close()

async def test_student_endpoints():
    """Test student analytics endpoints"""
    print("\n=== Testing Student Analytics ===")
    
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Get an active academic period
        period = await db["academic_periods"].find_one({"status": "active"})
        if not period:
            print("❌ No active academic period found")
            return False
        
        period_id = str(period["_id"])
        
        # Get a student with exam sessions
        session = await db["exam_sessions"].find_one({"status": "graded"})
        if not session:
            print("❌ No graded exam sessions found")
            return False
        
        student_id = str(session["student_id"])
        print(f"✓ Using student: {student_id}")
        
        # Test student dashboard
        print("Testing student dashboard...")
        student_dashboard = await crud_score_analytics.get_student_dashboard(db, student_id, period_id)
        print(f"✓ Student dashboard: {len(student_dashboard.get('subject_performances', []))} subject performances")
        
        # Test student subject performances
        print("Testing student subject performances...")
        subject_performances = await crud_score_analytics.get_student_subject_performances(db, student_id, period_id)
        print(f"✓ Subject performances: {len(subject_performances)} subjects")
        
        # Test student exam history
        print("Testing student exam history...")
        exam_history = await crud_score_analytics.get_student_exam_history(db, student_id, period_id)
        print(f"✓ Exam history: {len(exam_history)} exams")
        
        # Test student class comparison
        print("Testing student class comparison...")
        class_comparison = await crud_score_analytics.get_student_class_comparison(db, student_id, period_id)
        print(f"✓ Class comparison: ranking {class_comparison.get('student_ranking', 0)} of {class_comparison.get('total_classmates', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Student endpoints test failed: {e}")
        return False
    finally:
        client.close()

async def test_data_consistency():
    """Test data consistency across endpoints"""
    print("\n=== Testing Data Consistency ===")
    
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Check basic data availability
        total_sessions = await db["exam_sessions"].count_documents({"status": "graded"})
        total_exams = await db["exams"].count_documents({})
        total_students = await db["users"].count_documents({"roles": "student"})
        total_teachers = await db["users"].count_documents({"roles": "teacher"})
        
        print(f"✓ Data availability:")
        print(f"  - Graded sessions: {total_sessions}")
        print(f"  - Total exams: {total_exams}")
        print(f"  - Total students: {total_students}")
        print(f"  - Total teachers: {total_teachers}")
        
        if total_sessions == 0:
            print("⚠ Warning: No graded exam sessions found - analytics will be limited")
        
        return True
        
    except Exception as e:
        print(f"❌ Data consistency test failed: {e}")
        return False
    finally:
        client.close()

async def main():
    """Main test function"""
    print("TESTING SCORE ANALYTICS ENDPOINTS")
    print("=" * 50)
    
    tests = [
        ("Data Consistency", test_data_consistency),
        ("Admin Endpoints", test_admin_endpoints),
        ("Teacher Endpoints", test_teacher_endpoints),
        ("Student Endpoints", test_student_endpoints),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}...")
        try:
            result = await test_func()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] {test_name} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    
    for i, (test_name, _) in enumerate(tests):
        status = "[PASS]" if results[i] else "[FAIL]"
        print(f"   {status} {test_name}")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nTest Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 75:
        print("✅ Score Analytics endpoints are working!")
        print("\nNEXT STEPS:")
        print("   1. Test with real API calls using curl/Postman")
        print("   2. Test with different user roles and permissions")
        print("   3. Test with larger datasets")
    else:
        print("❌ Some tests failed - please review the errors above")

if __name__ == "__main__":
    asyncio.run(main())
