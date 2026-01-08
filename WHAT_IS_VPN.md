# What is a VPN and How My Project Works

This document explains VPN technology and how this project implements a custom VPN solution.

---

## 📚 Part 1: What is a VPN?

### Definition

**VPN = Virtual Private Network**

A VPN creates a **secure, encrypted connection** (called a "tunnel") between your device and a VPN server over the public internet. This tunnel protects your data from eavesdropping and masks your real IP address.

---

### The Problem VPNs Solve

#### Without VPN

```
┌──────────────────────────────────────────────────────────┐
│         Your Computer on Public Network                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  You (192.168.0.129)                                     │
│       │                                                  │
│       │ "GET /secret-page"                               │
│       │ (Plaintext, anyone can read)                     │
│       ↓                                                  │
│  [ISP Router]                                            │
│       │ Can see: What websites you visit                 │
│       │ Can see: What you're downloading                 │
│       │ Can block: Specific websites                     │
│       │ Can throttle: Certain types of traffic           │
│       ↓                                                  │
│  [Website Server]                                        │
│       │ Sees your real IP: 192.168.0.129                 │
│       │ Knows your location                              │
│       │ Can block you based on IP                        │
│       │ Can track your activity                          │
│                                                          │
│  ❌ No Privacy - ISP sees everything                    │
│  ❌ No Anonymity - Websites see your real IP            │
│  ❌ No Security - Data can be intercepted               │
│  ❌ No Access - Blocked sites stay blocked              │
└──────────────────────────────────────────────────────────┘
```

**Problems:**
1. **Privacy:** ISP can see all your internet activity
2. **Security:** Data transmitted in plaintext can be intercepted (especially on public WiFi)
3. **Anonymity:** Websites know your real IP address and location
4. **Censorship:** ISP or network admin can block certain websites
5. **Tracking:** Websites can track your activity across the internet
6. **Geo-restrictions:** Content blocked based on your location

---

#### With VPN

```
┌──────────────────────────────────────────────────────────┐
│         Your Computer Using VPN                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  You (192.168.0.129)                                     │
│       │                                                  │
│       │ "GET /secret-page"                               │
│       │ (Encrypted with AES-256)                         │
│       ↓                                                  │
│  [VPN Client - Encryption]                               │
│       │ \xf3\x8a\x9c... (encrypted gibberish)           │
│       ↓                                                  │
│  [ISP Router]                                            │
│       │ Can see: You're connected to VPN server          │
│       │ CANNOT see: What websites you visit              │
│       │ CANNOT see: What you're doing                    │
│       │ CANNOT block: Don't know destination             │
│       ↓                                                  │
│  🔒 Encrypted Tunnel 🔒                                  │
│       │ (Data protected from eavesdropping)              │
│       ↓                                                  │
│  [VPN Server] (192.168.0.120)                            │
│       │ Decrypts your request                            │
│       │ Forwards to website on your behalf               │
│       ↓                                                  │
│  [Website Server]                                        │
│       │ Sees VPN IP: 192.168.0.120 (not yours!)         │
│       │ Thinks request is from VPN location              │
│       │ Cannot track your real IP                        │
│                                                          │
│  ✅ Privacy - ISP only sees encrypted tunnel            │
│  ✅ Anonymity - Website sees VPN IP, not yours          │
│  ✅ Security - All data encrypted                       │
│  ✅ Access - Bypass blocks and restrictions             │
└──────────────────────────────────────────────────────────┘
```

**Benefits:**
1. **Privacy:** ISP only sees you're connected to VPN, not what you're doing
2. **Security:** All data encrypted with military-grade encryption
3. **Anonymity:** Your real IP address is hidden from websites
4. **Bypass blocks:** Access geo-restricted or blocked content
5. **Prevent tracking:** Websites can't track your real location
6. **Public WiFi safety:** Protected on untrusted networks

---

## 🔑 Core VPN Features

