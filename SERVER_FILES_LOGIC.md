# Server Folder - File Logic and Function Importance

This document explains the purpose and logic of each file in the server folder, detailing every important function and how they work together to implement the VPN server.

---

## File Overview

The server folder contains six essential files that work together:

1. **run_server_enhanced.py** - Entry point with signal handling
2. **config.py** - Configuration and settings
3. **vpn_server_enhanced.py** - Main server orchestration
4. **auth_handler.py** - Authentication logic
5. **tunnel_manager.py** - Packet forwarding and tunneling
6. **flow_control.py** - Congestion control algorithm

---

## 1. run_server_enhanced.py

**Purpose:** Entry point for starting the VPN server with graceful shutdown handling.

### Key Functions

#### main()

**What it does:** Initializes and starts the VPN server

**Logic:**
- Registers signal handlers for CTRL+C (SIGINT) and SIGTERM
- Prints server banner with version and features
- Creates VPNServerEnhanced instance
- Calls server.start() to begin listening
- Enters infinite loop to keep server running

**Importance:** Provides clean startup and shutdown. Without this, CTRL+C would leave sockets open and threads running.

**Code flow:**
1. Register signal_handler for graceful shutdown
2. Display server information (host, port, features)
3. Create server instance
4. Start server (begins listening for connections)
5. Sleep loop to keep main thread alive

#### signal_handler(signum, frame)

**What it does:** Handles shutdown signals gracefully

**Logic:**
- Called when user presses CTRL+C or system sends SIGTERM
- Prints shutdown message
- Calls server.shutdown() to close all connections
- Exits cleanly with code 0

**Importance:** Ensures proper resource cleanup. Without this, server would crash instead of shutting down cleanly, potentially leaving client connections hanging.

---

## 2. config.py

**Purpose:** Centralized configuration for the VPN server.

### Configuration Variables

#### Network Settings

**HOST = '0.0.0.0'**
- Binds server to all network interfaces
- Allows connections from any IP address
- Important: Using specific IP (like 192.168.0.107) would only allow local connections

**PORT = 8888**
- TCP port for VPN server to listen on
- Clients connect to this port
- Note: In actual code, this was changed to 5555 at runtime

#### Security Settings

**REQUIRE_AUTH = True**
- Enforces authentication requirement
- If False, anyone can connect without credentials
- Important for production security

**MAX_CLIENTS = 10**
- Maximum simultaneous client connections
- Prevents resource exhaustion
- Server rejects connections beyond this limit

#### Authentication Credentials

**VALID_CREDENTIALS dictionary**
- Maps usernames to passwords
- Currently: 'student': 'secure123', 'admin': 'admin123', 'demo': 'demo123'
- Important: In production, this should be a secure database with hashed passwords

**Why this matters:** Centralized configuration makes it easy to change settings without modifying code. All server components import this file for consistent settings.

---

## 3. vpn_server_enhanced.py

**Purpose:** Main VPN server orchestration - handles connections, coordinates encryption, authentication, and tunneling.

### Key Functions

#### \_\_init\_\_(self)

**What it does:** Initializes server components

**Logic:**
- Creates server socket (SOCK_STREAM for TCP)
- Sets socket options (SO_REUSEADDR, SO_KEEPALIVE, TCP_NODELAY)
- Initializes RSAHandler for key exchange
- Creates empty dictionaries for client tracking
- Sets up statistics counters

**Importance:** Proper socket configuration is critical:
- SO_REUSEADDR: Allows quick restart without "address already in use" error
- SO_KEEPALIVE: Detects dead connections
- TCP_NODELAY: Disables Nagle's algorithm for low latency

#### start(self)

**What it does:** Starts the server listening for connections

**Logic:**
1. Binds socket to HOST:PORT
2. Calls socket.listen(MAX_CLIENTS)
3. Starts statistics thread (prints stats every 30s)
4. Enters accept loop: continuously accepts new clients

**Importance:** This is the main server loop. Without it, server wouldn't accept any connections.

