# Congestion Control Logic - TCP Reno Implementation

## Overview

This VPN project implements a TCP Reno-like congestion control algorithm at the application layer. While TCP itself has built-in congestion control, this implementation demonstrates the algorithm's principles explicitly, showing how congestion windows grow and shrink in response to network conditions.

---

## Core Concepts

### What is Congestion Control?

Congestion control prevents a sender from overwhelming the network with too much data too quickly. Without it, packet loss increases, throughput decreases, and the network becomes unstable. The goal is to find the optimal sending rate: fast enough to use available bandwidth, slow enough to avoid congestion.

### Congestion Window (cwnd)

The congestion window represents the maximum amount of unacknowledged data that can be in flight at any time. Think of it as a "budget" for sending data:
- If cwnd = 4KB, you can send up to 4KB before waiting for acknowledgments
- When an ACK arrives, space opens in the window for more data
- Larger cwnd = higher throughput (but risk of congestion)
- Smaller cwnd = lower throughput (but safer, more stable)

### Slow Start Threshold (ssthresh)

The slow start threshold determines when to switch from aggressive exponential growth to conservative linear growth. Initially set to 8KB in this implementation, it acts as a dividing line between two phases of congestion control.

---

## Implementation Components

### File: server/flow_control.py

The FlowController class manages all congestion control logic. It is initialized with:
- min_window_size: 4096 bytes (4KB) - smallest allowed cwnd
- initial_window_size: 4096 bytes (4KB) - starting cwnd
- max_window_size: 1048576 bytes (1MB) - largest allowed cwnd
- ssthresh: 8192 bytes (8KB) - threshold between slow start and congestion avoidance

### Key Variables

**cwnd (Congestion Window)**
Current sending budget. Starts at 4KB and grows based on ACKs received.

**ssthresh (Slow Start Threshold)**
Set to 8KB. Determines when to transition from slow start to congestion avoidance.

**in_slow_start**
Boolean flag indicating current phase. True initially, becomes False when cwnd >= ssthresh.

**packets_in_flight**
Count of packets sent but not yet acknowledged. Cannot exceed cwnd.

**SRTT (Smoothed Round Trip Time)**
Exponentially weighted moving average of RTT samples. Used for timeout calculations.

**RTTVAR (RTT Variance)**
Measures how much RTT fluctuates. High variance indicates unstable network conditions.

---

## Congestion Control Phases

### Phase 1: Slow Start (Exponential Growth)

**Activation Condition**
- Initially active when connection starts
- in_slow_start = True
- cwnd < ssthresh

**Growth Algorithm**
When an ACK is received for packet_size bytes:
- cwnd = cwnd + packet_size
- Example: cwnd = 4KB, receive ACK for 111 bytes → cwnd = 4111 bytes

**Why "Exponential"?**
In a continuous data transfer where multiple packets are in flight:
- RTT 1: Send 1 packet (cwnd = 1×MTU), receive 1 ACK, cwnd doubles to 2×MTU
- RTT 2: Send 2 packets, receive 2 ACKs, cwnd doubles to 4×MTU
- RTT 3: Send 4 packets, receive 4 ACKs, cwnd doubles to 8×MTU

With sequential requests (like in this project), growth appears more gradual because only one packet is in flight at a time, but the algorithm is still exponential: each ACK increases cwnd by a full packet size.

**Transition Point**
When cwnd >= ssthresh (8KB), the system transitions to congestion avoidance. A log message appears: "Transitioned to CONGESTION AVOIDANCE".

**Purpose**
Quickly discover available bandwidth. Start conservatively but grow aggressively to reach optimal throughput fast.

### Phase 2: Congestion Avoidance (Linear Growth)

**Activation Condition**
- Activated when cwnd >= ssthresh
- in_slow_start = False
- Remains active until packet loss or timeout

**Growth Algorithm**
When an ACK is received for packet_size bytes:
- increment = (packet_size × packet_size) / cwnd
- cwnd = cwnd + increment
- Example: cwnd = 8KB, packet_size = 111 bytes → increment = (111×111)/8192 ≈ 1.5 bytes

