#!/usr/bin/env python3
"""
Quick Database Inspection untuk Subject Mastery Analytics
Script sederhana untuk melihat data real dan mengidentifikasi masalah
"""

import asyncio
import sys
import os
sys.path.append('.')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from bson import ObjectId
import json

# Database config - menggunakan konfigurasi dari aplikasi
MONGO_URL = "mongodb+srv://profesor:root@cluster0.6kpph5n.mongodb.net"
DATABASE_NAME = "school_db_mvp"

async def inspect_database():
    """Inspect database untuk Subject Mastery Analytics"""
    
    print("🔍 QUICK DATABASE INSPECTION - SUBJECT MASTERY ANALYTICS")
    print("=" * 65)
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        
        print("\n📊 1. DATA COUNTS")
        print("-" * 20)
        
        # Basic counts
        exam_sessions_total = await db.exam_sessions.count_documents({})
        exam_sessions_graded = await db.exam_sessions.count_documents({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None}
        })
        exams_total = await db.exams.count_documents({})
        teaching_assignments_total = await db.teaching_assignments.count_documents({})
        subjects_total = await db.subjects.count_documents({})
        
        print(f"📝 Exam Sessions (total): {exam_sessions_total}")
        print(f"✅ Exam Sessions (graded): {exam_sessions_graded}")
        print(f"📚 Exams: {exams_total}")
        print(f"👨‍🏫 Teaching Assignments: {teaching_assignments_total}")
        print(f"📖 Subjects: {subjects_total}")
        
        print("\n🔗 2. DATA RELATIONSHIPS")
        print("-" * 25)
        
        # Sample exam session to trace relationships
        sample_session = await db.exam_sessions.find_one({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$ne": None}
        })
        
        if sample_session:
            print(f"📋 Sample exam session ID: {sample_session['_id']}")
            print(f"   Student ID: {sample_session.get('student_id')}")
            print(f"   Exam ID: {sample_session.get('exam_id')}")
            print(f"   Score: {sample_session.get('score')}")
            print(f"   Status: {sample_session.get('status')}")
            
            # Trace to exam
            exam = await db.exams.find_one({"_id": sample_session.get('exam_id')})
            if exam:
                print(f"\n📚 Related exam:")
                print(f"   Title: {exam.get('title')}")
                print(f"   Teaching Assignment ID: {exam.get('teaching_assignment_id')}")
                
                # Trace to teaching assignment
                ta = await db.teaching_assignments.find_one({"_id": exam.get('teaching_assignment_id')})
                if ta:
                    print(f"\n👨‍🏫 Related teaching assignment:")
                    print(f"   Teacher ID: {ta.get('teacher_id')}")
                    print(f"   Subject ID: {ta.get('subject_id')}")
                    print(f"   Class ID: {ta.get('class_id')}")
                    
                    # Trace to subject
                    subject = await db.subjects.find_one({"_id": ta.get('subject_id')})
                    if subject:
                        print(f"\n📖 Related subject:")
                        print(f"   Name: {subject.get('name')}")
                        print(f"   Code: {subject.get('code', 'N/A')}")
                        print("\n✅ FULL CHAIN VERIFIED: Session → Exam → Teaching Assignment → Subject")
                    else:
                        print("\n❌ BROKEN CHAIN: Subject not found!")
                else:
                    print("\n❌ BROKEN CHAIN: Teaching assignment not found!")
            else:
                print("\n❌ BROKEN CHAIN: Exam not found!")
        else:
            print("❌ No graded exam sessions found!")
        
        print("\n🧪 3. RUN SUBJECT MASTERY QUERY")
        print("-" * 35)
        
        # Run the exact query used by Subject Mastery Analytics
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
            {"$group": {
                "_id": "$subject.name",
                "avg_score": {"$avg": "$score"},
                "exam_count": {"$sum": 1},
                "total_score": {"$sum": "$score"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        cursor = db.exam_sessions.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        print(f"📊 Query results: {len(results)} subjects found")
        
        if results:
            print("\n📋 SUBJECT MASTERY DATA:")
            for result in results:
                subject_name = result["_id"]
                avg_score = round(result["avg_score"], 1)
                exam_count = result["exam_count"]
                print(f"   📖 {subject_name}: {avg_score} avg (from {exam_count} exams)")
            
            print("\n✅ SUCCESS: Subject mastery data available!")
            print(f"   Total subjects with data: {len(results)}")
            
            # Calculate overall stats
            total_exams = sum(r["exam_count"] for r in results)
            total_score = sum(r["total_score"] for r in results)
            overall_avg = round(total_score / total_exams, 1) if total_exams > 0 else 0
            
            print(f"   📊 Overall average: {overall_avg}")
            print(f"   🔢 Total exams: {total_exams}")
            
        else:
            print("\n❌ NO RESULTS!")
            print("   Query returned empty - investigating step by step...")
            await debug_pipeline_steps(db)
        
        print("\n📅 4. DATE RANGE CHECK")
        print("-" * 23)
        
        # Check current academic year vs all time
        current_year = datetime.now().year
        academic_start = datetime(current_year, 7, 1)  # July 1st
        
        current_academic_sessions = await db.exam_sessions.count_documents({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$ne": None},
            "submitted_at": {"$gte": academic_start}
        })
        
        print(f"📊 Current academic year sessions: {current_academic_sessions}")
        print(f"📊 All time graded sessions: {exam_sessions_graded}")
        
        if exam_sessions_graded > current_academic_sessions:
            print(f"💡 {exam_sessions_graded - current_academic_sessions} sessions are outside current academic year")
            print("   Try using start_date/end_date parameters to include older data")
        
        print("\n🎯 5. RECOMMENDATIONS")
        print("-" * 22)
        
        if exam_sessions_graded == 0:
            print("❌ No graded exam sessions - create and grade some exams")
        elif teaching_assignments_total == 0:
            print("❌ No teaching assignments - create teacher-subject-class relationships")
        elif subjects_total == 0:
            print("❌ No subjects - add subject/mata pelajaran data")
        elif len(results) == 0:
            print("❌ Data chain is broken - check the pipeline debug above")
        else:
            print(f"✅ Data looks good! {len(results)} subjects should appear in Subject Mastery Analytics")
            print("   If still getting empty response, check:")
            print("   1. User permissions (student/teacher/admin access)")
            print("   2. Date filtering parameters")
            print("   3. Application logs for errors")
        
        print(f"\n✅ Inspection completed at: {datetime.now().isoformat()}")
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()

async def debug_pipeline_steps(db):
    """Debug pipeline step by step"""
    print("\n🔍 PIPELINE DEBUG:")
    
    # Step 1: Match graded sessions
    step1_count = await db.exam_sessions.count_documents({
        "status": {"$in": ["submitted", "graded"]},
        "score": {"$exists": True, "$ne": None, "$gte": 0}
    })
    print(f"   1️⃣ Graded sessions: {step1_count}")
    
    if step1_count == 0:
        print("   ❌ No graded sessions found!")
        return
    
    # Step 2: Check exam lookup
    pipeline_step2 = [
        {"$match": {
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        }},
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$match": {"exam": {"$ne": []}}},
        {"$count": "count"}
    ]
    
    result2 = await db.exam_sessions.aggregate(pipeline_step2).to_list(1)
    step2_count = result2[0]["count"] if result2 else 0
    print(f"   2️⃣ Sessions with valid exams: {step2_count}")
    
    if step2_count == 0:
        print("   ❌ No sessions have valid exam references!")
        # Check sample exam IDs
        sample_sessions = await db.exam_sessions.find({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$ne": None}
        }).limit(3).to_list(3)
        
        if sample_sessions:
            exam_ids = [s.get("exam_id") for s in sample_sessions]
            print(f"   🔍 Sample exam IDs from sessions: {exam_ids}")
            
            existing_exams = await db.exams.count_documents({"_id": {"$in": exam_ids}})
            print(f"   📚 Existing exams for these IDs: {existing_exams}")
        return
    
    # Step 3: Check teaching assignment lookup
    pipeline_step3 = [
        {"$match": {
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        }},
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "ta"}},
        {"$match": {"ta": {"$ne": []}}},
        {"$count": "count"}
    ]
    
    result3 = await db.exam_sessions.aggregate(pipeline_step3).to_list(1)
    step3_count = result3[0]["count"] if result3 else 0
    print(f"   3️⃣ Sessions with valid teaching assignments: {step3_count}")
    
    if step3_count == 0:
        print("   ❌ No sessions have valid teaching assignment references!")
        print("   🔍 This is likely the root cause!")
        
        # Check sample teaching assignment IDs from exams
        sample_exams = await db.exams.find().limit(5).to_list(5)
        if sample_exams:
            ta_ids = [e.get("teaching_assignment_id") for e in sample_exams if e.get("teaching_assignment_id")]
            print(f"   📋 Sample TA IDs from exams: {ta_ids[:3]}")
            
            if ta_ids:
                existing_tas = await db.teaching_assignments.count_documents({"_id": {"$in": ta_ids}})
                print(f"   👨‍🏫 Existing TAs for these IDs: {existing_tas}")
                
                if existing_tas == 0:
                    print("   💡 SOLUTION: Create teaching_assignments or fix exam.teaching_assignment_id references")
        return
    
    # Step 4: Check subject lookup
    pipeline_step4 = [
        {"$match": {
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        }},
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "ta"}},
        {"$unwind": "$ta"},
        {"$lookup": {"from": "subjects", "localField": "ta.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$match": {"subject": {"$ne": []}}},
        {"$count": "count"}
    ]
    
    result4 = await db.exam_sessions.aggregate(pipeline_step4).to_list(1)
    step4_count = result4[0]["count"] if result4 else 0
    print(f"   4️⃣ Sessions with valid subjects: {step4_count}")
    
    if step4_count == 0:
        print("   ❌ No sessions have valid subject references!")
        
        # Check sample subject IDs from teaching assignments
        sample_tas = await db.teaching_assignments.find().limit(5).to_list(5)
        if sample_tas:
            subject_ids = [ta.get("subject_id") for ta in sample_tas if ta.get("subject_id")]
            print(f"   📋 Sample subject IDs from TAs: {subject_ids[:3]}")
            
            if subject_ids:
                existing_subjects = await db.subjects.count_documents({"_id": {"$in": subject_ids}})
                print(f"   📖 Existing subjects for these IDs: {existing_subjects}")
    else:
        print(f"   ✅ Pipeline should work! {step4_count} sessions reach the final step")

if __name__ == "__main__":
    print("🚀 Starting Quick Database Inspection...")
    asyncio.run(inspect_database())