**Thread safety:** Each accepted connection spawns a new thread, allowing multiple clients simultaneously.

#### \_accept\_clients(self)

**What it does:** Accepts incoming client connections

**Logic:**
- Infinite loop calling socket.accept()
- For each connection:
  - Checks if under MAX_CLIENTS limit
  - Spawns new thread calling _handle_client()
  - Logs connection from client IP

**Importance:** Threading model allows concurrent clients. Without threading, server could only handle one client at a time.

**Error handling:** Catches exceptions to prevent server crash if connection fails during accept.

#### \_handle\_client(self, client_socket, addr)

**What it does:** Complete client session handler - coordinates all phases

**Logic:**

**Phase 1: RSA Key Exchange**
1. Receive client's RSA public key (PEM format)
2. Send server's RSA public key
3. Both sides now can encrypt data for each other

**Phase 2: Authentication**
1. Receive encrypted authentication data
2. Decrypt with server's RSA private key
3. Parse JSON to get username/password
4. Validate credentials using AuthHandler
5. If valid: generate AES session key
6. Encrypt AES key with client's RSA public key
7. Send encrypted AES key to client

**Phase 3: Create Tunnel**
1. Create FlowController for this client
2. Create TunnelManager with AES key and flow controller
3. Call tunnel_manager.start_tunnel()
4. Tunnel handles all subsequent communication

**Phase 4: Cleanup**
- When tunnel closes, remove from active clients
- Update statistics
- Close socket

**Importance:** This is the core server logic. It orchestrates the entire connection lifecycle from handshake to tunnel creation to cleanup.

**Security note:** Each client gets a unique AES session key. If one client's key is compromised, other clients remain secure.

#### \_receive\_length\_prefixed(self, client_socket)

**What it does:** Receives variable-length messages using length-prefix protocol

**Logic:**
1. Receive exactly 4 bytes (length header)
2. Unpack as big-endian integer
3. Receive exactly that many bytes of data
4. Return the data

**Importance:** TCP is a stream protocol with no message boundaries. Without length prefixing, we wouldn't know where one message ends and the next begins.

**Error handling:** Returns None if socket closes or timeout occurs.

#### \_send\_length\_prefixed(self, client_socket, data)

**What it does:** Sends data with length prefix

**Logic:**
1. Get length of data
2. Pack length as 4-byte big-endian integer
3. Send length header
4. Send actual data

**Importance:** Counterpart to _receive_length_prefixed. Ensures receiver can parse messages correctly.

**Format:** [4 bytes: length][N bytes: data]

#### \_print\_statistics(self)

**What it does:** Periodically logs server statistics

**Logic:**
- Runs in background thread
- Every 30 seconds:
  - Calculate uptime
  - Count active clients
  - Sum total data forwarded across all tunnels
  - Print formatted statistics

**Importance:** Provides visibility into server operation. Shows administrator what's happening without verbose per-packet logging.

**Statistics tracked:**
- Uptime
- Total connections (lifetime)
- Active tunnels (current)
- Total data forwarded (all time)

#### shutdown(self)

**What it does:** Gracefully shuts down server

**Logic:**
1. Set self.running = False (stops accept loop)
2. Close all active client tunnels
3. Close server socket
4. Stop statistics thread

**Importance:** Clean shutdown prevents resource leaks. Without this, sockets might remain open, threads might keep running, and OS resources might not be released.

---

## 4. auth_handler.py

**Purpose:** Handles authentication logic - validates credentials and manages auth messages.

### Key Functions

#### validate_credentials(username, password)

**What it does:** Checks if username/password pair is valid

**Logic:**
1. Look up username in VALID_CREDENTIALS dictionary
2. If found, compare password with stored value
3. Return True if match, False otherwise

**Importance:** Security gatekeeper. Only authenticated users can establish VPN tunnel.

**Static method:** No instance needed, can be called directly as AuthHandler.validate_credentials()