### 1. Encryption (Privacy & Security)

**What it does:** Scrambles your data so no one can read it

```
Original Data:     "GET /bank-account HTTP/1.1"
After Encryption:  "\xf3\x8a\x9c\x4e\xb7\x2d\x1c\xa3..."

Observer sees: Random bytes (meaningless)
Only VPN server with key can decrypt
```

**Benefit:** 
- ISP can't see what websites you visit
- Hackers can't steal your passwords on public WiFi
- Government can't monitor your browsing

---

### 2. Tunneling (Secure Pathway)

**What it does:** Creates a protected "tunnel" through the public internet

```
Your Device ═══🔒 Encrypted Tunnel 🔒═══ VPN Server ──→ Internet
               (Secure pathway)              (Exit point)
```

**Benefit:**
- Data travels safely through hostile networks
- Bypass firewalls and filters
- Create private connection over public infrastructure

---

### 3. IP Masquerading (Anonymity)

**What it does:** Hides your real IP address behind VPN server's IP

```
Without VPN:
Website sees: Your IP (192.168.0.129)
Location: Your actual location
Tracking: Possible

With VPN:
Website sees: VPN IP (192.168.0.120)
Location: VPN server's location
Tracking: Blocked
```

**Benefit:**
- Websites can't identify you
- Access geo-restricted content (Netflix regions, etc.)
- Bypass IP-based blocking

---

### 4. Authentication (Access Control)

**What it does:** Verifies you're authorized to use the VPN

```
Connection Attempt:
1. Provide username/password
2. Server validates credentials
3. If valid: Create tunnel
4. If invalid: Reject connection
```

**Benefit:**
- Only authorized users can connect
- Prevents unauthorized access
- Audit who's using the VPN

---

## 🌍 Real-World VPN Use Cases

### 1. Public WiFi Security

**Scenario:** You're at a coffee shop using their WiFi

**Problem:** Hacker on same WiFi can intercept your data
```
You → Public WiFi → Hacker (sees your passwords!)
```

**Solution:** VPN encrypts everything
```
You → Public WiFi → VPN Server → Internet
     (Encrypted)    (Hacker sees gibberish)
```

---

### 2. Bypass Geo-Restrictions

**Scenario:** Netflix shows different content in different countries

**Problem:** US-only shows not available in your country
```
You (UK) → Netflix → "Not available in your region"
```

**Solution:** VPN makes you appear to be in the US
```
You (UK) → VPN (US) → Netflix → "Here's US content!"
```

---

### 3. Bypass Censorship

**Scenario:** Government or school blocks certain websites

**Problem:** Direct access is blocked
```
You → Firewall → "Access Denied"
```

**Solution:** VPN bypasses the block
```
You → VPN (encrypted) → Outside Firewall → Blocked Site
     (Firewall can't see destination)
```

---

### 4. Corporate Remote Access

**Scenario:** Working from home, need to access company servers

**Problem:** Company servers only accept connections from office network
```
Home Computer → Company Server → "Unauthorized IP"
```

**Solution:** VPN gives you virtual presence in office
```
Home Computer → VPN → Company Network → "Authorized, welcome!"
                (Appears to be in office)
```

---

### 5. Hide Activity from ISP

**Scenario:** ISP tracks your browsing or throttles certain traffic

**Problem:** ISP monitors everything
```
You → ISP → "They're watching Netflix, let's slow it down"
```

**Solution:** VPN hides your activity
```
You → Encrypted Tunnel → VPN Server → Netflix
     (ISP sees: "Something encrypted, can't tell what")
```

---

## 🛠️ Part 2: How My Custom VPN Works

### Project Overview

**My VPN Project implements a fully functional VPN system with:**
- Encrypted tunnel using AES-256-CBC
- RSA-2048 key exchange
- IP masquerading
- Flow control and congestion management
- SOCKS proxy integration for browser support
- Two-VM architecture (client and server)

---

