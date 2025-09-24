#!/usr/bin/env python3
"""
Quick Diagnosis Script untuk Subject Mastery Analytics
Jalankan untuk mengidentifikasi penyebab data kosong
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from bson import ObjectId

# Database config (sesuaikan dengan setup Anda)
MONGO_URL = "mongodb://localhost:27017"
DATABASE_NAME = "smart_study_hub"

async def diagnose_subject_mastery_data():
    """Diagnostic lengkap untuk Subject Mastery Analytics"""
    
    print("🔬 SUBJECT MASTERY ANALYTICS DIAGNOSTIC")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        
        print("\n📊 1. BASIC DATA COUNTS")
        print("-" * 30)
        
        # Count basic collections
        exam_sessions_total = await db.exam_sessions.count_documents({})
        exam_sessions_graded = await db.exam_sessions.count_documents({
            "status": "graded", 
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        })
        exams_total = await db.exams.count_documents({})
        teaching_assignments_total = await db.teaching_assignments.count_documents({})
        subjects_total = await db.subjects.count_documents({})
        
        print(f"📝 Total exam sessions: {exam_sessions_total}")
        print(f"✅ Graded exam sessions: {exam_sessions_graded}")
        print(f"📚 Total exams: {exams_total}")
        print(f"👨‍🏫 Teaching assignments: {teaching_assignments_total}")
        print(f"📖 Subjects: {subjects_total}")
        
        # Quick assessment
        if exam_sessions_graded == 0:
            print("\n❌ PROBLEM IDENTIFIED: Tidak ada exam sessions yang graded!")
            print("   Solusi: Pastikan ada ujian yang sudah dinilai dengan status 'graded'")
        
        if teaching_assignments_total == 0:
            print("\n❌ PROBLEM IDENTIFIED: Tidak ada teaching assignments!")
            print("   Solusi: Buat teaching assignments untuk menghubungkan teacher-subject-class")
            
        if subjects_total == 0:
            print("\n❌ PROBLEM IDENTIFIED: Tidak ada mata pelajaran!")
            print("   Solusi: Tambahkan data subjects/mata pelajaran")
        
        print("\n🔗 2. DATA RELATIONSHIPS CHECK")
        print("-" * 35)
        
        # Check orphaned exams (no teaching assignment)
        orphaned_exams_pipeline = [
            {
                "$lookup": {
                    "from": "teaching_assignments",
                    "localField": "teaching_assignment_id",
                    "foreignField": "_id",
                    "as": "ta"
                }
            },
            {"$match": {"ta": {"$size": 0}}},
            {"$count": "orphaned_count"}
        ]
        
        orphaned_exams = await db.exams.aggregate(orphaned_exams_pipeline).to_list(length=1)
        orphaned_count = orphaned_exams[0]["orphaned_count"] if orphaned_exams else 0
        
        print(f"🔗 Orphaned exams (no teaching assignment): {orphaned_count}")
        if orphaned_count > 0:
            print("   ⚠️  WARNING: Ada exams yang tidak terhubung ke teaching assignments!")
        
        # Check subjects without names
        subjects_no_name = await db.subjects.count_documents({
            "$or": [
                {"name": {"$exists": False}},
                {"name": ""}
            ]
        })
        
        print(f"📖 Subjects tanpa nama: {subjects_no_name}")
        if subjects_no_name > 0:
            print("   ⚠️  WARNING: Ada subjects tanpa nama!")
        
        print("\n🧪 3. SAMPLE SUBJECT MASTERY QUERY")
        print("-" * 38)
        
        # Run sample query seperti yang dijalankan Subject Mastery Analytics
        sample_pipeline = [
            {"$match": {"status": "graded", "score": {"$ne": None}}},
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
            {"$sort": {"_id": 1}},
            {"$limit": 10}
        ]
        
        sample_results = await db.exam_sessions.aggregate(sample_pipeline).to_list(length=10)
        
        if sample_results:
            print("✅ SAMPLE DATA FOUND:")
            for result in sample_results:
                subject_name = result["_id"]
                avg_score = round(result["avg_score"], 1)
                exam_count = result["exam_count"]
                print(f"   📚 {subject_name}: {avg_score} (dari {exam_count} ujian)")
        else:
            print("❌ NO DATA FOUND!")
            print("   Data kosong karena salah satu dari:")
            print("   1. Tidak ada exam sessions graded")
            print("   2. Exams tidak terhubung ke teaching assignments") 
            print("   3. Teaching assignments tidak terhubung ke subjects")
            print("   4. Subjects tidak ada atau nama kosong")
        
        print("\n📅 4. DATE FILTERING CHECK")
        print("-" * 28)
        
        # Check current academic year data
        current_year = datetime.now().year
        academic_start = datetime(current_year, 7, 1)  # July 1st
        
        current_academic_sessions = await db.exam_sessions.count_documents({
            "status": "graded",
            "score": {"$ne": None},
            "submitted_at": {"$gte": academic_start}
        })
        
        all_time_sessions = await db.exam_sessions.count_documents({
            "status": "graded", 
            "score": {"$ne": None}
        })
        
        print(f"📊 Graded sessions (current academic year): {current_academic_sessions}")
        print(f"📊 Graded sessions (all time): {all_time_sessions}")
        
        if all_time_sessions > current_academic_sessions:
            print(f"   💡 TIP: Ada {all_time_sessions - current_academic_sessions} sessions di luar current academic year")
            print("   Coba gunakan parameter start_date dan end_date untuk mengakses data lama")
        
        print("\n🎯 5. RECOMMENDATIONS")
        print("-" * 22)
        
        if exam_sessions_graded == 0:
            print("1. ✅ Buat/grade beberapa exam sessions dengan status 'graded'")
        if teaching_assignments_total == 0:
            print("2. ✅ Buat teaching assignments untuk menghubungkan teacher-subject-class")
        if subjects_total == 0:
            print("3. ✅ Tambahkan data subjects/mata pelajaran")
        if orphaned_count > 0:
            print("4. ✅ Perbaiki exams yang tidak terhubung ke teaching assignments")
        if subjects_no_name > 0:
            print("5. ✅ Pastikan semua subjects memiliki nama")
        
        # Quick fix suggestions
        print("\n🔧 QUICK TESTING TIPS:")
        print("- Test dengan parameter: ?include_zero_scores=true&min_exams_per_subject=0")
        print("- Test dengan date range: ?start_date=2024-01-01&end_date=2025-12-31")
        print("- Check application logs untuk error messages")
        
        print(f"\n✅ Diagnosis completed at: {datetime.now().isoformat()}")
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()

async def quick_data_check(user_id: str = None, role: str = "student"):
    """Quick check untuk specific user"""
    print(f"\n🔍 QUICK CHECK FOR USER: {user_id} ({role})")
    print("-" * 40)
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        
        if not user_id:
            print("❌ No user_id provided for specific check")
            return
            
        user_obj_id = ObjectId(user_id)
        
        if role == "student":
            # Check student's graded sessions
            student_sessions = await db.exam_sessions.count_documents({
                "student_id": user_obj_id,
                "status": "graded",
                "score": {"$ne": None}
            })
            print(f"📝 Student's graded sessions: {student_sessions}")
            
        elif role == "teacher":
            # Check teacher's assignments and related sessions
            teacher_assignments = await db.teaching_assignments.count_documents({
                "teacher_id": user_obj_id
            })
            print(f"👨‍🏫 Teacher's assignments: {teacher_assignments}")
            
            if teacher_assignments > 0:
                # Get exam IDs
                assignments = await db.teaching_assignments.find({
                    "teacher_id": user_obj_id
                }, {"_id": 1}).to_list(length=None)
                
                assignment_ids = [ta["_id"] for ta in assignments]
                
                teacher_exams = await db.exams.count_documents({
                    "teaching_assignment_id": {"$in": assignment_ids}
                })
                print(f"📚 Teacher's exams: {teacher_exams}")
                
                if teacher_exams > 0:
                    exam_ids = await db.exams.find({
                        "teaching_assignment_id": {"$in": assignment_ids}
                    }, {"_id": 1}).to_list(length=None)
                    
                    exam_id_list = [e["_id"] for e in exam_ids]
                    
                    related_sessions = await db.exam_sessions.count_documents({
                        "exam_id": {"$in": exam_id_list},
                        "status": "graded"
                    })
                    print(f"✅ Related graded sessions: {related_sessions}")
        
    except Exception as e:
        print(f"❌ Error in quick check: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("🚀 Starting Subject Mastery Analytics Diagnosis...")
    
    # Run main diagnosis
    asyncio.run(diagnose_subject_mastery_data())
    
    # Optional: specific user check
    if len(sys.argv) >= 3:
        user_id = sys.argv[1]
        role = sys.argv[2]
        print(f"\n🔍 Running specific check for user {user_id} with role {role}")
        asyncio.run(quick_data_check(user_id, role))
    else:
        print("\n💡 Untuk check specific user: python diagnosis_subject_mastery.py USER_ID ROLE")
        print("   Example: python diagnosis_subject_mastery.py 507f1f77bcf86cd799439011 student")
