#!/usr/bin/env python3
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

async def main():
    print("=== Find Existing Sessions ===")
    
    # Connect to database
    mongo_url = getattr(settings, 'MONGO_URL', 'mongodb://localhost:27017')
    db_name = getattr(settings, 'MONGO_DB', 'smart_study_hub')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("1. Finding recent submitted/graded exam sessions...")
    
    # Get recent submitted/graded sessions
    recent_sessions = await db.exam_sessions.find({
        "status": {"$in": ["submitted", "graded"]},
        "score": {"$ne": None}
    }).sort("submitted_at", -1).limit(10).to_list(length=10)
    
    print(f"   Found {len(recent_sessions)} recent sessions:")
    
    exam_groups = {}
    
    for i, session in enumerate(recent_sessions, 1):
        session_id = str(session.get("_id"))
        exam_id = str(session.get("exam_id"))
        score = session.get("score")
        status = session.get("status")
        student_id = str(session.get("student_id"))
        submitted_at = session.get("submitted_at", "No date")
        
        print(f"   Session {i}: ID={session_id}")
        print(f"      Exam ID: {exam_id}")
        print(f"      Score: {score}")
        print(f"      Status: {status}")
        print(f"      Student: {student_id}")
        print(f"      Submitted: {submitted_at}")
        print()
        
        # Group by exam_id
        if exam_id not in exam_groups:
            exam_groups[exam_id] = []
        exam_groups[exam_id].append(session)
    
    print("2. Exams with multiple students:")
    
    multi_student_exams = {k: v for k, v in exam_groups.items() if len(v) > 1}
    
    for exam_id, sessions in multi_student_exams.items():
        print(f"   Exam {exam_id}: {len(sessions)} sessions")
        for session in sessions:
            print(f"      Session {session['_id']}: Score={session.get('score')}, Student={session.get('student_id')}")
        print()
    
    if multi_student_exams:
        # Test with first multi-student exam
        test_exam_id, test_sessions = list(multi_student_exams.items())[0]
        test_session_id = str(test_sessions[0]["_id"])
        
        print(f"3. Suggested test session ID: {test_session_id}")
        print(f"   This session belongs to exam {test_exam_id} with {len(test_sessions)} participants")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