## 🏗️ Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    My Custom VPN                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Client VM (192.168.0.129)        Server VM (192.168.0.120)│
│  ┌──────────────────────┐         ┌──────────────────────┐ │
│  │  Firefox Browser     │         │  VPN Server          │ │
│  │        ↓             │         │  • Decrypt requests  │ │
│  │  Local Proxy (8080)  │         │  • Forward traffic   │ │
│  │        ↓             │         │  • Flow control      │ │
│  │  VPN Client          │         │        ↓             │ │
│  │  • Encrypt           │  Tunnel │  Demo Site (9000)    │ │
│  │  • Connect to server │←═══════→│  • Access control    │ │
│  │  • Manage tunnel     │  🔒     │  • IP filtering      │ │
│  └──────────────────────┘         └──────────────────────┘ │
│                                                             │
│  Key Components:                                            │
│  • AES-256-CBC for data encryption                         │
│  • RSA-2048 for key exchange                               │
│  • TCP Reno flow control                                   │
│  • SOCKS proxy for browser integration                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Workflow

### Phase 1: Connection Establishment

**Step 1: Start VPN Server (Server VM)**
```bash
python3 server/vpn_server_enhanced.py
```

**What happens:**
- Server starts listening on port 5555 (VPN tunnel)
- Generates RSA key pair (public + private)
- Waits for client connections

---

**Step 2: Start Demo Site (Server VM)**
```bash
python3 demo_site/app.py
```

**What happens:**
- Website starts on port 9000
- Configures IP filtering:
  - ALLOWED: 127.0.0.1, 192.168.0.120 (VPN server)
  - BLOCKED: 192.168.0.129 (client)
- Demonstrates access control

---

**Step 3: Start VPN Client (Client VM)**
```bash
python3 client/vpn_client_enhanced.py
```

**What happens:**
```
┌──────────────────────────────────────────┐
│  1. Start Local Proxy Server            │
│     • Binds to localhost:8080            │
│     • Waits for Firefox connections      │
│                                          │
│  2. Connect to VPN Server                │
│     • TCP connection to 192.168.0.120:5555│
│                                          │
│  3. RSA Key Exchange                     │
│     • Exchange public keys               │
│     • Both sides can now encrypt for each│
│                                          │
│  4. Authentication                       │
│     • Encrypt credentials with server's  │
│       public key                         │
│     • Send to server                     │
│     • Server validates                   │
│                                          │
│  5. Receive AES Session Key              │
│     • Server generates random AES key    │
│     • Encrypts with client's public key  │
│     • Client decrypts with private key   │
│                                          │
│  ✅ Tunnel Established!                  │
└──────────────────────────────────────────┘
```

---

### Phase 2: Browser Configuration

**Step 4: Configure Firefox to Use VPN**

1. Open Firefox → Settings → Network Settings
2. Select "Manual proxy configuration"
3. HTTP Proxy: `localhost`, Port: `8080`
4. Click OK

**Why this works:**
- Firefox now sends ALL requests to localhost:8080
- VPN client's local proxy receives them
- Proxy forwards through encrypted tunnel
- No need for custom browser or browser extensions!

---

### Phase 3: Data Flow (Requesting a Website)

**Step 5: User Browses Website**

User types in Firefox: `http://192.168.0.120:9000`

**Complete Journey of the Request:**

