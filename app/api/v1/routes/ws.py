# ==============================================================================
# File: app/api/v1/routes/ws.py (Enhanced dengan improved logging dan error handling)
# Deskripsi: Enhanced WebSocket endpoints dengan comprehensive logging dan error handling
# ==============================================================================
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import logging
import time
import uuid
from datetime import datetime
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
    """Enhanced WebSocket endpoint dengan comprehensive logging dan error handling."""
    session_id = str(uuid.uuid4())
    start_time = time.time()
    
    if not user:
        logger.warning(f"🚫 WS_AUTH_FAILED | session_id={session_id} | reason=no_user_data")
        return # Jika otentikasi gagal, dependency akan menutup koneksi

    user_id = str(user["_id"])
    roles = user.get("roles", [])
    username = user.get("login_id", f"user_{user_id[:8]}")
    
    logger.info(
        f"  WS_CONNECTION_ATTEMPT | session_id={session_id} | user_id={user_id} | "
        f"username={username} | roles={roles}"
    )
    
    try:
        await manager.connect(websocket, user_id, roles)
        
        connection_time = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"WS_CONNECTION_SUCCESS | session_id={session_id} | user_id={user_id} | "
            f"connection_time={connection_time}ms"
        )
        
        # Send enhanced welcome message
        welcome_message = {
            "type": "connection_established",
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "session_id": session_id,
            "server_time": datetime.utcnow().isoformat(),
            "message": "WebSocket connection established successfully"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        message_count = 0
        while True:
            # Menerima pesan dari client
            data = await websocket.receive_text()
            message_count += 1
            
            try:
                message = json.loads(data)
                logger.debug(
                    f"📨 WS_MESSAGE_RECEIVED | session_id={session_id} | user_id={user_id} | "
                    f"message_type={message.get('type', 'unknown')} | message_count={message_count}"
                )
                # Update user activity on each message
                await manager.update_user_activity(user_id)
                await handle_incoming_message(websocket, user_id, roles, message, session_id)
                
            except json.JSONDecodeError as e:
                logger.warning(
                    f"❌ WS_INVALID_JSON | session_id={session_id} | user_id={user_id} | "
                    f"error={str(e)} | data={data[:100]}..."
                )
                error_message = {
                    "type": "error",
                    "error_code": "INVALID_JSON",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
                
            except Exception as e:
                logger.error(
                    f"❌ WS_MESSAGE_ERROR | session_id={session_id} | user_id={user_id} | "
                    f"error={str(e)} | message_count={message_count}"
                )
                error_message = {
                    "type": "error",
                    "error_code": "MESSAGE_PROCESSING_ERROR",
                    "message": "Error processing message",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
                
    except WebSocketDisconnect:
        session_duration = round(time.time() - start_time, 2)
        logger.info(
            f"  WS_DISCONNECT | session_id={session_id} | user_id={user_id} | "
            f"duration={session_duration}s | messages_processed={message_count}"
        )
    except Exception as e:
        session_duration = round(time.time() - start_time, 2)
        logger.error(
            f"💥 WS_ERROR | session_id={session_id} | user_id={user_id} | "
            f"error={str(e)} | duration={session_duration}s"
        )
    finally:
        await manager.disconnect(user_id)

@router.websocket("/lobby")
async def websocket_lobby(
    websocket: WebSocket,
    user: dict = Depends(deps.get_current_user_for_ws)
):
    """Enhanced WebSocket endpoint untuk lobby dengan comprehensive logging."""
    session_id = str(uuid.uuid4())
    start_time = time.time()
    
    if not user:
        logger.warning(f"🚫 WS_LOBBY_AUTH_FAILED | session_id={session_id} | reason=no_user_data")
        return

    user_id = str(user["_id"])
    roles = user.get("roles", [])
    username = user.get("login_id", f"user_{user_id[:8]}")
    
    logger.info(
        f"WS_LOBBY_CONNECTION_ATTEMPT | session_id={session_id} | user_id={user_id} | "
        f"username={username} | roles={roles}"
    )
    
    try:
        await manager.connect(websocket, user_id, roles, room_id=None)
        
        connection_time = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"WS_LOBBY_CONNECTION_SUCCESS | session_id={session_id} | user_id={user_id} | "
            f"connection_time={connection_time}ms"
        )
        
        # Send enhanced welcome message for lobby
        welcome_message = {
            "type": "lobby_connection_established",
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "session_id": session_id,
            "server_time": datetime.utcnow().isoformat(),
            "message": "Connected to lobby successfully"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        message_count = 0
        while True:
            data = await websocket.receive_text()
            message_count += 1
            
            try:
                message = json.loads(data)
                logger.debug(
                    f"📨 WS_LOBBY_MESSAGE | session_id={session_id} | user_id={user_id} | "
                    f"message_type={message.get('type', 'unknown')} | message_count={message_count}"
                )
                # Update user activity on each message
                await manager.update_user_activity(user_id)
                await handle_lobby_message(websocket, user_id, roles, message, session_id)
                
            except json.JSONDecodeError as e:
                logger.warning(
                    f"❌ WS_LOBBY_INVALID_JSON | session_id={session_id} | user_id={user_id} | "
                    f"error={str(e)} | data={data[:100]}..."
                )
            except Exception as e:
                logger.error(
                    f"❌ WS_LOBBY_MESSAGE_ERROR | session_id={session_id} | user_id={user_id} | "
                    f"error={str(e)} | message_count={message_count}"
                )
                
    except WebSocketDisconnect:
        session_duration = round(time.time() - start_time, 2)
        logger.info(
            f"  WS_LOBBY_DISCONNECT | session_id={session_id} | user_id={user_id} | "
            f"duration={session_duration}s | messages_processed={message_count}"
        )
    except Exception as e:
        session_duration = round(time.time() - start_time, 2)
        logger.error(
            f"💥 WS_LOBBY_ERROR | session_id={session_id} | user_id={user_id} | "
            f"error={str(e)} | duration={session_duration}s"
        )
    finally:
        await manager.disconnect(user_id)

async def handle_incoming_message(websocket: WebSocket, user_id: str, roles: list, message: dict, session_id: str):
    """Handle pesan masuk dari WebSocket client dengan enhanced logging."""
    
    message_type = message.get("type", "")
    message_id = message.get("message_id", str(uuid.uuid4()))
    
    logger.debug(
        f"🔄 WS_HANDLE_MESSAGE | session_id={session_id} | user_id={user_id} | "
        f"message_type={message_type} | message_id={message_id}"
    )
    
    if message_type == "ping":
        # Respond to ping with pong
        pong_message = {
            "type": "pong",
            "timestamp": message.get("timestamp"),
            "message_id": message_id,
            "server_time": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(pong_message))
        logger.debug(f"🏓 WS_PONG_SENT | session_id={session_id} | user_id={user_id}")
        
    elif message_type == "admin_broadcast" and "admin" in roles:
        # Admin broadcast ke roles tertentu
        target_roles = message.get("target_roles", ["student", "teacher"])
        broadcast_content = {
            "type": "admin_message",
            "message": message.get("message", ""),
            "sender": user_id,
            "timestamp": message.get("timestamp"),
            "message_id": message_id,
            "server_time": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_roles(broadcast_content, target_roles=target_roles)
        logger.info(
            f"📢 WS_ADMIN_BROADCAST | session_id={session_id} | user_id={user_id} | "
            f"target_roles={target_roles} | message_id={message_id}"
        )
        
    elif message_type == "request_stats" and "admin" in roles:
        # Send connection statistics to admin (menggunakan method baru yang efisien)
        stats_data = await manager._get_connection_stats_data()
        stats_message = {
            "type": "connection_stats_response",
            "stats": stats_data,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(stats_message))
        logger.info(f"📊 WS_STATS_SENT | session_id={session_id} | user_id={user_id}")
        
    elif message_type == "request_all_users" and "admin" in roles:
        # Send detailed list of all active users (on-demand only)
        all_users_data = await manager.get_all_active_users_details()
        all_users_message = {
            **all_users_data,
            "message_id": message_id
        }
        await websocket.send_text(json.dumps(all_users_message))
        logger.info(f"👥 WS_ALL_USERS_SENT | session_id={session_id} | user_id={user_id} | total_users={all_users_data['total_count']}")
        
    elif message_type == "heartbeat" or message_type == "heartbeat_pong":
        # Simple heartbeat response or pong acknowledgment
        if message_type == "heartbeat":
            # Client sent heartbeat, respond with ack
            heartbeat_response = {
                "type": "heartbeat_ack",
                "timestamp": message.get("timestamp"),
                "message_id": message_id,
                "server_time": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(heartbeat_response))
            logger.debug(f"💓 WS_HEARTBEAT_ACK | session_id={session_id} | user_id={user_id}")
        else:
            # Client responded to our ping
            logger.debug(f"💓 WS_HEARTBEAT_PONG_RECEIVED | session_id={session_id} | user_id={user_id}")
        
        # Both cases reset heartbeat failure count (handled by update_user_activity above)
        
    else:
        # Unknown message type atau tidak ada permission
        logger.warning(
            f"⚠️ WS_UNKNOWN_MESSAGE | session_id={session_id} | user_id={user_id} | "
            f"message_type={message_type} | roles={roles} | has_permission={message_type in ['ping', 'heartbeat']}"
        )
        
        # Send error response for unknown message types
        error_response = {
            "type": "error",
            "error_code": "UNKNOWN_MESSAGE_TYPE" if message_type else "MISSING_MESSAGE_TYPE",
            "message": f"Unknown or unauthorized message type: {message_type}",
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_response))

async def handle_lobby_message(websocket: WebSocket, user_id: str, roles: list, message: dict, session_id: str):
    """Handle pesan dari lobby WebSocket dengan enhanced logging."""
    
    message_type = message.get("type", "")
    message_id = message.get("message_id", str(uuid.uuid4()))
    
    logger.debug(
        f"WS_LOBBY_HANDLE | session_id={session_id} | user_id={user_id} | "
        f"message_type={message_type} | message_id={message_id}"
    )
    
    if message_type == "ping":
        pong_message = {
            "type": "pong",
            "timestamp": message.get("timestamp"),
            "message_id": message_id,
            "server_time": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(pong_message))
        logger.debug(f"🏓 WS_LOBBY_PONG | session_id={session_id} | user_id={user_id}")
        
    elif message_type == "heartbeat" or message_type == "heartbeat_pong":
        # Simple heartbeat response or pong acknowledgment for lobby
        if message_type == "heartbeat":
            heartbeat_response = {
                "type": "heartbeat_ack",
                "timestamp": message.get("timestamp"),
                "message_id": message_id,
                "server_time": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(heartbeat_response))
            logger.debug(f"💓 WS_LOBBY_HEARTBEAT_ACK | session_id={session_id} | user_id={user_id}")
        else:
            # Client responded to our ping
            logger.debug(f"💓 WS_LOBBY_HEARTBEAT_PONG | session_id={session_id} | user_id={user_id}")
        
    else:
        logger.warning(
            f"⚠️ WS_LOBBY_UNKNOWN | session_id={session_id} | user_id={user_id} | "
            f"message_type={message_type} | roles={roles}"
        )
        
        # Send error response for unknown message types
        error_response = {
            "type": "error",
            "error_code": "UNKNOWN_LOBBY_MESSAGE_TYPE",
            "message": f"Unknown lobby message type: {message_type}",
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_response))
