#!/usr/bin/env python3
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

async def main():
    print("=== Simple Debug ===")
    
    # Connect to database
    mongo_url = getattr(settings, 'MONGO_URL', 'mongodb://localhost:27017')
    db_name = getattr(settings, 'MONGO_DB', 'smart_study_hub')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Test session ID dari user
    session_id = ObjectId("68bb1b93b39c2a464c1819c4")
    
    print(f"1. Getting session data for: {session_id}")
    
    # Get the specific session
    current_session = await db.exam_sessions.find_one({"_id": session_id})
    
    if not current_session:
        print("Session not found!")
        return
    
    print(f"Session found:")
    print(f"   Student ID: {current_session.get('student_id')}")
    print(f"   Exam ID: {current_session.get('exam_id')}")
    print(f"   Score: {current_session.get('score')}")
    print(f"   Status: {current_session.get('status')}")
    
    exam_id = current_session.get('exam_id')
    
    print(f"2. Finding ALL sessions for exam: {exam_id}")
    
    # Get ALL sessions for this exam
    all_sessions = await db.exam_sessions.find({
        "exam_id": exam_id
    }).to_list(length=None)
    
    print(f"   Found {len(all_sessions)} total sessions:")
    
    for i, session in enumerate(all_sessions, 1):
        score = session.get("score")
        status = session.get("status")
        student_id = session.get("student_id")
        session_id_str = str(session.get("_id"))
        
        marker = " <- CURRENT" if session_id_str == "68bb1b93b39c2a464c1819c4" else ""
        
        print(f"   Session {i}: Score={score}, Status={status}, Student={student_id}{marker}")
    
    print(f"3. Finding SUBMITTED/GRADED sessions:")
    
    # Get submitted/graded sessions
    valid_sessions = await db.exam_sessions.find({
        "exam_id": exam_id,
        "status": {"$in": ["submitted", "graded"]}
    }).to_list(length=None)
    
    print(f"   Found {len(valid_sessions)} valid sessions:")
    
    scores = []
    for i, session in enumerate(valid_sessions, 1):
        score = session.get("score")
        status = session.get("status")
        
        if score is not None:
            scores.append(score)
        
        marker = " <- CURRENT" if str(session.get("_id")) == "68bb1b93b39c2a464c1819c4" else ""
        print(f"   Session {i}: Score={score}, Status={status}{marker}")
    
    # Manual calculation
    if scores:
        manual_avg = sum(scores) / len(scores)
        print(f"4. Manual Calculation:")
        print(f"   Valid Scores: {scores}")
        print(f"   Count: {len(scores)}")
        print(f"   Average: {manual_avg:.2f}")
        print(f"   Highest: {max(scores):.2f}")
        print(f"   Lowest: {min(scores):.2f}")
    else:
        print(f"4. No valid scores found!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
