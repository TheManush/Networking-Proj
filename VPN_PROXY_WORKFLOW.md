# VPN + Proxy Complete Workflow

This document explains **exactly** how your VPN works when you browse a website in Firefox.

---

## 🎯 The Big Picture (Simple Version)

```
YOU → Firefox → Local Proxy (8080) → VPN Tunnel (Encrypted) → VPN Server → Demo Site → Back to You
```

**Key Concept:** Firefox doesn't talk directly to websites. It talks to a local proxy server on your own computer, which then sends everything through an encrypted tunnel to the VPN server.

---

## 📋 Component Overview

Before we start, let's understand what each piece does:

| Component | Location | Port | What It Does |
|-----------|----------|------|--------------|
| **Firefox Browser** | Client VM (192.168.0.129) | N/A | Where you browse websites |
| **Local Proxy Server** | Client VM (192.168.0.129) | 8080 | Receives Firefox requests |
| **VPN Client** | Client VM (192.168.0.129) | 5555 | Encrypts and sends through tunnel |
| **VPN Server** | Server VM (192.168.0.120) | 5555 | Receives encrypted data, decrypts |
| **Demo Site** | Server VM (192.168.0.120) | 9000 | The website you want to visit |

---

## 🔧 Setup Phase (Do Once)

### Step 1: Configure Firefox Proxy

**What you do:**
1. Open Firefox → Settings → Network Settings
2. Select "Manual proxy configuration"
3. HTTP Proxy: `localhost` Port: `8080`
4. Click OK

**What this means:**
- Firefox will now send ALL web requests to `localhost:8080` instead of directly to websites
- `localhost:8080` is your VPN client's proxy server

**Why we need this:**
- Browsers understand proxies natively - no special browser extensions needed
- All your web traffic automatically goes through the VPN
- Any app that supports proxies can use your VPN

---

### Step 2: Start VPN Client

**What you do:**
```bash
python3 client/vpn_client_enhanced.py
```

**What happens inside:**

```
┌─────────────────────────────────────┐
│    VPN Client Starting...           │
├─────────────────────────────────────┤
│                                     │
│  1. Start Local Proxy Server       │
│     • Listens on port 8080         │
│     • Waits for Firefox            │
│                                     │
│  2. Connect to VPN Server          │
│     • Connects to 192.168.0.120:5555│
│     • Exchange RSA keys            │
│     • Get AES session key          │
│     • Tunnel established!          │
│                                     │
│  ✅ Ready to forward traffic        │
└─────────────────────────────────────┘
```

**Now you have:**
- A proxy server listening on port 8080 (for Firefox)
- An encrypted tunnel to the VPN server (for secure transmission)

---

## 🌐 Browsing Phase (Every Time You Visit a Website)

Let's trace what happens when you type `http://192.168.0.120:9000` in Firefox.

---

### 🔵 STEP 1: Firefox Sends Request to Local Proxy

**Location:** Client VM (192.168.0.129)

**What Firefox does:**
```
Firefox checks: "Do I have a proxy configured?"
Answer: YES - localhost:8080

Instead of connecting to 192.168.0.120:9000 directly,
Firefox connects to localhost:8080
```

**The HTTP request Firefox sends:**
```http
GET / HTTP/1.1
Host: 192.168.0.120:9000
User-Agent: Mozilla/5.0...
```

**Important:** This communication is **plaintext** because it's on your own computer (localhost). No encryption needed yet.

---

### 🔵 STEP 2: Local Proxy Receives Request

**Location:** Client VM (192.168.0.129), Port 8080

**What the proxy does:**

```python
# Proxy receives Firefox's request
request = "GET / HTTP/1.1\r\nHost: 192.168.0.120:9000..."

# Parse destination
destination_host = "192.168.0.120"
destination_port = 9000

# Wrap in JSON format
packet = {
    "destination_host": "192.168.0.120",
    "destination_port": 9000,
    "data": request  # The original HTTP request
}
```

