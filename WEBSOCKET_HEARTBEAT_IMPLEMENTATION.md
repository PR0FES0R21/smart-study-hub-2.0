# 🚨 WEBSOCKET HEARTBEAT IMPLEMENTATION - INSTRUKSI UNTUK TIM FRONTEND

## 📋 **MASALAH YANG TERJADI**

**Status**: Admin sering disconnect dari WebSocket dan tidak menerima real-time notifications.

**Root Cause**: Client tidak mengirim heartbeat ke server, sehingga server menganggap connection "stale" setelah 5-10 menit tidak aktif (tergantung role user).

**Dari Server Logs**:
- `STALE_CONNECTION | inactive_for=301s | role=user | timeout_threshold=300s` - User timeout setelah 5 menit
- `STALE_CONNECTION | inactive_for=601s | role=admin | timeout_threshold=600s` - Admin timeout setelah 10 menit
- `recipients=0` dalam broadcasts - Tidak ada admin yang connected

---

## 🎯 **WEBSOCKET ENDPOINTS YANG ADA**

Berdasarkan analisis backend, sistem memiliki **3 WebSocket endpoints**:

### 1. `/api/v1/ws/lobby`
- **Fungsi**: Admin dashboard monitoring, user presence
- **Authentication**: Query parameter `?token=JWT_TOKEN`
- **Messages yang diterima**: `user_connected`, `user_disconnected`, `bulk_update_progress`, `connection_stats_response`, `all_active_users`

### 2. `/api/v1/ws` 
- **Fungsi**: General WebSocket connection
- **Authentication**: Query parameter `?token=JWT_TOKEN`
- **Messages yang diterima**: `admin_message`, `connection_stats_response`, `all_active_users`

### 3. `/api/v1/ws/exam-room/{exam_id}`
- **Fungsi**: Exam monitoring dan proctoring
- **Authentication**: Query parameter `?token=JWT_TOKEN`
- **Messages yang diterima**: `violation_event`, `activity_event`, `room_user_event`

---

## 🛠️ **YANG PERLU DIIMPLEMENTASIKAN**

### **HEARTBEAT SYSTEM** (KUNCI UTAMA)

Server menjalankan heartbeat monitor setiap 60 detik dengan timeout:
- **Students/Teachers**: 5 menit (300 detik) tidak aktif
- **Admin**: 10 menit (600 detik) tidak aktif

#### **Client Requirements**:

1. **Kirim Heartbeat Regular**:
   - **Interval**: Setiap 50 detik (server check setiap 60 detik)
   - **Message format**:
     ```json
     {
       "type": "heartbeat",
       "timestamp": 1694012345000,
       "message_id": "msg_unique_id"
     }
     ```

2. **Handle Server Responses**:
   - **Heartbeat ACK**: Server kirim `{"type": "heartbeat_ack"}` - log ke console
   - **Server Ping**: Server kirim `{"type": "heartbeat_ping", "timestamp": xxx}`
   - **Client Response**: Balas dengan:
     ```json
     {
       "type": "heartbeat_pong", 
       "timestamp": original_timestamp,
       "server_time": current_time,
       "message_id": "pong_unique_id"
     }
     ```

3. **Activity Tracking**:
   - Setiap kali client mengirim message apapun, server update "last_activity"
   - Heartbeat atau message apapun reset timeout counter

---

## 🔗 **CONNECTION MANAGEMENT**

### **WebSocket URL Format**:
```
ws://localhost:8000/api/v1/ws/lobby?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### **Connection Lifecycle**:
1. **Connect**: Kirim JWT token via query parameter
2. **Welcome Message**: Server kirim connection established message
3. **Start Heartbeat**: Mulai kirim heartbeat setiap 25 detik
4. **Handle Messages**: Parse dan process incoming messages
5. **Disconnect**: Stop heartbeat, cleanup resources

### **Auto-Reconnection Requirements**:
- **Trigger**: Saat connection lost (network issue, server restart)
- **Max Attempts**: 5 kali
- **Delay**: 5 detik pertama, kemudian exponential backoff
- **Reset**: Reset attempt counter saat berhasil connect

---

## 📨 **MESSAGE HANDLING**

### **Outgoing Messages** (Client → Server):

#### **For Admin Dashboard** (`/api/v1/ws/lobby`):
```json
// Request connection statistics
{"type": "request_stats", "message_id": "unique_id", "timestamp": 1694012345000}

// Request all active users  
{"type": "request_all_users", "message_id": "unique_id", "timestamp": 1694012345000}

// Admin broadcast (if admin role)
{
  "type": "admin_broadcast",
  "target_roles": ["student", "teacher"], 
  "message": "System maintenance in 10 minutes",
  "message_id": "unique_id",
  "timestamp": 1694012345000
}
```

#### **For Exam Room** (`/api/v1/ws/exam-room/{exam_id}`):
```json
// Student violation report
{
  "type": "violation_event",
  "violation_type": "tab_switch", 
  "severity": "high",
  "details": {"previous_tab": "exam", "new_tab": "google.com"},
  "sessionId": "session_id",
  "timestamp": 1694012345000
}

