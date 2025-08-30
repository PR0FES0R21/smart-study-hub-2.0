# ==============================================================================
# File: app/api/v1/routes/ws_exam_room.py
# Deskripsi: Endpoint untuk koneksi WebSocket ke Ruang Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import json

from app.core.websocket import manager
from app.api.v1 import deps
from app.crud import crud_exam_sessions
from app.schemas.exam_session import InteractionLogItem
from datetime import datetime
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/exam-room/{exam_id}")
async def websocket_exam_room(
    websocket: WebSocket,
    exam_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    user: dict = Depends(deps.get_exam_room_participant)
):
    if not user: return

    user_id = str(user["_id"])
    participant_role = user["participant_role"]
    roles = user.get("roles", [])
    
    await manager.connect(websocket, user_id, roles, room_id=exam_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # FIX: Dapatkan profil siswa terlebih dahulu
            student_profile = await db["profiles"].find_one({"user_id": user["_id"]})
            student_name = student_profile.get("full_name", f"Student {user_id[-6:]}") if student_profile else f"Student {user_id[-6:]}"
            
            if participant_role == "student":
                # Log interaction ke database
                session = await db["exam_sessions"].find_one({"exam_id": ObjectId(exam_id), "student_id": user["_id"]})
                if session:
                    # Hanya log jika ini adalah aktivitas ujian
                    if message.get("type") in ["answer_selected", "answer_changed", "question_viewed", "auto_save"]:
                        log_item = InteractionLogItem(
                            timestamp=datetime.utcnow(),
                            question_id=message.get("details", {}).get("question_id"),
                            displayed_position=message.get("details", {}).get("displayed_position"),
                            action=message.get("type", message.get("violation_type", "unknown")),
                            student_answer=message.get("details", {}).get("answer", message.get("details", {}).get("student_answer"))
                        )
                        await crud_exam_sessions.log_student_interaction(db, session["_id"], log_item)
                
                # FIX: Buat broadcast message dengan struktur yang konsisten
                broadcast_message = {
                    "type": message.get("type"),  # violation_event, activity_event, dll
                    "violation_type": message.get("violation_type"),  # tab_switch, devtools_detected, dll
                    "activityType": message.get("activityType"),  # untuk activity_event
                    "severity": message.get("severity"),
                    "student_id": user_id,
                    "student_name": student_name,
                    "sessionId": message.get("sessionId"),
                    "examId": exam_id,
                    "timestamp": message.get("timestamp", datetime.utcnow().timestamp() * 1000),
                    "details": message.get("details", {}),
                    
                    # FIX: Tambahan field untuk debugging
                    "messageType": message.get("type"),  # Untuk backward compatibility
                    "full_name": student_name,
                    "raw_message": message  # Untuk debugging
                }
                
                # FIX: Kirim ke proctors dengan logging
                logger.info(f"Broadcasting message from student {user_id} to proctors in room {exam_id}: {broadcast_message.get('type')}")
                await manager.broadcast_to_proctors(exam_id, broadcast_message)
                
                # # FIX: Juga kirim ke semua admin untuk monitoring global
                # await manager.broadcast_to_roles(broadcast_message, target_roles=["admin"])

    except WebSocketDisconnect:
        logger.info(f"Student {user_id} disconnected from exam room {exam_id}")
        await manager.disconnect(user_id)