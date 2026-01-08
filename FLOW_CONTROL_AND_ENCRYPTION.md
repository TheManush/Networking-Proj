# Flow Control and Encryption Explained

This document explains the flow control mechanism and encryption algorithms used in the VPN project.

---

## 📊 Part 1: Flow Control

Flow control prevents the sender from overwhelming the receiver or network by regulating transmission speed.

### 🎯 The Problem Without Flow Control

**Scenario: Sending data as fast as possible**

```
Sender: "Here's 10MB of data!" → FLOOD → Network/Receiver
                                  ↓
                        Packets dropped, congestion, chaos
```

**Problems:**
- Network routers' buffers overflow → packet loss
- Receiver can't process data fast enough → dropped packets
- Network congestion affects other users
- Need retransmissions → wasted bandwidth
- Poor performance for everyone

**Solution:** Flow control regulates the sending rate to match network capacity.

---

## 🔄 Flow Control Components in Your VPN

Your VPN implements **three key mechanisms**:

### 1. Congestion Window (cwnd)
### 2. Transmission Blocking (wait_for_send_permission)
### 3. Rate Pacing (smooth transmission)

Let's understand each one:

---

## 1️⃣ Congestion Window (cwnd)

### What is cwnd?

**Definition:** Maximum amount of unacknowledged data (in bytes) that can be "in flight" on the network.

**Think of it like a water pipe:**
```
┌─────────────────────────────────────────────────┐
│         Congestion Window (cwnd = 8192 bytes)   │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Packet 1: 111 bytes] ✓ Sent, waiting for ACK │
│  [Packet 2: 111 bytes] ✓ Sent, waiting for ACK │
│  [Packet 3: 111 bytes] ✓ Sent, waiting for ACK │
│  [Packet 4: 111 bytes] ✓ Sent, waiting for ACK │
│  ...                                            │
│  [Packet 73: 111 bytes] ✓ Sent, waiting for ACK│
│                                                 │
│  Space used: 8103 bytes / 8192 bytes            │
│  Space remaining: 89 bytes                      │
│                                                 │
│  ❌ WINDOW FULL - MUST WAIT FOR ACK             │
└─────────────────────────────────────────────────┘
```

**Once window is full:**
- ⏸️ Sender MUST STOP and WAIT for acknowledgments (ACKs)
- When ACK arrives → packet removed from window → space freed
- Can send new packets with freed space

### Why cwnd Changes Dynamically

**Your VPN uses TCP Reno algorithm:**

```
┌──────────────────────────────────────────────────┐
│             Congestion Window Growth             │
├──────────────────────────────────────────────────┤
│                                                  │
│  Phase 1: SLOW START (Exponential Growth)       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                  │
│  Initial cwnd: 4KB                               │
│  ACK #1 arrives → cwnd: 4KB + 111 = 4207 bytes  │
│  ACK #2 arrives → cwnd: 4207 + 111 = 4318 bytes │
│  ACK #3 arrives → cwnd: 4318 + 111 = 4429 bytes │
│  ...                                             │
│  ACK #36 arrives → cwnd: 8192 bytes ✓            │
│                                                  │
│  Reached ssthresh (8KB) → Switch to Phase 2     │
│                                                  │
├──────────────────────────────────────────────────┤
│  Phase 2: CONGESTION AVOIDANCE (Linear Growth)  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                  │
│  cwnd: 8192 bytes                                │
│  ACK arrives → cwnd: 8192 + (111²/8192) = 8193.5│
│  ACK arrives → cwnd: 8193.5 + 1.5 = 8195 bytes  │
│  Growth is MUCH slower (linear vs exponential)  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Formula Summary:**

| Phase | Growth Rate | Formula | Speed |
|-------|------------|---------|-------|
| **Slow Start** | Exponential | `cwnd += packet_size` | Fast (4KB → 8KB in ~36 ACKs) |
| **Congestion Avoidance** | Linear | `cwnd += (packet_size² / cwnd)` | Slow (~1 byte per ACK) |

**Why this matters:**
- Start aggressively to utilize available bandwidth
- Slow down before causing congestion
- Adapt to network conditions in real-time

### Code Implementation

**File:** `server/flow_control.py`

```python
def on_ack_received(self, packet_size, rtt_sample):
    """Update cwnd when ACK arrives"""
    
    # Update RTT statistics
    self._update_rtt(rtt_sample)
    
    # Adjust congestion window based on phase
    if self.in_slow_start:  # Phase 1: Slow Start
        old_cwnd = self.cwnd
        self.cwnd += packet_size  # Exponential growth
        
        # Check if we should transition to congestion avoidance
        if self.cwnd >= self.ssthresh:
            self.in_slow_start = False
            print(f"🚦 [Flow Control] Transition to Congestion Avoidance")
            print(f"   cwnd: {old_cwnd} → {self.cwnd} bytes")
            
    else:  # Phase 2: Congestion Avoidance
        # Linear growth: Add (packet_size² / cwnd) per ACK
        increment = (packet_size * packet_size) / self.cwnd
        self.cwnd += increment
    
    # Ensure cwnd stays within bounds
    self.cwnd = max(min(self.cwnd, self.max_window_size), self.min_window_size)
    
    # Free up space in window
    self.packets_in_flight -= 1
