# ==============================================================================
# File: app/api/v1/routes/ws.py (Updated untuk Redis bridge support)
# Deskripsi: Endpoint WebSocket yang sudah ada dengan Redis bridge support
# ==============================================================================
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import logging
from app.core.websocket import manager
from app.api.v1 import deps

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    # Menggunakan dependency yang sudah ada untuk otentikasi WebSocket
    user: dict = Depends(deps.get_current_user_for_ws)
):
    """WebSocket endpoint utama dengan Redis bridge support."""
    if not user: 
        return # Jika otentikasi gagal, dependency akan menutup koneksi

    user_id = str(user["_id"])
    roles = user.get("roles", [])
    
    logger.info(f"WebSocket connection attempt: user_id={user_id}, roles={roles}")
    
    await manager.connect(websocket, user_id, roles)
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "user_id": user_id,
            "roles": roles,
            "message": "WebSocket connection established successfully"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        while True:
            # Menerima pesan dari client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_incoming_message(websocket, user_id, roles, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON dari user {user_id}: {data}")
                error_message = {
                    "type": "error",
                    "message": "Invalid JSON format"
                }
                await websocket.send_text(json.dumps(error_message))
            except Exception as e:
                logger.error(f"Error handling message dari user {user_id}: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error untuk user {user_id}: {e}")
    finally:
        await manager.disconnect(user_id)

@router.websocket("/lobby")
async def websocket_lobby(
    websocket: WebSocket,
    user: dict = Depends(deps.get_current_user_for_ws)
):
    """WebSocket endpoint untuk lobby dengan Redis bridge support."""
    if not user: 
        return

    user_id = str(user["_id"])
    roles = user.get("roles", [])
    
    logger.info(f"WebSocket lobby connection: user_id={user_id}, roles={roles}")
    
    await manager.connect(websocket, user_id, roles, room_id=None)
    
    try:
        # Send welcome message for lobby
        welcome_message = {
            "type": "lobby_connection_established",
            "user_id": user_id,
            "roles": roles,
            "message": "Connected to lobby successfully"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_lobby_message(websocket, user_id, roles, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON dari lobby user {user_id}: {data}")
            except Exception as e:
                logger.error(f"Error handling lobby message dari user {user_id}: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket lobby disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket lobby error untuk user {user_id}: {e}")
    finally:
        await manager.disconnect(user_id)

async def handle_incoming_message(websocket: WebSocket, user_id: str, roles: list, message: dict):
    """Handle pesan masuk dari WebSocket client."""
    
    message_type = message.get("type", "")
    
    if message_type == "ping":
        # Respond to ping with pong
        pong_message = {"type": "pong", "timestamp": message.get("timestamp")}
        await websocket.send_text(json.dumps(pong_message))
        
    elif message_type == "admin_broadcast" and "admin" in roles:
        # Admin broadcast ke roles tertentu
        target_roles = message.get("target_roles", ["student", "teacher"])
        broadcast_content = {
            "type": "admin_message", 
            "message": message.get("message", ""),
            "sender": user_id,
            "timestamp": message.get("timestamp")
        }
        await manager.broadcast_to_roles(broadcast_content, target_roles=target_roles)
        
    elif message_type == "request_stats" and "admin" in roles:
        # Send connection statistics to admin
        stats = await manager.get_connection_stats()
        stats_message = {
            "type": "connection_stats",
            "data": stats
        }
        await websocket.send_text(json.dumps(stats_message))
        
    elif message_type == "heartbeat":
        # Simple heartbeat response
        heartbeat_response = {
            "type": "heartbeat_ack",
            "timestamp": message.get("timestamp")
        }
        await websocket.send_text(json.dumps(heartbeat_response))
        
    else:
        # Unknown message type atau tidak ada permission
        logger.warning(f"Unknown/unauthorized message type '{message_type}' dari user {user_id} dengan roles {roles}")

async def handle_lobby_message(websocket: WebSocket, user_id: str, roles: list, message: dict):
    """Handle pesan dari lobby WebSocket."""
    
    message_type = message.get("type", "")
    
    if message_type == "ping":
        pong_message = {"type": "pong", "timestamp": message.get("timestamp")}
        await websocket.send_text(json.dumps(pong_message))
        
    elif message_type == "heartbeat":
        heartbeat_response = {
            "type": "heartbeat_ack", 
            "timestamp": message.get("timestamp")
        }
        await websocket.send_text(json.dumps(heartbeat_response))
