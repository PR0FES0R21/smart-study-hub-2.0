#!/usr/bin/env python3
"""
Debug script untuk memeriksa data exam session yang bermasalah
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json
from datetime import datetime

async def debug_exam_session():
    # Koneksi ke MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.smart_study_hub
    
    # ID session yang bermasalah
    session_id = "68b73495b09dfc3016243c46"
    
    try:
        print("=== FINDING AVAILABLE EXAM SESSIONS ===\n")
        
        # Cari exam sessions yang ada
        available_sessions = await db.exam_sessions.find({}).limit(5).to_list(length=5)
        
        if not available_sessions:
            print("❌ Tidak ada exam sessions di database!")
            return
        
        print(f"Ditemukan {len(available_sessions)} exam sessions:")
        for idx, session in enumerate(available_sessions):
            print(f"  {idx+1}. {session['_id']} - Status: {session.get('status', 'N/A')}")
        
        # Gunakan session pertama yang ada
        session_id = str(available_sessions[0]['_id'])
        
        print(f"\n=== DEBUGGING EXAM SESSION {session_id} ===\n")
        
        exam_session = await db.exam_sessions.find_one({"_id": ObjectId(session_id)})
        
        if not exam_session:
            print(f"❌ Exam session {session_id} tidak ditemukan!")
            return
            
        print("✅ Exam session ditemukan!")
        print(f"Exam ID: {exam_session.get('exam_id', 'N/A')}")
        print(f"Student ID: {exam_session.get('student_id', 'N/A')}")
        print(f"Status: {exam_session.get('status', 'N/A')}")
        print(f"Started at: {exam_session.get('started_at', 'N/A')}")
        print(f"Submitted at: {exam_session.get('submitted_at', 'N/A')}")
        
        # Cek tipe data answers
        answers = exam_session.get('answers', [])
        print(f"\nAnswers type: {type(answers)}")
        print(f"Answers count: {len(answers) if isinstance(answers, list) else 'Not a list'}")
        
        if isinstance(answers, list) and answers:
            print("First answer structure:")
            first_answer = answers[0]
            print(f"  Type: {type(first_answer)}")
            if isinstance(first_answer, dict):
                print(f"  Keys: {list(first_answer.keys())}")
            else:
                print(f"  Content: {first_answer}")
        
        # Cek tipe data violations
        violations = exam_session.get('violations', [])
        print(f"\nViolations type: {type(violations)}")
        print(f"Violations count: {len(violations) if isinstance(violations, list) else 'Not a list'}")
        
        if isinstance(violations, list) and violations:
            print("First violation structure:")
            first_violation = violations[0]
            print(f"  Type: {type(first_violation)}")
            if isinstance(first_violation, dict):
                print(f"  Keys: {list(first_violation.keys())}")
            else:
                print(f"  Content: {first_violation}")
        
        # Cek exam terkait
        print("\n=== CHECKING RELATED EXAM ===")
        exam = await db.exams.find_one({"_id": exam_session["exam_id"]})
        if exam:
            print("✅ Exam ditemukan!")
            print(f"Title: {exam.get('title', 'N/A')}")
            print(f"Type: {exam.get('exam_type', 'N/A')}")
            print(f"Duration: {exam.get('duration', exam.get('duration_minutes', 'N/A'))}")
            
            # Check question structure
            if "questions" in exam:
                questions = exam.get("questions", [])
                print(f"Questions (embedded): {len(questions) if isinstance(questions, list) else 'Not a list'}")
            elif "question_ids" in exam:
                question_ids = exam.get("question_ids", [])
                print(f"Question IDs: {len(question_ids) if isinstance(question_ids, list) else 'Not a list'}")
        else:
            print("❌ Exam tidak ditemukan!")
        
        # Cek student terkait
        print("\n=== CHECKING RELATED STUDENT ===")
        student = await db.users.find_one({"_id": exam_session["student_id"]})
        if student:
            print("✅ Student ditemukan!")
            print(f"Name: {student.get('first_name', '')} {student.get('last_name', '')}")
        else:
            print("❌ Student tidak ditemukan!")
        
        # Cek apakah ada analytics yang sudah ada
        print("\n=== CHECKING EXISTING ANALYTICS ===")
        existing_analytics = await db.exam_analytics.find_one({"exam_session_id": ObjectId(session_id)})
        if existing_analytics:
            print("✅ Analytics sudah ada di database!")
            print(f"Generated at: {existing_analytics.get('generated_at', 'N/A')}")
            print(f"Cache expires at: {existing_analytics.get('cache_expires_at', 'N/A')}")
            
            # Check structure of analytics
            perf_metrics = existing_analytics.get('performance_metrics')
            print(f"Performance metrics type: {type(perf_metrics)}")
            
            class_comp = existing_analytics.get('class_comparison')
            print(f"Class comparison type: {type(class_comp)}")
            
            violation_anal = existing_analytics.get('violation_analytics')
            print(f"Violation analytics type: {type(violation_anal)}")
            
        else:
            print("❌ Belum ada analytics di database")
    
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_exam_session())
