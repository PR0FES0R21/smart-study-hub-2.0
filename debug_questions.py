#!/usr/bin/env python3
"""
Debug script untuk memeriksa questions database
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def debug_questions():
    # Koneksi ke MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.smart_study_hub
    
    # Question IDs dari exam session
    question_ids = [
        "6888b18eda5b866b5af5a28b",
        "6888b1d8da5b866b5af5a291", 
        "6888bbb0da5b866b5af5a294",
        "688ba311c97c3d98965af418",
        "688c844bfcc1873a29ed958a"
    ]
    
    print("=== CHECKING QUESTIONS DATABASE ===\n")
    
    # Check if questions collection exists and has data
    questions_count = await db.questions.count_documents({})
    print(f"Total questions in database: {questions_count}")
    
    if questions_count == 0:
        print("❌ Questions collection is empty!")
        return
    
    # Sample some questions to see structure
    sample_questions = await db.questions.find({}).limit(3).to_list(length=3)
    print(f"\nSample question structure:")
    for q in sample_questions:
        print(f"  ID: {q['_id']}")
        print(f"  Type: {q.get('type', 'N/A')}")
        print(f"  Text: {q.get('question_text', 'N/A')[:50]}...")
        print()
    
    print("=== CHECKING SPECIFIC QUESTION IDS ===\n")
    
    # Check each question ID from the exam
    for question_id in question_ids:
        try:
            question = await db.questions.find_one({"_id": ObjectId(question_id)})
            if question:
                print(f"✅ {question_id}: FOUND")
                print(f"   Type: {question.get('type', 'N/A')}")
                print(f"   Text: {question.get('question_text', 'N/A')[:50]}...")
            else:
                print(f"❌ {question_id}: NOT FOUND")
        except Exception as e:
            print(f"💥 {question_id}: ERROR - {e}")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(debug_questions())
