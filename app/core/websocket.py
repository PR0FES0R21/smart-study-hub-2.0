# ==============================================================================
# File: app/core/websocket.py (Updated)
# Deskripsi: Updated WebSocket Manager with Redis integration
# ==============================================================================
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json
import asyncio
import logging
from app.core.redis_websocket import redis_bridge

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._redis_listener_started = False

    async def initialize(self):
        """Initialize the connection manager and start Redis listener."""
        if not self._redis_listener_started:
            try:
                await redis_bridge.initialize()
                # Start Redis listener in background
                asyncio.create_task(redis_bridge.listen_for_messages(self))
                self._redis_listener_started = True
                logger.info("WebSocket manager initialized with Redis bridge")
            except Exception as e:
                logger.error(f"Failed to initialize WebSocket manager: {e}")

    async def connect(self, websocket: WebSocket, user_id: str, roles: List[str], room_id: str | None = None):
        """Mendaftarkan pengguna ke daftar koneksi aktif dengan error handling."""
        # Ensure Redis bridge is initialized
        if not self._redis_listener_started:
            await self.initialize()
            
        try:
            await websocket.accept()
            
            async with self._lock:
                # Disconnect existing connection if any
                if user_id in self.active_connections:
                    await self._force_disconnect_user(user_id)
                
                self.active_connections[user_id] = {
                    "websocket": websocket, 
                    "roles": roles, 
                    "room_id": room_id,
                    "connected_at": asyncio.get_event_loop().time()
                }
            
            logger.info(f"User {user_id} connected (Room: {room_id or 'Lobby'}). Total active: {len(self.active_connections)}")
            
            # Send updates
            await self.broadcast_active_users_to_admins()
            if room_id:
                await self.broadcast_presence(room_id)
                
        except Exception as e:
            logger.error(f"Error connecting user {user_id}: {e}")
            raise

    async def disconnect(self, user_id: str):
        """Menghapus pengguna dari daftar koneksi aktif dengan thread safety."""
        async with self._lock:
            if user_id in self.active_connections:
                room_id = self.active_connections[user_id].get("room_id")
                del self.active_connections[user_id]
                logger.info(f"User {user_id} disconnected. Total active: {len(self.active_connections)}")
                
                # Send updates outside the lock
                asyncio.create_task(self._post_disconnect_updates(room_id))

    async def _post_disconnect_updates(self, room_id: str | None):
        """Handle post-disconnect updates asynchronously."""
        try:
            await self.broadcast_active_users_to_admins()
            if room_id:
                await self.broadcast_presence(room_id)
        except Exception as e:
            logger.error(f"Error in post-disconnect updates: {e}")

    async def _force_disconnect_user(self, user_id: str):
        """Force disconnect a user (internal method, assumes lock is held)."""
        if user_id in self.active_connections:
            try:
                ws = self.active_connections[user_id]["websocket"]
                await ws.close()
            except Exception as e:
                logger.warning(f"Error closing websocket for user {user_id}: {e}")
            finally:
                del self.active_connections[user_id]

    async def broadcast_to_roles(self, message: dict, target_roles: List[str]):
        """Mengirim pesan ke semua pengguna dengan peran tertentu dengan error handling."""
        if not target_roles:
            return
            
        target_roles_set = set(target_roles)
        failed_users = []
        
        # Create snapshot to avoid lock during message sending
        async with self._lock:
            connections_snapshot = {
                user_id: conn_data.copy() 
                for user_id, conn_data in self.active_connections.items()
                if not target_roles_set.isdisjoint(conn_data.get("roles", []))
            }
        
        logger.debug(f"Broadcasting to {len(connections_snapshot)} users with roles {target_roles}")
        
        # Send messages without holding the lock
        for user_id, connection_data in connections_snapshot.items():
            try:
                await connection_data["websocket"].send_text(json.dumps(message))
                logger.debug(f"Message sent to user {user_id}: {message.get('type', 'unknown')}")
            except WebSocketDisconnect:
                logger.info(f"User {user_id} disconnected during broadcast")
                failed_users.append(user_id)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                failed_users.append(user_id)
        
        # Clean up failed connections
        if failed_users:
            async with self._lock:
                for user_id in failed_users:
                    if user_id in self.active_connections:
                        del self.active_connections[user_id]

    async def broadcast_to_proctors(self, room_id: str, message: dict):
        """Mengirim pesan hanya ke pengawas di dalam satu ruangan ujian."""
        if not room_id:
            return
            
        failed_users = []
        
        # Create snapshot
        async with self._lock:
            proctor_connections = {}
            for user_id, conn_data in self.active_connections.items():
                is_proctor = bool({"teacher", "admin"} & set(conn_data.get("roles", [])))
                if conn_data.get("room_id") == room_id and is_proctor:
                    proctor_connections[user_id] = conn_data.copy()
        
        # Send messages
        for user_id, connection_data in proctor_connections.items():
            try:
                await connection_data["websocket"].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to proctor {user_id}: {e}")
                failed_users.append(user_id)
        
        # Clean up failed connections
        if failed_users:
            async with self._lock:
                for user_id in failed_users:
                    if user_id in self.active_connections:
                        del self.active_connections[user_id]

    async def broadcast_presence(self, room_id: str):
        """Mengirim update jumlah peserta di ruangan ke pengawas."""
        if not room_id:
            return
        
        async with self._lock:
            proctor_count = 0
            student_count = 0
            
            for conn_data in self.active_connections.values():
                if conn_data.get("room_id") == room_id:
                    roles = set(conn_data.get("roles", []))
                    if {"teacher", "admin"} & roles:
                        proctor_count += 1
                    elif "student" in roles:
                        student_count += 1

        message = {
            "type": "presence_update", 
            "room_id": room_id,
            "proctor_count": proctor_count, 
            "student_count": student_count
        }
        await self.broadcast_to_proctors(room_id, message)

    async def broadcast_active_users_to_admins(self):
        """Menghitung dan mengirim jumlah pengguna aktif hanya ke admin."""
        async with self._lock:
            active_users_count = len(self.active_connections)
        
        message = {"type": "active_users_count", "count": active_users_count}
        await self.broadcast_to_roles(message, target_roles=["admin"])

    async def get_connection_stats(self):
        """Get connection statistics for monitoring."""
        async with self._lock:
            stats = {
                "total_connections": len(self.active_connections),
                "by_role": {},
                "by_room": {}
            }
            
            for conn_data in self.active_connections.values():
                # Count by roles
                for role in conn_data.get("roles", []):
                    stats["by_role"][role] = stats["by_role"].get(role, 0) + 1
                
                # Count by room
                room_id = conn_data.get("room_id", "lobby")
                stats["by_room"][room_id] = stats["by_room"].get(room_id, 0) + 1
            
            return stats

# Global instance
manager = ConnectionManager()
