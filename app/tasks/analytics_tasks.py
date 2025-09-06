# ==============================================================================
# File: app/tasks/analytics_tasks.py
# Deskripsi: Background task untuk perhitungan analitik yang berat.
# --- DITAMBAHKAN ---
# ==============================================================================
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.websocket import manager
from app.core.cache import set_cache, invalidate_cache
from app.crud.crud_analytics import build_competency_pipeline, generate_cache_key
from typing import Optional, Dict, Any

def get_db_connection():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    return client[settings.DATABASE_NAME]

@celery_app.task
def recompute_competency_profile_task(filters: Optional[Dict] = None):
    """
    Menghitung ulang data profil kompetensi (global atau terfilter) 
    dan menyimpannya ke cache.
    """
    filters = filters or {}
    
    async def compute():
        db = get_db_connection()
        pipeline = build_competency_pipeline(filters)
        
        if not filters:
            facet_pipeline = {
                "$facet": {
                    "grade_10": pipeline + [{"$match": {"class_info.grade_level": 10}}, {"$group": {"_id": "$subject.name", "average_score": {"$avg": "$sessions.score"}}}],
                    "grade_11": pipeline + [{"$match": {"class_info.grade_level": 11}}, {"$group": {"_id": "$subject.name", "average_score": {"$avg": "$sessions.score"}}}],
                    "grade_12": pipeline + [{"$match": {"class_info.grade_level": 12}}, {"$group": {"_id": "$subject.name", "average_score": {"$avg": "$sessions.score"}}}],
                }
            }
            result = await db["users"].aggregate([facet_pipeline]).to_list(1)
            final_data = result[0] if result else {"grade_10": [], "grade_11": [], "grade_12": []}
            
            for grade in final_data:
                for item in final_data[grade]:
                    item["subject"] = item.pop("_id")
                    item["average_score"] = round(item["average_score"], 2)
        else:
            pipeline.append({"$group": {"_id": "$subject.name", "average_score": {"$avg": "$sessions.score"}}})
            pipeline.append({"$project": {"_id": 0, "subject": "$_id", "average_score": {"$round": ["$average_score", 2]}}})
            final_data = await db["users"].aggregate(pipeline).to_list(None)

        cache_key = generate_cache_key(filters)
        await set_cache(cache_key, final_data)
        
        await manager.broadcast_to_roles(
            {"type": "analytics_ready", "report_key": cache_key},
            target_roles=["admin"]
        )
        print(f"Analitik untuk cache key '{cache_key}' berhasil dihitung ulang.")

    asyncio.run(compute())
    return {"status": "Completed"}
