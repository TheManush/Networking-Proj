"""
Shared Constants
Common constants used across client and server
"""

# Network Configuration
DEFAULT_VPN_PORT = 8888
DEFAULT_BUFFER_SIZE = 4096
CONNECTION_TIMEOUT = 10

# Encryption Configuration
AES_KEY_SIZE = 32  # 256 bits
AES_BLOCK_SIZE = 16  # 128 bits
RSA_KEY_SIZE = 2048

# Authentication
DEFAULT_USERNAME = 'student'
DEFAULT_PASSWORD = 'secure123'

# Demo Site Configuration
DEMO_SITE_PORT = 9000
ACCESS_CONTROL_FILE = 'vpn_access.txt'

# Status Messages
STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'
STATUS_CONNECTED = 'connected'
STATUS_DISCONNECTED = 'disconnected'