**Why "Linear"?**
The formula ensures that cwnd increases by approximately one packet_size per RTT (when multiple packets are in flight):
- If cwnd = 8 packets, send 8 packets per RTT
- Receive 8 ACKs, each adding (1/8) packet size
- Total growth per RTT = 8 × (1/8) = 1 packet size
- This is linear growth: fixed amount per RTT

**Purpose**
Cautiously probe for more bandwidth without causing congestion. Once near network capacity, grow slowly to avoid packet loss.

---

## RTT Measurement and Adaptation

### RTT Sample Collection

For each request-response cycle:
- Record send_time when forwarding request
- Record receive_time when response arrives
- rtt_sample = receive_time - send_time

### Exponential Weighted Moving Average (EWMA)

**SRTT Calculation**
- alpha = 0.125 (weight for new sample)
- SRTT = (1 - alpha) × old_SRTT + alpha × rtt_sample
- SRTT = 0.875 × old_SRTT + 0.125 × rtt_sample

This smooths out variations, giving more weight to historical values while incorporating new measurements.

**RTTVAR Calculation**
- beta = 0.25 (weight for variance)
- RTTVAR = (1 - beta) × old_RTTVAR + beta × |SRTT - rtt_sample|
- RTTVAR = 0.75 × old_RTTVAR + 0.25 × |SRTT - rtt_sample|

This measures how much RTT fluctuates. Stable network = low RTTVAR. Unstable network = high RTTVAR.

### Timeout Calculation (RTO)

Retransmission timeout is calculated as:
- RTO = SRTT + 4 × RTTVAR
- Minimum RTO = 1 second

This formula (from RFC 6298) ensures timeouts accommodate both average RTT and variability. More variable networks get longer timeouts.

---

## Flow Control Functions

### wait_for_send_permission(data_size)

**Purpose:** Block transmission when congestion window is full

**Logic:**
1. Calculate required_packets = ceil(data_size / avg_packet_size)
2. While packets_in_flight + required_packets > cwnd:
   - Sleep for 100ms
   - Wait for ACKs to arrive and free up window space
3. Return True when window has space

**Effect:** Prevents sending too much data at once, enforcing the cwnd limit

### pace_transmission(data_size)

**Purpose:** Rate limiting to smooth out traffic bursts

**Logic:**
1. Calculate pacing_rate = cwnd / SRTT (bytes per second)
2. Calculate delay = data_size / pacing_rate (seconds)
3. Apply minimum delay of 1ms, maximum of 1 second
4. Sleep for calculated delay

**Effect:** Spreads packets over time rather than bursting them all at once

### on_packet_sent(packet_size)

**Purpose:** Track packets in flight

**Logic:**
1. Increment packets_in_flight counter
2. Increment total_packets_sent counter

**Effect:** Maintains accurate count for cwnd enforcement

### on_ack_received(packet_size, rtt_sample)

**Purpose:** Update cwnd and RTT metrics when ACK arrives

**Logic:**
1. Update RTT statistics (SRTT, RTTVAR)
2. Calculate throughput
3. If in_slow_start:
   - cwnd += packet_size (exponential growth)
   - If cwnd >= ssthresh: transition to congestion avoidance
4. Else (congestion avoidance):
   - increment = (packet_size × packet_size) / cwnd
   - cwnd += increment (linear growth)
5. Ensure cwnd stays within min/max bounds
6. Decrement packets_in_flight
7. Log current state

**Effect:** Implements the core congestion control algorithm

---

## Handling Packet Loss and Timeouts

### on_packet_loss()

**Purpose:** React to detected packet loss (duplicate ACKs or loss signal)