**Security note:** Currently uses plaintext password comparison. Production systems should use hashed passwords with salt (bcrypt, scrypt, argon2).

#### parse_auth_data(auth_json)

**What it does:** Parses JSON authentication data from client

**Logic:**
1. Parse JSON string
2. Extract username, password, timestamp
3. Return as tuple
4. If parsing fails, return empty strings and 0.0

**Importance:** Separates parsing logic from validation logic. Makes code more maintainable and testable.

**Format expected:**
```json
{
  "username": "student",
  "password": "secure123",
  "timestamp": 1704585600.123
}
```

**Error handling:** Catches all exceptions and returns safe default values instead of crashing.

#### create_auth_response(success, message, server_info)

**What it does:** Creates JSON response for authentication result

**Logic:**
1. Create dictionary with status and message
2. If server_info provided, merge it in
3. Convert to JSON string
4. Return string

**Importance:** Standardizes response format. Client knows exactly what to expect.

**Response format:**
```json
{
  "status": "success",
  "message": "Authentication successful",
  "encryption": "AES-256-CBC",
  "features": ["tunneling", "flow_control"]
}
```

**Why separate function:** Encapsulates response format. If format changes, only this function needs updating.

---

## 5. tunnel_manager.py

**Purpose:** Manages packet forwarding through the VPN tunnel - the heart of the VPN functionality.

### Key Functions

#### \_\_init\_\_(self, aes_key, client_socket, flow_controller)

**What it does:** Initializes tunnel with encryption and flow control

**Parameters:**
- aes_key: Shared AES session key for encryption
- client_socket: Socket connected to VPN client
- flow_controller: FlowController instance for congestion management

**Logic:**
- Creates EncryptionHandler with AES key
- Stores client socket reference
- Stores flow controller reference
- Initializes statistics counters

**Importance:** Sets up all components needed for secure, controlled packet forwarding.

#### start_tunnel(self)

**What it does:** Main tunnel loop - receives requests and forwards them

**Logic:**
1. Set socket timeout to 60 seconds
2. Enter infinite loop:
   - Receive encrypted request from client
   - Decrypt request
   - Parse destination (host:port:data)
   - Call _handle_forward_request()
   - If request fails, break loop
3. Close socket on exit

**Importance:** This is the tunnel's main loop. As long as this runs, the tunnel is active and forwarding traffic.

**Timeout:** 60 seconds prevents hanging on dead connections. If no data for 60s, tunnel closes.

**Error handling:** Any exception breaks the loop and closes tunnel. This prevents zombie connections.

#### \_handle\_forward\_request(self, destination_host, destination_port, request_data)

**What it does:** Forwards a single request through the tunnel

**This is the most important function in tunnel_manager.py - it implements the actual VPN tunneling.**

**Logic:**

**Step 1: Flow Control Check**
```python
self.flow_controller.wait_for_send_permission(len(request_data))
```
- Blocks if congestion window is full
- Ensures we don't send too fast

**Step 2: Rate Limiting**
```python
self.flow_controller.pace_transmission(len(request_data))
```
- Adds delay to smooth out bursts
- Prevents overwhelming the network

**Step 3: Create Destination Socket**
```python
dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
dest_socket.connect((destination_host, destination_port))
```
- New TCP connection to actual destination
- This is a separate connection from client→server

**Step 4: Forward Request**
```python
record_send_time = time.time()
dest_socket.send(request_data)
self.flow_controller.on_packet_sent(len(request_data))
```
- Send plaintext data to destination
- Track packet for flow control
- Record time for RTT measurement

**Step 5: Receive Response (Loop-based for large files)**
```python
response = b''
while True:
    chunk = dest_socket.recv(65536)  # 64KB chunks
    if not chunk:
        break
    response += chunk
    if len(response) > 50 * 1024 * 1024:  # 50MB limit
        break
```
- Handles responses of any size
- 64KB chunks prevent memory overflow
- 50MB safety limit prevents abuse