**The proxy creates a package** that contains:
- Where the request should go (192.168.0.120:9000)
- What the request is (GET / HTTP/1.1...)

---

### 🔵 STEP 3: VPN Client Encrypts and Sends

**Location:** Client VM (192.168.0.129)

**What happens:**

```
┌──────────────────────────────┐
│  1. Take the JSON packet     │
│  2. Encrypt with AES-256     │
│  3. Send through tunnel to   │
│     192.168.0.120:5555       │
└──────────────────────────────┘
```

**Before encryption (readable):**
```json
{
  "destination_host": "192.168.0.120",
  "destination_port": 9000,
  "data": "GET / HTTP/1.1..."
}
```

**After encryption (unreadable):**
```
\xf3\x8a\x9c\x4e\xb7\x2d... (encrypted bytes)
```

**On the network:** If you capture this in Wireshark between 192.168.0.129 and 192.168.0.120, you see **encrypted garbage** - completely secure!

---

### 🟢 STEP 4: VPN Server Receives and Decrypts

**Location:** Server VM (192.168.0.120), Port 5555

**What the VPN server does:**

```
┌──────────────────────────────────────┐
│  1. Receive encrypted packet         │
│  2. Decrypt with AES-256             │
│  3. Parse JSON                       │
│  4. Extract information:             │
│     • Destination: 192.168.0.120:9000│
│     • Request: GET / HTTP/1.1...     │
└──────────────────────────────────────┘
```

**Now the server knows:**
- Client wants to access `192.168.0.120:9000`
- The HTTP request to send

---

### 🟢 STEP 5: VPN Server Forwards to Demo Site

**Location:** Server VM (192.168.0.120)

**What happens:**

```python
# VPN Server creates NEW connection to demo site
demo_socket = socket.socket()
demo_socket.connect(('192.168.0.120', 9000))

# Send the ORIGINAL HTTP request (plaintext)
demo_socket.send(b"GET / HTTP/1.1\r\nHost: 192.168.0.120:9000...")
```

**Key Point:** The VPN server makes a **brand new connection** to the demo site on behalf of the client.

**From the demo site's perspective:**
- The request comes from `192.168.0.120` (the VPN server)
- **NOT** from `192.168.0.129` (the real client)
- **This is IP masquerading** - your real identity is hidden!

---

### 🟢 STEP 6: Demo Site Checks Access

**Location:** Server VM (192.168.0.120), Port 9000

**What the demo site does:**

```python
# Demo site checks: Who is connecting?
client_ip = request.remote_addr  # Gets: 192.168.0.120

# Check allowed IPs
ALLOWED_IPS = ['127.0.0.1', '192.168.0.120']
BLOCKED_IPS = ['192.168.0.129']  # Your real IP is blocked!

if client_ip in ALLOWED_IPS:
    return "200 OK - Welcome!"  # ✅ ALLOWED
elif client_ip in BLOCKED_IPS:
    return "403 Forbidden"      # ❌ BLOCKED
```

**Result:** ✅ Access Granted! Because the request appears to come from `192.168.0.120`, which is allowed.

**Important:** If the client tried to connect directly (without VPN), the demo site would see `192.168.0.129` and **block** the connection!

---

### 🟢 STEP 7: Demo Site Sends Response

**Location:** Server VM (192.168.0.120), Port 9000

**What the demo site sends back:**

```http
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234

<!DOCTYPE html>
<html>
<head><title>Demo Site</title></head>
<body>
    <h1>Welcome to the Demo Site!</h1>
    <p>You are accessing through VPN!</p>
</body>
</html>
```

**This response goes back to the VPN server** (not directly to the client).

---

### 🔵 STEP 8: VPN Server Encrypts Response

**Location:** Server VM (192.168.0.120)

**What the VPN server does:**

