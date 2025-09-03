# ==============================================================================
# File: test_analytics_debug.py
# Deskripsi: Debug test untuk exam analytics tanpa pytest
# ==============================================================================

import asyncio
import traceback
from datetime import datetime, timedelta
from bson import ObjectId

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_real_database_issue():
    """Test with real database to reproduce the teacher_id error"""
    print("🔍 Testing Real Database Issue...")
    
    from app.crud.exam_analytics import exam_analytics_crud
    from app.core.db import db
    
    # Let's first check what actual exam session looks like
    session_id = "68b73495b09dfc3016243c46"  # The failing session ID from your error
    
    try:
        # Get the actual exam session data from database
        exam_session = await db.exam_sessions.find_one({"_id": ObjectId(session_id)})
        
        if not exam_session:
            print(f"❌ Exam session {session_id} not found in database")
            return
        
        print(f"✅ Found exam session: {session_id}")
        print(f"   - Exam ID: {exam_session.get('exam_id')}")
        print(f"   - Student ID: {exam_session.get('student_id')}")
        print(f"   - Status: {exam_session.get('status')}")
        
        # Now get the exam data
        exam = await db.exams.find_one({"_id": exam_session["exam_id"]})
        
        if not exam:
            print(f"❌ Exam {exam_session['exam_id']} not found in database")
            return
        
        print(f"✅ Found exam: {exam.get('title')}")
        print(f"   - Has teacher_id: {'teacher_id' in exam}")
        
        if 'teacher_id' not in exam:
            print("❌ FOUND THE ISSUE: exam data is missing 'teacher_id' field!")
            print("   Available fields in exam:")
            for key in exam.keys():
                print(f"     - {key}: {type(exam[key])}")
        else:
            print(f"   - Teacher ID: {exam.get('teacher_id')}")
            
            # Check if teacher exists
            teacher = await db.users.find_one({"_id": exam["teacher_id"]})
            if teacher:
                print(f"   - Teacher: {teacher.get('first_name')} {teacher.get('last_name')}")
            else:
                print(f"❌ Teacher {exam['teacher_id']} not found in database")
        
        # Try to generate analytics and catch specific error
        print("\n🧪 Trying to generate analytics...")
        
        try:
            analytics = await exam_analytics_crud.generate_exam_analytics(session_id)
            print("✅ Analytics generated successfully!")
            
        except KeyError as e:
            print(f"❌ KeyError caught: {e}")
            print("   This confirms the missing field issue")
            
        except Exception as e:
            print(f"❌ Other error: {type(e).__name__}: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        traceback.print_exc()

async def test_exam_structure_requirements():
    """Test what fields are required in exam document"""
    print("\n📋 Testing Exam Structure Requirements...")
    
    from app.core.db import db
    
    # Sample recent exams to see structure
    recent_exams = await db.exams.find().limit(5).to_list(length=None)
    
    print(f"Found {len(recent_exams)} recent exams:")
    
    for i, exam in enumerate(recent_exams, 1):
        print(f"\n📄 Exam {i}: {exam.get('title', 'Untitled')}")
        
        required_fields = ['teacher_id', 'subject_id', 'class_id', 'title', 'duration', 'questions']
        missing_fields = []
        
        for field in required_fields:
            if field in exam:
                print(f"   ✅ {field}: {type(exam[field])}")
            else:
                print(f"   ❌ {field}: MISSING")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ⚠️ Missing required fields: {missing_fields}")
        else:
            print(f"   ✅ All required fields present")

async def test_session_structure():
    """Test exam session structure"""
    print("\n📋 Testing Exam Session Structure...")
    
    from app.core.db import db
    
    # Get the failing session specifically
    session_id = "68b73495b09dfc3016243c46"
    
    try:
        session = await db.exam_sessions.find_one({"_id": ObjectId(session_id)})
        
        if session:
            print(f"✅ Session found: {session_id}")
            
            required_fields = ['exam_id', 'student_id', 'started_at', 'submitted_at', 'status', 'answers']
            
            for field in required_fields:
                if field in session:
                    value = session[field]
                    if field in ['started_at', 'submitted_at']:
                        print(f"   ✅ {field}: {value} ({type(value)})")
                    elif field == 'answers':
                        print(f"   ✅ {field}: {len(value) if value else 0} answers")
                    else:
                        print(f"   ✅ {field}: {value}")
                else:
                    print(f"   ❌ {field}: MISSING")
                    
            # Check violations
            violations = session.get('violations', [])
            print(f"   📊 Violations: {len(violations)}")
            
            # Check score
            score = session.get('score', 'Not set')
            print(f"   📊 Score: {score}")
            
        else:
            print(f"❌ Session {session_id} not found")
            
    except Exception as e:
        print(f"❌ Error checking session: {e}")

async def debug_analytics_generation_step_by_step():
    """Debug each step of analytics generation"""
    print("\n🔧 Step-by-step Analytics Debug...")
    
    from app.crud.exam_analytics import exam_analytics_crud
    from app.core.db import db
    
    session_id = "68b73495b09dfc3016243c46"
    
    try:
        print("Step 1: Get exam session...")
        exam_session = await db.exam_sessions.find_one({"_id": ObjectId(session_id)})
        if not exam_session:
            print("❌ No exam session found")
            return
        print("✅ Exam session found")
        
        print("Step 2: Get exam...")
        exam = await db.exams.find_one({"_id": exam_session["exam_id"]})
        if not exam:
            print("❌ No exam found")
            return
        print("✅ Exam found")
        
        print("Step 3: Check teacher_id...")
        if 'teacher_id' not in exam:
            print("❌ teacher_id missing from exam!")
            print("Available fields:")
            for key in exam.keys():
                print(f"   - {key}")
            
            # Let's check if it's in a different field name
            potential_teacher_fields = [k for k in exam.keys() if 'teacher' in k.lower()]
            if potential_teacher_fields:
                print(f"Potential teacher fields: {potential_teacher_fields}")
            
            return
        print("✅ teacher_id present")
        
        print("Step 4: Get teacher...")
        teacher = await db.users.find_one({"_id": exam["teacher_id"]})
        if not teacher:
            print("❌ Teacher not found")
            return
        print(f"✅ Teacher found: {teacher.get('first_name')} {teacher.get('last_name')}")
        
        print("Step 5: Get student...")
        student = await db.users.find_one({"_id": exam_session["student_id"]})
        if not student:
            print("❌ Student not found")
            return
        print(f"✅ Student found: {student.get('first_name')} {student.get('last_name')}")
        
        print("Step 6: Get subject...")
        subject = await db.subjects.find_one({"_id": exam["subject_id"]})
        print(f"Subject: {'Found' if subject else 'Not found'}")
        
        print("Step 7: Get class...")
        class_info = await db.classes.find_one({"_id": exam["class_id"]})
        print(f"Class: {'Found' if class_info else 'Not found'}")
        
        print("Step 8: Try basic analytics generation...")
        
        # Try just performance metrics first
        performance = await exam_analytics_crud._generate_performance_metrics(exam_session, exam)
        print(f"✅ Performance metrics: {performance.score}")
        
        print("All steps completed successfully!")
        
    except Exception as e:
        print(f"❌ Error at step: {type(e).__name__}: {e}")
        traceback.print_exc()

async def main():
    """Main debug function"""
    print("🔍 DEBUGGING EXAM ANALYTICS ERRORS")
    print("=" * 60)
    
    await test_real_database_issue()
    await test_exam_structure_requirements() 
    await test_session_structure()
    await debug_analytics_generation_step_by_step()
    
    print("\n" + "=" * 60)
    print("🎯 Debug completed!")

if __name__ == "__main__":
    asyncio.run(main())
