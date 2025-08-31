#!/usr/bin/env python3
"""
Test script untuk menguji fitur search pada teaching assignments dan teachers basic.
"""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.crud.crud_teaching_assignments import get_filtered_assignment_ids, get_assignments_details_by_ids
from app.crud.crud_users import get_all_teachers_basic
from app.core.config import settings

async def test_teaching_assignments_search():
    """Test search functionality for teaching assignments"""
    print("=== Testing Teaching Assignments Search ===")
    
    # Connect to database
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Test 1: Get all assignments without search
        print("\n1. Testing without search...")
        filters = {}
        all_ids = await get_filtered_assignment_ids(db, "676c8b5c4b0123456789abcd", filters)  # Replace with actual academic_period_id
        print(f"Total assignments without search: {len(all_ids)}")
        
        # Test 2: Search with a common term
        print("\n2. Testing with search term 'matematika'...")
        filters_with_search = {"search": "matematika"}
        search_ids = await get_filtered_assignment_ids(db, "676c8b5c4b0123456789abcd", filters_with_search)
        print(f"Assignments found with 'matematika': {len(search_ids)}")
        
        # Test 3: Search with teacher name
        print("\n3. Testing with search term for teacher name...")
        filters_teacher_search = {"search": "guru"}
        teacher_search_ids = await get_filtered_assignment_ids(db, "676c8b5c4b0123456789abcd", filters_teacher_search)
        print(f"Assignments found with 'guru': {len(teacher_search_ids)}")
        
        # Test 4: Get details for first few results
        if search_ids:
            print("\n4. Getting details for search results...")
            details_ids = [ObjectId(id_str) for id_str in search_ids[:3]]  # First 3 results
            details = await get_assignments_details_by_ids(db, details_ids)
            for detail in details:
                teacher_name = detail.get('teacher_details', {}).get('profile_details', {}).get('full_name', 'N/A')
                subject_name = detail.get('subject_details', {}).get('name', 'N/A')
                class_name = detail.get('class_details', {}).get('name', 'N/A')
                print(f"  - Teacher: {teacher_name}, Subject: {subject_name}, Class: {class_name}")
        
    except Exception as e:
        print(f"Error testing teaching assignments search: {e}")
    finally:
        client.close()

async def test_teachers_basic_search():
    """Test search functionality for teachers basic"""
    print("\n=== Testing Teachers Basic Search ===")
    
    # Connect to database
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Test 1: Get all teachers without search
        print("\n1. Testing without search...")
        all_teachers = await get_all_teachers_basic(db)
        print(f"Total active teachers: {len(all_teachers)}")
        
        # Test 2: Search with a common name
        print("\n2. Testing with search term 'ahmad'...")
        search_teachers = await get_all_teachers_basic(db, search="ahmad")
        print(f"Teachers found with 'ahmad': {len(search_teachers)}")
        
        # Test 3: Search with partial name
        print("\n3. Testing with search term 'guru'...")
        partial_search = await get_all_teachers_basic(db, search="guru")
        print(f"Teachers found with 'guru': {len(partial_search)}")
        
        # Test 4: Display first few results
        if all_teachers:
            print("\n4. Sample teachers (first 5):")
            for teacher in all_teachers[:5]:
                print(f"  - ID: {teacher['_id']}, Name: {teacher['full_name']}")
        
        if search_teachers:
            print("\n5. Search results for 'ahmad':")
            for teacher in search_teachers:
                print(f"  - ID: {teacher['_id']}, Name: {teacher['full_name']}")
        
    except Exception as e:
        print(f"Error testing teachers basic search: {e}")
    finally:
        client.close()

async def main():
    """Main test function"""
    print("Starting search functionality tests...")
    
    # Test teaching assignments search
    await test_teaching_assignments_search()
    
    # Test teachers basic search
    await test_teachers_basic_search()
    
    print("\n=== Tests completed ===")

if __name__ == "__main__":
    asyncio.run(main())