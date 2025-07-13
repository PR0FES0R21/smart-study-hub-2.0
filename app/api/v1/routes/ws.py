# ==============================================================================
# File: app/api/v1/routes/ws.py
# Deskripsi: Endpoint untuk koneksi WebSocket.
# --- DITAMBAHKAN ---
# ==============================================================================
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket import manager
from app.api.v1 import deps

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    # Menggunakan dependency baru untuk otentikasi WebSocket
    user: dict = Depends(deps.get_current_user_for_ws)
):
    if not user: return # Jika otentikasi gagal, dependency akan menutup koneksi

    user_id = str(user["_id"])
    roles = user.get("roles", [])
    
    await manager.connect(websocket, user_id, roles)
    try:
        while True:
            # Biarkan koneksi terbuka untuk menerima pesan jika dibutuhkan
            data = await websocket.receive_text()
            # Contoh: Admin bisa mengirim broadcast dari sini
            if "admin" in roles:
                await manager.broadcast_to_roles({"type": "admin_message", "message": data}, target_roles=["student", "teacher"])
    except WebSocketDisconnect:
        await manager.disconnect(user_id)

@router.websocket("/lobby")
async def websocket_lobby(
    websocket: WebSocket,
    user: dict = Depends(deps.get_current_user_for_ws)
):
    if not user: return

    user_id = str(user["_id"])
    roles = user.get("roles", [])
    
    await manager.connect(websocket, user_id, roles, room_id=None)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(user_id)