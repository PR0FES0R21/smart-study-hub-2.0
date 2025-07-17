# ==============================================================================
# File: app/core/cache.py
# Deskripsi: Utilitas untuk mengelola cache di Redis.
# --- DITAMBAHKAN ---
# ==============================================================================
import json
from .db import redis_client
from typing import Optional

async def get_cache(key: str):
    """Mengambil data dari cache Redis."""
    cached_data = await redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)
    return None

async def set_cache(key: str, data: any, ttl: Optional[int] = None):
    """Menyimpan data ke cache Redis."""
    # Kita menggunakan json.dumps untuk menyimpan list/dict sebagai string
    await redis_client.set(key, json.dumps(data, default=str), ex=ttl)

async def invalidate_cache(key_pattern: str):
    """Menghapus cache berdasarkan pola kunci (misal: 'analytics:*')."""
    keys_to_delete = []
    async for key in redis_client.scan_iter(key_pattern):
        keys_to_delete.append(key)
    
    if keys_to_delete:
        await redis_client.delete(*keys_to_delete)
        print(f"Cache invalidated for keys: {keys_to_delete}")