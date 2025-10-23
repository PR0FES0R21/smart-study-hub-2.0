"""
Script untuk setup test data untuk new course system.

Usage:
    python scripts/setup_test_data_course_system.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "smart_study_hub")


async def setup_test_data():
    """Setup test data for course system testing"""
    
    # Connect to database
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    print("🔧 Setting up test data for new course system...")
    
    # ==================== 1. CREATE TEST USERS ====================
    print("\n1️⃣ Creating test users...")
    
    # Check if users already exist
    existing_teacher = await db["users"].find_one({"email": "teacher.test@school.com"})
    existing_student1 = await db["users"].find_one({"email": "student1.test@school.com"})
    existing_student2 = await db["users"].find_one({"email": "student2.test@school.com"})
    
    if existing_teacher:
        print("   ⚠️  Teacher user already exists")
        teacher_id = existing_teacher["_id"]
    else:
        # Create teacher user
        teacher = {
            "_id": ObjectId(),
            "email": "teacher.test@school.com",
            "username": "teacher_test",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5K5VkZEo7xPPG",  # "password123"
            "roles": ["teacher"],
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        await db["users"].insert_one(teacher)
        teacher_id = teacher["_id"]
        print(f"   ✅ Created teacher: {teacher['email']}")
    
    if existing_student1:
        print("   ⚠️  Student1 user already exists")
        student1_id = existing_student1["_id"]
    else:
        # Create student 1
        student1 = {
            "_id": ObjectId(),
            "email": "student1.test@school.com",
            "username": "student1_test",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5K5VkZEo7xPPG",
            "roles": ["student"],
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        await db["users"].insert_one(student1)
        student1_id = student1["_id"]
        print(f"   ✅ Created student1: {student1['email']}")
    
    if existing_student2:
        print("   ⚠️  Student2 user already exists")
        student2_id = existing_student2["_id"]
    else:
        # Create student 2
        student2 = {
            "_id": ObjectId(),
            "email": "student2.test@school.com",
            "username": "student2_test",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5K5VkZEo7xPPG",
            "roles": ["student"],
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        await db["users"].insert_one(student2)
        student2_id = student2["_id"]
        print(f"   ✅ Created student2: {student2['email']}")
    
    # ==================== 2. CREATE TEST SUBJECT ====================
    print("\n2️⃣ Creating test subject...")
    
    existing_subject = await db["subjects"].find_one({"name": "Matematika Test"})
    if existing_subject:
        print("   ⚠️  Subject already exists")
        subject_id = existing_subject["_id"]
    else:
        subject = {
            "_id": ObjectId(),
            "name": "Matematika Test",
            "code": "MTK-TEST",
            "description": "Test subject for course system",
            "created_at": datetime.utcnow()
        }
        await db["subjects"].insert_one(subject)
        subject_id = subject["_id"]
        print(f"   ✅ Created subject: {subject['name']}")
    
    # ==================== 3. CREATE TEST CLASS ====================
    print("\n3️⃣ Creating test class...")
    
    existing_class = await db["classes"].find_one({"name": "10A Test"})
    if existing_class:
        print("   ⚠️  Class already exists")
        class_id = existing_class["_id"]
    else:
        test_class = {
            "_id": ObjectId(),
            "name": "10A Test",
            "grade_level": 10,
            "academic_year": "2024/2025",
            "created_at": datetime.utcnow()
        }
        await db["classes"].insert_one(test_class)
        class_id = test_class["_id"]
        print(f"   ✅ Created class: {test_class['name']}")
    
    # Update students with class_id
    await db["users"].update_one(
        {"_id": student1_id},
        {"$set": {"class_id": class_id}}
    )
    await db["users"].update_one(
        {"_id": student2_id},
        {"$set": {"class_id": class_id}}
    )
    print(f"   ✅ Assigned students to class")
    
    # ==================== 4. CREATE TEACHING ASSIGNMENT ====================
    print("\n4️⃣ Creating teaching assignment...")
    
    existing_ta = await db["teaching_assignments"].find_one({
        "teacher_id": teacher_id,
        "class_id": class_id
    })
    if existing_ta:
        print("   ⚠️  Teaching assignment already exists")
    else:
        teaching_assignment = {
            "_id": ObjectId(),
            "teacher_id": teacher_id,
            "class_id": class_id,
            "subject_id": subject_id,
            "status": "active",
            "created_at": datetime.utcnow()
        }
        await db["teaching_assignments"].insert_one(teaching_assignment)
        print(f"   ✅ Created teaching assignment")
    
    # ==================== 5. CREATE TEST MODULES & LESSONS ====================
    print("\n5️⃣ Creating test modules and lessons...")
    
    # Module 1
    existing_module1 = await db["modules"].find_one({"title": "Test Module 1: Aljabar"})
    if existing_module1:
        print("   ⚠️  Module 1 already exists")
        module1_id = existing_module1["_id"]
    else:
        # Create lessons for Module 1
        lesson1_1 = {
            "_id": ObjectId(),
            "title": "Lesson 1.1: Persamaan Linear",
            "content": "Test content",
            "created_at": datetime.utcnow()
        }
        lesson1_2 = {
            "_id": ObjectId(),
            "title": "Lesson 1.2: Pertidaksamaan",
            "content": "Test content",
            "created_at": datetime.utcnow()
        }
        await db["lessons"].insert_many([lesson1_1, lesson1_2])
        
        module1 = {
            "_id": ObjectId(),
            "title": "Test Module 1: Aljabar",
            "description": "Test module for course system",
            "subject_id": subject_id,
            "lesson_refs": [
                {"lesson_id": lesson1_1["_id"], "order": 1},
                {"lesson_id": lesson1_2["_id"], "order": 2}
            ],
            "created_at": datetime.utcnow()
        }
        await db["modules"].insert_one(module1)
        module1_id = module1["_id"]
        print(f"   ✅ Created Module 1 with 2 lessons")
    
    # Module 2
    existing_module2 = await db["modules"].find_one({"title": "Test Module 2: Geometri"})
    if existing_module2:
        print("   ⚠️  Module 2 already exists")
        module2_id = existing_module2["_id"]
    else:
        lesson2_1 = {
            "_id": ObjectId(),
            "title": "Lesson 2.1: Segitiga",
            "content": "Test content",
            "created_at": datetime.utcnow()
        }
        lesson2_2 = {
            "_id": ObjectId(),
            "title": "Lesson 2.2: Lingkaran",
            "content": "Test content",
            "created_at": datetime.utcnow()
        }
        await db["lessons"].insert_many([lesson2_1, lesson2_2])
        
        module2 = {
            "_id": ObjectId(),
            "title": "Test Module 2: Geometri",
            "description": "Test module",
            "subject_id": subject_id,
            "lesson_refs": [
                {"lesson_id": lesson2_1["_id"], "order": 1},
                {"lesson_id": lesson2_2["_id"], "order": 2}
            ],
            "created_at": datetime.utcnow()
        }
        await db["modules"].insert_one(module2)
        module2_id = module2["_id"]
        print(f"   ✅ Created Module 2 with 2 lessons")
    
    # Module 3
    existing_module3 = await db["modules"].find_one({"title": "Test Module 3: Trigonometri"})
    if existing_module3:
        print("   ⚠️  Module 3 already exists")
        module3_id = existing_module3["_id"]
    else:
        lesson3_1 = {
            "_id": ObjectId(),
            "title": "Lesson 3.1: Sin Cos Tan",
            "content": "Test content",
            "created_at": datetime.utcnow()
        }
        await db["lessons"].insert_one(lesson3_1)
        
        module3 = {
            "_id": ObjectId(),
            "title": "Test Module 3: Trigonometri",
            "description": "Test module",
            "subject_id": subject_id,
            "lesson_refs": [
                {"lesson_id": lesson3_1["_id"], "order": 1}
            ],
            "created_at": datetime.utcnow()
        }
        await db["modules"].insert_one(module3)
        module3_id = module3["_id"]
        print(f"   ✅ Created Module 3 with 1 lesson")
    
    # ==================== 6. CREATE TEST COURSE ====================
    print("\n6️⃣ Creating test course...")
    
    existing_course = await db["courses"].find_one({"title": "Test Course: Matematika Kelas 10"})
    if existing_course:
        print("   ⚠️  Course already exists")
        course_id = existing_course["_id"]
    else:
        course = {
            "_id": ObjectId(),
            "title": "Test Course: Matematika Kelas 10",
            "description": "Test course for new course system",
            "slug": "test-course-matematika-10",
            "subject_id": subject_id,
            "grade_level": 10,
            "coordinator_id": teacher_id,  # Teacher as coordinator for testing
            "module_refs": [
                {"module_id": module1_id, "order": 1, "required": True},
                {"module_id": module2_id, "order": 2, "required": True},
                {"module_id": module3_id, "order": 3, "required": True}
            ],
            "sequential_mode": True,
            "status": "published",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db["courses"].insert_one(course)
        course_id = course["_id"]
        print(f"   ✅ Created course with 3 modules")
    
    # ==================== 7. PRINT TEST DATA INFO ====================
    print("\n" + "="*60)
    print("✅ TEST DATA SETUP COMPLETE!")
    print("="*60)
    
    print("\n📋 TEST CREDENTIALS:")
    print(f"   Teacher:")
    print(f"   - Email: teacher.test@school.com")
    print(f"   - Password: password123")
    print(f"   - ID: {teacher_id}")
    
    print(f"\n   Student 1:")
    print(f"   - Email: student1.test@school.com")
    print(f"   - Password: password123")
    print(f"   - ID: {student1_id}")
    
    print(f"\n   Student 2:")
    print(f"   - Email: student2.test@school.com")
    print(f"   - Password: password123")
    print(f"   - ID: {student2_id}")
    
    print(f"\n📚 TEST DATA IDs:")
    print(f"   Subject ID: {subject_id}")
    print(f"   Class ID: {class_id}")
    print(f"   Course ID: {course_id}")
    print(f"   Module 1 ID: {module1_id}")
    print(f"   Module 2 ID: {module2_id}")
    print(f"   Module 3 ID: {module3_id}")
    
    print(f"\n🎯 READY FOR TESTING!")
    print(f"   Start with: POST /api/v1/course-assignments")
    print(f"   Body: {{course_id: '{course_id}', class_id: '{class_id}'}}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(setup_test_data())
