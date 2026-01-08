# Networking Concepts Used in VPN Project

This document outlines the key networking concepts implemented in the custom VPN project and explains how each was used.

---

## 1. Socket Programming (TCP Connection)

### What It Is

Sockets are the fundamental interface for network communication. TCP (Transmission Control Protocol) sockets provide reliable, connection-oriented, bidirectional communication between two endpoints.

### How We Used It

**Socket Creation**
```python
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```
- `AF_INET`: IPv4 addressing
- `SOCK_STREAM`: TCP protocol (reliable, connection-oriented)

**Socket Configuration**
```python
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
```
- `SO_REUSEADDR`: Allows quick server restart without "address in use" error
- `SO_KEEPALIVE`: Detects dead connections automatically
- `TCP_NODELAY`: Disables Nagle's algorithm for low latency (important for VPN)

**Three-Way Handshake**

TCP automatically performs the connection handshake:
1. Client sends SYN (synchronize) packet
2. Server responds with SYN-ACK (synchronize-acknowledge)
3. Client sends ACK (acknowledge)
4. Connection established

This is visible in Wireshark as the first three packets when VPN client connects.

**Binding and Listening (Server)**
```python
server_socket.bind(('0.0.0.0', 5555))  # Listen on all interfaces, port 5555
server_socket.listen(10)                # Queue up to 10 pending connections
```

**Connecting (Client)**
```python
client_socket.connect(('192.168.0.107', 5555))  # Connect to server
```

**Accepting Connections (Server)**
```python
client_socket, addr = server_socket.accept()  # Block until client connects
```

**Implementation Locations**
- Server: `server/vpn_server_enhanced.py` - `__init__()` and `start()`
- Client: `client/vpn_client_enhanced.py` - `connect()`

**Why This Matters**

