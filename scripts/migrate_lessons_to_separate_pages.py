# ==============================================================================
# File: scripts/migrate_lessons_to_separate_pages.py
# Deskripsi: Migration script to separate embedded pages into lesson_pages collection
# ==============================================================================
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from datetime import datetime
from bson import ObjectId

async def migrate_lessons_to_separate_pages():
    """
    Migrate embedded pages from lessons to separate lesson_pages collection.
    
    BEFORE:
    lessons collection: { pages: [...] }  // Embedded
    
    AFTER:
    lessons collection: { metadata: {...} }  // No pages
    lesson_pages collection: [{ lesson_id, page_number, ... }]  // Separate
    """
    
    print("="*80)
    print("MIGRATION: Separating Lesson Pages")
    print("="*80)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Step 1: Get all lessons with embedded pages
        print("\n[1/5] Fetching lessons with embedded pages...")
        lessons = await db["lessons"].find({"pages": {"$exists": True, "$ne": []}}).to_list(None)
        print(f"   Found {len(lessons)} lessons to migrate")
        
        if len(lessons) == 0:
            print("\n✅ No lessons to migrate. All done!")
            return
        
        # Step 2: Create indexes for lesson_pages collection
        print("\n[2/5] Creating indexes for lesson_pages collection...")
        await db["lesson_pages"].create_index([("lesson_id", 1), ("page_number", 1)], unique=True)
        await db["lesson_pages"].create_index([("lesson_id", 1), ("status", 1)])
        await db["lesson_pages"].create_index([("created_at", -1)])
        await db["lesson_pages"].create_index([("status", 1)])
        print("   ✅ Indexes created")
        
        # Step 3: Migrate pages
        print("\n[3/5] Migrating pages to lesson_pages collection...")
        total_pages_migrated = 0
        
        for lesson in lessons:
            lesson_id = lesson["_id"]
            pages = lesson.get("pages", [])
            
            if not pages:
                continue
            
            print(f"\n   Lesson: {lesson.get('title', 'Untitled')} ({lesson_id})")
            print(f"   Pages to migrate: {len(pages)}")
            
            # Extract and insert each page
            for page in pages:
                page_doc = {
                    "lesson_id": lesson_id,
                    "page_number": page.get("page_number", 1),
                    "title": page.get("title", "Untitled Page"),
                    "content_markdown": page.get("content_markdown", ""),
                    "media_references": page.get("media_references", []),
                    "embedded_components": page.get("embedded_components", []),
                    "estimated_duration": page.get("estimated_duration", 10),
                    "difficulty_level": page.get("difficulty_level", "medium"),
                    "learning_objectives": page.get("learning_objectives", []),
                    "status": "published" if lesson.get("status") == "published" else "draft",
                    "version": 1,
                    "created_at": page.get("created_at", lesson.get("created_at", datetime.utcnow())),
                    "updated_at": page.get("updated_at", lesson.get("updated_at", datetime.utcnow())),
                    "published_at": lesson.get("published_at"),
                    "created_by": lesson.get("created_by"),
                    "updated_by": None
                }
                
                try:
                    # Insert or update (in case of re-run)
                    await db["lesson_pages"].update_one(
                        {
                            "lesson_id": lesson_id,
                            "page_number": page_doc["page_number"]
                        },
                        {"$set": page_doc},
                        upsert=True
                    )
                    total_pages_migrated += 1
                except Exception as e:
                    print(f"      ⚠️  Error migrating page {page_doc['page_number']}: {e}")
            
            print(f"   ✅ Migrated {len(pages)} pages")
        
        print(f"\n   Total pages migrated: {total_pages_migrated}")
        
        # Step 4: Update lessons collection (remove pages, update metadata)
        print("\n[4/5] Updating lessons collection (removing embedded pages)...")
        
        for lesson in lessons:
            lesson_id = lesson["_id"]
            pages = lesson.get("pages", [])
            
            # Calculate metadata
            total_pages = len(pages)
            total_duration = sum(p.get("estimated_duration", 10) for p in pages)
            total_media = sum(len(p.get("media_references", [])) for p in pages)
            total_components = sum(len(p.get("embedded_components", [])) for p in pages)
            
            # Update lesson: remove pages, update metadata
            update_doc = {
                "$unset": {"pages": ""},
                "$set": {
                    "metadata.total_pages": total_pages,
                    "metadata.total_duration": total_duration,
                    "metadata.total_media": total_media,
                    "metadata.total_components": total_components,
                    "metadata.calculated_at": datetime.utcnow(),
                    "migrated_at": datetime.utcnow(),
                    "migration_version": 1
                }
            }
            
            await db["lessons"].update_one(
                {"_id": lesson_id},
                update_doc
            )
        
        print(f"   ✅ Updated {len(lessons)} lessons")
        
        # Step 5: Verification
        print("\n[5/5] Verifying migration...")
        
        # Check lessons no longer have pages field
        lessons_with_pages = await db["lessons"].count_documents({"pages": {"$exists": True}})
        
        # Count migrated pages
        total_pages_in_collection = await db["lesson_pages"].count_documents({})
        
        print(f"   Lessons still with embedded pages: {lessons_with_pages}")
        print(f"   Total pages in lesson_pages collection: {total_pages_in_collection}")
        
        if lessons_with_pages == 0 and total_pages_in_collection == total_pages_migrated:
            print("\n" + "="*80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"\nSummary:")
            print(f"  - Lessons migrated: {len(lessons)}")
            print(f"  - Pages extracted: {total_pages_migrated}")
            print(f"  - New lesson_pages documents: {total_pages_in_collection}")
            print(f"\nNext steps:")
            print(f"  1. Test new endpoints: GET /lessons/{{id}}/pages")
            print(f"  2. Update frontend to use new endpoints")
            print(f"  3. Monitor performance improvements")
        else:
            print("\n⚠️  WARNING: Verification failed!")
            print(f"  Please check the migration results manually.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close connection
        client.close()
        print("\nDatabase connection closed.")

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: This migration will restructure your lessons data!")
    print("   Make sure you have a backup before proceeding.")
    print("\nDo you want to continue? (yes/no): ", end="")
    
    confirmation = input().strip().lower()
    
    if confirmation in ["yes", "y"]:
        asyncio.run(migrate_lessons_to_separate_pages())
    else:
        print("\nMigration cancelled.")
