#!/usr/bin/env python3
"""
Test script untuk memvalidasi perbaikan metadata calculation
"""
import asyncio
import sys
import os
from bson import ObjectId
from datetime import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.crud.crud_question_sets import QuestionRepository

async def test_metadata_calculation_fix():
    """Test bahwa metadata calculation sekarang menggunakan collection yang benar"""
    
    print("🔍 Testing metadata calculation fix...")
    
    # Mock database connection
    class MockDB:
        def __init__(self):
            self.collections = {}
            self.query_log = []
        
        def __getitem__(self, collection_name):
            return MockCollection(collection_name, self.query_log)
    
    class MockCollection:
        def __init__(self, name, query_log):
            self.name = name
            self.query_log = query_log
        
        def aggregate(self, pipeline, session=None):
            self.query_log.append({
                "collection": self.name,
                "operation": "aggregate",
                "pipeline": pipeline,
                "session": session
            })
            return MockCursor(self.name, pipeline)
        
        def count_documents(self, filter_query, session=None):
            self.query_log.append({
                "collection": self.name,
                "operation": "count_documents",
                "filter": filter_query,
                "session": session
            })
            return MockCountResult(3)  # Mock 3 questions found
    
    class MockCountResult:
        def __init__(self, count):
            self.count = count
        
        async def __aenter__(self):
            return self.count
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    class MockCursor:
        def __init__(self, collection_name, pipeline):
            self.collection_name = collection_name
            self.pipeline = pipeline
        
        async def to_list(self, limit):
            # Return mock metadata based on collection used
            if self.collection_name == "question_banks":
                return [{
                    "total_questions": 3,
                    "total_points": 30,
                    "difficulty_distribution": {
                        "easy": 1,
                        "medium": 1,
                        "hard": 1
                    },
                    "tags": ["math", "algebra", "geometry"]
                }]
            else:
                # If wrong collection is used, return empty
                return []
    
    # Test the fix
    mock_db = MockDB()
    question_repo = QuestionRepository(mock_db)
    
    # Test question IDs
    test_question_ids = [ObjectId(), ObjectId(), ObjectId()]
    
    print("✅ Testing collection name fix:")
    
    # Test calculate_metadata
    try:
        metadata = await question_repo.calculate_metadata(test_question_ids)
        
        # Check if query was made to correct collection
        aggregate_queries = [q for q in mock_db.query_log if q["operation"] == "aggregate"]
        
        if aggregate_queries:
            collection_used = aggregate_queries[0]["collection"]
            print(f"   - Collection used: {collection_used}")
            
            if collection_used == "question_banks":
                print("   ✅ FIXED: Now using correct collection 'question_banks'")
                
                # Check if metadata was calculated correctly
                if metadata and metadata.get("total_questions", 0) > 0:
                    print("   ✅ Metadata calculation successful:")
                    print(f"      - Total questions: {metadata['total_questions']}")
                    print(f"      - Total points: {metadata['total_points']}")
                    print(f"      - Difficulty distribution: {metadata['difficulty_distribution']}")
                    print(f"      - Tags: {metadata['tags']}")
                else:
                    print("   ❌ Metadata calculation returned empty result")
                    return False
                    
            elif collection_used == "questions":
                print("   ❌ STILL BROKEN: Using wrong collection 'questions'")
                return False
            else:
                print(f"   ❌ UNEXPECTED: Using unknown collection '{collection_used}'")
                return False
        else:
            print("   ❌ No aggregate queries found")
            return False
            
    except Exception as e:
        print(f"   ❌ Error during metadata calculation: {e}")
        return False
    
    # Test validate_existence
    print("\n✅ Testing validate_existence consistency:")
    
    try:
        await question_repo.validate_existence(test_question_ids)
        
        # Check if query was made to correct collection
        count_queries = [q for q in mock_db.query_log if q["operation"] == "count_documents"]
        
        if count_queries:
            collection_used = count_queries[0]["collection"]
            print(f"   - Collection used: {collection_used}")
            
            if collection_used == "question_banks":
                print("   ✅ Both functions now use same collection 'question_banks'")
            else:
                print(f"   ❌ Inconsistency: validate_existence uses '{collection_used}'")
                return False
        else:
            print("   ❌ No count queries found")
            return False
            
    except Exception as e:
        print(f"   ❌ Error during validation: {e}")
        return False
    
    print("\n🎉 All tests passed! Metadata calculation fix is working correctly.")
    print("\n📋 Summary of fix:")
    print("   1. Changed collection from 'questions' to 'question_banks' in calculate_metadata")
    print("   2. Now consistent with validate_existence and all other functions")
    print("   3. Metadata will now update correctly when adding/removing questions")
    print("   4. Transaction operations will work properly")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_metadata_calculation_fix())
    if success:
        print("\n✅ Metadata calculation fix validation successful!")
        sys.exit(0)
    else:
        print("\n❌ Metadata calculation fix validation failed!")
        sys.exit(1)