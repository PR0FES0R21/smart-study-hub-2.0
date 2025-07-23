# ==============================================================================
# File: app/tasks/bulk_operations_tasks.py
# Deskripsi: Background task untuk operasi massal.
# --- DITAMBAHKAN ---
# ==============================================================================
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any
from bson import ObjectId

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.websocket import manager
from app.crud import crud_teaching_assignments
from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentUpdate

def get_db_connection():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    return client[settings.DATABASE_NAME]

@celery_app.task(bind=True)
def bulk_update_assignments_task(self, actions: List[Dict[str, Any]], admin_user_id: str):
    """
    Memproses daftar aksi (create, update, delete) untuk penugasan mengajar.
    """
    loop = asyncio.get_event_loop()
    db = get_db_connection()
    
    total_actions = len(actions)
    results = {
        "created": 0, "updated": 0, "deleted": 0, "failed": 0,
        "errors": []
    }

    async def process():
        for i, action in enumerate(actions):
            try:
                action_type = action.get("type")
                if action_type == "create":
                    create_data = TeachingAssignmentCreate(**action.get("data", {}))
                    await crud_teaching_assignments.create_teaching_assignment(db, create_data)
                    results["created"] += 1
                
                elif action_type == "update":
                    assignment_id = ObjectId(action.get("assignment_id"))
                    update_data = TeachingAssignmentUpdate(**action.get("data", {}))
                    await crud_teaching_assignments.update_teaching_assignment(db, assignment_id, update_data)
                    results["updated"] += 1

                elif action_type == "delete":
                    assignment_id = str(action.get("assignment_id"))
                    await crud_teaching_assignments.delete_teaching_assignment(db, assignment_id)
                    results["deleted"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Action {i+1} ({action.get('type')}): {str(e)}")

            # Kirim progres ke admin via WebSocket
            progress_message = {
                "type": "bulk_update_progress",
                "task_id": self.request.id,
                "processed": i + 1,
                "total": total_actions,
                "success": results["created"] + results["updated"] + results["deleted"],
                "failed": results["failed"]
            }
            # Kita broadcast ke semua admin, frontend akan filter berdasarkan task_id
            await manager.broadcast_to_roles(progress_message, target_roles=["admin"])

    loop.run_until_complete(process())

    # Kirim pesan selesai
    final_status = "PARTIAL_SUCCESS" if results["failed"] > 0 else "SUCCESS"
    final_message = {
        "type": "bulk_update_complete",
        "task_id": self.request.id,
        "status": final_status,
        "details": results
    }
    loop.run_until_complete(manager.broadcast_to_roles(final_message, target_roles=["admin"]))

    return results