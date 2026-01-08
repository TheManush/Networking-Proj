# VPN Project - Working Principles

## Overview

This project implements a custom VPN (Virtual Private Network) that demonstrates core networking principles including TCP socket programming, encryption, tunneling, flow control, and congestion management. The system consists of a VPN server, VPN clients, and a demo website that implements IP-based access control.

---

## System Architecture

### Components

**Client VM (192.168.0.129 / 192.168.0.120)**
- VPN Client application with GUI
- Initiates encrypted connection to VPN server
- Sends HTTP requests through encrypted tunnel
- Tracks connection statistics (RTT, throughput, packets)

**Server VM (192.168.0.107)**
- VPN Server listening on port 5555
- Demo website on port 9000 with IP blocking
- Handles multiple simultaneous client connections
- Implements flow control and congestion management

---

## Working Flow

### Phase 1: Connection Establishment

**Step 1: TCP Socket Connection**

The client initiates a TCP connection to the VPN server on port 5555. The operating system handles the three-way handshake automatically:
- Client sends SYN packet to server
- Server responds with SYN-ACK packet
- Client sends ACK packet
- TCP connection established

This handshake is visible in Wireshark as the first three packets when the VPN client connects.

**Step 2: RSA Key Exchange**

Once the TCP connection is established, both client and server exchange their RSA-2048 public keys:
- Each side generates an RSA key pair (public + private)
- Client sends its RSA public key to server (visible as PEM format in Wireshark)
- Server sends its RSA public key to client
- Both sides now have each other's public key for secure communication

**Step 3: Authentication**

The client authenticates with the server using encrypted credentials:
- Client encrypts username and password using server's RSA public key
- Server receives encrypted credentials
- Server decrypts using its RSA private key
- Server verifies credentials against stored users
- If valid, authentication succeeds

**Step 4: AES Session Key Distribution**

After successful authentication, the server generates a secure session key for fast encryption:
- Server generates random 32-byte AES-256 key
- Server encrypts this AES key using client's RSA public key
- Client receives encrypted AES key
- Client decrypts using its RSA private key
- Both sides now share the same AES key for symmetric encryption

At this point, the VPN tunnel is fully established and ready for data transmission.

---

### Phase 2: Data Transmission Through Tunnel

**Step 1: Client Prepares HTTP Request**

When the user wants to access the demo site, the client prepares a standard HTTP request containing the destination address and the actual request data.

**Step 2: Encryption**

The plaintext HTTP request is encrypted using AES-256-CBC with the shared session key. This converts readable text into unreadable ciphertext. A 4-byte length header is prepended to indicate the message size.

**Step 3: Transmission to VPN Server**

The encrypted packet is sent through the TCP socket to the VPN server. In Wireshark on the client side, this appears as encrypted data - just random-looking bytes. No one intercepting this traffic can read the actual HTTP request.

**Step 4: Server Receives and Decrypts**

The VPN server receives the encrypted packet, reads the length header, receives the full encrypted message, and decrypts it using the shared AES key. The server now has the plaintext HTTP request and knows the destination (192.168.0.107:9000).

**Step 5: Flow Control Check**

Before forwarding the request, the flow controller checks if transmission is permitted:
- Checks if congestion window (cwnd) has space
- If packets_in_flight >= cwnd, waits until window opens
- Calculates pacing delay based on current cwnd and RTT
- Controls transmission rate to prevent network congestion

**Step 6: Forwarding to Demo Site**

The VPN server creates a new TCP connection to the demo site (loopback: 127.0.0.1:9000). This involves another TCP handshake, visible in Wireshark on the server's loopback interface. The server sends the plaintext HTTP request to the demo site.

**Step 7: Demo Site Processes Request**

The demo site receives the request and checks the source IP address:
- If request comes from 192.168.0.129 or 192.168.0.120 directly: ACCESS DENIED (403)
- If request comes from 192.168.0.107 (the VPN server): ACCESS GRANTED (200)

Since the request is forwarded by the VPN server, it appears to come from 192.168.0.107, so access is granted.

**Step 8: Demo Site Response**

The demo site generates an HTTP response (HTML content, headers, etc.) and sends it back to the VPN server through the loopback connection. This plaintext response is visible in Wireshark on the server's loopback interface.

**Step 9: Flow Control Update**

The VPN server measures the round-trip time (RTT) from when the request was sent to when the response was received. The flow controller updates its metrics:
- Calculates RTT sample
- Updates smoothed RTT (SRTT) using exponential moving average
- Updates RTT variance (RTTVAR)
- Updates congestion window (cwnd) based on current phase
- Decrements packets_in_flight counter

**Step 10: Response Encryption**

The VPN server encrypts the demo site's response using AES-256 with the session key, prepends a length header, and sends the encrypted response back to the client through the VPN tunnel.