```

**Log Example from Your VPN:**
```
📊 [Flow Control] ACK received: cwnd=4096 → 4207 | ssthresh=8192 | Phase: slow_start
📊 [Flow Control] ACK received: cwnd=4207 → 4318 | ssthresh=8192 | Phase: slow_start
📊 [Flow Control] ACK received: cwnd=4318 → 4429 | ssthresh=8192 | Phase: slow_start
...
🚦 [Flow Control] Transition to Congestion Avoidance
   cwnd: 8081 → 8192 bytes
📊 [Flow Control] ACK received: cwnd=8192 → 8193.5 | ssthresh=8192 | Phase: congestion_avoidance
```

---

## 2️⃣ Transmission Blocking (wait_for_send_permission)

### What It Does

**Prevents sending when congestion window is full.**

Think of it like a traffic light:
```
🟢 GREEN: cwnd has space → Send packet
🔴 RED: cwnd is full → WAIT for ACK
```

### How It Works

**File:** `server/flow_control.py`

```python
def wait_for_send_permission(self, data_size):
    """Block transmission when window is full"""
    
    # Calculate how many packets we need to send
    avg_packet_size = 111  # Average HTTP request size
    required_packets = math.ceil(data_size / avg_packet_size)
    
    # Wait until window has enough space
    while self.packets_in_flight + required_packets > self.cwnd:
        print(f"⏸️  [Flow Control] Waiting for window space")
        print(f"   In flight: {self.packets_in_flight} | Required: {required_packets} | cwnd: {self.cwnd}")
        time.sleep(0.1)  # Sleep 100ms and check again
    
    return True  # Permission granted!
```

### Visual Example

**Scenario: Trying to send when window is full**

```
┌─────────────────────────────────────────────┐
│   Current State:                            │
│   packets_in_flight = 73                    │
│   cwnd = 8192 bytes                         │
│   avg_packet_size = 111 bytes               │
│                                             │
│   Space used: 73 × 111 = 8103 bytes         │
│   Space available: 8192 - 8103 = 89 bytes   │
└─────────────────────────────────────────────┘

New request arrives: 111 bytes

┌─────────────────────────────────────────────┐
│   Check: Can we send?                       │
│                                             │
│   packets_in_flight + 1 = 74                │
│   74 > 73.8 (cwnd / avg_packet_size)        │
│                                             │
│   ❌ NO SPACE! Window is full               │
│                                             │
│   Action: BLOCK and WAIT                    │
└─────────────────────────────────────────────┘

⏸️ Sender PAUSES...

(100ms later, ACK arrives)

┌─────────────────────────────────────────────┐
│   ACK received for Packet #1                │
│   packets_in_flight = 73 - 1 = 72           │
│   cwnd increased slightly: 8192 → 8193      │
│                                             │
│   Check again: Can we send now?             │
│   packets_in_flight + 1 = 73                │
│   73 < 73.8                                 │
│                                             │
│   ✅ YES! Space available                   │
│                                             │
│   Action: SEND PACKET                       │
└─────────────────────────────────────────────┘

