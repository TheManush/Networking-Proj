"""
VPN Server Configuration
"""

# Server Network Settings
HOST = '0.0.0.0'  # Bind to all interfaces
PORT = 8888       # VPN server port

# Security Settings
REQUIRE_AUTH = True
MAX_CLIENTS = 10

# Logging
VERBOSE_LOGGING = True
LOG_ENCRYPTION_DETAILS = False

# Authentication Credentials
# In production, these should be in a secure database
VALID_CREDENTIALS = {
    'student': 'secure123',
    'admin': 'admin123',
    'demo': 'demo123'
}