```
┌─────────────────────────────────────────────────────────┐
│  1. Firefox → Local Proxy (Port 8080)                   │
│     HTTP Request: "GET / HTTP/1.1"                      │
│     (Plaintext on localhost)                            │
├─────────────────────────────────────────────────────────┤
│  2. Local Proxy → VPN Client Encryption                 │
│     Wrap in JSON: {destination, port, data}             │
│     Encrypt with AES-256-CBC                            │
│     Result: \xf3\x8a\x9c... (encrypted bytes)           │
├─────────────────────────────────────────────────────────┤
│  3. VPN Client → VPN Server (Port 5555)                 │
│     Send encrypted packet over network                  │
│     🔒 ENCRYPTED TUNNEL 🔒                              │
│     (ISP sees: gibberish, can't read content)           │
├─────────────────────────────────────────────────────────┤
│  4. VPN Server Receives & Decrypts                      │
│     Decrypt with shared AES key                         │
│     Extract: destination=192.168.0.120:9000             │
│     Extract: data="GET / HTTP/1.1..."                   │
├─────────────────────────────────────────────────────────┤
│  5. VPN Server → Flow Control                           │
│     Check congestion window (cwnd)                      │
│     Apply rate pacing                                   │
│     Permission granted → Continue                       │
├─────────────────────────────────────────────────────────┤
│  6. VPN Server → Demo Site (Port 9000)                  │
│     Create new TCP connection                           │
│     Forward HTTP request (plaintext)                    │
│     FROM: 192.168.0.120 (VPN server IP!)                │
├─────────────────────────────────────────────────────────┤
│  7. Demo Site Access Check                              │
│     Check source IP: 192.168.0.120                      │
│     In ALLOWED_IPS? YES ✅                              │
│     Process request, generate response                  │
├─────────────────────────────────────────────────────────┤
│  8. Demo Site → VPN Server                              │
│     HTTP Response: "HTTP/1.1 200 OK..."                 │
│     HTML content                                        │
├─────────────────────────────────────────────────────────┤
│  9. VPN Server → Encryption                             │
│     Encrypt response with AES-256-CBC                   │
│     Measure RTT, update flow control                    │
├─────────────────────────────────────────────────────────┤
│  10. VPN Server → VPN Client (Port 5555)                │
│      Send encrypted response                            │
│      🔒 ENCRYPTED TUNNEL 🔒                             │
├─────────────────────────────────────────────────────────┤
│  11. VPN Client Receives & Decrypts                     │
│      Decrypt with shared AES key                        │
│      Extract HTTP response                              │
├─────────────────────────────────────────────────────────┤
│  12. Local Proxy → Firefox                              │
│      Forward plaintext HTTP response                    │
├─────────────────────────────────────────────────────────┤
│  13. Firefox Renders Page                               │
│      Parse HTML, render webpage                         │
│      🎉 User sees the website!                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Implementation

### 1. Hybrid Encryption (RSA + AES)

**Why two algorithms?**

```
┌────────────────────────────────────────┐
│  Challenge: Key Distribution           │
├────────────────────────────────────────┤
│                                        │
│  Problem: Client and server need to   │
│           share encryption key but     │
│           never met before!            │
│                                        │
│  Solution: Hybrid Cryptosystem         │
│  1. RSA-2048: Secure key exchange     │
│  2. AES-256: Fast data encryption     │
└────────────────────────────────────────┘
```

**My Implementation:**

| Phase | Algorithm | Purpose | Speed | When Used |
|-------|-----------|---------|-------|-----------|
| **Initial Connection** | RSA-2048 | Exchange AES key securely | Slow (~0.1 MB/s) | Once per session |
| **All Data Traffic** | AES-256-CBC | Encrypt/decrypt packets | Fast (~1000 MB/s) | Every packet |

**Security Level:**
- RSA-2048: Would take ~300 trillion CPU-years to break
- AES-256: 2^256 possible keys = practically unbreakable

---

### 2. Authentication System

**File:** `server/auth_handler.py`

```python
# Credentials validated before tunnel creation
def validate_credentials(username, password):
    if username in VALID_CREDENTIALS:
        return VALID_CREDENTIALS[username] == password
    return False