🟢 Sender RESUMES and sends packet
```

### Why This Prevents Overflow

**Without blocking:**
```
Sender sends 100 packets instantly
    ↓
Network buffers: "Too much! Dropping packets!"
    ↓
Packet loss → Retransmission → Waste bandwidth
```

**With blocking:**
```
Sender sends packet #73
    ↓
wait_for_send_permission() blocks
    ↓
Wait for ACK → Free space → Send next packet
    ↓
Smooth, controlled transmission → No packet loss
```

---

## 3️⃣ Rate Pacing (Smooth Transmission)

### What It Does

**Adds calculated delays between packets to prevent bursts.**

### The Problem: Bursty Traffic

**Without pacing:**
```
Time: ──────┬──┬──┬──┬──────────────────────
Packets:    1  2  3  4  (all sent at once)
            └──┴──┴──┘
            Burst!
```

**Network routers:** "Whoa! Buffer overflow! Drop packets!"

**With pacing:**
```
Time: ──────┬────┬────┬────┬────┬────┬────
Packets:    1    2    3    4    5    6
            Smooth, steady flow
```

**Network routers:** "Perfect! I can handle this."

### How It Works

**File:** `server/flow_control.py`

```python
def pace_transmission(self, data_size):
    """Add delay to smooth out transmission"""
    
    # Calculate pacing rate (bytes per second)
    if self.smoothed_rtt > 0:
        pacing_rate = self.cwnd / self.smoothed_rtt  # bytes/sec
    else:
        pacing_rate = self.cwnd / 0.001  # Default if no RTT yet
    
    # Calculate delay for this packet
    delay = data_size / pacing_rate  # seconds
    
    # Clamp delay between 1ms and 1 second
    delay = max(0.001, min(delay, 1.0))
    
    # Sleep for calculated delay
    time.sleep(delay)
```

### Example Calculation

**Scenario:**
- cwnd = 8192 bytes
- SRTT (Smoothed RTT) = 20ms = 0.02 seconds
- Packet size = 111 bytes

**Step 1: Calculate pacing rate**
```
pacing_rate = cwnd / SRTT
pacing_rate = 8192 / 0.02
pacing_rate = 409,600 bytes/second
```

**Step 2: Calculate delay for this packet**
```
delay = packet_size / pacing_rate
delay = 111 / 409,600
delay = 0.00027 seconds = 0.27 milliseconds
```

**Step 3: Sleep**
```python
time.sleep(0.00027)  # Wait 0.27ms before sending next packet
```

**Result:** Packets spread evenly over time instead of all at once.

### Visual Comparison

**Without Rate Pacing:**
```
Timeline (milliseconds):
0ms          10ms
├────────────┤
│ 100 packets│  (Burst!)
└────────────┘
             └─ Network: "Too fast! Dropping packets!"
```

**With Rate Pacing:**
```
Timeline (milliseconds):
0ms                    27ms
├──────────────────────┤
│P1 P2 P3 P4 P5 P6 ... P100│ (Evenly spaced)
└──────────────────────┘
                       └─ Network: "Perfect rate!"
```

---

## 🔄 All Three Components Working Together

**File:** `server/tunnel_manager.py` → `_handle_forward_request()`

```python
def _handle_forward_request(self, destination_host, destination_port, request_data):
    """Forward a request through the tunnel with flow control"""
    
    # === STEP 1: Check congestion window ===
    # Block if window is full
    self.flow_controller.wait_for_send_permission(len(request_data))
    print(f"✅ Permission granted to send {len(request_data)} bytes")
    
    # === STEP 2: Rate pacing ===
    # Add delay to smooth transmission
    self.flow_controller.pace_transmission(len(request_data))
    print(f"⏱️  Pacing delay applied")
    
    # === STEP 3: Send packet ===
    send_start = time.time()
    dest_socket = socket.socket()
    dest_socket.connect((destination_host, destination_port))
    dest_socket.send(request_data)
    
    # Track packet in flight
    self.flow_controller.on_packet_sent(len(request_data))
    print(f"📤 Packet sent, in flight: {self.flow_controller.packets_in_flight}")
    
    # === STEP 4: Receive response ===
    response = dest_socket.recv(65536)
    
    # === STEP 5: Calculate RTT and update cwnd ===
    rtt = time.time() - send_start
    self.flow_controller.on_ack_received(len(request_data), rtt)
    print(f"📊 ACK received, cwnd updated")
    
    # === STEP 6: Send response back to client ===
    encrypted_response = self.encryption.encrypt(response)
    self.client_socket.send(encrypted_response)
    
    return True
