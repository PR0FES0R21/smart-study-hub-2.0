#!/usr/bin/env python3
"""
Simple test runner untuk identify errors in teacher analytics
"""
import sys
import os
import traceback
from datetime import datetime

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test basic imports"""
    print("🧪 Testing imports...")
    
    try:
        print("  ✅ Testing basic imports...")
        from bson import ObjectId
        from datetime import datetime, timedelta
        print("  ✅ Basic imports successful")
        
        print("  🔍 Testing schema imports...")
        from app.schemas.teacher_analytics import (
            ExamMetadata, ClassStatistics, QuestionAnalysis,
            StudentPerformance, TimeAnalysis, ViolationAnalysis,
            AnalyticsTask, ExamAnalytics
        )
        print("  ✅ Schema imports successful")
        
        print("  🔍 Testing CRUD imports...")
        from app.crud.crud_teacher_analytics import TeacherAnalyticsCRUD
        print("  ✅ CRUD imports successful")
        
        print("  🔍 Testing task imports...")
        from app.tasks.teacher_analytics_tasks import TeacherAnalyticsTaskManager
        print("  ✅ Task imports successful")
        
        print("  🔍 Testing route imports...")
        from app.api.v1.routes.teacher_analytics import router
        print("  ✅ Route imports successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import error: {str(e)}")
        traceback.print_exc()
        return False

def test_schema_validation():
    """Test Pydantic schema validation"""
    print("\n🧪 Testing schema validation...")
    
    try:
        from app.schemas.teacher_analytics import ExamMetadata, ClassStatistics
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        # Test ExamMetadata
        print("  🔍 Testing ExamMetadata...")
        metadata = ExamMetadata(
            exam_id=ObjectId(),
            exam_title="Test Exam",
            exam_type="official_uts",
            subject_name="Mathematics",
            class_name="10A", 
            teacher_name="John Doe",
            total_questions=25,
            max_score=100,
            duration_minutes=90,
            availability_start_time=datetime.utcnow(),
            availability_end_time=datetime.utcnow() + timedelta(hours=2),
            academic_period="2024/2025"
        )
        print(f"  ✅ ExamMetadata created: {metadata.exam_title}")
        
        # Test ClassStatistics
        print("  🔍 Testing ClassStatistics...")
        stats = ClassStatistics(
            total_students=30,
            students_completed=25,
            students_in_progress=3,
            students_not_started=2,
            completion_rate=83.33,
            class_average=75.5,
            median_score=78.0,
            highest_score=95,
            lowest_score=45,
            standard_deviation=12.5,
            passing_rate=80.0,
            grade_distribution={"A": 5, "B": 10, "C": 8, "D": 2, "E": 0},
            score_ranges={"81-100": 8, "61-80": 12, "41-60": 4, "21-40": 1, "0-20": 0}
        )
        print(f"  ✅ ClassStatistics created: {stats.total_students} students")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Schema validation error: {str(e)}")
        traceback.print_exc()
        return False

def test_crud_initialization():
    """Test CRUD class initialization"""
    print("\n🧪 Testing CRUD initialization...")
    
    try:
        from app.crud.crud_teacher_analytics import TeacherAnalyticsCRUD
        
        print("  🔍 Creating CRUD instance...")
        crud = TeacherAnalyticsCRUD()
        print(f"  ✅ CRUD instance created: {type(crud)}")
        
        # Test some basic methods exist
        methods = ['generate_exam_analytics', 'get_analytics', 'delete_analytics']
        for method in methods:
            if hasattr(crud, method):
                print(f"  ✅ Method exists: {method}")
            else:
                print(f"  ❌ Method missing: {method}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ CRUD initialization error: {str(e)}")
        traceback.print_exc()
        return False

def test_task_manager():
    """Test background task manager"""
    print("\n🧪 Testing Task Manager...")
    
    try:
        from app.tasks.teacher_analytics_tasks import TeacherAnalyticsTaskManager
        from bson import ObjectId
        
        print("  🔍 Testing task ID generation...")
        exam_id = "test_exam_123"
        teacher_id = ObjectId()
        
        task_id = TeacherAnalyticsTaskManager.generate_task_id(exam_id, teacher_id)
        print(f"  ✅ Task ID generated: {task_id}")
        
        expected_prefix = f"analytics_{exam_id}_{teacher_id}_"
        if task_id.startswith(expected_prefix):
            print("  ✅ Task ID format correct")
        else:
            print(f"  ❌ Task ID format incorrect. Expected prefix: {expected_prefix}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Task manager error: {str(e)}")
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection"""
    print("\n🧪 Testing database connection...")
    
    try:
        from app.api.v1.deps import get_database
        
        print("  🔍 Getting database instance...")
        db = get_database()
        print(f"  ✅ Database instance: {type(db)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database connection error: {str(e)}")
        traceback.print_exc()
        return False

def test_api_router():
    """Test API router"""
    print("\n🧪 Testing API router...")
    
    try:
        from app.api.v1.api import api_router
        print("  ✅ API router imported successfully")
        
        # Check if teacher-analytics routes are included
        routes = [route.path for route in api_router.routes]
        teacher_analytics_routes = [r for r in routes if 'teacher-analytics' in r]
        
        if teacher_analytics_routes:
            print(f"  ✅ Teacher analytics routes found: {len(teacher_analytics_routes)}")
            for route in teacher_analytics_routes[:3]:  # Show first 3
                print(f"    - {route}")
        else:
            print("  ❌ No teacher analytics routes found")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ API router error: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Teacher Analytics Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Schema Validation", test_schema_validation),
        ("CRUD Initialization", test_crud_initialization),
        ("Task Manager", test_task_manager),
        ("Database Connection", test_database_connection),
        ("API Router", test_api_router),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Unexpected error in {test_name}: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System looks healthy.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
