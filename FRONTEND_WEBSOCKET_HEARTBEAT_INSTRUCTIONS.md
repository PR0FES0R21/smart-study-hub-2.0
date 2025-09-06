# 🚨 INSTRUKSI IMPLEMENTASI WEBSOCKET HEARTBEAT UNTUK TIM FRONTEND

## 📋 **RINGKASAN MASALAH**

**Status**: Admin sering disconnect dari WebSocket dan tidak menerima real-time notifications (recipients=0 di server logs).

**Root Cause**: Client tidak mengirim heartbeat ke server, sehingga server menganggap connection "stale" dan memutuskannya setelah 90 detik tidak aktif.

**Dampak**: 
- Bulk operations progress tidak terlihat di admin dashboard
- Real-time notifications tidak sampai ke admin
- Teaching assignments real-time updates tidak berfungsi

---

## 🎯 **WEBSOCKET ENDPOINTS YANG PERLU DIPERBAIKI**

Sistem memiliki **3 WebSocket endpoints** yang semuanya memerlukan heartbeat:

### 1. **`/api/v1/ws/lobby`** (PRIORITAS TINGGI)
- **Fungsi**: Admin dashboard monitoring, user lobby
- **Pengguna**: Admin untuk monitoring sistem secara real-time
- **Pesan**: user_connected, user_disconnected, bulk_update_progress, connection_stats

### 2. **`/api/v1/ws`** (PRIORITAS TINGGI) 
- **Fungsi**: General WebSocket connection
- **Pengguna**: Semua user untuk general messaging
- **Pesan**: admin_broadcast, system notifications

### 3. **`/api/v1/ws/exam-room/{exam_id}`** (PRIORITAS SEDANG)
- **Fungsi**: Exam monitoring dan proctoring
- **Pengguna**: Teachers (proctors) dan Students dalam ujian
- **Pesan**: violation_event, activity_event, room_user_event

---

## 🛠️ **STRATEGI IMPLEMENTASI**

### **PENDEKATAN**: 
Buat **1 WebSocket wrapper class/utility** yang dapat digunakan untuk semua 3 endpoints di atas, sehingga tidak perlu duplicate code.

### **ARSITEKTUR**:
- **WebSocketManager Class**: Handle connection, heartbeat, reconnection
- **Endpoint-specific handlers**: Handle pesan spesifik per endpoint
- **Global status monitoring**: Optional untuk debugging

---

## 📝 **LANGKAH IMPLEMENTASI DETAIL**

### **STEP 1: BUAT WEBSOCKET MANAGER UTILITY**

**File yang perlu dibuat**: `src/utils/WebSocketManager.js` atau `src/services/WebSocketManager.js`

**Requirements untuk class ini**:

#### **A. Constructor Parameters**:
- `endpoint`: String path WebSocket (misal: `/api/v1/ws/lobby`)
- `token`: JWT token dari localStorage/session
- `onMessage`: Callback function untuk handle pesan
- `onConnect`: Callback function saat connected
- `onDisconnect`: Callback function saat disconnected
- `onError`: Callback function untuk error handling

