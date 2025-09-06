#!/usr/bin/env python3
"""
Debug script untuk melihat data exam dan session secara detail
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

async def debug_exam_sessions():
    """Debug exam sessions untuk melihat data detail"""
    print("=== Debug Exam Sessions Data ===")
    
    try:
        # Connect to database
        mongo_url = getattr(settings, 'MONGO_URL', 'mongodb://localhost:27017')
        db_name = getattr(settings, 'MONGO_DB', 'smart_study_hub')
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test session ID dari user
        session_id = ObjectId("68bb1b93b39c2a464c1819c4")
        
        print(f"\\n1. Getting session data for: {session_id}")
        
        # Get the specific session
        current_session = await db.exam_sessions.find_one({"_id": session_id})
        
        if not current_session:
            print("❌ Session not found!")
            return False
        
        print(f"✅ Session found:")
        print(f"   📊 Student ID: {current_session.get('student_id')}")
        print(f"   📊 Exam ID: {current_session.get('exam_id')}")
        print(f"   📊 Score: {current_session.get('score')}")
        print(f"   📊 Status: {current_session.get('status')}")
        
        exam_id = current_session.get('exam_id')
        
        print(f"\n2. Finding ALL sessions for exam: {exam_id}")
        
        # Get ALL sessions for this exam (any status)
        all_sessions = await db.exam_sessions.find({
            "exam_id": exam_id
        }).to_list(length=None)
        
        print(f"\n   📊 Found {len(all_sessions)} total sessions:")
        
        for i, session in enumerate(all_sessions, 1):
            score = session.get("score")
            status = session.get("status")
            student_id = session.get("student_id")
            session_id_str = str(session.get("_id"))
            
            # Mark current session
            marker = " <- CURRENT" if session_id_str == "68bb1b93b39c2a464c1819c4" else ""
            
            print(f"   Session {i}: ID={session_id_str}, Student={student_id}, Score={score}, Status={status}{marker}")
        
        print(f"\n3. Finding SUBMITTED/GRADED sessions for exam: {exam_id}")
        
        # Get submitted/graded sessions for this exam
        valid_sessions = await db.exam_sessions.find({
            "exam_id": exam_id,
            "status": {"$in": ["submitted", "graded"]}
        }).to_list(length=None)
        
        print(f"\n   📊 Found {len(valid_sessions)} submitted/graded sessions:")
        
        scores = []
        for i, session in enumerate(valid_sessions, 1):
            score = session.get("score")
            status = session.get("status")
            student_id = session.get("student_id")
            session_id_str = str(session.get("_id"))
            
            if score is not None:
                scores.append(score)
            
            marker = " <- CURRENT" if session_id_str == "68bb1b93b39c2a464c1819c4" else ""
            
            print(f"   Session {i}: ID={session_id_str}, Student={student_id}, Score={score}, Status={status}{marker}")
        
        # Manual calculation
        if scores:
            manual_avg = sum(scores) / len(scores)
            print(f"\n4. Manual Calculation:")
            print(f"   📊 Valid Scores: {scores}")
            print(f"   📊 Count: {len(scores)}")
            print(f"   📊 Average: {manual_avg:.2f}")
            print(f"   📊 Highest: {max(scores):.2f}")
            print(f"   📊 Lowest: {min(scores):.2f}")
            
            # Check if scores are actually different
            unique_scores = set(scores)
            print(f"   📊 Unique Scores: {list(unique_scores)}")
            
            if len(unique_scores) == 1:
                print("   ℹ️  All students have the same score - this explains why avg = individual score")
            else:
                print(f"   ✅ Students have different scores - avg should be different from individual")
        else:
            print(f"\n4. ❌ No valid scores found!")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
