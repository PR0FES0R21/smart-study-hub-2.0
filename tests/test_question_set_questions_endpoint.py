#!/usr/bin/env python3
"""
Test script for the new question set questions endpoint
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.crud.crud_question_sets import get_question_set_questions
from app.core.config import settings

async def test_question_set_questions():
    """Test the new get_question_set_questions function"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Find a question set with questions
        question_set = await db["question_sets"].find_one({
            "question_ids": {"$exists": True, "$ne": []}
        })
        
        if not question_set:
            print("❌ No question sets with questions found in database")
            return
        
        question_set_id = question_set["_id"]
        creator_id = question_set["created_by_coordinator_id"]
        
        print(f"🧪 Testing with question set: {question_set['name']}")
        print(f"📝 Question set ID: {question_set_id}")
        print(f"👤 Creator ID: {creator_id}")
        print(f"📊 Expected questions: {len(question_set.get('question_ids', []))}")
        
        # Test the function
        result = await get_question_set_questions(
            db=db,
            question_set_id=question_set_id,
            user_id=creator_id  # Use creator as user (should have access)
        )
        
        if result:
            print("✅ Function executed successfully!")
            print(f"📋 Question set name: {result['question_set_name']}")
            print(f"🔢 Total questions returned: {result['total_questions']}")
            print(f"📝 Question IDs length: {len(result['question_ids'])}")
            
            # Show question IDs
            if result['question_ids']:
                print(f"🎯 Question IDs:")
                for i, qid in enumerate(result['question_ids'][:5]):  # Show first 5
                    print(f"   {i+1}. {qid}")
                if len(result['question_ids']) > 5:
                    print(f"   ... and {len(result['question_ids']) - 5} more")
            
            print("✅ Test completed successfully!")
        else:
            print("❌ Function returned None")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

async def test_access_control():
    """Test access control for the endpoint"""
    
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Find a private question set
        question_set = await db["question_sets"].find_one({
            "is_public": False,
            "question_ids": {"$exists": True, "$ne": []}
        })
        
        if not question_set:
            print("❌ No private question sets found for access control test")
            return
        
        # Find a different user (not the creator)
        different_user = await db["users"].find_one({
            "_id": {"$ne": question_set["created_by_coordinator_id"]},
            "roles": {"$in": ["teacher", "coordinator"]}
        })
        
        if not different_user:
            print("❌ No different user found for access control test")
            return
        
        print(f"🔒 Testing access control with different user")
        print(f"📝 Question set: {question_set['name']}")
        print(f"👤 Different user ID: {different_user['_id']}")
        
        # This should raise an access denied error
        try:
            result = await get_question_set_questions(
                db=db,
                question_set_id=question_set["_id"],
                user_id=different_user["_id"]
            )
            print("❌ Access control failed - should have been denied")
        except Exception as e:
            if "Access denied" in str(e) or "403" in str(e):
                print("✅ Access control working correctly - access denied as expected")
            else:
                print(f"❌ Unexpected error: {str(e)}")
    
    except Exception as e:
        print(f"❌ Error during access control test: {str(e)}")
    
    finally:
        client.close()

async def main():
    """Run all tests"""
    print("🚀 Starting question set questions endpoint tests...\n")
    
    print("=" * 60)
    print("TEST 1: Basic functionality")
    print("=" * 60)
    await test_question_set_questions()
    
    print("\n" + "=" * 60)
    print("TEST 2: Access control")
    print("=" * 60)
    await test_access_control()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())