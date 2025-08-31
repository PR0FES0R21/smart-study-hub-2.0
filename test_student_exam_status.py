#!/usr/bin/env python3
"""
Test script untuk memverifikasi endpoint /student dengan computed_status
yang mempertimbangkan exam session.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.crud.crud_exams import get_exams_by_student
from bson import ObjectId

async def test_student_exam_status():
    """Test fungsi get_exams_by_student dengan computed_status"""
    
    # Connect to database
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        print("Testing student exam status computation...")
        
        # Ambil sample student profile (coba beberapa cara)
        student_profile = await db["profiles"].find_one({"role": "student"})
        if not student_profile:
            # Coba cari profile yang memiliki class_id (kemungkinan siswa)
            student_profile = await db["profiles"].find_one({"class_id": {"$exists": True, "$ne": None}})
        
        if not student_profile:
            # Coba ambil profile pertama yang ada
            student_profile = await db["profiles"].find_one({})
            if student_profile:
                print("WARNING: Using first available profile (may not be student)")
            else:
                print("ERROR: No profiles found in database")
                return
            
        print(f"SUCCESS: Found student profile: {student_profile.get('full_name', 'Unknown')}")
        print(f"   Class ID: {student_profile.get('class_id')}")
        print(f"   User ID: {student_profile.get('user_id')}")
        
        # Test fungsi get_exams_by_student
        result = await get_exams_by_student(
            db=db,
            student_profile=student_profile,
            academic_period_id=None,  # Use current period
            status=None,  # Get all statuses
            skip=0,
            limit=5
        )
        
        print(f"\nResults:")
        print(f"   Total items: {result['total_items']}")
        print(f"   Data count: {len(result['data'])}")
        
        # Analyze each exam
        for i, exam in enumerate(result['data'], 1):
            print(f"\nExam {i}:")
            print(f"   Title: {exam.get('title', 'Unknown')}")
            print(f"   Original Status: {exam.get('status', 'Unknown')}")
            print(f"   Computed Status: {exam.get('computed_status', 'Not set')}")
            print(f"   Has Session Data: {'Yes' if exam.get('exam_session_data') else 'No'}")
            
            if exam.get('exam_session_data'):
                session = exam['exam_session_data']
                print(f"   Session Status: {session.get('status', 'Unknown')}")
                print(f"   Session Score: {session.get('score', 'Not graded')}")
                print(f"   Started At: {session.get('started_at', 'Unknown')}")
        
        # Test dengan filter status
        print(f"\nTesting with status filter 'completed'...")
        completed_result = await get_exams_by_student(
            db=db,
            student_profile=student_profile,
            academic_period_id=None,
            status="completed",
            skip=0,
            limit=5
        )
        
        print(f"   Completed exams: {completed_result['total_items']}")
        
        print(f"\nTesting with status filter 'ready'...")
        ready_result = await get_exams_by_student(
            db=db,
            student_profile=student_profile,
            academic_period_id=None,
            status="ready",
            skip=0,
            limit=5
        )
        
        print(f"   Ready exams: {ready_result['total_items']}")
        
        print(f"\nSUCCESS: Test completed successfully!")
        
    except Exception as e:
        print(f"ERROR: Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_student_exam_status())