```

### Complete Flow Control Cycle

```
┌─────────────────────────────────────────────────────────────┐
│  1. wait_for_send_permission()                              │
│     Check: cwnd has space?                                  │
│     • YES → Continue                                        │
│     • NO → Block and wait for ACK                           │
├─────────────────────────────────────────────────────────────┤
│  2. pace_transmission()                                     │
│     Calculate delay based on cwnd and RTT                   │
│     Sleep to prevent burst                                  │
├─────────────────────────────────────────────────────────────┤
│  3. Send packet                                             │
│     Transmit data over network                              │
├─────────────────────────────────────────────────────────────┤
│  4. on_packet_sent()                                        │
│     Increment packets_in_flight counter                     │
│     Track packet in congestion window                       │
├─────────────────────────────────────────────────────────────┤
│  5. Receive ACK (response from destination)                 │
│     Measure RTT (round-trip time)                           │
├─────────────────────────────────────────────────────────────┤
│  6. on_ack_received()                                       │
│     • Update cwnd (grow window)                             │
│     • Update SRTT (smoothed RTT)                            │
│     • Decrement packets_in_flight                           │
│     • Free space in window                                  │
└─────────────────────────────────────────────────────────────┘
         ↓
      Repeat for next packet
```

---

## 📈 Benefits of Flow Control

### 1. Prevents Packet Loss
```
Without Flow Control:
Send rate: 10 MB/s
Network capacity: 5 MB/s
Result: 5 MB/s dropped! 50% loss!

With Flow Control:
Send rate: Adaptive (starts slow, grows carefully)
Network capacity: 5 MB/s
Result: No loss, optimal throughput
```

### 2. Fair Network Usage
```
Multiple clients sharing network:
• Each client's cwnd adapts independently
• Network resources divided fairly
• No single client monopolizes bandwidth
```

### 3. Improved Performance
```
Without Flow Control:
• 50% packets lost
• Need retransmissions
• Actual throughput: 2.5 MB/s (50% of 5 MB/s)

With Flow Control:
• 0% packets lost
• No retransmissions
• Actual throughput: 4.8 MB/s (95% of 5 MB/s)
```

### 4. Receiver Protection
```
Receiver buffer: 10 KB
Sender sends: 50 KB instantly
Result without flow control: Buffer overflow, crash

