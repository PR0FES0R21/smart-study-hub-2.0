#==============================================================================
# File: app/core/redis_websocket.py
# Deskripsi: Redis-based WebSocket communication untuk cross-process messaging
# ==============================================================================
import redis.asyncio as redis
import json
import asyncio
import logging
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisWebSocketBridge:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.is_listening = False
        
    async def initialize(self):
        """Initialize Redis connection for WebSocket bridge."""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("websocket_messages")
            logger.info("Redis WebSocket bridge initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis WebSocket bridge: {e}")
            raise
    
    async def publish_message(self, message: Dict[str, Any]):
        """Publish message to Redis channel for WebSocket broadcast."""
        try:
            if not self.redis_client:
                await self.initialize()
            
            await self.redis_client.publish("websocket_messages", json.dumps(message))
            logger.debug(f"Published message to Redis: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish message to Redis: {e}")
    
    async def listen_for_messages(self, websocket_manager):
        """Listen for messages from Redis and broadcast via WebSocket."""
        if self.is_listening:
            return
            
        self.is_listening = True
        logger.info("Starting Redis message listener")
        
        try:
            if not self.pubsub:
                await self.initialize()
                
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._handle_redis_message(data, websocket_manager)
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            self.is_listening = False
    
    async def _handle_redis_message(self, data: Dict[str, Any], websocket_manager):
        """Handle incoming Redis message and route to appropriate WebSocket broadcast."""
        message_type = data.get("broadcast_type", "roles")
        
        if message_type == "roles":
            target_roles = data.get("target_roles", [])
            message_content = data.get("message", {})
            await websocket_manager.broadcast_to_roles(message_content, target_roles)
            
        elif message_type == "proctors":
            room_id = data.get("room_id")
            message_content = data.get("message", {})
            if room_id:
                await websocket_manager.broadcast_to_proctors(room_id, message_content)
                
        logger.debug(f"Handled Redis message: {data.get('message', {}).get('type', 'unknown')}")
    
    async def close(self):
        """Close Redis connections."""
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe("websocket_messages")
                await self.pubsub.close()
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Redis WebSocket bridge closed")
        except Exception as e:
            logger.error(f"Error closing Redis WebSocket bridge: {e}")

# Global instance
redis_bridge = RedisWebSocketBridge()
