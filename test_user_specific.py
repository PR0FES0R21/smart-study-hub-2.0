#!/usr/bin/env python3
"""
Test User-Specific Subject Mastery Analytics
Debug dengan user roles dan permissions yang spesifik
"""

import asyncio
import sys
import os
sys.path.append('.')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from bson import ObjectId
import json

# Database config
MONGO_URL = "mongodb+srv://profesor:root@cluster0.6kpph5n.mongodb.net"
DATABASE_NAME = "school_db_mvp"

async def test_user_permissions():
    """Test user permissions dengan data real dari database"""
    
    print("🧪 TESTING USER-SPECIFIC SUBJECT MASTERY ANALYTICS")
    print("=" * 55)
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        
        # Ambil sample users dari database
        print("\n👤 1. GET SAMPLE USERS")
        print("-" * 25)
        
        # Get sample student
        sample_student = await db.users.find_one({"roles": {"$in": ["student"]}})
        if sample_student:
            print(f"👨‍🎓 Sample Student ID: {sample_student['_id']}")
            
            # Test student access
            await test_student_access(db, sample_student['_id'])
        else:
            print("❌ No students found in database")
        
        # Get sample teacher
        sample_teacher = await db.users.find_one({"roles": {"$in": ["teacher"]}})
        if sample_teacher:
            print(f"\n👨‍🏫 Sample Teacher ID: {sample_teacher['_id']}")
            
            # Test teacher access
            await test_teacher_access(db, sample_teacher['_id'])
        else:
            print("❌ No teachers found in database")
        
        # Get sample admin
        sample_admin = await db.users.find_one({"roles": {"$in": ["admin"]}})
        if sample_admin:
            print(f"\n🔐 Sample Admin ID: {sample_admin['_id']}")
            
            # Test admin access
            await test_admin_access(db, sample_admin['_id'])
        else:
            print("❌ No admins found in database")
        
        print(f"\n✅ User permission testing completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()

async def test_student_access(db, student_id):
    """Test student access to subject mastery data"""
    print(f"\n🔍 Testing Student Access: {student_id}")
    print("-" * 35)
    
    # Check student's exam sessions
    student_sessions = await db.exam_sessions.count_documents({
        "student_id": ObjectId(student_id),
        "status": {"$in": ["submitted", "graded"]},
        "score": {"$ne": None}
    })
    
    print(f"📝 Student's exam sessions: {student_sessions}")
    
    if student_sessions > 0:
        # Run student-specific query
        pipeline = [
            {"$match": {
                "student_id": ObjectId(student_id),
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$exists": True, "$ne": None, "$gte": 0}
            }},
            {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
            {"$unwind": "$exam"},
            {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "ta"}},
            {"$unwind": "$ta"},
            {"$lookup": {"from": "subjects", "localField": "ta.subject_id", "foreignField": "_id", "as": "subject"}},
            {"$unwind": "$subject"},
            {"$group": {
                "_id": "$subject.name",
                "avg_score": {"$avg": "$score"},
                "exam_count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        cursor = db.exam_sessions.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        if results:
            print(f"✅ Student should see {len(results)} subjects:")
            for result in results:
                subject_name = result["_id"]
                avg_score = round(result["avg_score"], 1)
                exam_count = result["exam_count"]
                print(f"   📖 {subject_name}: {avg_score} avg (from {exam_count} exams)")
        else:
            print("❌ No subject mastery data for this student")
            print("   Possible causes:")
            print("   - Student sessions don't link to exams with teaching assignments")
            print("   - Broken data relationships")
    else:
        print("❌ Student has no graded exam sessions")

async def test_teacher_access(db, teacher_id):
    """Test teacher access to subject mastery data"""
    print(f"\n🔍 Testing Teacher Access: {teacher_id}")
    print("-" * 35)
    
    # Check teacher's assignments
    teacher_assignments = await db.teaching_assignments.count_documents({
        "teacher_id": ObjectId(teacher_id)
    })
    
    print(f"👨‍🏫 Teacher's assignments: {teacher_assignments}")
    
    if teacher_assignments > 0:
        # Get assignment details
        assignments = await db.teaching_assignments.find({
            "teacher_id": ObjectId(teacher_id)
        }).to_list(length=None)
        
        assignment_ids = [ta["_id"] for ta in assignments]
        
        # Get exams for these assignments
        teacher_exams = await db.exams.find({
            "teaching_assignment_id": {"$in": assignment_ids}
        }).to_list(length=None)
        
        print(f"📚 Teacher's exams: {len(teacher_exams)}")
        
        if teacher_exams:
            exam_ids = [exam["_id"] for exam in teacher_exams]
            
            # Get sessions for these exams
            related_sessions = await db.exam_sessions.count_documents({
                "exam_id": {"$in": exam_ids},
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$ne": None}
            })
            
            print(f"📊 Related graded sessions: {related_sessions}")
            
            if related_sessions > 0:
                # Run teacher-specific aggregation (class-level)
                pipeline = [
                    {"$match": {
                        "exam_id": {"$in": exam_ids},
                        "status": {"$in": ["submitted", "graded"]},
                        "score": {"$exists": True, "$ne": None, "$gte": 0}
                    }},
                    {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
                    {"$unwind": "$exam"},
                    {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "ta"}},
                    {"$unwind": "$ta"},
                    {"$lookup": {"from": "subjects", "localField": "ta.subject_id", "foreignField": "_id", "as": "subject"}},
                    {"$unwind": "$subject"},
                    {"$lookup": {"from": "classes", "localField": "ta.class_id", "foreignField": "_id", "as": "class"}},
                    {"$unwind": "$class"},
                    {"$group": {
                        "_id": {
                            "class_id": "$ta.class_id",
                            "subject_name": "$subject.name"
                        },
                        "avg_score": {"$avg": "$score"},
                        "exam_count": {"$sum": 1},
                        "class_name": {"$first": "$class.name"},
                        "grade_level": {"$first": "$class.grade_level"}
                    }},
                    {"$sort": {"_id.class_id": 1, "_id.subject_name": 1}}
                ]
                
                cursor = db.exam_sessions.aggregate(pipeline)
                class_results = await cursor.to_list(length=None)
                
                if class_results:
                    print(f"✅ Teacher should see class-level data:")
                    print(f"   📊 {len(class_results)} class-subject combinations:")
                    for result in class_results[:5]:  # Show first 5
                        class_name = result.get("class_name", "Unknown")
                        grade_level = result.get("grade_level", "?")
                        subject_name = result["_id"]["subject_name"]
                        avg_score = round(result["avg_score"], 1)
                        exam_count = result["exam_count"]
                        print(f"   📖 {grade_level}-{class_name} | {subject_name}: {avg_score} avg ({exam_count} exams)")
                else:
                    print("❌ No class-level data found for teacher")
                    print("   Debug: Run pipeline step by step...")
            else:
                print("❌ No graded sessions for teacher's exams")
        else:
            print("❌ No exams found for teacher's assignments")
    else:
        print("❌ Teacher has no teaching assignments")

async def test_admin_access(db, admin_id):
    """Test admin access to subject mastery data"""
    print(f"\n🔍 Testing Admin Access: {admin_id}")
    print("-" * 30)
    
    # Admin should see all data
    total_sessions = await db.exam_sessions.count_documents({
        "status": {"$in": ["submitted", "graded"]},
        "score": {"$ne": None}
    })
    
    print(f"🔐 Admin can see all {total_sessions} graded sessions")
    
    # Run admin-level aggregation (school-wide)
    pipeline = [
        {"$match": {
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        }},
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "ta"}},
        {"$unwind": "$ta"},
        {"$lookup": {"from": "subjects", "localField": "ta.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        {"$lookup": {"from": "classes", "localField": "ta.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        {"$group": {
            "_id": {
                "class_id": "$ta.class_id",
                "subject_name": "$subject.name"
            },
            "avg_score": {"$avg": "$score"},
            "exam_count": {"$sum": 1},
            "class_name": {"$first": "$class.name"},
            "grade_level": {"$first": "$class.grade_level"}
        }},
        {"$sort": {"_id.class_id": 1, "_id.subject_name": 1}}
    ]
    
    cursor = db.exam_sessions.aggregate(pipeline)
    admin_results = await cursor.to_list(length=None)
    
    if admin_results:
        print(f"✅ Admin should see school-wide data:")
        print(f"   📊 {len(admin_results)} class-subject combinations")
        
        # Group by class for summary
        classes = {}
        for result in admin_results:
            class_id = str(result["_id"]["class_id"])
            if class_id not in classes:
                classes[class_id] = {
                    "name": result.get("class_name", "Unknown"),
                    "grade": result.get("grade_level", "?"),
                    "subjects": []
                }
            classes[class_id]["subjects"].append(result["_id"]["subject_name"])
        
        print(f"   📋 Classes with data: {len(classes)}")
        for class_id, class_data in list(classes.items())[:3]:  # Show first 3
            subjects_count = len(class_data["subjects"])
            print(f"   🏫 {class_data['grade']}-{class_data['name']}: {subjects_count} subjects")
    else:
        print("❌ No school-wide data found")

async def test_with_date_ranges():
    """Test dengan berbagai date ranges"""
    print(f"\n📅 TESTING DATE RANGE FILTERS")
    print("-" * 30)
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        
        # Test different date ranges
        ranges = [
            ("All time", None, None),
            ("Current academic year", datetime(datetime.now().year, 7, 1), None),
            ("Last 3 months", datetime.now() - timedelta(days=90), None),
            ("Last month", datetime.now() - timedelta(days=30), None)
        ]
        
        for range_name, start_date, end_date in ranges:
            filters = {
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$exists": True, "$ne": None, "$gte": 0}
            }
            
            if start_date:
                date_filter = {"$gte": start_date}
                if end_date:
                    date_filter["$lte"] = end_date
                filters["submitted_at"] = date_filter
            
            count = await db.exam_sessions.count_documents(filters)
            print(f"   📊 {range_name}: {count} sessions")
        
    except Exception as e:
        print(f"❌ Error testing date ranges: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("🚀 Starting User-Specific Testing...")
    asyncio.run(test_user_permissions())
    asyncio.run(test_with_date_ranges())