// Student activity report
{
  "type": "activity_event", 
  "activityType": "answer_changed",
  "details": {"question_id": "q1", "answer": "B"},
  "sessionId": "session_id", 
  "timestamp": 1694012345000
}
```

### **Incoming Messages** (Server → Client):

#### **From Admin Dashboard**:
```json
// User connected event
{
  "type": "user_connected",
  "user": {"user_id": "xxx", "username": "John", "roles": ["student"]},
  "stats": {"total_count": 5, "users_by_role": {"admin": 1, "student": 4}}
}

// Bulk operation progress
{
  "type": "bulk_update_progress", 
  "operation": "teaching_assignments",
  "progress": 60,
  "total": 100,
  "current_step": "Creating assignment 6 of 10"
}
```

#### **From Exam Room**:
```json
// Student violation detected
{
  "type": "violation_event",
  "student_id": "xxx",
  "student_name": "John Doe", 
  "violation_type": "tab_switch",
  "severity": "high",
  "examId": "exam123",
  "timestamp": 1694012345000
}

// Room user event (for proctors only)
{
  "type": "room_user_event",
  "action": "connected",
  "user": {"user_id": "xxx", "username": "John", "user_type": "student"},
  "room_stats": {"proctor_count": 1, "student_count": 3}
}
```

---

## 🧪 **TESTING & VALIDATION**

### **Console Logs yang Harus Terlihat**:
```
✅ WebSocket connected: /api/v1/ws/lobby
💓 Heartbeat sent: /api/v1/ws/lobby (every 50 seconds)
💓 Heartbeat acknowledged
🏓 Server ping received, sending pong
```

### **Browser Network Tab**:
- WebSocket connection status: 101 Switching Protocols
- Messages tab showing heartbeat exchanges (every 50 seconds)
- No connection drops: Students > 5 menit, Admin > 10 menit

### **Server Logs Validation**:
- Tidak ada `STALE_CONNECTION` untuk active users dalam timeout period
- `recipients=1` atau lebih dalam broadcasts (bukan 0)
- `WS_HEARTBEAT_ACK` messages dari clients setiap 50 detik
- Server log: `Starting heartbeat monitor (interval: 60s, student_timeout: 300s, admin_timeout: 600s)`

---

## 🎯 **IMPLEMENTATION PRIORITIES**

### **HIGH PRIORITY**:
1. **Admin Dashboard Heartbeat** - untuk `/api/v1/ws/lobby`
   - Admin gets 10 menit timeout (lebih tolerant)
   - Heartbeat setiap 50 detik (relaxed)
   - Priority untuk menerima bulk operation progress

### **MEDIUM PRIORITY**: 
2. **Exam Room Heartbeat** - untuk `/api/v1/ws/exam-room/{exam_id}`
   - Teachers get 5 menit timeout (normal)
   - Students get 5 menit timeout (cukup untuk exam sessions)
   - Heartbeat setiap 50 detik

### **LOW PRIORITY**:
3. **General WebSocket** - untuk `/api/v1/ws` (jika digunakan)

---

## 📊 **SUCCESS METRICS**

### **Before Implementation**:
- Admin disconnect setelah 5-10 menit (role-based)
- Server logs: `recipients=0` 
- Bulk operations: No progress updates
- Real-time notifications: Tidak sampai

### **After Implementation**:
- ✅ Admin tetap connected dengan 10 menit tolerance
- ✅ Students/Teachers dengan 5 menit tolerance  
- ✅ Server logs: `recipients=1+`
- ✅ Bulk operations: Progress updates working
- ✅ Real-time notifications: Working properly
- ✅ `STALE_CONNECTION` hanya untuk truly inactive users

---

## ⚠️ **CRITICAL TECHNICAL SPECS**

### **Timing Requirements**:
- **Heartbeat interval**: 50 detik (school-friendly, relaxed timing)
- **Server check interval**: 60 detik  
- **Server timeout**: 5 menit for students, 10 menit for admin
- **Reconnection delay**: 5 detik first attempt, exponential backoff (max 30 detik)

### **Message Format Requirements**:
- All messages harus JSON format
- `type` field wajib ada
- `timestamp` dalam milliseconds (Date.now())
- `message_id` unique untuk tracking

### **Authentication Requirements**:
- JWT token via query parameter: `?token=xxx`
- Token harus valid dan not expired
- Server akan close connection jika token invalid

### **Error Handling Requirements**:
- Handle WebSocket close codes (1000=normal, others=error)  
- Handle JSON parse errors
- Handle network interruptions
- Handle token expiry gracefully

## 🎯 **ROLE-BASED TIMEOUT BENEFITS**

### **Admin Users (10 menit timeout)**:
- ✅ Lebih tolerant untuk admin yang multitasking
- ✅ Tidak terputus saat mengerjakan bulk operations
- ✅ Reliable untuk monitoring sistem jangka panjang
- ✅ Priority treatment untuk critical users

### **Students/Teachers (5 menit timeout)**:
- ✅ Sufficient untuk normal school activities
- ✅ Balance antara resource efficiency dan user experience
- ✅ Automatic cleanup untuk inactive sessions
- ✅ Optimal untuk exam sessions dan classroom activities

### **School-Friendly Settings**:
- ✅ 50 detik heartbeat interval (tidak terlalu aggressive)
- ✅ Compatible dengan school network conditions
- ✅ Less false positives dari network hiccups
- ✅ Reduced server load dibanding sistem sebelumnya

Dengan mengikuti spesifikasi ini, masalah `recipients=0` dan admin disconnection akan teratasi dengan approach yang **school-friendly** dan **resource-efficient**.
