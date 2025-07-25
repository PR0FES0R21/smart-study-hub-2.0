# ==============================================================================
# File: app/tasks/bulk_operations_tasks.py (Updated)
# Deskripsi: Updated bulk operations task using Redis bridge
# ==============================================================================
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any
from bson import ObjectId
import logging
from contextlib import asynccontextmanager

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.redis_websocket import redis_bridge
from app.crud import crud_teaching_assignments
from app.schemas.teaching_assignment import TeachingAssignmentCreate, TeachingAssignmentUpdate

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_db_connection():
    """Context manager for database connection with proper cleanup."""
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    try:
        yield client[settings.DATABASE_NAME]
    finally:
        client.close()

async def send_websocket_message(message: Dict[str, Any], target_roles: List[str]):
    """Helper function to send WebSocket message via Redis bridge."""
    try:
        redis_message = {
            "broadcast_type": "roles",
            "target_roles": target_roles,
            "message": message
        }
        await redis_bridge.publish_message(redis_message)
        logger.debug(f"Sent WebSocket message via Redis: {message.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket message via Redis: {e}")

@celery_app.task(bind=True)
def bulk_update_assignments_task(self, actions: List[Dict[str, Any]], admin_user_id: str):
    """
    Memproses daftar aksi (create, update, delete) untuk penugasan mengajar.
    Updated version using Redis bridge for WebSocket communication.
    """
    
    async def process_bulk_operations():
        total_actions = len(actions)
        results = {
            "created": 0, "updated": 0, "deleted": 0, "failed": 0,
            "errors": []
        }

        logger.info(f"Starting bulk update task {self.request.id} with {total_actions} actions")

        async with get_db_connection() as db:
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
                    
                    logger.debug(f"Processed action {i+1}/{total_actions}: {action_type}")
                    
                except Exception as e:
                    logger.error(f"Error processing action {i+1}: {e}")
                    results["failed"] += 1
                    results["errors"].append(f"Action {i+1} ({action.get('type')}): {str(e)}")

                # Send progress update via Redis
                progress_message = {
                    "type": "bulk_update_progress",
                    "task_id": self.request.id,
                    "processed": i + 1,
                    "total": total_actions,
                    "success": results["created"] + results["updated"] + results["deleted"],
                    "failed": results["failed"]
                }
                
                await send_websocket_message(progress_message, target_roles=["admin"])
                
                # Add small delay to prevent overwhelming
                await asyncio.sleep(0.1)

        # Send completion message via Redis
        final_status = "PARTIAL_SUCCESS" if results["failed"] > 0 else "SUCCESS"
        final_message = {
            "type": "bulk_update_complete",
            "task_id": self.request.id,
            "status": final_status,
            "details": results
        }
        
        await send_websocket_message(final_message, target_roles=["admin"])
        logger.info(f"Completed bulk update task {self.request.id}: {final_status}")

        return results

    # Run the async function properly
    try:
        return asyncio.run(process_bulk_operations())
    except Exception as e:
        logger.error(f"Critical error in bulk update task: {e}")
        
        # Send error message to admin via Redis
        try:
            error_message = {
                "type": "bulk_update_error",
                "task_id": self.request.id,
                "error": str(e)
            }
            asyncio.run(send_websocket_message(error_message, target_roles=["admin"]))
        except Exception as redis_error:
            logger.error(f"Failed to send error message via Redis: {redis_error}")
        
        raise