**Step 11: Client Receives and Displays**

The client receives the encrypted response, decrypts it using the shared AES key, extracts the HTTP response, and displays the content to the user. The client also updates its statistics (bytes received, packets, throughput, RTT).

---

## Key Networking Principles Demonstrated

### 1. Socket Programming

The project uses TCP sockets (SOCK_STREAM) for reliable, connection-oriented communication. Sockets are configured with specific options:
- SO_KEEPALIVE: Keeps idle connections alive
- TCP_NODELAY: Disables Nagle's algorithm for low latency
- SO_REUSEADDR: Allows quick server restart without waiting for socket timeout

### 2. Encryption and Security

Two encryption methods work together:

**RSA-2048-OAEP (Asymmetric)**
- Used once during connection setup
- Secure key exchange without pre-shared secrets
- Slow but secure for small data (keys)

**AES-256-CBC (Symmetric)**
- Used for all actual data transmission
- Fast encryption suitable for large amounts of data
- Requires both parties to have the same key

### 3. Tunneling and IP Masquerading

The VPN creates an encrypted tunnel between client and server. From the demo site's perspective, all requests appear to come from the VPN server's IP address (192.168.0.107), not the client's real IP. This demonstrates IP masquerading - a key VPN feature that hides the client's true identity and location.

### 4. Flow Control

Flow control prevents the sender from overwhelming the receiver. The implementation tracks:
- Congestion window (cwnd): Amount of data that can be in flight
- Packets in flight: Currently unacknowledged packets
- Transmission permission: Blocks sending when window is full
- Pacing: Delays between packets based on available bandwidth

### 5. Congestion Control (TCP Reno)

The project implements TCP Reno congestion control algorithm with two phases:

**Slow Start Phase**
- Starts with small congestion window (4KB)
- Grows exponentially (doubles every RTT in theory)
- Fast bandwidth discovery
- Continues until reaching ssthresh (8KB)

**Congestion Avoidance Phase**
- Activated when cwnd >= ssthresh
- Grows linearly (slowly)
- Prevents network congestion
- Sustainable bandwidth utilization

### 6. RTT Measurement

Round-trip time is measured for every request-response cycle. The system maintains:
- RTT samples: Individual measurements
- SRTT: Smoothed RTT using exponential moving average
- RTTVAR: RTT variance measuring fluctuation
- RTO: Retransmission timeout calculated as SRTT + 4×RTTVAR

### 7. Multi-threading

The server uses threading to handle multiple clients simultaneously. Each client connection runs in its own thread, allowing concurrent VPN tunnels without blocking. This demonstrates scalable server architecture.

### 8. Length-Prefixed Protocol

All messages use a length-prefixed protocol: a 4-byte header indicates the message size, followed by the actual data. This solves the problem of variable-length messages over TCP streams, ensuring complete messages are received before processing.

### 9. Wireshark Analysis

The project allows network packet analysis at different points:

**Client VM capture (port 5555)**
- Shows encrypted tunnel traffic
- Demonstrates AES encryption in action
- All data appears as random bytes

**Server VM loopback capture (port 9000)**
- Shows plaintext traffic to demo site
- Demonstrates tunneling and decryption
- Readable HTTP requests and responses

**Comparing both captures**
- Proves encryption is working
- Shows the transformation from encrypted to plaintext
- Visualizes the tunnel concept

---

## Statistics and Monitoring

### Client Statistics

**RTT (Round Trip Time)**
- Measures time from client sending request to receiving response
- Includes network latency + VPN processing + demo site response
- Updated in real-time in GUI

**Bytes Sent/Received**
- Total data transmitted in both directions
- Includes all encrypted data, headers, and overhead
- Accurate measurement of network usage

**Packets**
- Count of application-level packets sent
- Not the same as TCP segments (TCP may split into multiple segments)

**Uptime**
- Seconds since VPN connection established
- Simple timer tracking connection duration

**Throughput**
- Average data rate: bytes_received / uptime
- Measured in KB/s
- Real-time calculation of bandwidth usage

### Server Statistics

**Total Data Forwarded**
- Sum of all data passing through VPN server
- Across all client connections
- Demonstrates server load

**Active Tunnels**
- Number of currently connected clients
- Shows concurrent connection handling

**Flow Control Metrics**
- Current congestion window (cwnd)
- Slow start threshold (ssthresh)
- Current phase (SLOW START or CONG AVOID)
- SRTT and RTTVAR values
- Per-client metrics for each tunnel

---

## Summary

This VPN project demonstrates fundamental networking concepts through practical implementation. It shows how TCP sockets establish reliable connections, how encryption secures data in transit, how tunneling hides client identity, and how flow and congestion control manage network resources efficiently. The system is observable through Wireshark at multiple points, allowing verification of encryption, tunneling, and protocol behavior.