```

**Security Features:**
- Credentials encrypted with RSA during transmission
- Only authenticated users can create tunnel
- Invalid credentials → connection rejected

**Valid Users (Demo):**
- `student / secure123`
- `admin / admin123`
- `demo / demo123`

---

### 3. Encrypted Tunnel

**File:** `shared/encryption_handler.py`

**AES-256-CBC Implementation:**
```python
def encrypt(data, aes_key):
    # Generate random IV for CBC mode
    iv = get_random_bytes(16)
    
    # Create AES cipher
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    
    # Pad to 16-byte blocks
    padded_data = pad(data, 16)
    
    # Encrypt
    ciphertext = cipher.encrypt(padded_data)
    
    # Return IV + ciphertext
    return iv + ciphertext
```

**Why CBC Mode:**
- Adds randomness - same plaintext → different ciphertext each time
- More secure than basic ECB mode
- Industry standard for secure encryption

---

## ⚡ Performance Features

### Flow Control System

My VPN implements **TCP Reno-style flow control** with three mechanisms:

#### 1. Congestion Window (cwnd)

**Purpose:** Limit how much unacknowledged data can be "in flight"

```
┌─────────────────────────────────────┐
│  Slow Start Phase                   │
│  cwnd = 4KB → 8KB (exponential)     │
│  Fast growth to find capacity       │
├─────────────────────────────────────┤
│  Congestion Avoidance Phase         │
│  cwnd = 8KB → ... (linear)          │
│  Careful growth to avoid overload   │
└─────────────────────────────────────┘
```

**Benefits:**
- Adapts to network capacity
- Prevents network congestion
- Optimal throughput without packet loss

---

#### 2. Transmission Blocking

**Purpose:** Pause sending when window is full

```python
def wait_for_send_permission(data_size):
    while packets_in_flight > cwnd:
        time.sleep(0.1)  # Wait for ACK
    return True  # Permission granted
```

**Benefits:**
- Prevents overwhelming receiver
- Enforces flow control limits
- Protects against buffer overflow

---

#### 3. Rate Pacing

**Purpose:** Smooth out transmission bursts

```python
def pace_transmission(data_size):
    pacing_rate = cwnd / smoothed_rtt
    delay = data_size / pacing_rate
    time.sleep(delay)  # Wait before sending
```

**Benefits:**
- Prevents bursty traffic
- Gentler on network equipment
- Reduces packet loss

---

## 🎭 Key VPN Features Demonstrated

### 1. ✅ Encryption (Privacy)

**Proof:** Wireshark capture on port 5555
```
Data: \xf3\x8a\x9c\x4e\xb7\x2d... (unreadable!)
```

**What it proves:**
- ISP cannot read your traffic
- Hackers cannot steal your data
- All communication encrypted end-to-end

---

### 2. ✅ IP Masquerading (Anonymity)

**Without VPN:**
```bash
# Direct access from client
curl http://192.168.0.120:9000
# Result: 403 Forbidden (IP 192.168.0.129 blocked)
```

**With VPN:**
```bash
# Through VPN tunnel
curl -x http://localhost:8080 http://192.168.0.120:9000
# Result: 200 OK (appears to come from 192.168.0.120)
```

**What it proves:**
- Your real IP is hidden
- Website sees VPN server's IP
- Bypass IP-based restrictions

---

### 3. ✅ Secure Tunnel (Protected Connection)

**Architecture:**
```
Client ═══🔒 Encrypted ══→ Server ──→ Destination
        (Port 5555)          (Plaintext forwarding)