With flow control:
• Sender sends at receiver's rate
• Receiver never overwhelmed
• Stable connection
```

---

## 📊 Summary: Flow Control Mechanisms

| Mechanism | Purpose | Implementation | Benefit |
|-----------|---------|----------------|---------|
| **Congestion Window (cwnd)** | Limit unacknowledged data | Dynamic size (4KB-1MB) | Prevents network congestion |
| **Transmission Blocking** | Enforce cwnd limit | `wait_for_send_permission()` blocks when full | Prevents receiver overflow |
| **Rate Pacing** | Smooth out bursts | Calculated delay between packets | Prevents buffer overflow |

**Together they ensure:**
- ✅ Sender never overwhelms receiver
- ✅ Network capacity not exceeded
- ✅ Optimal throughput without packet loss
- ✅ Fair bandwidth sharing
- ✅ Stable, reliable connection

---

# 🔐 Part 2: Encryption (AES and RSA)

Your VPN uses **two different encryption algorithms** for different purposes.

---

## 🔑 Encryption Overview

### Why Two Algorithms?

```
┌──────────────────────────────────────────────────────────┐
│              Encryption Trade-offs                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  FAST Encryption (AES)        SECURE Key Exchange (RSA) │
│  ✅ Very fast                 ✅ Very secure             │
│  ✅ Efficient                 ✅ No shared secret        │
│  ❌ Need shared key           ❌ Very slow               │
│  ❌ Key distribution problem  ❌ Limited data size       │
│                                                          │
│         SOLUTION: Use both!                              │
│  • RSA for initial key exchange (once)                  │
│  • AES for all data encryption (thousands of times)     │
└──────────────────────────────────────────────────────────┘
```

---

## 🔵 AES-256-CBC (Symmetric Encryption)

### What is AES?

**AES = Advanced Encryption Standard**

- **Type:** Symmetric encryption (same key for encrypt and decrypt)
- **Key size:** 256 bits (32 bytes)
- **Mode:** CBC (Cipher Block Chaining)
- **Speed:** Very fast (~1000 MB/s)

### How Symmetric Encryption Works

**Concept:** Both parties share the same secret key

```
┌────────────────────────────────────────────────────────┐
│                    Symmetric Encryption                │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Sender Side:                                          │
│  ┌──────────┐    ┌─────────┐    ┌──────────────┐     │
│  │ Plaintext│ +  │ AES Key │ → │  Ciphertext  │     │
│  │ "Hello"  │    │ (shared)│    │ \xf3\x8a...  │     │
│  └──────────┘    └─────────┘    └──────────────┘     │
│                                                        │
│  Receiver Side:                                        │
│  ┌──────────────┐  ┌─────────┐  ┌──────────┐         │
│  │  Ciphertext  │+ │ AES Key │→ │ Plaintext│         │
│  │ \xf3\x8a...  │  │ (shared)│  │ "Hello"  │         │
│  └──────────────┘  └─────────┘  └──────────┘         │
│                                                        │
│  🔑 SAME KEY for both encryption and decryption       │
└────────────────────────────────────────────────────────┘
```

### AES-256 Details

**256-bit key = 2^256 possible keys**

How secure is this?

```
2^256 = 115,792,089,237,316,195,423,570,985,008,687,907,853,269,984,665,640,564,039,457,584,007,913,129,639,936

To brute-force:
• Try 1 trillion keys per second
• Would take: 3.7 × 10^51 years
• Age of universe: 1.4 × 10^10 years

Conclusion: IMPOSSIBLE to break by brute force
```

### CBC Mode (Cipher Block Chaining)

**Why CBC?**

**Problem with basic encryption:**
```
Encrypt "AAA" → \xf3\xf3\xf3 (same plaintext → same ciphertext)
Attacker sees: "Pattern! They sent the same thing 3 times!"
```

**Solution: CBC adds randomness**
```
Step 1: Generate random IV (Initialization Vector)
Step 2: XOR first block with IV before encrypting
Step 3: XOR next block with previous ciphertext
Result: Same plaintext → Different ciphertext each time!
```

**Visual:**
```
┌─────────────────────────────────────────────────┐
│          CBC Mode Encryption                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  Block 1:  [Plaintext] ⊕ [IV] → Encrypt → [C1] │
│  Block 2:  [Plaintext] ⊕ [C1] → Encrypt → [C2] │
│  Block 3:  [Plaintext] ⊕ [C2] → Encrypt → [C3] │
│                                                 │
│  Same plaintext → Different ciphertext!         │
└─────────────────────────────────────────────────┘
```

### AES Implementation in Your VPN

**File:** `shared/encryption_handler.py`

```python
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def encrypt(self, data, aes_key):
    """Encrypt data with AES-256-CBC"""
    
    # Generate random IV (16 bytes for AES)
    iv = get_random_bytes(16)
    
    # Create AES cipher in CBC mode
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    
    # Pad data to multiple of 16 bytes (AES block size)
    padded_data = self._pad(data)
    
    # Encrypt
    ciphertext = cipher.encrypt(padded_data)
    
    # Return IV + ciphertext
    # (Receiver needs IV to decrypt)
    return iv + ciphertext

