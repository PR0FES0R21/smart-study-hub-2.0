#!/usr/bin/env python3
"""
Unit Test Script untuk Debug Subject Mastery Analytics
Menjalankan test langsung terhadap database dan CRUD logic
"""

import asyncio
import sys
import os
sys.path.append('.')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from bson import ObjectId
import logging
from typing import Dict, Any

# Import modules yang diperlukan
from app.crud.subject_mastery_analytics import subject_mastery_crud
from app.schemas.subject_mastery_analytics import SubjectMasteryRequest
from app.api.v1.deps import get_database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubjectMasteryDebugger:
    def __init__(self):
        self.db = None
        
    async def setup(self):
        """Setup database connection"""
        self.db = get_database()
        
    async def debug_step_by_step(self, current_user: Dict[str, Any]):
        """Debug step by step untuk melihat di mana masalahnya"""
        
        print("🔍 SUBJECT MASTERY ANALYTICS - STEP BY STEP DEBUG")
        print("=" * 60)
        
        user_roles = current_user.get("roles", [])
        user_id = current_user.get("_id")
        
        print(f"👤 User ID: {user_id}")
        print(f"🔐 User Roles: {user_roles}")
        
        # Step 1: Check basic data counts
        print("\n📊 STEP 1: BASIC DATA COUNTS")
        print("-" * 35)
        
        exam_sessions_graded = await self.db.exam_sessions.count_documents({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        })
        
        exams_count = await self.db.exams.count_documents({})
        teaching_assignments_count = await self.db.teaching_assignments.count_documents({})
        subjects_count = await self.db.subjects.count_documents({})
        
        print(f"✅ Graded exam sessions: {exam_sessions_graded}")
        print(f"📚 Total exams: {exams_count}")
        print(f"👨‍🏫 Teaching assignments: {teaching_assignments_count}")
        print(f"📖 Subjects: {subjects_count}")
        
        # Step 2: Check role-specific data access
        print(f"\n🔐 STEP 2: ROLE-SPECIFIC ACCESS CHECK ({user_roles[0] if user_roles else 'unknown'})")
        print("-" * 45)
        
        if "student" in user_roles:
            await self._debug_student_access(user_id)
        elif "teacher" in user_roles:
            await self._debug_teacher_access(user_id)
        elif "admin" in user_roles:
            await self._debug_admin_access()
        
        # Step 3: Test filter building
        print("\n🛠️ STEP 3: FILTER BUILDING TEST")
        print("-" * 32)
        
        request = SubjectMasteryRequest()
        filters = await subject_mastery_crud._build_role_based_filters(request, current_user)
        
        print(f"🔧 Generated filters: {filters}")
        
        # Test filter effectiveness
        filtered_sessions = await self.db.exam_sessions.count_documents(filters)
        print(f"📊 Sessions matching filters: {filtered_sessions}")
        
        if filtered_sessions == 0:
            print("❌ PROBLEM: Filters menghasilkan 0 sessions!")
            print("   Ini adalah root cause dari data kosong")
            await self._diagnose_filter_issues(filters, user_roles, user_id)
        
        # Step 4: Test aggregation pipeline
        print("\n⚙️ STEP 4: AGGREGATION PIPELINE TEST")
        print("-" * 37)
        
        if filtered_sessions > 0:
            await self._test_aggregation_pipeline(filters, current_user)
        else:
            print("⏩ Skipping aggregation test (no sessions match filters)")
        
        # Step 5: Test actual CRUD call
        print("\n🧪 STEP 5: ACTUAL CRUD CALL TEST")
        print("-" * 33)
        
        try:
            result = await subject_mastery_crud.get_subject_mastery_analytics(request, current_user)
            print(f"✅ CRUD call successful!")
            print(f"📄 Result type: {type(result).__name__}")
            
            if hasattr(result, 'entities'):
                print(f"📊 Entities count: {len(result.entities)}")
                if result.entities:
                    print("📋 First entity preview:")
                    entity = result.entities[0]
                    print(f"   - ID: {entity.entity_id}")
                    print(f"   - Type: {entity.entity_type}")
                    print(f"   - Name: {entity.entity_name}")
                    print(f"   - Subjects: {len(entity.mastery_data.subject_scores)}")
                    print(f"   - Overall avg: {entity.mastery_data.overall_average}")
            elif hasattr(result, 'entity_id'):
                print(f"📋 Single entity: {result.entity_name}")
                print(f"📊 Subjects: {len(result.mastery_data.subject_scores)}")
                print(f"📈 Overall avg: {result.mastery_data.overall_average}")
                print(f"🔢 Total exams: {result.mastery_data.total_exams}")
            
        except Exception as e:
            print(f"❌ CRUD call failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def _debug_student_access(self, user_id):
        """Debug student-specific access"""
        student_sessions = await self.db.exam_sessions.count_documents({
            "student_id": ObjectId(user_id),
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$ne": None}
        })
        
        print(f"👨‍🎓 Student's graded sessions: {student_sessions}")
        
        if student_sessions > 0:
            # Sample of student's sessions
            sample_sessions = await self.db.exam_sessions.find({
                "student_id": ObjectId(user_id),
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$ne": None}
            }).limit(3).to_list(length=3)
            
            print("📋 Sample student sessions:")
            for i, session in enumerate(sample_sessions, 1):
                print(f"   {i}. Score: {session.get('score', 'N/A')}, Status: {session.get('status')}")
                print(f"      Exam ID: {session.get('exam_id')}")
        else:
            print("❌ No sessions found for this student!")
            # Check if user_id exists in any session
            any_sessions = await self.db.exam_sessions.count_documents({
                "student_id": ObjectId(user_id)
            })
            print(f"   Total sessions for this student (any status): {any_sessions}")
    
    async def _debug_teacher_access(self, user_id):
        """Debug teacher-specific access"""
        teaching_assignments = await self.db.teaching_assignments.find({
            "teacher_id": ObjectId(user_id)
        }).to_list(length=None)
        
        print(f"👨‍🏫 Teacher's assignments: {len(teaching_assignments)}")
        
        if teaching_assignments:
            assignment_ids = [ta["_id"] for ta in teaching_assignments]
            
            # Get exams for these assignments
            teacher_exams = await self.db.exams.find({
                "teaching_assignment_id": {"$in": assignment_ids}
            }).to_list(length=None)
            
            print(f"📚 Teacher's exams: {len(teacher_exams)}")
            
            if teacher_exams:
                exam_ids = [exam["_id"] for exam in teacher_exams]
                
                # Get sessions for these exams
                related_sessions = await self.db.exam_sessions.count_documents({
                    "exam_id": {"$in": exam_ids},
                    "status": {"$in": ["submitted", "graded"]},
                    "score": {"$ne": None}
                })
                
                print(f"✅ Related graded sessions: {related_sessions}")
                
                # Sample sessions
                if related_sessions > 0:
                    sample_sessions = await self.db.exam_sessions.find({
                        "exam_id": {"$in": exam_ids},
                        "status": {"$in": ["submitted", "graded"]},
                        "score": {"$ne": None}
                    }).limit(3).to_list(length=3)
                    
                    print("📋 Sample sessions from teacher's exams:")
                    for i, session in enumerate(sample_sessions, 1):
                        print(f"   {i}. Score: {session.get('score', 'N/A')}, Status: {session.get('status')}")
                        print(f"      Student: {session.get('student_id')}, Exam: {session.get('exam_id')}")
            else:
                print("❌ No exams found for teacher's assignments!")
        else:
            print("❌ No teaching assignments for this teacher!")
    
    async def _debug_admin_access(self):
        """Debug admin-specific access (should see all data)"""
        total_sessions = await self.db.exam_sessions.count_documents({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$ne": None}
        })
        
        print(f"🔐 Admin can access all sessions: {total_sessions}")
        
        # Sample of all sessions
        if total_sessions > 0:
            sample_sessions = await self.db.exam_sessions.find({
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$ne": None}
            }).limit(5).to_list(length=5)
            
            print("📋 Sample sessions (admin view):")
            for i, session in enumerate(sample_sessions, 1):
                print(f"   {i}. Score: {session.get('score', 'N/A')}, Status: {session.get('status')}")
                print(f"      Student: {session.get('student_id')}, Exam: {session.get('exam_id')}")
    
    async def _diagnose_filter_issues(self, filters, user_roles, user_id):
        """Diagnose why filters are returning 0 results"""
        print("\n🔍 FILTER DIAGNOSIS:")
        print("   Testing each filter component individually...")
        
        # Test base filters
        base_count = await self.db.exam_sessions.count_documents({
            "status": {"$in": ["submitted", "graded"]},
            "score": {"$exists": True, "$ne": None, "$gte": 0}
        })
        print(f"   📊 Base filter (status + score): {base_count} sessions")
        
        # Test date filter if present
        if "submitted_at" in filters:
            date_filter = filters["submitted_at"]
            date_count = await self.db.exam_sessions.count_documents({
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$exists": True, "$ne": None, "$gte": 0},
                "submitted_at": date_filter
            })
            print(f"   📅 With date filter: {date_count} sessions")
            print(f"      Date range: {date_filter}")
            
            # Check if there are sessions outside this date range
            all_sessions = await self.db.exam_sessions.count_documents({
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$exists": True, "$ne": None, "$gte": 0}
            })
            
            if all_sessions > date_count:
                print(f"   ⚠️  {all_sessions - date_count} sessions are outside the date range!")
                print("      Try using start_date and end_date parameters to include older data")
        
        # Test role-specific filters
        if "student_id" in filters:
            student_count = await self.db.exam_sessions.count_documents({
                "student_id": filters["student_id"],
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$ne": None}
            })
            print(f"   👨‍🎓 Student filter: {student_count} sessions")
        
        if "exam_id" in filters and "$in" in filters["exam_id"]:
            exam_ids = filters["exam_id"]["$in"]
            exam_count = await self.db.exam_sessions.count_documents({
                "exam_id": {"$in": exam_ids},
                "status": {"$in": ["submitted", "graded"]},
                "score": {"$ne": None}
            })
            print(f"   📚 Exam IDs filter: {exam_count} sessions")
            print(f"      Checking {len(exam_ids)} exam IDs")
            
            if exam_count == 0 and exam_ids:
                print("   🔍 Let's check if these exam IDs have any sessions at all...")
                any_sessions = await self.db.exam_sessions.count_documents({
                    "exam_id": {"$in": exam_ids}
                })
                print(f"      Sessions with these exam IDs (any status): {any_sessions}")
    
    async def _test_aggregation_pipeline(self, filters, current_user):
        """Test the aggregation pipeline step by step"""
        user_roles = current_user.get("roles", [])
        
        print("🔄 Testing aggregation pipeline...")
        
        if "student" in user_roles:
            # Test student pipeline
            pipeline = [
                {"$match": filters},
                {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
                {"$unwind": "$exam"},
                {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment"}},
                {"$unwind": "$teaching_assignment"},
                {"$lookup": {"from": "subjects", "localField": "teaching_assignment.subject_id", "foreignField": "_id", "as": "subject"}},
                {"$unwind": "$subject"},
                {"$group": {
                    "_id": "$subject.name",
                    "avg_score": {"$avg": "$score"},
                    "exam_count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            cursor = self.db.exam_sessions.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            print(f"📊 Pipeline results: {len(results)} subjects")
            
            if results:
                print("📋 Subject breakdown:")
                for result in results[:5]:  # Show first 5
                    subject_name = result["_id"]
                    avg_score = round(result["avg_score"], 1)
                    exam_count = result["exam_count"]
                    print(f"   📖 {subject_name}: {avg_score} avg (from {exam_count} exams)")
            else:
                print("❌ Pipeline returned no results!")
                print("   Checking pipeline step by step...")
                await self._debug_pipeline_steps(filters)
    
    async def _debug_pipeline_steps(self, filters):
        """Debug each step of the aggregation pipeline"""
        print("\n🔍 PIPELINE STEP-BY-STEP DEBUG:")
        
        # Step 1: Match
        step1 = await self.db.exam_sessions.count_documents(filters)
        print(f"   1️⃣ Match: {step1} documents")
        
        if step1 == 0:
            print("   ❌ No documents match the initial filter!")
            return
        
        # Step 2: After exam lookup
        pipeline_step2 = [
            {"$match": filters},
            {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
            {"$match": {"exam": {"$ne": []}}}  # Only documents with exam data
        ]
        
        cursor2 = self.db.exam_sessions.aggregate([*pipeline_step2, {"$count": "count"}])
        result2 = await cursor2.to_list(length=1)
        step2_count = result2[0]["count"] if result2 else 0
        
        print(f"   2️⃣ After exam lookup: {step2_count} documents")
        
        if step2_count == 0:
            print("   ❌ No exams found for the exam_ids!")
            # Check if exam_ids exist
            sample_sessions = await self.db.exam_sessions.find(filters).limit(3).to_list(length=3)
            if sample_sessions:
                sample_exam_ids = [s.get("exam_id") for s in sample_sessions]
                print(f"   🔍 Sample exam IDs: {sample_exam_ids[:3]}")
                
                exam_exists = await self.db.exams.count_documents({"_id": {"$in": sample_exam_ids}})
                print(f"   📚 Exams exist for these IDs: {exam_exists}")
            return
        
        # Step 3: After teaching assignment lookup
        pipeline_step3 = [
            *pipeline_step2,
            {"$unwind": "$exam"},
            {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "teaching_assignment"}},
            {"$match": {"teaching_assignment": {"$ne": []}}}
        ]
        
        cursor3 = self.db.exam_sessions.aggregate([*pipeline_step3, {"$count": "count"}])
        result3 = await cursor3.to_list(length=1)
        step3_count = result3[0]["count"] if result3 else 0
        
        print(f"   3️⃣ After teaching assignment lookup: {step3_count} documents")
        
        if step3_count == 0:
            print("   ❌ No teaching assignments found!")
            print("   🔍 This is likely the root cause!")
            
            # Check what teaching_assignment_ids are in the exams
            sample_exams = await self.db.exams.find().limit(5).to_list(length=5)
            if sample_exams:
                ta_ids = [e.get("teaching_assignment_id") for e in sample_exams if e.get("teaching_assignment_id")]
                print(f"   📋 Sample teaching assignment IDs from exams: {ta_ids[:3]}")
                
                if ta_ids:
                    ta_exists = await self.db.teaching_assignments.count_documents({"_id": {"$in": ta_ids}})
                    print(f"   👨‍🏫 Teaching assignments exist: {ta_exists}")
            return
        
        # Step 4: After subject lookup
        pipeline_step4 = [
            *pipeline_step3,
            {"$unwind": "$teaching_assignment"},
            {"$lookup": {"from": "subjects", "localField": "teaching_assignment.subject_id", "foreignField": "_id", "as": "subject"}},
            {"$match": {"subject": {"$ne": []}}}
        ]
        
        cursor4 = self.db.exam_sessions.aggregate([*pipeline_step4, {"$count": "count"}])
        result4 = await cursor4.to_list(length=1)
        step4_count = result4[0]["count"] if result4 else 0
        
        print(f"   4️⃣ After subject lookup: {step4_count} documents")
        
        if step4_count == 0:
            print("   ❌ No subjects found for teaching assignments!")
        else:
            print(f"   ✅ Pipeline should produce results!")

# Main test function
async def run_debug_test():
    """Run the debug test"""
    
    print("🚀 Starting Subject Mastery Analytics Debug Test...")
    
    # Setup debugger
    debugger = SubjectMasteryDebugger()
    await debugger.setup()
    
    # Test different user roles
    test_users = [
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),  # Replace with real user ID
            "roles": ["student"]
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439012"),  # Replace with real teacher ID
            "roles": ["teacher"]
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439013"),  # Replace with real admin ID
            "roles": ["admin"]
        }
    ]
    
    # Or get from command line arguments
    if len(sys.argv) >= 3:
        user_id = sys.argv[1]
        role = sys.argv[2]
        test_users = [{
            "_id": ObjectId(user_id),
            "roles": [role]
        }]
        print(f"🎯 Testing with specific user: {user_id} ({role})")
    else:
        print("💡 Usage: python test_subject_mastery_debug.py USER_ID ROLE")
        print("   Example: python test_subject_mastery_debug.py 507f1f77bcf86cd799439011 student")
        print("\n🔄 Running with default test user IDs...")
    
    for i, user in enumerate(test_users):
        try:
            print(f"\n{'='*60}")
            print(f"TEST #{i+1}: USER ROLE = {user['roles'][0].upper()}")
            print(f"{'='*60}")
            
            await debugger.debug_step_by_step(user)
            
        except Exception as e:
            print(f"❌ Error testing user {user['_id']}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Debug test completed!")

if __name__ == "__main__":
    # Ensure we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: Please run this script from the project root directory")
        print("   Current directory should contain 'app' folder")
        sys.exit(1)
    
    asyncio.run(run_debug_test())