TCP sockets provide the reliable foundation for our VPN. Features we get automatically:
- Guaranteed delivery (packets arrive in order)
- Error detection (checksums)
- Flow control (TCP's built-in window mechanism)
- Connection state management

---

## 2. Flow Control

### What It Is

Flow control prevents a fast sender from overwhelming a slow receiver. It regulates the rate of data transmission to match the receiver's capacity to process data.

### How We Used It

**Congestion Window (cwnd)**

We implemented application-level flow control using a congestion window:
```python
cwnd = 4096  # Start with 4KB window
ssthresh = 8192  # Slow start threshold
```

The congestion window limits how much unacknowledged data can be "in flight" at any time.

**Blocking Transmission**
```python
def wait_for_send_permission(self, data_size):
    required_packets = ceil(data_size / avg_packet_size)
    while packets_in_flight + required_packets > cwnd:
        time.sleep(0.1)  # Wait until window space available
    return True
```

Before sending data:
1. Check if sending would exceed cwnd
2. If yes: **block and wait** for acknowledgments
3. If no: proceed with transmission

**Tracking Packets**
```python
def on_packet_sent(self, packet_size):
    self.packets_in_flight += 1  # Track outstanding data

def on_ack_received(self, packet_size, rtt_sample):
    self.packets_in_flight -= 1  # Free up window space
    # Update cwnd based on current phase
```

**Rate Pacing**
```python
def pace_transmission(self, data_size):
    pacing_rate = cwnd / SRTT  # bytes per second
    delay = data_size / pacing_rate
    time.sleep(delay)  # Smooth out bursts
```

Pacing prevents sending all available data in one burst, spreading transmissions over time.

**Implementation Locations**
- `server/flow_control.py` - `wait_for_send_permission()`, `pace_transmission()`
- `server/tunnel_manager.py` - Calls flow control before forwarding packets

**How It Works in Practice**

Example scenario:
1. cwnd = 4KB, client wants to send 111-byte request
2. Flow controller checks: 111 bytes < 4KB available? Yes
3. Permission granted, packet sent
4. packets_in_flight increases by 1
5. Response arrives, acknowledgment processed
6. packets_in_flight decreases by 1
7. Window space freed for next request

**Why This Matters**

Without flow control:
- Sender could flood the network with data
- Router buffers overflow
- Packets dropped
- Wasted retransmissions
- Poor performance for everyone

With flow control:
- Transmission rate matches network capacity
- No buffer overflow
- Stable, predictable performance
- Fair sharing among multiple flows

---

## 3. Congestion Control (TCP Reno Algorithm)

### What It Is

Congestion control prevents the sender from overwhelming the network itself (not just the receiver). It dynamically adjusts the sending rate based on network conditions, probing for available bandwidth while backing off when congestion is detected.

### How We Used It

**Two-Phase Algorithm**

**Phase 1: Slow Start (Exponential Growth)**
```python
if in_slow_start and cwnd < ssthresh:
    cwnd += packet_size  # Exponential growth
    
    if cwnd >= ssthresh:
        in_slow_start = False  # Transition to congestion avoidance
```

Starting conditions:
- cwnd = 4KB (conservative start)
- Each ACK increases cwnd by full packet size
- Growth: 4KB → 4.1KB → 4.2KB → ... → 8KB

Purpose: Quickly discover available bandwidth

**Phase 2: Congestion Avoidance (Linear Growth)**
```python
else:  # Congestion avoidance
    increment = (packet_size * packet_size) / cwnd
    cwnd += increment  # Linear growth
```

After cwnd reaches ssthresh (8KB):
- Each ACK increases cwnd by smaller amount
- Growth: 8.0KB → 8.01KB → 8.02KB → ...
- Formula ensures approximately 1 packet increase per RTT

Purpose: Cautiously probe for more bandwidth

**RTT Measurement**
```python
def _update_rtt(self, rtt_sample):
    # Exponential weighted moving average
    SRTT = 0.875 * old_SRTT + 0.125 * rtt_sample
    RTTVAR = 0.75 * old_RTTVAR + 0.25 * |SRTT - rtt_sample|
```

Every request-response cycle:
1. Record send_time when forwarding request
2. Record receive_time when response arrives  
3. rtt_sample = receive_time - send_time
4. Update SRTT (smoothed RTT) and RTTVAR (variance)

**Handling Packet Loss (Multiplicative Decrease)**
```python
def on_packet_loss(self):
    ssthresh = max(cwnd / 2, min_window_size)
    cwnd = max(cwnd / 2, min_window_size)  # Halve cwnd
```

When packet loss detected:
- Immediately cut cwnd in half
- Quick reaction to congestion
- Prevents further losses

**Handling Timeout (Severe Congestion)**
```python
def on_timeout(self):
    ssthresh = max(cwnd / 2, min_window_size)
    cwnd = min_window_size  # Reset to 4KB
    in_slow_start = True    # Restart slow start
```

When no response within timeout period:
- Reset to minimum window
- Start over from slow start
- Severe reaction to severe congestion

**AIMD Principle**

Additive Increase, Multiplicative Decrease:
- **Increase**: Add constant amount per RTT (linear, gradual)
- **Decrease**: Multiply by 0.5 when loss detected (exponential, aggressive)

This asymmetry ensures network stability and fairness among competing flows.

**Implementation Locations**
- `server/flow_control.py` - Complete TCP Reno implementation
- All congestion control logic: `on_ack_received()`, `on_packet_loss()`, `on_timeout()`

**Observable Behavior**

In server logs, you can see:
```
📊 Phase: SLOW START | cwnd: 4.0KB → 6.2KB
🔄 Transitioned to CONGESTION AVOIDANCE | cwnd: 8.0KB
📊 Phase: CONG AVOID | cwnd: 8.02KB → 8.05KB
```

**Why This Matters**

Congestion control is what makes the Internet work:
- Prevents congestion collapse (network meltdown)
- Provides fairness (multiple flows share bandwidth equally)
- Adapts to changing network conditions
- Balances throughput vs stability

Without it:
- Everyone sends at maximum rate
- Network becomes congested
- Packet loss increases
- Everyone's performance suffers
- Positive feedback loop to collapse

With it:
- Flows back off when congested
- Network stabilizes
- Resources shared fairly
- Sustainable high performance

---

## 4. Reliable Data Transfer

### What It Is

Reliable data transfer ensures that data sent arrives completely, correctly, and in order at the destination - despite potential packet loss, corruption, or reordering in the network.

### How We Used It

**Built-in TCP Reliability**

TCP provides automatic reliability mechanisms:
- **Sequence numbers**: Each byte has a sequence number
- **Acknowledgments**: Receiver confirms received data
- **Retransmissions**: Lost packets automatically resent
- **Checksums**: Detect corrupted data
- **Ordering**: Data delivered in correct order

We inherit these features by using TCP sockets (SOCK_STREAM).

**Application-Level Reliability**

We added our own reliability layer on top of TCP:

**1. Length-Prefixed Protocol**
```python
def _send_length_prefixed(self, socket, data):
    length = len(data)
    length_header = struct.pack('>I', length)  # 4-byte big-endian
    socket.send(length_header + data)
```

Problem: TCP is a stream protocol with no message boundaries
Solution: Prefix each message with its length
- Receiver knows exactly how much data to expect
- No ambiguity about where messages start/end

**2. Complete Message Reception**
```python
def _receive_length_prefixed(self, socket):
    # Step 1: Receive exactly 4 bytes (length header)
    length_data = b''
    while len(length_data) < 4:
        chunk = socket.recv(4 - len(length_data))
        if not chunk:
            return None  # Connection closed
        length_data += chunk
    
    # Step 2: Parse length
    length = struct.unpack('>I', length_data)[0]
    
    # Step 3: Receive exactly that many bytes
    message = b''
    while len(message) < length:
        chunk = socket.recv(length - len(message))
        if not chunk:
            return None
        message += chunk
    
    return message
```

This ensures complete messages even if TCP splits data across multiple packets.

**3. Loop-Based Reception for Large Files**
```python
response = b''
while True:
    chunk = dest_socket.recv(65536)  # 64KB chunks
    if not chunk:
        break  # End of data
    response += chunk
    if len(response) > 50 * 1024 * 1024:
        break  # 50MB safety limit
```

For large responses (1MB, 5MB, 10MB files):
- Receive in chunks to avoid memory overflow
- Continue until no more data
- Safety limit prevents abuse

**4. Socket Timeouts**
```python
socket.settimeout(60.0)  # 60 second timeout
```

Prevents hanging forever if:
- Server crashes
- Network disconnects
- Client becomes unresponsive

After timeout, connection closes cleanly instead of blocking forever.

**5. Error Handling and Fallback**
```python
try:
    data = self._receive_length_prefixed(client_socket)
    if data is None:
        # Connection closed cleanly
        break
except socket.timeout:
    # No data for 60 seconds
    break
except Exception as e:
    # Other error
    logging.error(f"Error: {e}")
    break
```

Every network operation wrapped in error handling:
- Socket closed: Clean shutdown
- Timeout: Close connection
- Other errors: Log and close

**6. Encryption Integrity**

AES-256-CBC with PKCS7 padding:
```python
encrypted_data = encryption.encrypt(plaintext)
plaintext = encryption.decrypt(encrypted_data)
```

Benefits:
- If data corrupted in transit, decryption fails (detectable)
- Ensures data integrity along with confidentiality
- Prevents tampering

**Implementation Locations**
- Length-prefixed protocol: `server/vpn_server_enhanced.py`, `server/tunnel_manager.py`
- Loop-based reception: `server/tunnel_manager.py` - `_handle_forward_request()`
- Error handling: Throughout all files
- Timeout configuration: Socket setup in server and client

**Why This Matters**

Reliability is critical for a VPN:
- Users expect data to arrive correctly
- Lost data means failed downloads, broken pages
- Out-of-order data causes protocol errors
- Incomplete messages crash applications

Our layered approach provides:
1. **TCP layer**: Handles low-level packet reliability
2. **Protocol layer**: Handles message framing and completeness
3. **Application layer**: Handles large transfers and error recovery
4. **Encryption layer**: Provides integrity verification

**Example: Downloading 1MB File**

Without reliability:
- TCP might deliver 800KB, lose 200KB
- Application crashes or shows corrupt file

With reliability:
- TCP detects loss, retransmits missing data
- Length prefix ensures all 1,048,576 bytes received
- Loop continues until complete
- Decryption verifies integrity
- User gets complete, correct file

---

## Summary: Integration of All Concepts

These four networking concepts work together in our VPN:

**1. Socket Connection** provides the foundation
- TCP handshake establishes connection
- Reliable stream communication channel
- Built-in error detection and recovery

**2. Flow Control** prevents overwhelming the receiver
- Congestion window limits in-flight data
- Blocking when window full
- Rate pacing smooths transmission

**3. Congestion Control** adapts to network conditions
- Slow start discovers bandwidth quickly
- Congestion avoidance maintains stability
- Multiplicative decrease responds to congestion
- RTT measurement tracks network state

**4. Reliable Data Transfer** ensures correctness
- TCP provides byte-stream reliability
- Length-prefixed protocol ensures message boundaries
- Loop-based reception handles large data
- Error handling provides graceful degradation

**Complete Request Flow**

When client sends HTTP request through VPN:

1. **Socket**: TCP connection already established (handshake done)
2. **Reliable Transfer**: Request formatted with length prefix
3. **Encryption**: Request encrypted with AES-256
4. **Socket**: Encrypted data sent through TCP socket
5. **Flow Control**: Check cwnd before forwarding (wait if needed)
6. **Congestion Control**: Pace transmission based on SRTT
7. **Socket**: New TCP connection to destination (demo site)
8. **Reliable Transfer**: Loop receives complete response
9. **Congestion Control**: Measure RTT, update cwnd
10. **Encryption**: Response encrypted
11. **Reliable Transfer**: Send with length prefix
12. **Socket**: TCP delivers to client
13. **Reliable Transfer**: Client receives complete encrypted response
14. **Encryption**: Client decrypts
15. **Result**: User sees webpage

**Why All Four Are Necessary**

Each concept solves a specific problem:

- **No sockets**: Can't communicate over network
- **No flow control**: Sender overwhelms receiver
- **No congestion control**: Network becomes congested and collapses
- **No reliable transfer**: Data arrives corrupted or incomplete

Together, they create a robust, efficient, fair, and reliable VPN system that demonstrates fundamental networking principles in action.

---

## Presentation Talking Points

**For Slides:**

**Slide 1: Socket Programming**
- "We used TCP sockets for reliable, connection-oriented communication"
- "Configured with SO_KEEPALIVE, TCP_NODELAY for optimal performance"
- "TCP three-way handshake visible in Wireshark demonstration"

**Slide 2: Flow Control**
- "Implemented congestion window limiting in-flight data"
- "Blocks transmission when window full - prevents receiver overflow"
- "Rate pacing smooths bursts for stable network utilization"

**Slide 3: Congestion Control**
- "Implemented TCP Reno algorithm with two phases"
- "Slow start: exponential growth for fast bandwidth discovery"
- "Congestion avoidance: linear growth for stability"
- "AIMD principle: additive increase, multiplicative decrease"
- "Observable in real-time through server logs"

**Slide 4: Reliable Data Transfer**
- "Built on TCP's automatic reliability (sequence numbers, ACKs, retransmission)"
- "Added length-prefixed protocol for message boundaries"
- "Loop-based reception handles large file transfers"
- "Error handling and timeouts prevent hanging"
- "Encryption provides integrity verification"

**Slide 5: Integration**
- "All four concepts work together for robust VPN"
- "Socket provides channel, flow control regulates receiver, congestion control adapts to network, reliable transfer ensures correctness"
- "Demonstrated through working implementation with Wireshark validation"