**Logic:**
1. Set ssthresh = max(cwnd / 2, min_window_size)
2. Set cwnd = max(cwnd / 2, min_window_size) (multiplicative decrease)
3. Stay in current phase (don't reset to slow start)
4. Log the loss event

**Effect:** Quickly reduce sending rate by half, preventing further congestion

### on_timeout()

**Purpose:** React to timeout (no response within RTO period)

**Logic:**
1. Set ssthresh = max(cwnd / 2, min_window_size)
2. Reset cwnd = min_window_size (back to 4KB)
3. Set in_slow_start = True (restart slow start phase)
4. Reset packets_in_flight = 0
5. Log timeout event

**Effect:** Severe reaction for severe congestion. Start over from scratch.

---

## AIMD Principle: Additive Increase, Multiplicative Decrease

The congestion control algorithm follows the AIMD principle, proven to be stable and fair:

**Additive Increase**
- In congestion avoidance, cwnd increases by approximately one packet per RTT
- Linear growth: cwnd(t) = cwnd(t-1) + constant
- Gradual probing for more bandwidth

**Multiplicative Decrease**
- On packet loss, cwnd is halved: cwnd = cwnd / 2
- On timeout, cwnd resets to minimum
- Aggressive backoff prevents congestion collapse

This asymmetry (slow increase, fast decrease) ensures network stability. Multiple flows converge to fair bandwidth sharing.

---

## Practical Example: Observing cwnd Growth

### Initial State
- cwnd = 4096 bytes (4KB)
- ssthresh = 8192 bytes (8KB)
- in_slow_start = True

### Request 1
- Send 111-byte request
- Receive ACK, RTT = 14.5ms
- cwnd += 111 → cwnd = 4207 bytes
- Still in slow start (4207 < 8192)

### Request 2
- Send 111-byte request
- Receive ACK, RTT = 13.2ms
- cwnd += 111 → cwnd = 4318 bytes
- Still in slow start

### Requests 3-35 (approximately)
- Each ACK adds 111 bytes to cwnd
- cwnd grows: 4429, 4540, 4651... 7889, 8000

### Request 36
- Send 111-byte request
- Receive ACK, RTT = 15.1ms
- cwnd += 111 → cwnd = 8111 bytes
- Transition! cwnd >= ssthresh (8111 >= 8192)
- in_slow_start = False
- Log: "Transitioned to CONGESTION AVOIDANCE"

### Request 37
- Send 111-byte request
- Receive ACK, RTT = 14.8ms
- increment = (111 × 111) / 8111 ≈ 1.52 bytes
- cwnd += 1.52 → cwnd = 8112.52 bytes
- Growth is now much slower

### Request 38
- increment ≈ 1.52 bytes
- cwnd = 8114.04 bytes
- Linear, steady growth

---

## Why This Matters

### Network Efficiency
Without congestion control, the VPN would send data as fast as possible, overwhelming the network and causing:
- Packet loss (buffers overflow)
- Retransmissions (wasting bandwidth)
- Increased latency (queue buildup)
- Poor performance for all users

### Fairness
Multiple VPN clients share the network. TCP Reno ensures each gets a fair share of bandwidth through:
- AIMD convergence (flows equalize over time)
- Responsive reduction (doesn't hog bandwidth when congested)
- Gradual increase (doesn't starve other flows)

### Stability
The two-phase approach balances competing goals:
- Fast discovery of available bandwidth (slow start)
- Stable operation near capacity (congestion avoidance)
- Quick reaction to congestion (multiplicative decrease)

### Observability
By implementing congestion control explicitly at the application layer, the project makes these algorithms visible and understandable. Logs show cwnd growth, phase transitions, and RTT measurements in real-time, demonstrating concepts that are normally hidden inside the TCP stack.

---

## Summary

The congestion control implementation demonstrates TCP Reno's key principles: starting cautiously with slow start, transitioning to conservative congestion avoidance, and reacting quickly to loss with multiplicative decrease. Combined with RTT measurement and adaptive timeouts, the system dynamically adjusts sending rates to maximize throughput while preventing network congestion. This application-layer implementation makes networking concepts tangible and observable, showing how theory translates to working code.