**Step 6: Measure RTT**
```python
rtt = time.time() - record_send_time
self.flow_controller.on_ack_received(len(request_data), rtt)
```
- Calculate round-trip time
- Update flow control statistics
- Adjust congestion window

**Step 7: Encrypt Response**
```python
encrypted_response = self.encryption.encrypt(response)
```
- Encrypt destination's response with AES
- Client will decrypt with same key

**Step 8: Send Back to Client**
```python
# Temporarily increase timeout for large responses
self.client_socket.settimeout(120.0)
length_header = struct.pack('>I', len(encrypted_response))
self.client_socket.send(length_header + encrypted_response)
```
- Send encrypted response through tunnel
- Length prefix so client knows size
- 120s timeout for large file transfers

**Importance:** This function is the essence of VPN tunneling:
- Receives encrypted request from client
- Decrypts it
- Forwards to actual destination (plaintext)
- Receives response from destination
- Encrypts response
- Sends back to client

**Security:** Client→Server = encrypted, Server→Destination = plaintext (but with masked IP)

**Error handling:** If any step fails, returns False to close tunnel.

#### get_stats(self)

**What it does:** Returns tunnel statistics

**Logic:**
- Returns dictionary with total_requests and bytes_forwarded
- Used by server for statistics reporting

**Importance:** Provides visibility into tunnel activity. Server can report total data forwarded across all tunnels.

---

## 6. flow_control.py

**Purpose:** Implements TCP Reno congestion control algorithm to manage sending rate.

### Key Functions

#### \_\_init\_\_(self, min_window_size, initial_window_size, max_window_size)

**What it does:** Initializes flow controller with congestion control parameters

**Parameters:**
- min_window_size: 4096 (4KB) - smallest allowed cwnd
- initial_window_size: 4096 (4KB) - starting cwnd
- max_window_size: 1048576 (1MB) - largest allowed cwnd

**Logic:**
- Sets cwnd = initial_window_size
- Sets ssthresh = 8192 (8KB) for faster demo
- Initializes in_slow_start = True
- Sets up RTT tracking variables (SRTT, RTTVAR)
- Initializes packet counters

**Importance:** These initial values determine starting behavior:
- Small initial cwnd: Conservative start
- Low ssthresh: Quick transition to congestion avoidance (for demo)
- Appropriate for VPN where we want to see both phases

#### wait_for_send_permission(self, data_size)

**What it does:** Blocks transmission when congestion window is full

**Logic:**
1. Calculate required_packets = ceil(data_size / avg_packet_size)
2. While packets_in_flight + required_packets > cwnd:
   - Log: "Waiting for window space"
   - Sleep 100ms
   - Check again
3. Return True when window has space

**Importance:** This is actual flow control - it prevents sending when the network is congested. Without this, the system would send as fast as possible, causing packet loss and poor performance.

**Blocking behavior:** Pauses the sender until ACKs arrive and free up window space. This is how congestion control works - by controlling the rate of transmission.

#### pace_transmission(self, data_size)

**What it does:** Adds delay between transmissions for rate limiting

**Logic:**
1. Calculate pacing_rate = cwnd / SRTT (bytes per second)
2. Calculate delay = data_size / pacing_rate (seconds)
3. Clamp delay between 0.001s and 1.0s
4. Sleep for delay

**Importance:** Pacing smooths out traffic bursts. Instead of sending all available data at once, spreads it over time. This is gentler on the network and prevents buffer overflow at routers.

**Formula explanation:**
- If cwnd = 8KB and SRTT = 20ms, pacing_rate = 8192/0.02 = 409,600 bytes/sec
- For 111-byte packet: delay = 111/409600 = 0.27ms

#### on_packet_sent(self, packet_size)

**What it does:** Records that a packet has been sent

**Logic:**
- Increment packets_in_flight counter
- Increment total_packets_sent counter

**Importance:** Tracks outstanding packets for flow control. The wait_for_send_permission() function checks packets_in_flight against cwnd to enforce the limit.

