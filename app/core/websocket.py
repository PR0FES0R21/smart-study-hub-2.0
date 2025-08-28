# ==============================================================================
# File: app/core/websocket.py (Updated)
# Deskripsi: Enhanced WebSocket Manager with improved logging and race condition fixes
# ==============================================================================
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Optional
import json
import asyncio
import logging
import time
import uuid
from datetime import datetime
from app.core.redis_websocket import redis_bridge
from app.core.db import db
from app.crud.crud_users import get_user_by_id

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._redis_listener_started = False
        self._connection_versions: Dict[str, int] = {}  # Track connection versions to prevent race conditions

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
        """Mendaftarkan pengguna ke daftar koneksi aktif dengan enhanced logging dan race condition protection."""
        connection_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Ensure Redis bridge is initialized
        if not self._redis_listener_started:
            await self.initialize()
            
        try:
            await websocket.accept()
            
            # Get user details for enhanced logging
            user_details = await self._get_user_details(user_id)
            username = user_details.get("username", f"user_{user_id[:8]}")
            
            async with self._lock:
                # Increment connection version to prevent race conditions
                self._connection_versions[user_id] = self._connection_versions.get(user_id, 0) + 1
                current_version = self._connection_versions[user_id]
                
                # Disconnect existing connection if any
                if user_id in self.active_connections:
                    await self._force_disconnect_user_unsafe(user_id)
                
                self.active_connections[user_id] = {
                    "websocket": websocket,
                    "roles": roles,
                    "room_id": room_id,
                    "connected_at": time.time(),
                    "connection_id": connection_id,
                    "version": current_version,
                    "username": username,
                    "user_details": user_details
                }
            
            connection_time = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"🟢 USER_CONNECTED | user_id={user_id} | username={username} | "
                f"roles={roles} | room_id={room_id or 'lobby'} | "
                f"connection_id={connection_id} | total_active={len(self.active_connections)} | "
                f"connection_time={connection_time}ms"
            )
            
            # Send enhanced connection events AFTER user is added to active_connections
            await self._broadcast_user_connected_event(user_id, username, roles, room_id, connection_id)
            
        except Exception as e:
            logger.error(
                f"❌ CONNECTION_ERROR | user_id={user_id} | error={str(e)} | "
                f"connection_time={round((time.time() - start_time) * 1000, 2)}ms"
            )
            raise

    async def disconnect(self, user_id: str):
        """Menghapus pengguna dari daftar koneksi aktif dengan enhanced logging dan race condition protection."""
        disconnect_time = time.time()
        connection_info = None
        
        async with self._lock:
            if user_id in self.active_connections:
                connection_info = self.active_connections[user_id].copy()
                room_id = connection_info.get("room_id")
                username = connection_info.get("username", f"user_{user_id[:8]}")
                connection_id = connection_info.get("connection_id", "unknown")
                connected_duration = round(disconnect_time - connection_info.get("connected_at", disconnect_time), 2)
                
                del self.active_connections[user_id]
                
                logger.info(
                    f"🔴 USER_DISCONNECTED | user_id={user_id} | username={username} | "
                    f"room_id={room_id or 'lobby'} | connection_id={connection_id} | "
                    f"total_active={len(self.active_connections)} | duration={connected_duration}s"
                )
        
        # Send enhanced disconnect events OUTSIDE the lock to prevent deadlock
        if connection_info:
            await self._broadcast_user_disconnected_event(
                user_id, connection_info.get("username", f"user_{user_id[:8]}"),
                connection_info.get("roles", []),
                connection_info.get("room_id"),
                connection_info.get("connection_id", "unknown")
            )

    async def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details for enhanced logging and messaging."""
        try:
            user = await get_user_by_id(db, user_id)
            if user and user.get("profile_id"):
                # Get profile details
                profile = await db["profiles"].find_one({"_id": user["profile_id"]})
                return {
                    "username": profile.get("full_name", user.get("login_id", f"user_{user_id[:8]}")),
                    "email": user.get("email", ""),
                    "full_name": profile.get("full_name", "") if profile else "",
                    "roles": user.get("roles", [])
                }
        except Exception as e:
            logger.warning(f"Failed to get user details for {user_id}: {e}")
        
        return {
            "username": f"user_{user_id[:8]}",
            "email": "",
            "full_name": "",
            "roles": []
        }

    async def _force_disconnect_user_unsafe(self, user_id: str):
        """Force disconnect a user (internal method, assumes lock is held). Non-blocking version."""
        if user_id in self.active_connections:
            try:
                ws = self.active_connections[user_id]["websocket"]
                # Schedule close operation without waiting
                asyncio.create_task(self._close_websocket_safely(ws, user_id))
            except Exception as e:
                logger.warning(f"Error scheduling websocket close for user {user_id}: {e}")
            finally:
                del self.active_connections[user_id]
    
    async def _close_websocket_safely(self, websocket: WebSocket, user_id: str):
        """Safely close websocket without blocking."""
        try:
            await websocket.close()
        except Exception as e:
            logger.debug(f"Error closing websocket for user {user_id}: {e}")

    async def broadcast_to_roles(self, message: dict, target_roles: List[str]):
        """Mengirim pesan ke semua pengguna dengan peran tertentu dengan enhanced error handling dan race condition protection."""
        if not target_roles:
            return
            
        broadcast_id = str(uuid.uuid4())
        start_time = time.time()
        target_roles_set = set(target_roles)
        failed_users = []
        
        # Create snapshot with version checking to avoid race conditions
        async with self._lock:
            connections_snapshot = {}
            for user_id, conn_data in self.active_connections.items():
                if not target_roles_set.isdisjoint(conn_data.get("roles", [])):
                    # Include version info to detect stale connections
                    snapshot_data = conn_data.copy()
                    snapshot_data["snapshot_version"] = conn_data.get("version", 0)
                    connections_snapshot[user_id] = snapshot_data
        
        logger.info(
            f"📡 BROADCAST_START | broadcast_id={broadcast_id} | "
            f"message_type={message.get('type', 'unknown')} | "
            f"target_roles={target_roles} | recipients={len(connections_snapshot)}"
        )
        
        # Send messages without holding the lock
        successful_sends = 0
        for user_id, connection_data in connections_snapshot.items():
            try:
                # Validate connection is still active and version matches
                current_conn = self.active_connections.get(user_id)
                if (current_conn and
                    current_conn.get("version") == connection_data.get("snapshot_version")):
                    
                    await connection_data["websocket"].send_text(json.dumps(message))
                    successful_sends += 1
                    logger.debug(
                        f"📤 MESSAGE_SENT | user_id={user_id} | "
                        f"username={connection_data.get('username', 'unknown')} | "
                        f"message_type={message.get('type', 'unknown')}"
                    )
                else:
                    logger.debug(f"Skipping stale connection for user {user_id}")
                    
            except WebSocketDisconnect:
                logger.info(f"🔌 User {user_id} disconnected during broadcast")
                failed_users.append(user_id)
            except Exception as e:
                logger.error(f"❌ Failed to send message to user {user_id}: {e}")
                failed_users.append(user_id)
        
        # Clean up failed connections with version checking
        if failed_users:
            await self._cleanup_failed_connections(failed_users, connections_snapshot)
        
        broadcast_time = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"📡 BROADCAST_COMPLETE | broadcast_id={broadcast_id} | "
            f"successful={successful_sends}/{len(connections_snapshot)} | "
            f"failed={len(failed_users)} | time={broadcast_time}ms"
        )

    async def broadcast_to_proctors(self, room_id: str, message: dict):
        """Mengirim pesan hanya ke pengawas di dalam satu ruangan ujian dengan enhanced error handling."""
        if not room_id:
            return
            
        broadcast_id = str(uuid.uuid4())
        start_time = time.time()
        failed_users = []
        
        # Create snapshot with version checking
        async with self._lock:
            proctor_connections = {}
            for user_id, conn_data in self.active_connections.items():
                is_proctor = bool({"teacher", "admin"} & set(conn_data.get("roles", [])))
                if conn_data.get("room_id") == room_id and is_proctor:
                    snapshot_data = conn_data.copy()
                    snapshot_data["snapshot_version"] = conn_data.get("version", 0)
                    proctor_connections[user_id] = snapshot_data
        
        logger.debug(
            f"👨‍🏫 PROCTOR_BROADCAST | broadcast_id={broadcast_id} | "
            f"room_id={room_id} | message_type={message.get('type', 'unknown')} | "
            f"proctors={len(proctor_connections)}"
        )
        
        # Send messages with version validation
        successful_sends = 0
        for user_id, connection_data in proctor_connections.items():
            try:
                current_conn = self.active_connections.get(user_id)
                if (current_conn and
                    current_conn.get("version") == connection_data.get("snapshot_version")):
                    
                    await connection_data["websocket"].send_text(json.dumps(message))
                    successful_sends += 1
                else:
                    logger.debug(f"Skipping stale proctor connection for user {user_id}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to send message to proctor {user_id}: {e}")
                failed_users.append(user_id)
        
        # Clean up failed connections
        if failed_users:
            await self._cleanup_failed_connections(failed_users, proctor_connections)
        
        broadcast_time = round((time.time() - start_time) * 1000, 2)
        logger.debug(
            f"👨‍🏫 PROCTOR_BROADCAST_COMPLETE | broadcast_id={broadcast_id} | "
            f"successful={successful_sends}/{len(proctor_connections)} | time={broadcast_time}ms"
        )

    async def broadcast_presence(self, room_id: str):
        """Mengirim update jumlah peserta di ruangan ke pengawas dengan enhanced data."""
        if not room_id:
            return
        
        async with self._lock:
            proctor_count = 0
            student_count = 0
            proctors = []
            students = []
            
            for user_id, conn_data in self.active_connections.items():
                if conn_data.get("room_id") == room_id:
                    roles = set(conn_data.get("roles", []))
                    user_info = {
                        "user_id": user_id,
                        "username": conn_data.get("username", f"user_{user_id[:8]}"),
                        "connected_at": conn_data.get("connected_at", time.time())
                    }
                    
                    if {"teacher", "admin"} & roles:
                        proctor_count += 1
                        proctors.append(user_info)
                    elif "student" in roles:
                        student_count += 1
                        students.append(user_info)

        message = {
            "type": "presence_update",
            "room_id": room_id,
            "proctor_count": proctor_count,
            "student_count": student_count,
            "proctors": proctors,
            "students": students,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_proctors(room_id, message)

    async def broadcast_connection_stats_to_admins(self):
        """Mengirim statistik koneksi yang efisien ke admin (hanya count, tanpa detail user)."""
        async with self._lock:
            active_users_count = len(self.active_connections)
            users_by_role = {}
            users_by_room = {}
            admin_count = 0
            
            for user_id, conn_data in self.active_connections.items():
                # Count by roles
                for role in conn_data.get("roles", []):
                    users_by_role[role] = users_by_role.get(role, 0) + 1
                    if role == "admin":
                        admin_count += 1
                
                # Count by room
                room_id = conn_data.get("room_id", "lobby")
                users_by_room[room_id] = users_by_room.get(room_id, 0) + 1
        
        logger.info(f"📊 Sending connection stats to {admin_count} admins | total_users={active_users_count}")
        
        # Efficient message with only counts, no user details
        message = {
            "type": "connection_stats_update",
            "total_count": active_users_count,
            "users_by_role": users_by_role,
            "users_by_room": users_by_room,
            "timestamp": datetime.utcnow().isoformat()
        }
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

    async def get_all_active_users_details(self):
        """Get detailed list of all active users - hanya dipanggil ketika diminta."""
        async with self._lock:
            active_users = []
            
            for user_id, conn_data in self.active_connections.items():
                active_users.append({
                    "user_id": user_id,
                    "username": conn_data.get("username", f"user_{user_id[:8]}"),
                    "roles": conn_data.get("roles", []),
                    "room_id": conn_data.get("room_id", "lobby"),
                    "connected_at": conn_data.get("connected_at", time.time()),
                    "connection_id": conn_data.get("connection_id", "unknown"),
                    "connection_duration": round(time.time() - conn_data.get("connected_at", time.time()), 2)
                })
            
            return {
                "type": "all_active_users",
                "total_count": len(active_users),
                "users": active_users,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _cleanup_failed_connections(self, failed_users: List[str], connections_snapshot: Dict[str, Dict[str, Any]]):
        """Clean up failed connections with version checking to prevent race conditions."""
        cleanup_count = 0
        async with self._lock:
            for user_id in failed_users:
                current_conn = self.active_connections.get(user_id)
                snapshot_conn = connections_snapshot.get(user_id, {})
                
                # Only remove if the connection version matches (preventing race conditions)
                if (current_conn and
                    current_conn.get("version") == snapshot_conn.get("snapshot_version")):
                    del self.active_connections[user_id]
                    cleanup_count += 1
                    logger.debug(f"🧹 Cleaned up failed connection for user {user_id}")
                else:
                    logger.debug(f"Skipped cleanup for user {user_id} (version mismatch or already reconnected)")
        
        if cleanup_count > 0:
            logger.info(f"🧹 CLEANUP_COMPLETE | removed={cleanup_count}/{len(failed_users)} failed connections")

    async def _broadcast_user_connected_event(self, user_id: str, username: str, roles: List[str], room_id: str | None, connection_id: str):
        """Broadcast efficient user connected event - hanya data user yang connect."""
        try:
            # Get current connection count
            async with self._lock:
                total_connections = len(self.active_connections)
            
            logger.info(f"🔔 Broadcasting user connected event for {username} to admins")
            
            # Efficient event for admins - hanya data user yang connect + total count
            admin_message = {
                "type": "user_connected",
                "action": "connect",
                "user": {
                    "user_id": user_id,
                    "username": username,
                    "roles": roles,
                    "room_id": room_id or "lobby",
                    "connection_id": connection_id,
                    "connected_at": time.time()
                },
                "total_connections": total_connections,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.broadcast_to_roles(admin_message, target_roles=["admin"])
            
            # Send lightweight connection stats update
            await self.broadcast_connection_stats_to_admins()
            
            # Update room presence if in a room (hanya untuk room tertentu)
            if room_id:
                await self.broadcast_presence(room_id)
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting user connected event: {e}")

    async def _broadcast_user_disconnected_event(self, user_id: str, username: str, roles: List[str], room_id: str | None, connection_id: str):
        """Broadcast efficient user disconnected event - hanya data user yang disconnect."""
        try:
            # Get current connection count
            async with self._lock:
                total_connections = len(self.active_connections)
            
            logger.info(f"🔔 Broadcasting user disconnected event for {username} to admins")
            
            # Efficient event for admins - hanya data user yang disconnect + total count
            admin_message = {
                "type": "user_disconnected",
                "action": "disconnect",
                "user": {
                    "user_id": user_id,
                    "username": username,
                    "roles": roles,
                    "room_id": room_id or "lobby",
                    "connection_id": connection_id,
                    "disconnected_at": time.time()
                },
                "total_connections": total_connections,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.broadcast_to_roles(admin_message, target_roles=["admin"])
            
            # Send lightweight connection stats update
            await self.broadcast_connection_stats_to_admins()
            
            # Update room presence if was in a room (hanya untuk room tertentu)
            if room_id:
                await self.broadcast_presence(room_id)
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting user disconnected event: {e}")

    async def get_room_participants(self, room_id: str) -> Dict[str, Any]:
        """Get detailed information about participants in a specific room."""
        async with self._lock:
            participants = {
                "room_id": room_id,
                "proctors": [],
                "students": [],
                "total_count": 0
            }
            
            for user_id, conn_data in self.active_connections.items():
                if conn_data.get("room_id") == room_id:
                    user_info = {
                        "user_id": user_id,
                        "username": conn_data.get("username", f"user_{user_id[:8]}"),
                        "roles": conn_data.get("roles", []),
                        "connected_at": conn_data.get("connected_at", time.time()),
                        "connection_id": conn_data.get("connection_id", "unknown")
                    }
                    
                    roles = set(conn_data.get("roles", []))
                    if {"teacher", "admin"} & roles:
                        participants["proctors"].append(user_info)
                    elif "student" in roles:
                        participants["students"].append(user_info)
                    
                    participants["total_count"] += 1
            
            return participants

    async def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected."""
        async with self._lock:
            return user_id in self.active_connections

    async def get_user_connection_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information for a specific user."""
        async with self._lock:
            conn_data = self.active_connections.get(user_id)
            if conn_data:
                return {
                    "user_id": user_id,
                    "username": conn_data.get("username", f"user_{user_id[:8]}"),
                    "roles": conn_data.get("roles", []),
                    "room_id": conn_data.get("room_id"),
                    "connected_at": conn_data.get("connected_at", time.time()),
                    "connection_id": conn_data.get("connection_id", "unknown"),
                    "version": conn_data.get("version", 0)
                }
            return None

# Global instance
manager = ConnectionManager()
