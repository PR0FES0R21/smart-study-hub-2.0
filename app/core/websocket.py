# ==============================================================================
# File: app/core/websocket.py
# Deskripsi: Manajer koneksi untuk WebSocket.
# --- DIUBAH TOTAL --- (Implementasi arsitektur yang lebih sederhana dan benar)
# ==============================================================================
from fastapi import WebSocket
from typing import Dict, Any, List
import json

class ConnectionManager:
    def __init__(self):
        # Satu sumber kebenaran: { "user_id": {"websocket": ws, "roles": [...], "room_id": "..." atau None } }
        self.active_connections: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, roles: List[str], room_id: str | None = None):
        """Mendaftarkan pengguna ke daftar koneksi aktif."""
        await websocket.accept()
        self.active_connections[user_id] = {"websocket": websocket, "roles": roles, "room_id": room_id}
        print(f"User {user_id} terhubung (Room: {room_id or 'Lobby'}). Total pengguna aktif: {len(self.active_connections)}")
        
        # Kirim update ke admin dan ke ruangan ujian jika ada
        await self.broadcast_active_users_to_admins()
        if room_id:
            await self.broadcast_presence(room_id)

    async def disconnect(self, user_id: str):
        """Menghapus pengguna dari daftar koneksi aktif."""
        if user_id in self.active_connections:
            room_id = self.active_connections[user_id].get("room_id")
            del self.active_connections[user_id]
            print(f"User {user_id} terputus. Total pengguna aktif: {len(self.active_connections)}")
            
            # Kirim update ke admin dan ke ruangan ujian jika ada
            await self.broadcast_active_users_to_admins()
            if room_id:
                await self.broadcast_presence(room_id)

    async def broadcast_to_roles(self, message: dict, target_roles: List[str]):
        """Mengirim pesan ke semua pengguna dengan peran tertentu, di mana pun mereka berada."""
        target_roles_set = set(target_roles)
        for connection_data in self.active_connections.values():
            if not target_roles_set.isdisjoint(connection_data.get("roles", [])):
                await connection_data["websocket"].send_text(json.dumps(message))

    async def broadcast_to_proctors(self, room_id: str, message: dict):
        """Mengirim pesan hanya ke pengawas di dalam satu ruangan ujian."""
        if not room_id: return
        for connection_data in self.active_connections.values():
            is_proctor = "teacher" in connection_data.get("roles", []) or "admin" in connection_data.get("roles", [])
            if connection_data.get("room_id") == room_id and is_proctor:
                await connection_data["websocket"].send_text(json.dumps(message))

    async def broadcast_presence(self, room_id: str):
        """Mengirim update jumlah peserta di ruangan ke pengawas."""
        if not room_id: return
        
        proctor_count = 0
        student_count = 0
        for conn_data in self.active_connections.values():
            if conn_data.get("room_id") == room_id:
                if "teacher" in conn_data.get("roles", []) or "admin" in conn_data.get("roles", []):
                    proctor_count += 1
                elif "student" in conn_data.get("roles", []):
                    student_count += 1

        message = {"type": "presence_update", "proctor_count": proctor_count, "student_count": student_count}
        await self.broadcast_to_proctors(room_id, message)

    async def broadcast_active_users_to_admins(self):
        """Menghitung dan mengirim jumlah pengguna aktif hanya ke admin."""
        active_users_count = len(self.active_connections)
        message = {"type": "active_users_count", "count": active_users_count}
        await self.broadcast_to_roles(message, target_roles=["admin"])

manager = ConnectionManager()