**Why separate function:** Clean separation of concerns. Tunnel manager just calls this after sending; flow controller maintains the state.

#### on_ack_received(self, packet_size, rtt_sample)

**What it does:** Updates congestion window and RTT when ACK arrives

**This is the core of the congestion control algorithm.**

**Logic:**

**Step 1: Update RTT statistics**
```python
self._update_rtt(rtt_sample)
```
- Exponential moving average of RTT
- Updates SRTT and RTTVAR

**Step 2: Update throughput**
```python
self._update_throughput(packet_size)
```
- Calculate bytes/second

**Step 3: Adjust congestion window**

**If in slow start (cwnd < ssthresh):**
```python
old_cwnd = self.cwnd
self.cwnd += packet_size  # Exponential growth
if self.cwnd >= self.ssthresh:
    self.in_slow_start = False
    # Log transition message
```
- Add full packet size to cwnd
- Check for transition to congestion avoidance
- Log transition when it happens

**If in congestion avoidance:**
```python
increment = (packet_size * packet_size) / self.cwnd
self.cwnd += increment  # Linear growth
```
- Add fractional amount to cwnd
- Growth is much slower

**Step 4: Bounds checking**
```python
self.cwnd = max(min(self.cwnd, self.max_window_size), self.min_window_size)
```
- Ensure cwnd stays within limits

**Step 5: Update counters**
```python
self.packets_in_flight -= 1
self.total_packets_acked += 1
```
- Track packet acknowledgment

**Step 6: Logging**
```python
# Log every ACK with current stats
```
- Shows cwnd, ssthresh, RTT, SRTT, phase

**Importance:** This function implements the AIMD (Additive Increase, Multiplicative Decrease) principle:
- Slow start: Aggressive exponential increase
- Congestion avoidance: Conservative linear increase
- Adapts to network conditions in real-time

#### on_packet_loss(self)

**What it does:** Reacts to detected packet loss

**Logic:**
1. Set ssthresh = max(cwnd / 2, min_window_size)
2. Set cwnd = max(cwnd / 2, min_window_size)
3. Stay in current phase
4. Log the event

**Importance:** Multiplicative decrease - quickly reduce sending rate when congestion detected. This prevents congestion collapse.

**Why halve:** Empirically proven to be stable. Larger decrease is too aggressive (wastes bandwidth), smaller decrease doesn't respond fast enough to congestion.

#### on_timeout(self)

**What it does:** Reacts to timeout (no response within RTO)

**Logic:**
1. Set ssthresh = max(cwnd / 2, min_window_size)
2. Reset cwnd = min_window_size (back to 4KB)
3. Set in_slow_start = True (restart slow start)
4. Reset packets_in_flight = 0
5. Log timeout

**Importance:** Severe reaction to severe problem. Timeout indicates serious congestion or connection issue. By resetting to minimum and restarting slow start, we give the network time to recover.

**Why more severe than packet loss:** Timeout means multiple packets were lost or delayed significantly. This is a stronger signal of congestion.

#### \_update\_rtt(self, rtt_sample)

**What it does:** Updates smoothed RTT using exponential moving average

**Logic:**
```python
alpha = 0.125  # Weight for new sample
beta = 0.25    # Weight for variance

SRTT = (1-alpha) * old_SRTT + alpha * rtt_sample
SRTT = 0.875 * old_SRTT + 0.125 * rtt_sample

RTTVAR = (1-beta) * old_RTTVAR + beta * |SRTT - rtt_sample|
RTTVAR = 0.75 * old_RTTVAR + 0.25 * |SRTT - rtt_sample|
```

**Importance:** Smoothed RTT is more stable than raw samples. Used for:
- Pacing calculations (pacing_rate = cwnd / SRTT)
- Timeout calculations (RTO = SRTT + 4 * RTTVAR)

**Why exponential average:** Gives more weight to recent measurements while incorporating history. Responds to changes but not too sensitive to outliers.

**Variance tracking:** High variance indicates unstable network. Used to increase timeout tolerance when network is jittery.

