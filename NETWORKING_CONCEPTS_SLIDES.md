# Networking Concepts - Slide Format

## Socket Programming (TCP Connection)

**What it is:**
Sockets are the fundamental interface for network communication. TCP sockets provide reliable, connection-oriented, bidirectional communication between client and server.

**How we used it:**
- Created TCP sockets (SOCK_STREAM) for VPN client-server connection
- Configured with SO_REUSEADDR, SO_KEEPALIVE, TCP_NODELAY for optimal performance
- TCP automatically handles three-way handshake (SYN → SYN-ACK → ACK) visible in Wireshark

---

## Flow Control

**What it is:**
Flow control prevents a fast sender from overwhelming a slow receiver by regulating the transmission rate to match receiver capacity.

**How we used it:**
- Implemented congestion window (cwnd) limiting maximum unacknowledged data in flight
- Block transmission when window full using wait_for_send_permission() to prevent receiver overflow
- Rate pacing smooths transmission bursts by adding calculated delays between packets

---

## Congestion Control (TCP Reno)

**What it is:**
Congestion control dynamically adjusts sending rate based on network conditions to prevent overwhelming the network and ensure fair bandwidth sharing.

**How we used it:**
- Slow Start phase: exponential cwnd growth (4KB → 8KB) for fast bandwidth discovery
- Congestion Avoidance phase: linear cwnd growth after reaching threshold for network stability
- AIMD principle: additive increase on success, multiplicative decrease (halve cwnd) on packet loss

---

## Reliable Data Transfer

**What it is:**
Reliable data transfer ensures data arrives completely, correctly, and in order despite potential packet loss, corruption, or reordering.

**How we used it:**
- TCP provides automatic reliability (sequence numbers, ACKs, retransmissions, checksums)
- Length-prefixed protocol (4-byte header) ensures complete message reception despite TCP stream nature
- Loop-based reception with 64KB chunks handles large file transfers (up to 50MB) without memory overflow
