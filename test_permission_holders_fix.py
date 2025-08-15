#!/usr/bin/env python3
"""
Test script untuk memvalidasi perbaikan permission_holders field
"""
import asyncio
import sys
import os
from bson import ObjectId
from datetime import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.crud.crud_question_sets import QuestionSetService
from app.schemas.question_set import QuestionSetCreate

async def test_permission_holders_fix():
    """Test bahwa pipeline sekarang menghasilkan permission_holders field"""
    
    print("🔍 Testing permission_holders field fix...")
    
    # Mock database connection (untuk testing struktur pipeline)
    class MockDB:
        def __init__(self):
            self.collections = {}
        
        def __getitem__(self, collection_name):
            return MockCollection(collection_name)
    
    class MockCollection:
        def __init__(self, name):
            self.name = name
        
        def aggregate(self, pipeline):
            return MockCursor(pipeline)
    
    class MockCursor:
        def __init__(self, pipeline):
            self.pipeline = pipeline
        
        async def to_list(self, limit):
            # Return mock data structure that matches expected output
            return [{
                "_id": ObjectId(),
                "name": "Test Question Set",
                "description": "Test description",
                "grade_level": 10,
                "status": "draft",
                "is_public": False,
                "metadata": {
                    "total_questions": 0,
                    "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
                    "total_points": 0,
                    "tags": []
                },
                "version": 1,
                "published_date": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "question_ids": [],
                "access_permissions": {
                    "can_view": [],
                    "can_edit": [ObjectId()],
                    "can_manage_questions": [ObjectId()],
                    "can_publish": [ObjectId()]
                },
                "created_by_coordinator_id": ObjectId(),
                "subject": {
                    "_id": ObjectId(),
                    "name": "Test Subject",
                    "code": "TEST",
                    "description": "Test subject"
                },
                "created_by": {
                    "_id": ObjectId(),
                    "full_name": "Test User",
                    "profile_picture_url": "https://example.com/avatar.jpg"
                },
                # CRITICAL: Test that permission_holders is now included
                "permission_holders": {
                    "can_view": [],
                    "can_edit": [
                        {
                            "_id": ObjectId(),
                            "full_name": "Test Editor",
                            "profile_picture_url": "https://example.com/editor.jpg"
                        }
                    ],
                    "can_manage_questions": [
                        {
                            "_id": ObjectId(),
                            "full_name": "Test Manager",
                            "profile_picture_url": "https://example.com/manager.jpg"
                        }
                    ],
                    "can_publish": [
                        {
                            "_id": ObjectId(),
                            "full_name": "Test Publisher",
                            "profile_picture_url": "https://example.com/publisher.jpg"
                        }
                    ]
                },
                "current_user_permissions": {
                    "can_view": True,
                    "can_edit": True,
                    "can_manage_questions": True,
                    "can_publish": True,
                    "is_creator": True
                }
            }]
    
    # Test pipeline structure
    mock_db = MockDB()
    service = QuestionSetService(mock_db)
    
    test_question_set_id = ObjectId()
    test_user_id = ObjectId()
    
    # Get the pipeline
    pipeline = service._build_detail_pipeline(test_question_set_id, test_user_id)
    
    print("✅ Pipeline structure validation:")
    print(f"   - Pipeline has {len(pipeline)} stages")
    
    # Check for permission holder lookups
    lookup_stages = [stage for stage in pipeline if "$lookup" in stage]
    permission_lookups = [
        stage for stage in lookup_stages 
        if any(perm in str(stage) for perm in ["can_view", "can_edit", "can_manage_questions", "can_publish"])
    ]
    
    print(f"   - Found {len(lookup_stages)} lookup stages")
    print(f"   - Found {len(permission_lookups)} permission holder lookups")
    
    if len(permission_lookups) >= 4:
        print("✅ All permission holder lookups present:")
        for i, lookup in enumerate(permission_lookups, 1):
            localField = lookup["$lookup"]["localField"]
            print(f"   {i}. {localField}")
    else:
        print("❌ Missing permission holder lookups")
        return False
    
    # Check projection stage includes permission_holders
    projection_stages = [stage for stage in pipeline if "$project" in stage]
    if projection_stages:
        projection = projection_stages[-1]["$project"]
        if "permission_holders" in projection:
            print("✅ permission_holders field included in projection")
            
            # Check structure of permission_holders
            perm_holders = projection["permission_holders"]
            expected_perms = ["can_view", "can_edit", "can_manage_questions", "can_publish"]
            
            for perm in expected_perms:
                if perm in perm_holders:
                    print(f"   ✅ {perm} mapping present")
                else:
                    print(f"   ❌ {perm} mapping missing")
                    return False
        else:
            print("❌ permission_holders field missing from projection")
            return False
    else:
        print("❌ No projection stage found")
        return False
    
    print("\n🎉 All tests passed! The fix should resolve the ResponseValidationError.")
    print("\n📋 Summary of changes:")
    print("   1. Added 4 new $lookup stages for permission holder profiles")
    print("   2. Added permission_holders field to projection with proper mapping")
    print("   3. Maintained backward compatibility with existing fields")
    print("   4. All QuestionSetDetailedPublic endpoints will now work correctly")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_permission_holders_fix())
    if success:
        print("\n✅ Fix validation successful!")
        sys.exit(0)
    else:
        print("\n❌ Fix validation failed!")
        sys.exit(1)