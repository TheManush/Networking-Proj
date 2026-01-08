# 🌐 Two-Device VPN Demo Setup

## Overview
This guide shows how to set up a REAL VPN demo using two separate devices on the same network. This provides the most realistic demonstration of VPN functionality.

## 📱 What You Need
- **Device 1** (Server): Laptop/Desktop running Windows (your main computer)
- **Device 2** (Client): Another laptop, desktop, or even a phone with browser
- Both devices on the **same WiFi/network**

---

## 🔧 Setup - Device 1 (Server)

### Step 1: Find Your IP Address

Open Command Prompt and run:
```cmd
ipconfig
```

Look for your **IPv4 Address** under your WiFi/Ethernet adapter:
```
IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

**Write this down!** (Example: `192.168.1.100`)

### Step 2: Allow VPN Server Through Firewall

1. Press `Win + R` → type `wf.msc` → Enter
2. Click "Inbound Rules" → "New Rule..."
3. **Port** → Next
4. **TCP** → Specific ports: `8888` → Next
5. **Allow the connection** → Next
6. Check all profiles → Next
7. Name: `Allow VPN Server` → Finish

### Step 3: Block Demo Website Port

1. Still in Windows Firewall
2. "New Rule..." → Port → TCP → Specific ports: `9000` → Next
3. **Block the connection** → Next ⚠️
4. Check all profiles → Next
5. Name: `Block Demo Website Port` → Finish

### Step 4: Edit Demo Website

Open `demo_website_simple.py` and make sure it binds to `0.0.0.0`:
```python
app.run(host='0.0.0.0', port=9000, debug=False)
```

### Step 5: Edit VPN Server

Open `vpn_server.py` and make sure it binds to `0.0.0.0`:
```python
self.host = '0.0.0.0'
self.port = 8888
```

### Step 6: Start the Servers

**Terminal 1:**
```cmd
python vpn_server.py
```

**Terminal 2:**
```cmd
python demo_website_simple.py
```

Both should be running!

---

## 📱 Setup - Device 2 (Client)

### Step 1: Test Direct Access (Should Fail)

1. Open web browser on Device 2
2. Go to: `http://192.168.1.100:9000` (use Device 1's IP)
3. **Expected Result**: "This site can't be reached" ✅
4. This proves the firewall is blocking access!

### Step 2: Copy VPN Client to Device 2

Option A: If Device 2 is Windows with Python:
- Copy these files to Device 2:
  - `vpn_client_integrated.py`
  - `templates/` folder

Option B: If Device 2 is a phone/tablet:
- You'll need to access via browser only (see alternative below)

### Step 3: Configure VPN Client

On Device 2, open `vpn_client_integrated.py` and change the server address:

Find this line:
```python
self.server_entry.insert(0, 'localhost')
```

Change to Device 1's IP:
```python
self.server_entry.insert(0, '192.168.1.100')
```

### Step 4: Run VPN Client

On Device 2:
```cmd
python vpn_client_integrated.py
```

### Step 5: Connect VPN

1. Click **"CONNECT VPN"** button
2. Watch the connection establish
3. Status changes to **"● CONNECTED"**

### Step 6: Test Access Through VPN

**The Problem**: Even with VPN connected, the firewall still blocks port 9000 because the browser is trying to connect directly.

**The Solution**: You need the VPN to act as a proxy/tunnel to forward the traffic.

---

## 🎯 Realistic Demo Flow

Since the firewall blocks ALL connections to port 9000 (even through VPN tunnel), here's the **best demo approach** with two devices:

### Method 1: Different Network Simulation

1. **Device 1** (Server):
   - Connected to WiFi Network A
   - VPN Server running
   - Demo website accessible locally

2. **Device 2** (Client):
   - Connected to Mobile Hotspot (different network)
   - Cannot access Demo website at all (different network + firewall)
   - Connects via VPN
   - Can now access through VPN tunnel

### Method 2: IP-Based Blocking

Edit `demo_website_simple.py` to block specific IPs:

```python
BLOCKED_IPS = ['192.168.1.50']  # Device 2's IP

@app.before_request
def check_access():
    client_ip = request.remote_addr
    if client_ip in BLOCKED_IPS:
        abort(403)
```

Now Device 2 is blocked, but VPN traffic comes from Device 1's IP (allowed)!

---

## 💡 Simplified Two-Device Demo

### Easiest Approach:

**On Device 1:**
```cmd
# Terminal 1
python vpn_server.py

# Terminal 2  
python demo_website_blockable.py
```

**On Device 2:**
1. Copy `vpn_client_integrated.py`
2. Copy `vpn_access.txt` file (shared via network folder or USB)
3. Change server IP to Device 1's IP
4. Run the client

**Demo Flow:**
- Device 2 tries to access website → Blocked
- Device 2 connects VPN → Website becomes accessible
- Both devices read/write the same `vpn_access.txt` (via shared folder)

---

## 🎬 Presentation with Two Devices

### Setup Before Presentation:

1. Both devices ready
2. Device 1 running VPN server & website
3. Device 2 has VPN client ready (not connected)

### During Presentation:

**Show on Device 2's screen:**

1. "Let me try to access this restricted website..."
   - Open browser → Show "This site can't be reached"

2. "Now I'll connect to our VPN server..."
   - Open VPN client
   - Show Device 1's IP as server
   - Click "CONNECT VPN"
   - Show encryption details

3. "With VPN connected, let's try again..."
   - Refresh browser
   - If using IP blocking method → Site loads! ✅
   - If using file-based method → Site loads! ✅

4. "Let's disconnect and verify..."
   - Disconnect VPN
   - Refresh browser → Blocked again!

---

## 🔥 Pro Tips

1. **Test everything before presentation** - Make sure both devices can communicate
2. **Use WiFi, not mobile data** - Easier to troubleshoot
3. **Keep devices close** - Better WiFi connection
4. **Have backup** - Also have single-device demo ready
5. **Explain the setup** - Tell audience you're using two devices for realism

---

## 🛠️ Troubleshooting

**Device 2 can't connect to VPN Server:**
- Check Device 1's firewall allows port 8888
- Ping Device 1 from Device 2: `ping 192.168.1.100`
- Make sure VPN server is bound to `0.0.0.0` not `localhost`

**Website still accessible without VPN:**
- Check firewall rule is active
- Use IP-based blocking method instead
- Verify Device 2's IP is correctly blocked

**VPN connects but website still blocked:**
- This is expected with port blocking
- Use the file-based method instead
- Or use IP-based blocking method

---

## 📊 Summary

Two-device setup is **more impressive** for demonstration but requires:
- ✅ More setup time
- ✅ Network configuration
- ✅ Testing beforehand

Single-device setup (automatic method) is:
- ✅ Simpler
- ✅ More reliable
- ✅ Still demonstrates all VPN concepts

**Recommendation**: Practice single-device first, then try two-device if you have time!
