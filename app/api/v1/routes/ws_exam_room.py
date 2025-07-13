# ==============================================================================
# File: app/api/v1/routes/ws_exam_room.py
# Deskripsi: Endpoint untuk koneksi WebSocket ke Ruang Ujian.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json

from app.core.websocket import manager
from app.api.v1 import deps
from app.crud import crud_exam_sessions
from app.schemas.exam_session import InteractionLogItem
from app.core.db import db
from datetime import datetime
from bson import ObjectId


router = APIRouter()

@router.websocket("/exam-room/{exam_id}")
async def websocket_exam_room(
    websocket: WebSocket,
    exam_id: str,
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
            
            if participant_role == "student":
                session = await db["exam_sessions"].find_one({"exam_id": ObjectId(exam_id), "student_id": user["_id"]})
                if session:
                    log_item = InteractionLogItem(
                        timestamp=datetime.utcnow(),
                        question_id=message.get("details", {}).get("question_id"),
                        displayed_position=message.get("details", {}).get("displayed_position"),
                        action=message.get("type"),
                        student_answer=message.get("details", {}).get("answer")
                    )
                    await crud_exam_sessions.log_student_interaction(db, session["_id"], log_item)
                
                broadcast_message = {
                    "type": message.get("type"),
                    "student_id": user_id,
                    "student_name": (await db["profiles"].find_one({"user_id": user["_id"]})).get("full_name"),
                    "details": message.get("details")
                }
                await manager.broadcast_to_proctors(exam_id, broadcast_message)

    except WebSocketDisconnect:
        await manager.disconnect(user_id)