#!/usr/bin/env python3
# ==============================================================================
# File: scripts/create_analytics_indexes.py  
# Deskripsi: Create optimized MongoDB indexes untuk analytics performance
# Usage: python scripts/create_analytics_indexes.py
# ==============================================================================

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_analytics_indexes():
    """
    Create optimized indexes untuk analytics performance
    """
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    logger.info("Creating analytics performance indexes...")
    
    try:
        # ============================================================================
        # EXAM_SESSIONS Collection Indexes (Critical for performance)
        # ============================================================================
        
        # 1. Core analytics filter index
        await db.exam_sessions.create_index([
            ("status", 1),
            ("submitted_at", 1), 
            ("score", 1)
        ], background=True, name="analytics_core_filter")
        logger.info("✅ Created exam_sessions.analytics_core_filter")
        
        # 2. Student-specific analytics index
        await db.exam_sessions.create_index([
            ("student_id", 1),
            ("submitted_at", 1),
            ("status", 1)
        ], background=True, name="student_analytics")
        logger.info("✅ Created exam_sessions.student_analytics")
        
        # 3. Exam-based analytics index  
        await db.exam_sessions.create_index([
            ("exam_id", 1),
            ("status", 1),
            ("submitted_at", 1)
        ], background=True, name="exam_analytics")
        logger.info("✅ Created exam_sessions.exam_analytics")
        
        # 4. Date-range performance index
        await db.exam_sessions.create_index([
            ("submitted_at", 1),
            ("status", 1)
        ], background=True, name="date_range_analytics")
        logger.info("✅ Created exam_sessions.date_range_analytics")
        
        # 5. Score analytics index
        await db.exam_sessions.create_index([
            ("score", 1),
            ("status", 1),
            ("exam_id", 1)
        ], background=True, name="score_analytics")
        logger.info("✅ Created exam_sessions.score_analytics")
        
        # ============================================================================
        # EXAMS Collection Indexes
        # ============================================================================
        
        # 1. Teaching assignment lookup index
        await db.exams.create_index([
            ("teaching_assignment_id", 1),
            ("status", 1)
        ], background=True, name="teaching_assignment_lookup")
        logger.info("✅ Created exams.teaching_assignment_lookup")
        
        # 2. Academic period analytics
        await db.exams.create_index([
            ("academic_period_id", 1),
            ("status", 1)
        ], background=True, name="academic_period_analytics")
        logger.info("✅ Created exams.academic_period_analytics")
        
        # ============================================================================
        # TEACHING_ASSIGNMENTS Collection Indexes
        # ============================================================================
        
        # 1. Teacher-based filtering index
        await db.teaching_assignments.create_index([
            ("teacher_id", 1),
            ("academic_period_id", 1)
        ], background=True, name="teacher_assignments")
        logger.info("✅ Created teaching_assignments.teacher_assignments")
        
        # 2. Class-subject combination index
        await db.teaching_assignments.create_index([
            ("class_id", 1),
            ("subject_id", 1)
        ], background=True, name="class_subject_lookup")
        logger.info("✅ Created teaching_assignments.class_subject_lookup")
        
        # 3. Subject analytics index
        await db.teaching_assignments.create_index([
            ("subject_id", 1)
        ], background=True, name="subject_analytics")
        logger.info("✅ Created teaching_assignments.subject_analytics")
        
        # ============================================================================
        # CLASSES Collection Indexes
        # ============================================================================
        
        # 1. Grade and expertise analytics
        await db.classes.create_index([
            ("grade_level", 1),
            ("expertise_id", 1)
        ], background=True, name="grade_expertise_analytics")
        logger.info("✅ Created classes.grade_expertise_analytics")
        
        # 2. Academic year filtering
        await db.classes.create_index([
            ("academic_year", 1),
            ("grade_level", 1)
        ], background=True, name="academic_year_analytics")
        logger.info("✅ Created classes.academic_year_analytics")
        
        # ============================================================================
        # PROFILES Collection Indexes (for student lookups)
        # ============================================================================
        
        # 1. User ID lookup (critical for profile joins)
        await db.profiles.create_index([
            ("user_id", 1)
        ], background=True, name="user_lookup", unique=True)
        logger.info("✅ Created profiles.user_lookup")
        
        # 2. Class membership index
        await db.profiles.create_index([
            ("class_id", 1),
            ("user_id", 1)
        ], background=True, name="class_membership")
        logger.info("✅ Created profiles.class_membership")
        
        # ============================================================================
        # SUBJECTS Collection Index
        # ============================================================================
        
        # Simple name lookup for efficient subject joins
        await db.subjects.create_index([
            ("name", 1)
        ], background=True, name="subject_name_lookup")
        logger.info("✅ Created subjects.subject_name_lookup")
        
        # ============================================================================
        # EXPERTISE_PROGRAMS Collection Index  
        # ============================================================================
        
        # Abbreviation lookup for class names
        await db.expertise_programs.create_index([
            ("abbreviation", 1)
        ], background=True, name="expertise_abbr_lookup")
        logger.info("✅ Created expertise_programs.expertise_abbr_lookup")
        
        # ============================================================================
        # USERS Collection Indexes
        # ============================================================================
        
        # Role-based filtering
        await db.users.create_index([
            ("roles", 1),
            ("is_active", 1)
        ], background=True, name="user_role_analytics")
        logger.info("✅ Created users.user_role_analytics")
        
        logger.info("🎉 All analytics indexes created successfully!")
        
        # ============================================================================
        # Index Statistics
        # ============================================================================
        
        logger.info("\n📊 Index Statistics:")
        collections = [
            "exam_sessions", "exams", "teaching_assignments", 
            "classes", "profiles", "subjects", "expertise_programs", "users"
        ]
        
        total_indexes = 0
        for collection_name in collections:
            collection = db[collection_name]
            indexes = await collection.list_indexes().to_list(length=None)
            index_count = len(indexes)
            total_indexes += index_count
            
            logger.info(f"  {collection_name}: {index_count} indexes")
            for idx in indexes:
                if idx['name'] != '_id_':  # Skip default _id index
                    logger.info(f"    - {idx['name']}")
        
        logger.info(f"\n✅ Total indexes created: {total_indexes}")
        logger.info("🚀 Analytics performance should be significantly improved!")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        raise
    finally:
        client.close()

async def analyze_index_usage():
    """
    Analyze index usage statistics (MongoDB 4.4+)
    """
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        logger.info("\n🔍 Analyzing index usage...")
        
        # Get index stats for exam_sessions (most critical collection)
        stats = await db.command("collStats", "exam_sessions", indexDetails=True)
        
        if "indexSizes" in stats:
            logger.info("📈 Index sizes (exam_sessions):")
            for index_name, size in stats["indexSizes"].items():
                size_mb = size / (1024 * 1024)
                logger.info(f"  {index_name}: {size_mb:.2f} MB")
    
    except Exception as e:
        logger.warning(f"⚠️  Could not analyze index usage: {e}")
    finally:
        client.close()

async def drop_unused_indexes():
    """
    Drop potentially unused indexes (run with caution!)
    """
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    logger.warning("⚠️  This function will drop unused indexes. Use with caution!")
    
    # Add logic to identify and drop unused indexes
    # This should be run after monitoring index usage in production
    
    client.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB Analytics Index Management")
    parser.add_argument("--action", choices=["create", "analyze", "drop"], default="create",
                      help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "create":
        asyncio.run(create_analytics_indexes())
    elif args.action == "analyze":
        asyncio.run(analyze_index_usage())
    elif args.action == "drop":
        logger.warning("Drop functionality not implemented for safety")
        # asyncio.run(drop_unused_indexes())