```

**What it proves:**
- Direct encrypted pathway
- No intermediate proxies can read data
- End-to-end protection

---

### 4. ✅ Flow Control (Performance)

**Observable Metrics:**
```
📊 [Flow Control] cwnd=4096 → 8192 | Phase: slow_start
📊 [Flow Control] RTT: 2.35ms | Throughput: 450 KB/s
```

**What it proves:**
- Adaptive to network conditions
- Prevents packet loss
- Optimal performance

---

## 📊 Comparison: My VPN vs Commercial VPNs

| Feature | My Custom VPN | Commercial VPN (NordVPN, ExpressVPN) |
|---------|---------------|--------------------------------------|
| **Encryption** | ✅ AES-256-CBC | ✅ AES-256-GCM/CBC |
| **Key Exchange** | ✅ RSA-2048 | ✅ RSA-2048/4096 |
| **Authentication** | ✅ Username/Password | ✅ Username/Password + 2FA |
| **Tunneling** | ✅ Custom protocol | ✅ OpenVPN, WireGuard, IKEv2 |
| **IP Masquerading** | ✅ Hides real IP | ✅ Hides real IP |
| **Flow Control** | ✅ TCP Reno | ✅ Various algorithms |
| **Browser Integration** | ✅ SOCKS Proxy | ✅ Apps with system-level VPN |
| **Multi-Platform** | ⚠️ Python-based (cross-platform) | ✅ Windows, Mac, iOS, Android, Linux |
| **Server Locations** | ⚠️ Single location | ✅ 50+ countries |
| **Kill Switch** | ❌ Not implemented | ✅ Cuts internet if VPN drops |
| **Split Tunneling** | ❌ Not implemented | ✅ Route some apps through VPN |
| **DNS Leak Protection** | ❌ Not implemented | ✅ Prevents DNS leaks |

**What My VPN Demonstrates:**
- ✅ Core VPN principles and cryptography
- ✅ Secure tunnel implementation
- ✅ Flow control and congestion management
- ✅ Real network programming concepts
- ✅ Client-server architecture

**Commercial VPNs Add:**
- More protocols (OpenVPN, WireGuard)
- Hundreds of server locations worldwide
- Advanced features (kill switch, split tunneling)
- User-friendly apps for all platforms
- 24/7 support and maintenance

**Conclusion:** My VPN implements the **fundamental concepts** used by commercial VPNs, demonstrating deep understanding of VPN technology!

---

## 🎓 Technical Highlights

### 1. Custom Protocol Design

**Instead of using existing VPN protocols (OpenVPN, WireGuard), I designed my own:**

```python
# Packet format: [Length Header][Encrypted Payload]
packet = length_header(4 bytes) + encrypted_data(variable)
```

**Benefits:**
- Complete control over implementation
- Understanding of protocol design
- Demonstrates networking fundamentals

---

### 2. Hybrid Cryptosystem

**Industry-standard approach:**
```
RSA (slow) for key exchange → AES (fast) for data
```

**Same approach used by:**
- HTTPS/TLS (secure websites)
- SSH (secure remote access)
- Signal (encrypted messaging)
- WhatsApp (encrypted calls)

---

### 3. Flow Control Implementation

**TCP Reno algorithm:**
- Slow Start (exponential growth)
- Congestion Avoidance (linear growth)
- Fast Recovery (on packet loss)

**Demonstrates understanding of:**
- Network congestion
- Adaptive rate control
- TCP internals

---

### 4. Real Network Architecture

**Two-VM setup provides:**
- Actual network traffic
- Real RTT measurements
- Observable encryption in Wireshark
- Practical client-server separation

---

## 🎯 Project Achievements

### What This VPN Successfully Demonstrates

✅ **Security:**
- Military-grade encryption (AES-256)
- Secure key exchange (RSA-2048)
- Authentication system
- Protected tunnel

✅ **Networking:**
- TCP socket programming
- Client-server architecture
- Protocol design
- Network analysis (Wireshark)

✅ **Performance:**
- Flow control (TCP Reno)
- Congestion management
- Rate pacing
- RTT measurement

✅ **Integration:**
- Browser support (SOCKS proxy)
- Multi-client capability
- Real-time statistics
- Cross-platform (Python)

✅ **Real-World Relevance:**
- IP masquerading (VPN core feature)
- Access control bypass
- Privacy protection
- Practical use case

---

## 🎤 For Your Presentation

### Elevator Pitch (30 seconds)

*"I built a custom VPN that creates an encrypted tunnel between a client and server. The VPN uses AES-256 for fast data encryption and RSA-2048 for secure key exchange - the same hybrid cryptosystem used by commercial VPNs. It demonstrates core networking concepts including TCP socket programming, flow control, and IP masquerading. The two-VM architecture allows real network traffic analysis with Wireshark, proving the encryption works and showing how VPNs protect privacy."*

---

### Key Talking Points

**1. What is a VPN?**
- Virtual Private Network creates encrypted tunnel
- Protects privacy by hiding traffic from ISP
- Provides anonymity by masking your IP address
- Bypasses restrictions by appearing to be elsewhere

**2. How My VPN Works:**
- Client connects to VPN server
- RSA key exchange establishes shared AES key
- All traffic encrypted with AES-256-CBC
- Server forwards requests with its IP (masquerading)
- Responses encrypted and sent back through tunnel

**3. Technical Implementations:**
- Hybrid cryptosystem (RSA + AES) like TLS/SSH
- TCP Reno flow control for optimal performance
- SOCKS proxy for browser integration
- Two-VM architecture for realistic testing

**4. Demonstrated Concepts:**
- Encryption and decryption
- Secure key exchange
- Network protocols
- Flow control and congestion management
- IP masquerading
- Client-server architecture

**5. Real-World Validation:**
- Wireshark shows encrypted traffic
- Demo site blocks direct access, allows VPN access
- Flow control adapts to network conditions
- Multi-client support working

---

### Demo Sequence

**1. Show the Problem (No VPN):**
```bash
curl http://192.168.0.120:9000
# Result: 403 Forbidden
```

**2. Connect VPN:**
```bash
python3 client/vpn_client_enhanced.py
# Show GUI: Connected, statistics
```

**3. Show It Works (With VPN):**
```bash
curl -x http://localhost:8080 http://192.168.0.120:9000
# Result: 200 OK - Content delivered!
```

**4. Prove Encryption (Wireshark):**
- Capture on port 5555: Encrypted gibberish
- Capture on port 9000: Plaintext (proves decryption)

**5. Show Flow Control:**
- Server logs showing cwnd growth
- Slow start → Congestion avoidance transition
- RTT measurements

---

## 📝 Summary

### What is a VPN?

A VPN is a technology that:
1. **Encrypts** your internet traffic for privacy
2. **Tunnels** data through a secure pathway
3. **Masks** your real IP address for anonymity
4. **Bypasses** restrictions and censorship

### How My Project Works as a Custom VPN

My project implements a complete VPN system featuring:

**Core VPN Components:**
- ✅ Encrypted tunnel (AES-256-CBC)
- ✅ Secure key exchange (RSA-2048)
- ✅ IP masquerading (hides real IP)
- ✅ Authentication (user validation)

**Advanced Features:**
- ✅ Flow control (TCP Reno algorithm)
- ✅ Browser integration (SOCKS proxy)
- ✅ Multi-client support
- ✅ Real-time statistics

**Educational Value:**
- ✅ Demonstrates networking fundamentals
- ✅ Shows cryptography in practice
- ✅ Proves concepts with Wireshark
- ✅ Real-world architecture (2 VMs)

**Result:** A functional VPN that demonstrates the same principles used by commercial VPN services like NordVPN and ExpressVPN!

---

## 🔗 Related Documentation

For more details, see:
- [VPN_PROXY_WORKFLOW.md](VPN_PROXY_WORKFLOW.md) - Complete step-by-step flow
- [VPN_TUNNELING_EXPLAINED.md](VPN_TUNNELING_EXPLAINED.md) - Tunneling concept
- [FLOW_CONTROL_AND_ENCRYPTION.md](FLOW_CONTROL_AND_ENCRYPTION.md) - Flow control and encryption details
- [WHY_TWO_VMS.md](WHY_TWO_VMS.md) - Architecture rationale
- [WORKING_PRINCIPLES.md](WORKING_PRINCIPLES.md) - Complete system overview
