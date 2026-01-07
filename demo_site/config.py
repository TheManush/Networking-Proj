"""
Demo Website Configuration
"""

# Server Settings
HOST = '0.0.0.0'  # Bind to all interfaces for two-device setup
PORT = 9000

# Access Control
ACCESS_CONTROL_FILE = 'vpn_access.txt'

# IP-based blocking (for two-device setup)
USE_IP_BLOCKING = True
BLOCKED_IPS = ['192.168.0.130']  # VM2 (Client) IP - blocked from direct access
ALLOWED_IPS = ['127.0.0.1', '::1', '192.168.0.105']  # VM1 (Server) IP - allowed

# File-based access control (for single-device demo)
USE_FILE_BASED_CONTROL = False  # Disabled for 2-VM setup

# Demo mode
DEMO_MODE = True