```
┌──────────────────────────────────┐
│  1. Receive HTTP response from   │
│     demo site (plaintext)        │
│  2. Encrypt with AES-256         │
│  3. Send through tunnel back to  │
│     client (192.168.0.129:5555)  │
└──────────────────────────────────┘
```

**Before encryption:**
```
HTTP/1.1 200 OK
Content-Type: text/html
...
```

**After encryption:**
```
\xe7\x4c\x9a\x2f... (encrypted bytes)
```

**On the network:** Again, if you capture this in Wireshark, it's **encrypted** - no one can read the response!

---

### 🔵 STEP 9: VPN Client Receives and Decrypts

**Location:** Client VM (192.168.0.129)

**What the VPN client does:**

```
┌──────────────────────────────────┐
│  1. Receive encrypted response   │
│  2. Decrypt with AES-256         │
│  3. Extract HTTP response        │
└──────────────────────────────────┘
```

**Decrypted response:**
```http
HTTP/1.1 200 OK
Content-Type: text/html
...
```

---

### 🔵 STEP 10: Local Proxy Sends to Firefox

**Location:** Client VM (192.168.0.129), Port 8080

**What the proxy does:**

```python
# Send the decrypted HTTP response to Firefox
firefox_socket.send(http_response)
```

**Firefox receives:**
```http
HTTP/1.1 200 OK
Content-Type: text/html
...
```

**Important:** Firefox has NO IDEA that encryption happened! It just thinks it talked to a normal proxy server.

---

### 🔵 STEP 11: Firefox Renders Page

**Location:** Client VM (192.168.0.129)

**What Firefox does:**
1. Parse HTML: `<html><head>...</head><body>...</body></html>`
2. Render the page on screen
3. **You see the website!** 🎉

---

## 🔄 Complete Visual Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client VM (192.168.0.129)                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Firefox Browser]                                               │
│         ↓ 1. HTTP Request (plaintext)                           │
│         ↓ "GET http://192.168.0.120:9000/"                      │
│         ↓                                                        │
│  [Local Proxy Server - Port 8080]                               │
│         ↓ 2. Wrap in JSON                                        │
│         ↓ {"destination_host": "192.168.0.120", ...}            │
│         ↓                                                        │
│  [VPN Client - Encryption Engine]                               │
│         ↓ 3. Encrypt with AES-256-CBC                           │
│         ↓ Result: \xf3\x8a\x9c... (encrypted bytes)             │
│         ↓                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
          │ 4. Send encrypted packet to 192.168.0.120:5555
          │    🔒 ENCRYPTED TUNNEL 🔒
          ↓
┌──────────────────────────────────────────────────────────────────┐
│                         Server VM (192.168.0.120)                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [VPN Server - Port 5555]                                        │
│         ↓ 5. Receive encrypted packet                           │
│         ↓ 6. Decrypt with AES-256-CBC                           │
│         ↓ Result: {"destination_host": "192.168.0.120", ...}    │
│         ↓                                                        │
│  [VPN Server - Forwarding Engine]                               │
│         ↓ 7. Extract destination: 192.168.0.120:9000            │
│         ↓ 8. Create new socket to demo site                     │
│         ↓ 9. Forward HTTP request (plaintext)                   │
│         ↓                                                        │
│  [Demo Site - Port 9000]                                         │
│         ↓ 10. Check IP: 192.168.0.120 ✅ Allowed                │
│         ↓ 11. Process request                                    │
│         ↓ 12. Generate HTTP response                             │
│         ↑ 13. Send response back                                 │
│         ↑                                                        │
│  [VPN Server - Encryption Engine]                               │
│         ↑ 14. Encrypt response with AES-256-CBC                 │
│         ↑ Result: \xe7\x4c\x9a... (encrypted bytes)             │
│         ↑                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
          │ 15. Send encrypted response to 192.168.0.129:5555
          │    🔒 ENCRYPTED TUNNEL 🔒
          ↑
