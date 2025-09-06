# WebSocket Client Implementation Guide

## Problem Analysis from Logs

Your WebSocket system is working correctly, but **clients are not sending heartbeat messages**, causing them to be disconnected as "stale connections" after 90 seconds of inactivity.

## Required Client-Side Implementation

### 1. JavaScript WebSocket with Heartbeat

```javascript
class SmartWebSocket {
    constructor(token, endpoint = '/api/v1/ws/lobby') {
        this.token = token;
        this.endpoint = endpoint;
        this.ws = null;
        this.heartbeatInterval = null;
        this.reconnectInterval = null;
        this.heartbeatIntervalMs = 25000; // 25 seconds (less than server's 30s check)
        this.reconnectIntervalMs = 5000;   // 5 seconds
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
    }

    connect() {
        const wsUrl = `ws://your-server${this.endpoint}?token=${this.token}`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.reconnectAttempts = 0;
            this.startHeartbeat();
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = (event) => {
            console.log('🔌 WebSocket disconnected:', event.code, event.reason);
            this.stopHeartbeat();
            this.attemptReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
        };
    }
    
    startHeartbeat() {
        // Send heartbeat every 25 seconds
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.sendHeartbeat();
            }
        }, this.heartbeatIntervalMs);
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    sendHeartbeat() {
        const heartbeat = {
            type: 'heartbeat',
            timestamp: Date.now(),
            message_id: this.generateMessageId()
        };
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(heartbeat));
            console.log('💓 Heartbeat sent');
        }
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'heartbeat_ack':
                console.log('💓 Heartbeat acknowledged');
                break;
            case 'heartbeat_ping':
                // Server sent us a ping, respond with pong
                this.sendHeartbeatPong(data.timestamp);
                break;
            case 'connection_established':
            case 'lobby_connection_established':
                console.log('🎉 Connection established:', data);
                break;
            case 'user_connected':
            case 'user_disconnected':
                console.log('👥 User event:', data);
                // Handle user connection events for admin dashboard
                this.updateUserList(data);
                break;
            case 'bulk_update_progress':
                console.log('📊 Bulk update progress:', data);
                // Handle bulk operation progress
                this.updateProgress(data);
                break;
            default:
                console.log('📨 Message received:', data);
        }
    }
    
    sendHeartbeatPong(timestamp) {
        const pong = {
            type: 'heartbeat_pong',
            timestamp: timestamp,
            server_time: Date.now(),
            message_id: this.generateMessageId()
        };
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(pong));
            console.log('🏓 Heartbeat pong sent');
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectIntervalMs);
        } else {
            console.error('❌ Max reconnection attempts reached');
            // Show user notification about connection failure
            this.showConnectionError();
        }
    }
    
    generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Admin functions
    requestUserStats() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'request_stats',
                message_id: this.generateMessageId(),
                timestamp: Date.now()
            };
            this.ws.send(JSON.stringify(message));
        }
    }
    
    requestAllUsers() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'request_all_users',
                message_id: this.generateMessageId(),
                timestamp: Date.now()
            };
            this.ws.send(JSON.stringify(message));
        }
    }
    
    // Placeholder methods - implement based on your UI
    updateUserList(data) {
        // Update admin dashboard user list
        console.log('Updating user list:', data);
    }
    
    updateProgress(data) {
        // Update progress bars for bulk operations
        console.log('Updating progress:', data);
    }
    
    showConnectionError() {
        // Show user-friendly error message
        alert('Connection lost. Please refresh the page.');
    }
    
    disconnect() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
        }
    }
}

// Usage Example
const token = localStorage.getItem('access_token'); // Your JWT token
const wsClient = new SmartWebSocket(token);

// Connect when page loads
wsClient.connect();

// Disconnect when page unloads
window.addEventListener('beforeunload', () => {
    wsClient.disconnect();
});
```

### 2. React Hook Implementation

```javascript
import { useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (token) => {
    const wsRef = useRef(null);
    const heartbeatRef = useRef(null);
    const reconnectAttemptsRef = useRef(0);
    
    const connect = useCallback(() => {
        if (!token) return;
        
        const wsUrl = `ws://your-server/api/v1/ws/lobby?token=${token}`;
        wsRef.current = new WebSocket(wsUrl);
        
        wsRef.current.onopen = () => {
            console.log('✅ WebSocket connected');
            reconnectAttemptsRef.current = 0;
            startHeartbeat();
        };
        
        wsRef.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleMessage(data);
        };
        
        wsRef.current.onclose = () => {
            console.log('🔌 WebSocket disconnected');
            stopHeartbeat();
            attemptReconnect();
        };
        
    }, [token]);
    
    const startHeartbeat = useCallback(() => {
        heartbeatRef.current = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                    type: 'heartbeat',
                    timestamp: Date.now(),
                    message_id: `msg_${Date.now()}`
                }));
            }
        }, 25000); // 25 seconds
    }, []);
    
    const stopHeartbeat = useCallback(() => {
        if (heartbeatRef.current) {
            clearInterval(heartbeatRef.current);
            heartbeatRef.current = null;
        }
    }, []);
    
    const handleMessage = useCallback((data) => {
        switch(data.type) {
            case 'heartbeat_ack':
                console.log('💓 Heartbeat acknowledged');
                break;
            case 'heartbeat_ping':
                // Respond to server ping
                wsRef.current?.send(JSON.stringify({
                    type: 'heartbeat_pong',
                    timestamp: data.timestamp,
                    message_id: `pong_${Date.now()}`
                }));
                break;
            // Add other message handlers
        }
    }, []);
    
    const attemptReconnect = useCallback(() => {
        if (reconnectAttemptsRef.current < 5) {
            reconnectAttemptsRef.current++;
            setTimeout(connect, 5000);
        }
    }, [connect]);
    
    useEffect(() => {
        connect();
        
        return () => {
            stopHeartbeat();
            wsRef.current?.close();
        };
    }, [connect, stopHeartbeat]);
    
    return {
        sendMessage: (message) => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(message));
            }
        },
        isConnected: wsRef.current?.readyState === WebSocket.OPEN
    };
};
```

## Why This Fixes The Problem

1. **Prevents Stale Connections**: Client sends heartbeat every 25 seconds (before server's 90s timeout)
2. **Automatic Reconnection**: Reconnects when connection is lost (token expiry, network issues)
3. **Bidirectional Heartbeat**: Responds to server pings with pongs
4. **Better Error Handling**: Graceful handling of disconnections

## Server Configuration (Already Implemented)

Your server already has:
- ✅ 30-second heartbeat monitoring
- ✅ 90-second connection timeout
- ✅ Automatic stale connection cleanup
- ✅ Activity tracking on message receipt

## Implementation Steps

1. **Update your frontend JavaScript** to include the heartbeat implementation above
2. **Test connection stability** - admin should stay connected longer than 90 seconds
3. **Monitor logs** - you should see "💓 Heartbeat acknowledged" messages
4. **Test reconnection** - disconnect internet and reconnect to verify auto-reconnection

After implementing this, your `recipients=0` problem should be resolved because admin connections will stay alive and receive broadcasts properly.