def decrypt(self, encrypted_data, aes_key):
    """Decrypt data with AES-256-CBC"""
    
    # Extract IV (first 16 bytes)
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]
    
    # Create AES cipher with same IV
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    
    # Decrypt
    plaintext = cipher.decrypt(ciphertext)
    
    # Remove padding
    return self._unpad(plaintext)
```

### Why AES for Data Encryption?

**Speed Comparison:**

| Algorithm | Speed | 1 GB File |
|-----------|-------|-----------|
| **AES-256** | ~1000 MB/s | 1 second |
| **RSA-2048** | ~0.1 MB/s | 10,000 seconds (2.7 hours) |

**Efficiency:**
- AES: Encrypt 1000 packets in 1 second ✅
- RSA: Encrypt 1000 packets in 2.7 hours ❌

**Your VPN sends thousands of packets per session.**  
**AES is the only practical choice for bulk data!**

---

## 🔴 RSA-2048 (Asymmetric Encryption)

### What is RSA?

**RSA = Rivest–Shamir–Adleman** (inventors' names)

- **Type:** Asymmetric encryption (different keys for encrypt/decrypt)
- **Key size:** 2048 bits (256 bytes)
- **Speed:** Very slow (~0.1 MB/s)
- **Use case:** Key exchange, digital signatures

### How Asymmetric Encryption Works

**Concept:** Two mathematically related keys - public and private

```
┌────────────────────────────────────────────────────────┐
│               Asymmetric Encryption                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Key Generation:                                       │
│  ┌────────────────────────────────────────┐           │
│  │  Generate Key Pair                     │           │
│  │  • Public Key  (share with everyone)   │           │
│  │  • Private Key (keep secret!)          │           │
│  └────────────────────────────────────────┘           │
│                                                        │
│  Encryption (by sender):                               │
│  ┌──────────┐   ┌────────────┐   ┌────────────┐      │
│  │Plaintext │ + │ Public Key │ → │ Ciphertext │      │
│  │ "Hello"  │   │ (receiver's)│   │ \xf3\x8a...│      │
│  └──────────┘   └────────────┘   └────────────┘      │
│                                                        │
│  Decryption (by receiver):                             │
│  ┌────────────┐  ┌─────────────┐  ┌──────────┐       │
│  │Ciphertext  │+ │ Private Key │→ │Plaintext │       │
│  │\xf3\x8a... │  │ (receiver's)│  │ "Hello"  │       │
│  └────────────┘  └─────────────┘  └──────────┘       │
│                                                        │
│  🔑 DIFFERENT keys for encryption and decryption      │
│  ✅ Only private key holder can decrypt               │
└────────────────────────────────────────────────────────┘
```

### Key Properties

**1. Public Key → Anyone can encrypt**
```
Alice has Bob's public key
Alice encrypts: "Secret message" + Bob's public key → Ciphertext
Bob decrypts: Ciphertext + Bob's private key → "Secret message"

Eve intercepts ciphertext: Cannot decrypt without Bob's private key!
```

**2. Private Key → Only you can decrypt**
```
Private key NEVER shared
Kept secure on your machine
If stolen: Security compromised!
```

**3. Mathematically related but can't derive one from the other**
```
Public key: Based on (n, e)
Private key: Based on (n, d)

Given public key → Cannot calculate private key
(Would require factoring very large prime numbers - computationally infeasible)
```

### RSA-2048 Security

**2048-bit key = Based on product of two 1024-bit prime numbers**

**To break RSA-2048:**
1. Factor n (2048-bit number) into two primes
2. Best known algorithm: General Number Field Sieve
3. Estimated time: ~300 trillion CPU-years

**Current recommendation:** RSA-2048 secure until ~2030

---

## 🔄 How Your VPN Uses Both

### Phase 1: Connection Establishment (RSA)

**Purpose:** Securely exchange the AES key

```
┌──────────────────────────────────────────────────────┐
│         Initial Connection (RSA Key Exchange)        │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Step 1: Client → Server                             │
│  ┌────────────────────────────────────────┐          │
│  │ "Here's my RSA public key"             │          │
│  │ (Anyone can see this, it's public)     │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│                                                      │
│  Step 2: Server → Client                             │
│  ┌────────────────────────────────────────┐          │
│  │ "Here's my RSA public key"             │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│                                                      │
│  Step 3: Authentication                              │
│  ┌────────────────────────────────────────┐          │
│  │ Client encrypts credentials with       │          │
│  │ Server's RSA public key:               │          │
│  │ {"username": "student",                │          │
│  │  "password": "secure123"}              │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│  ┌────────────────────────────────────────┐          │
│  │ Server decrypts with its private key   │          │
│  │ Validates credentials                  │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│                                                      │
│  Step 4: AES Key Exchange                            │
│  ┌────────────────────────────────────────┐          │
│  │ Server generates random AES-256 key    │          │
│  │ Encrypts it with Client's public key   │          │
│  │ Sends encrypted AES key to client      │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│  ┌────────────────────────────────────────┐          │
│  │ Client decrypts with its private key   │          │
│  │ Now both have the shared AES key!      │          │
│  └────────────────────────────────────────┘          │
│                                                      │
│  ✅ Secure key exchange complete                    │
│  🔒 AES key never transmitted in plaintext          │
└──────────────────────────────────────────────────────┘
```

**Code:** `server/vpn_server_enhanced.py` → `_handle_client()`

```python
# Step 1: Receive client's RSA public key
client_public_key_pem = self._receive_length_prefixed(client_socket)
client_public_key = serialization.load_pem_public_key(client_public_key_pem)

# Step 2: Send server's RSA public key
server_public_key_pem = self.rsa_handler.get_public_key_pem()
self._send_length_prefixed(client_socket, server_public_key_pem)

# Step 3: Receive encrypted credentials (encrypted with server's public key)
encrypted_auth = self._receive_length_prefixed(client_socket)
auth_data = self.rsa_handler.decrypt(encrypted_auth)  # Decrypt with server's private key

# Step 4: Generate and send AES key (encrypted with client's public key)
aes_key = get_random_bytes(32)  # 256 bits = 32 bytes
encrypted_aes_key = client_public_key.encrypt(aes_key, ...)
self._send_length_prefixed(client_socket, encrypted_aes_key)
```

**Why RSA here?**
- ✅ No pre-shared secret needed
- ✅ Client and server never met before
- ✅ Can exchange AES key securely over untrusted network
- ✅ Even if attacker intercepts everything, can't get AES key (needs private key)

---

### Phase 2: Data Transmission (AES)

**Purpose:** Encrypt all VPN traffic

```
┌──────────────────────────────────────────────────────┐
│          All Subsequent Traffic (AES)                │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Client → Server:                                    │
│  ┌────────────────────────────────────────┐          │
│  │ HTTP Request (plaintext)               │          │
│  │ "GET / HTTP/1.1..."                    │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│  ┌────────────────────────────────────────┐          │
│  │ Encrypt with AES-256-CBC               │          │
│  │ Result: \xf3\x8a\x9c\x4e...            │          │
│  └────────────────────────────────────────┘          │
│                ↓                                     │
│          [Network]                                   │
│  (Encrypted, unreadable to attackers)                │
│                ↓                                     │
│  ┌────────────────────────────────────────┐          │
│  │ Decrypt with AES-256-CBC               │          │
│  │ Result: "GET / HTTP/1.1..."            │          │
│  └────────────────────────────────────────┘          │
│                                                      │
│  Server → Client:                                    │
│  (Same process for responses)                        │
│                                                      │
│  Speed: ~1000 packets per second ✅                 │
└──────────────────────────────────────────────────────┘
```

**Code:** `server/tunnel_manager.py`

```python
# Receive encrypted request from client
encrypted_request = self._receive_length_prefixed(self.client_socket)

# Decrypt with AES
plaintext_request = self.encryption.decrypt(encrypted_request, self.aes_key)

# Forward to demo site...
response = forward_to_demo_site(plaintext_request)

# Encrypt response with AES
encrypted_response = self.encryption.encrypt(response, self.aes_key)

# Send back to client
self._send_length_prefixed(self.client_socket, encrypted_response)
```

**Why AES here?**
- ✅ Fast enough for bulk data (thousands of packets)
- ✅ Secure (256-bit key = unbreakable)
- ✅ Efficient (low CPU usage)

---

## 📊 Comparison Summary

| Feature | AES-256-CBC | RSA-2048 |
|---------|-------------|----------|
| **Type** | Symmetric | Asymmetric |
| **Keys** | 1 shared key | Public + Private pair |
| **Key Size** | 256 bits (32 bytes) | 2048 bits (256 bytes) |
| **Speed** | ⚡ Very fast (~1000 MB/s) | 🐌 Slow (~0.1 MB/s) |
| **Use Case** | Bulk data encryption | Key exchange, authentication |
| **Security** | Unbreakable (2^256 keyspace) | Secure until ~2030 |
| **Key Distribution** | ❌ Problem: How to share? | ✅ Public key can be shared openly |
| **Data Size** | ✅ Unlimited | ❌ Limited (max ~200 bytes) |
| **When Used** | All VPN traffic | Initial connection only |

---

## 🎯 Why This Combination is Perfect

```
┌─────────────────────────────────────────────────────┐
│              Best of Both Worlds                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  RSA (Asymmetric):                                  │
│  ✅ Solves key distribution problem                │
│  ✅ No pre-shared secret needed                    │
│  ✅ Secure key exchange over untrusted network     │
│  ➡️  Used ONCE per connection                      │
│                                                     │
│  AES (Symmetric):                                   │
│  ✅ Fast bulk encryption                           │
│  ✅ Low CPU usage                                  │
│  ✅ Can encrypt unlimited data                     │
│  ➡️  Used THOUSANDS of times per session           │
│                                                     │
│  Combined = Hybrid Cryptosystem                     │
│  Used by: TLS, SSH, VPNs, Signal, WhatsApp         │
└─────────────────────────────────────────────────────┘
```

**Real-World Analogy:**

```
RSA = Secure courier to deliver key
AES = The locked box for all your valuables

Process:
1. Use secure courier (RSA) to safely deliver the box key
2. Use the box (AES) for all your daily secure storage
3. Courier is expensive (slow) but you only need it once
4. Box is cheap (fast) and you use it constantly
```

---

## 📝 Summary

### Flow Control:

**Three key mechanisms work together:**

1. **Congestion Window (cwnd)** - Dynamic limit on unacknowledged data
   - Grows during slow start (exponential)
   - Grows slowly in congestion avoidance (linear)
   - Adapts to network conditions

2. **wait_for_send_permission()** - Blocks transmission when window full
   - Prevents overwhelming receiver
   - Enforces cwnd limit
   - Resumes when ACKs free space

3. **pace_transmission()** - Smooths out transmission bursts
   - Calculates delay based on cwnd/RTT
   - Prevents buffer overflow
   - Improves network efficiency

**Result:** Optimal throughput without packet loss ✅

### Encryption:

**Two algorithms for different purposes:**

1. **RSA-2048** - Asymmetric encryption for key exchange
   - Used once per connection
   - Slow but solves key distribution
   - Enables secure communication without pre-shared secret

2. **AES-256-CBC** - Symmetric encryption for data
   - Used for all VPN traffic
   - Fast and efficient
   - Unbreakable security

**Result:** Secure, fast VPN tunnel ✅

---

## 🎓 For Your Presentation

**When asked about flow control:**

*"I implemented TCP Reno-style flow control with three mechanisms:*

1. *Congestion window that limits unacknowledged data in flight*
2. *Transmission blocking that waits when the window is full*
3. *Rate pacing that smooths transmission bursts*

*Together, these prevent packet loss, protect the receiver, and ensure optimal network utilization."*

**When asked about encryption:**

*"I use a hybrid cryptosystem - RSA-2048 for initial key exchange and AES-256-CBC for all data:*

- *RSA solves the key distribution problem securely*
- *AES provides fast, efficient bulk encryption*
- *This is the same approach used by TLS, SSH, and commercial VPNs"*

✅ Clear, confident, technically accurate!