┌─────────┼────────────────────────────────────────────────────────┐
│         ↑              Client VM (192.168.0.129)                │
├─────────┼────────────────────────────────────────────────────────┤
│         ↑                                                        │
│  [VPN Client]                                                    │
│         ↑ 16. Receive encrypted response                         │
│         ↑ 17. Decrypt with AES-256-CBC                           │
│         ↑ Result: HTTP/1.1 200 OK...                             │
│         ↑                                                        │
│  [Local Proxy Server - Port 8080]                               │
│         ↑ 18. Forward to Firefox                                 │
│         ↑                                                        │
│  [Firefox Browser]                                               │
│         ↑ 19. Receive HTTP response                              │
│         ↑ 20. Parse HTML                                         │
│         ↑ 21. Render webpage                                     │
│                                                                  │
│  ✅ YOU SEE THE WEBSITE!                                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Encryption vs Plaintext Summary

| Connection | Protocol | Encrypted? | Why? |
|------------|----------|------------|------|
| Firefox → Local Proxy (8080) | HTTP | ❌ No | Localhost - no need |
| VPN Client → VPN Server (5555) | Custom | ✅ **YES** | Crosses network - needs security |
| VPN Server → Demo Site (9000) | HTTP | ❌ No | Same machine - localhost |

**Key Point:** Only the data traveling between the two VMs is encrypted. This protects your data on the network.

---

## 🎭 IP Masquerading (Why This Matters)

### Without VPN (Direct Access)

```
Client (192.168.0.129) ──→ Demo Site (192.168.0.120:9000)
                            
Demo Site sees: 192.168.0.129
Demo Site checks: BLOCKED_IPS = ['192.168.0.129']
Result: ❌ 403 Forbidden
```

### With VPN (Through Tunnel)

```
Client (192.168.0.129) ──→ VPN Server (192.168.0.120:5555)
                            
VPN Server (192.168.0.120) ──→ Demo Site (192.168.0.120:9000)

Demo Site sees: 192.168.0.120
Demo Site checks: ALLOWED_IPS = ['192.168.0.120']
Result: ✅ 200 OK
```

**This is the core VPN feature:**
- Your real IP (`192.168.0.129`) is hidden
- Demo site only sees VPN server's IP (`192.168.0.120`)
- You can access blocked content!

---

## 🛠️ Why Use a Proxy Server?

**Question:** Why not make Firefox talk directly to the VPN client?

**Answer:** Browsers already understand proxies!

### Benefits of Proxy Approach:

1. **No Custom Browser:** Works with any browser (Firefox, Chrome, Edge)
2. **Easy Configuration:** Just set proxy in browser settings
3. **Universal Support:** Any app that supports proxies can use your VPN
4. **Standard Protocol:** Uses well-established SOCKS5/HTTP proxy standards
5. **Transparent:** Browser doesn't know it's using a VPN

### Alternative (Without Proxy):

Would require:
- Custom browser extension
- Or modifying every application
- Or OS-level network driver (complex!)

---

## 🧪 Testing with Wireshark

### What You Should See:

**1. Capture on Client VM (192.168.0.129):**

Filter: `tcp.port == 5555`

```
Source: 192.168.0.129
Destination: 192.168.0.120
Protocol: TCP
Data: \xf3\x8a\x9c\x4e\xb7\x2d... (encrypted gibberish)
```

**2. Capture on Server VM (192.168.0.120) - Loopback:**

Filter: `tcp.port == 9000`

```
Source: 192.168.0.120 (lo)
Destination: 192.168.0.120 (lo)
Protocol: HTTP
Data: GET / HTTP/1.1... (readable plaintext!)
```

**This proves:**
- Network traffic is encrypted ✅
- Local forwarding is plaintext ✅
- VPN is working correctly ✅

---

## 📝 Quick Reference

### Port Assignments

