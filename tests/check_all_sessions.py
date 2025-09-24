#!/usr/bin/env python3
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

async def main():
    print("=== Check All Sessions ===")
    
    # Connect to database
    mongo_url = getattr(settings, 'MONGO_URL', 'mongodb://localhost:27017')
    db_name = getattr(settings, 'MONGO_DB', 'smart_study_hub')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("1. Checking all collections...")
    collections = await db.list_collection_names()
    print(f"   Available collections: {collections}")
    
    if 'exam_sessions' in collections:
        print("2. Checking exam_sessions collection...")
        
        # Get total count
        total_count = await db.exam_sessions.count_documents({})
        print(f"   Total exam sessions: {total_count}")
        
        if total_count > 0:
            print("3. Sample sessions (any status):")
            
            sample_sessions = await db.exam_sessions.find({}).limit(5).to_list(length=5)
            
            for i, session in enumerate(sample_sessions, 1):
                session_id = str(session.get("_id"))
                exam_id = str(session.get("exam_id", "No exam"))
                score = session.get("score", "No score")
                status = session.get("status", "No status")
                student_id = str(session.get("student_id", "No student"))
                
                print(f"   Session {i}: {session_id}")
                print(f"      Exam: {exam_id}")
                print(f"      Score: {score}")
                print(f"      Status: {status}")
                print(f"      Student: {student_id}")
                print()
        else:
            print("   No exam sessions found in database!")
    else:
        print("2. exam_sessions collection not found!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
