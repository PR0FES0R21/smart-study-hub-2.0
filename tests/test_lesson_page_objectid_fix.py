# ==============================================================================
# File: tests/test_lesson_page_objectid_fix.py
# Description: Verify LessonPage ObjectId to string conversion fix
# ==============================================================================
import sys
import os
from bson import ObjectId
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lesson_page_model_has_string_fields():
    """Test that LessonPage model has string fields (not PyObjectId)"""
    from app.models.lesson_page import LessonPage
    
    # Get model fields
    fields = LessonPage.model_fields
    
    # Check lesson_id is string type
    assert 'lesson_id' in fields, "Should have lesson_id field"
    lesson_id_annotation = str(fields['lesson_id'].annotation)
    assert 'str' in lesson_id_annotation, f"lesson_id should be str, got {lesson_id_annotation}"
    
    # Check created_by is Optional[str]
    assert 'created_by' in fields, "Should have created_by field"
    created_by_annotation = str(fields['created_by'].annotation)
    assert 'str' in created_by_annotation, f"created_by should be Optional[str], got {created_by_annotation}"
    
    # Check updated_by is Optional[str]
    assert 'updated_by' in fields, "Should have updated_by field"
    updated_by_annotation = str(fields['updated_by'].annotation)
    assert 'str' in updated_by_annotation, f"updated_by should be Optional[str], got {updated_by_annotation}"
    
    print("[PASS] LessonPage model has correct string field types")

def test_from_mongo_converts_objectid_to_string():
    """Test that from_mongo() properly converts ObjectId to string"""
    from app.models.lesson_page import LessonPage
    
    # Create mock MongoDB document
    lesson_oid = ObjectId()
    created_by_oid = ObjectId()
    page_oid = ObjectId()
    
    mongo_doc = {
        "_id": page_oid,
        "lesson_id": lesson_oid,
        "page_number": 1,
        "title": "Test Page",
        "content_markdown": "# Test Content",
        "media_references": [],
        "embedded_components": [],
        "estimated_duration": 10,
        "difficulty_level": "medium",
        "learning_objectives": [],
        "status": "published",
        "version": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": created_by_oid,
        "updated_by": None
    }
    
    # Convert using from_mongo
    page = LessonPage.from_mongo(mongo_doc)
    
    # Verify conversions
    assert isinstance(page.id, str), f"id should be string, got {type(page.id)}"
    assert page.id == str(page_oid), f"id should be '{str(page_oid)}', got '{page.id}'"
    
    assert isinstance(page.lesson_id, str), f"lesson_id should be string, got {type(page.lesson_id)}"
    assert page.lesson_id == str(lesson_oid), f"lesson_id should be '{str(lesson_oid)}', got '{page.lesson_id}'"
    
    assert isinstance(page.created_by, str), f"created_by should be string, got {type(page.created_by)}"
    assert page.created_by == str(created_by_oid), f"created_by should be '{str(created_by_oid)}', got '{page.created_by}'"
    
    assert page.updated_by is None, "updated_by should be None"
    
    print("[PASS] from_mongo() converts ObjectId to string correctly")

def test_lesson_page_dict_for_response():
    """Test that page.dict() returns serializable data"""
    from app.models.lesson_page import LessonPage
    
    page_id = str(ObjectId())
    lesson_id = str(ObjectId())
    created_by = str(ObjectId())
    
    # Create LessonPage with string IDs
    page = LessonPage(
        id=page_id,
        lesson_id=lesson_id,
        page_number=1,
        title="Test Page",
        content_markdown="# Content",
        created_by=created_by
    )
    
    # Convert to dict
    page_dict = page.dict()
    
    # Verify all ID fields are strings
    assert isinstance(page_dict['id'], str), "id should be string in dict"
    assert isinstance(page_dict['lesson_id'], str), "lesson_id should be string in dict"
    assert isinstance(page_dict['created_by'], str), "created_by should be string in dict"
    
    # Should not have ObjectId type
    assert 'ObjectId' not in str(type(page_dict['lesson_id'])), "lesson_id should not be ObjectId"
    assert 'ObjectId' not in str(type(page_dict['created_by'])), "created_by should not be ObjectId"
    
    print("[PASS] page.dict() returns serializable data")

def test_response_schema_compatibility():
    """Test that LessonPage is compatible with PageResponse schema"""
    from app.models.lesson_page import LessonPage
    from app.schemas.lesson_page import PageResponse
    
    page_id = str(ObjectId())
    lesson_id = str(ObjectId())
    created_by = str(ObjectId())
    
    # Create LessonPage
    page = LessonPage(
        id=page_id,
        lesson_id=lesson_id,
        page_number=1,
        title="Test",
        content_markdown="# Test",
        media_references=[],
        embedded_components=[],
        created_by=created_by
    )
    
    # Convert to dict
    page_dict = page.dict()
    
    # Should be able to create PageResponse
    try:
        response = PageResponse(**page_dict)
        assert response.lesson_id == lesson_id, "lesson_id should match"
        assert response.created_by == created_by, "created_by should match"
        print("[PASS] LessonPage compatible with PageResponse schema")
    except Exception as e:
        raise AssertionError(f"Failed to create PageResponse: {e}")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("RUNNING LESSON PAGE OBJECTID FIX VERIFICATION")
    print("="*80 + "\n")
    
    tests = [
        test_lesson_page_model_has_string_fields,
        test_from_mongo_converts_objectid_to_string,
        test_lesson_page_dict_for_response,
        test_response_schema_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {str(e)}")
            failed += 1
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    print("="*80 + "\n")
    
    if failed == 0:
        print("SUCCESS: LessonPage ObjectId fix verified!")
        print("\nFixed issues:")
        print("  [OK] lesson_id: PyObjectId -> str")
        print("  [OK] created_by: Optional[PyObjectId] -> Optional[str]")
        print("  [OK] updated_by: Optional[PyObjectId] -> Optional[str]")
        print("  [OK] from_mongo() converts ObjectId to string")
        print("  [OK] page.dict() returns serializable data")
        print("  [OK] Compatible with PageResponse schema")
        print("\nNo more ResponseValidationError!")
    else:
        print("FAILURE: Some tests failed. Please review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