- **8080:** Local proxy (Firefox connects here)
- **5555:** VPN tunnel (encrypted connection)
- **9000:** Demo site (the website)

### IP Addresses

- **192.168.0.129:** Client VM (your computer)
- **192.168.0.120:** Server VM (VPN server + demo site)

### Key Files

- **Client Side:**
  - `client/vpn_client_enhanced.py` - Main VPN client with proxy
  - `client/config.py` - Server IP configuration
  
- **Server Side:**
  - `server/vpn_server_enhanced.py` - VPN server
  - `server/tunnel_manager.py` - Forwards requests
  - `demo_site/app.py` - The website

### Commands

**Start Demo Site:**
```bash
cd /path/to/Netpro
python3 demo_site/app.py
```

**Start VPN Server:**
```bash
cd /path/to/Netpro
python3 server/vpn_server_enhanced.py
```

**Start VPN Client:**
```bash
cd /path/to/Netpro
python3 client/vpn_client_enhanced.py
```

**Configure Firefox:**
```
Settings → Network Settings → Manual proxy configuration
HTTP Proxy: localhost
Port: 8080
```

---

## ❓ Common Questions

### Q1: Why do we need both port 8080 and 5555?

**A:** They serve different purposes:
- **Port 8080:** Where Firefox connects (local proxy interface)
- **Port 5555:** Where encrypted tunnel operates (network connection)

Think of it like a mail service:
- Port 8080 = Your local post office (accepts your letters)
- Port 5555 = The secure delivery truck (transports encrypted mail)

### Q2: What happens if I don't configure Firefox proxy?

**A:** Firefox will try to connect directly to websites:
- Demo site will see your real IP (192.168.0.129)
- Demo site will **block** your request
- You won't be able to access the site

### Q3: Can I use other apps besides Firefox?

**A:** Yes! Any application that supports HTTP/SOCKS proxies:
- Chrome/Edge: Set proxy to `localhost:8080`
- curl: `curl -x http://localhost:8080 http://192.168.0.120:9000`
- wget: `http_proxy=http://localhost:8080 wget http://192.168.0.120:9000`

### Q4: What's the difference between AES and RSA?

**A:** They serve different purposes:

| Feature | RSA-2048 | AES-256 |
|---------|----------|---------|
| **Type** | Asymmetric | Symmetric |
| **Speed** | Slow (1000x slower) | Fast |
| **Use** | Key exchange only | Data encryption |
| **Keys** | Public + Private pair | Single shared key |

**In your VPN:**
- RSA is used ONCE at connection start to exchange the AES key
- AES is used for ALL subsequent data encryption (faster)

### Q5: Where exactly is the data encrypted?

**A:**

Encrypted:
- ✅ Client VM → Server VM (across network, port 5555)
- ✅ Server VM → Client VM (across network, port 5555)

NOT Encrypted (plaintext):
- ❌ Firefox → Local Proxy (same computer, localhost)
- ❌ VPN Server → Demo Site (same computer, localhost)

**Why?** Encryption is only needed when data crosses the network. Local communication on the same computer doesn't need encryption.

---

## 🎓 Summary

**Your VPN works in 3 main stages:**

1. **Setup:** Firefox → Proxy on port 8080, VPN tunnel to server on port 5555
2. **Request:** Firefox → Proxy → Encrypt → VPN Server → Decrypt → Demo Site
3. **Response:** Demo Site → VPN Server → Encrypt → VPN Client → Decrypt → Firefox

**Key Features:**
- 🔒 **Encryption:** AES-256-CBC for all network traffic
- 🎭 **IP Masquerading:** Hide your real IP address
- 🌐 **Proxy Integration:** Works with any browser/app that supports proxies
- ⚡ **Flow Control:** TCP Reno algorithm manages speed and congestion

**The Magic:** Demo site thinks requests come from the VPN server (192.168.0.120), not from you (192.168.0.129), allowing you to access blocked content!