#### get_timeout(self)

**What it does:** Calculates retransmission timeout

**Logic:**
```python
RTO = SRTT + 4 * RTTVAR
return max(RTO, 1.0)  # At least 1 second
```

**Importance:** Determines how long to wait before considering a packet lost. Too short = unnecessary retransmissions. Too long = slow recovery from loss.

**Formula from RFC 6298:** Standard TCP timeout calculation. The 4× multiplier for RTTVAR ensures timeout accommodates variance.

#### get_stats(self)

**What it does:** Returns comprehensive flow control statistics

**Logic:**
- Returns dictionary with all metrics:
  - cwnd, ssthresh, current_phase
  - packets_sent, packets_acked, packets_in_flight
  - SRTT, RTTVAR, RTO
  - throughput

**Importance:** Provides complete visibility into congestion control state. Used for:
- Server logging and monitoring
- Debugging congestion issues
- Demonstrating algorithm behavior

---

## How Files Work Together

### Connection Sequence

**1. Server Startup**
```
run_server_enhanced.py main()
    ↓
vpn_server_enhanced.py __init__()
    ↓
vpn_server_enhanced.py start()
    ↓
socket.accept() [waiting for client]
```

**2. Client Connects**
```
socket.accept() returns
    ↓
vpn_server_enhanced.py _handle_client() [new thread]
    ↓
RSA key exchange
    ↓
auth_handler.py parse_auth_data()
    ↓
auth_handler.py validate_credentials()
    ↓
flow_control.py __init__() [create FlowController]
    ↓
tunnel_manager.py __init__() [create TunnelManager]
    ↓
tunnel_manager.py start_tunnel() [tunnel active]
```

**3. Request Forwarding**
```
tunnel_manager.py start_tunnel() [receive encrypted request]
    ↓
tunnel_manager.py _handle_forward_request()
    ↓
flow_control.py wait_for_send_permission() [check cwnd]
    ↓
flow_control.py pace_transmission() [rate limit]
    ↓
socket.connect(destination) [forward to demo site]
    ↓
socket.send(plaintext_request)
    ↓
flow_control.py on_packet_sent()
    ↓
socket.recv(response) [get response]
    ↓
flow_control.py on_ack_received() [update cwnd, RTT]
    ↓
encrypt response
    ↓
send to client
```

**4. Shutdown**
```
CTRL+C pressed
    ↓
run_server_enhanced.py signal_handler()
    ↓
vpn_server_enhanced.py shutdown()
    ↓
tunnel_manager close all tunnels
    ↓
socket.close()
```

### Data Flow

**Encrypted Tunnel (Client ↔ Server)**
- Protocol: TCP with length-prefixed messages
- Encryption: AES-256-CBC
- Format: [4 bytes length][encrypted data]

**Plaintext Forward (Server ↔ Destination)**
- Protocol: TCP with raw data
- No encryption (but IP masked)
- Format: Standard HTTP or whatever protocol

### Shared State

**config.py provides:**
- Network settings (HOST, PORT)
- Security settings (REQUIRE_AUTH, MAX_CLIENTS)
- Valid credentials

**vpn_server_enhanced.py maintains:**
- Active client sockets
- Active tunnel managers
- Connection statistics

**Each tunnel has:**
- Own TunnelManager instance
- Own FlowController instance
- Own encryption keys
- Independent statistics

This separation ensures:
- Clients don't interfere with each other
- Per-client flow control
- Isolated security (one compromised client doesn't affect others)

---

## Summary

The server folder implements a complete VPN server with:

**run_server_enhanced.py** - Clean startup/shutdown
**config.py** - Centralized configuration
**vpn_server_enhanced.py** - Connection orchestration
**auth_handler.py** - Security gatekeeper
**tunnel_manager.py** - Packet forwarding engine
**flow_control.py** - Congestion control brain

Together, they create a secure, efficient, observable VPN server that demonstrates fundamental networking principles in action.