#### **B. Connection Management**:
- Deteksi protocol (ws:// atau wss://) berdasarkan window.location.protocol
- Build WebSocket URL: `${protocol}//${host}${endpoint}?token=${token}`
- Track connection state dengan boolean flag
- Handle WebSocket events: onopen, onmessage, onclose, onerror

#### **C. Heartbeat System** (KUNCI UTAMA):
- **Interval**: Kirim heartbeat setiap 25 detik (sebelum server timeout 90 detik)
- **Message format**: `{type: 'heartbeat', timestamp: Date.now(), message_id: unique_id}`
- **Start heartbeat**: Saat connection established
- **Stop heartbeat**: Saat disconnected
- **Handle server response**: Terima `heartbeat_ack` dari server
- **Handle server ping**: Terima `heartbeat_ping`, balas dengan `heartbeat_pong`

#### **D. Auto-Reconnection System**:
- **Max attempts**: 5 kali reconnection attempts
- **Delay**: 5 detik pertama, exponential backoff untuk attempts berikutnya
- **Trigger**: Auto-reconnect saat connection lost (kecuali manual disconnect)
- **Reset counter**: Reset attempts saat connection berhasil

#### **E. Message Handling**:
- Parse JSON messages dari server
- Handle heartbeat messages secara internal
- Forward non-heartbeat messages ke callback function
- Log semua activities untuk debugging

#### **F. Utility Methods**:
- `connect()`: Establish connection
- `disconnect()`: Manual disconnect
- `sendMessage(object)`: Send JSON message ke server
- `getStatus()`: Return connection status object
- `generateMessageId()`: Generate unique message ID

---

### **STEP 2: UPDATE ADMIN DASHBOARD**

**File yang perlu diupdate**: Component yang handle admin dashboard (misal: `AdminDashboard.jsx` atau similar)

**Requirements**:

#### **A. WebSocket Initialization**:
- Import WebSocketManager
- Initialize dengan endpoint `/api/v1/ws/lobby`
- Get JWT token dari localStorage atau state management
- Setup callback functions untuk handle different message types

#### **B. Message Handlers**:
- **user_connected**: Update connected users list di UI
- **user_disconnected**: Remove user dari list di UI  
- **bulk_update_progress**: Update progress bar untuk bulk operations
- **connection_stats_response**: Update system statistics
- **all_active_users**: Update complete user list

#### **C. Admin-specific Functions**:
- **Request user stats**: Kirim message `{type: 'request_stats'}` ke server
- **Request all users**: Kirim message `{type: 'request_all_users'}` ke server
- **Auto-refresh**: Periodic request statistics setiap 30 detik

#### **D. UI Status Indicators**:
- Show WebSocket connection status (connected/disconnected/error)
- Show real-time user count
- Show progress untuk bulk operations
- Show toast notifications untuk user events

#### **E. Lifecycle Management**:
- Connect saat component mount
- Disconnect saat component unmount
- Handle token refresh/expiry

---

### **STEP 3: UPDATE EXAM ROOM COMPONENTS**

**File yang perlu diupdate**: Components untuk exam proctoring dan student exam session

#### **A. Proctor/Teacher Components**:

**Endpoint**: `/api/v1/ws/exam-room/{exam_id}`

**Message Handlers**:
- **violation_event**: Handle student violations (tab switch, devtools, etc.)
- **activity_event**: Handle student activities (answer changes, navigation)
- **room_user_event**: Handle student connect/disconnect dalam exam

**UI Updates**:
- Real-time violation list dengan timestamp
- Student activity log
- Connected students count in exam room
- Alert notifications untuk violations

**Functions**:
- Auto-connect saat masuk exam proctoring page
- Track all students dalam exam room
- Send proctor commands jika diperlukan

#### **B. Student Components** (jika ada):

**Endpoint**: `/api/v1/ws/exam-room/{exam_id}`

**Outgoing Messages**:
- Send violation reports ke proctors
- Send activity updates ke proctors
- Send exam progress updates

**Requirements**:
- Connect saat masuk exam session
- Auto-report violations (window focus changes, etc.)
- Handle connection loss gracefully

---

### **STEP 4: UPDATE GENERAL WEBSOCKET (jika digunakan)**

**File yang perlu diupdate**: Components yang menggunakan `/api/v1/ws` endpoint

**Requirements**:
- Handle admin broadcasts
- Handle system notifications
- Handle general messaging

---

### **STEP 5: OPTIONAL - GLOBAL STATUS MONITORING**

**File baru (optional)**: `src/components/WebSocketStatus.jsx`

**Requirements**:
- Show status semua active WebSocket connections
- Display heartbeat status
- Show reconnection attempts
- Position: Fixed di bottom-right corner untuk debugging
- Only show di development mode

---

## 🧪 **TESTING REQUIREMENTS**

### **A. Connection Test**:
- Verify WebSocket connects successfully
- Check browser Network tab untuk WebSocket connection
- Verify token dikirim dalam query parameter

### **B. Heartbeat Test** (PALING PENTING):
- Buka browser console
- Verify log "Heartbeat sent" muncul setiap 25 detik
- Verify log "Heartbeat acknowledged" muncul setelah server response
- Test harus pass untuk semua 3 endpoints

### **C. Message Test**:
- Test admin dashboard menerima user connection events
- Test bulk operations progress notifications
- Test exam room violation notifications
- Verify UI updates sesuai dengan incoming messages

### **D. Reconnection Test**:
- Disconnect internet connection
- Wait 10 seconds
- Reconnect internet
- Verify auto-reconnect attempts work
- Verify UI shows proper status

### **E. Long Connection Test**:
- Admin harus tetap connected lebih dari 90 detik
- Check server logs tidak ada "STALE_CONNECTION" untuk active users
- Verify broadcasts menunjukkan recipients > 0

### **F. Token Expiry Test**:
- Test behavior saat JWT token expired
- Verify reconnection dengan fresh token
- Handle authentication failures gracefully

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **PRE-DEPLOYMENT**:
- [ ] WebSocketManager class implemented dan tested
- [ ] Admin dashboard heartbeat working
- [ ] Exam room heartbeat working (jika ada)
- [ ] All message handlers implemented
- [ ] Error handling implemented
- [ ] Auto-reconnection tested
- [ ] Browser console shows heartbeat logs

### **POST-DEPLOYMENT VALIDATION**:
- [ ] Server logs menunjukkan heartbeat messages dari clients
- [ ] Server logs menunjukkan `recipients=1` atau lebih (bukan 0)
- [ ] Admin tetap connected > 90 detik tanpa "STALE_CONNECTION"
- [ ] Bulk operations notifications sampai ke admin
- [ ] Real-time user events working
- [ ] No WebSocket connection errors dalam production

---

## ⚠️ **CRITICAL POINTS**

### **HARUS DIPERHATIKAN**:

1. **Heartbeat Timing**: Kirim setiap 25 detik, jangan lebih dari 30 detik
2. **Message Format**: Exactly follow format yang expected server
3. **Token Management**: Handle token expiry dan refresh
4. **Error Handling**: Graceful handling untuk semua error scenarios
5. **Memory Leaks**: Proper cleanup saat component unmount
6. **Browser Compatibility**: Test di Chrome, Firefox, Safari, Edge

### **DEBUGGING**:
- Enable console logging untuk semua WebSocket activities
- Monitor server logs untuk verification
- Use browser Network tab untuk inspect WebSocket traffic
- Check for JavaScript errors yang bisa break heartbeat

### **PERFORMANCE**:
- Jangan create multiple connections ke same endpoint
- Reuse WebSocketManager instances where possible
- Proper cleanup untuk prevent memory leaks
- Minimize message frequency untuk non-critical updates

---

## 🎯 **SUCCESS CRITERIA**

**BEFORE FIX**:
- Admin disconnects after 90+ seconds
- Server logs: `recipients=0` dalam broadcasts
- Bulk operations: No progress notifications
- Real-time updates: Not working

**AFTER FIX**:
- ✅ Admin stays connected indefinitely dengan heartbeat
- ✅ Server logs: `recipients=1+` dalam broadcasts  
- ✅ Bulk operations: Progress notifications working
- ✅ Real-time updates: Working properly
- ✅ No "STALE_CONNECTION" errors untuk active users

---

## 📞 **SUPPORT**

**Questions tentang**:
- Server message formats: Contact backend team
- WebSocket endpoints: Check API documentation  
- Error debugging: Check server logs
- Token management: Check authentication system

**Urgent issues**: Implementasi ini high priority karena affecting admin functionality dan real-time system monitoring.
