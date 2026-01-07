"""
VPN Client Configuration
"""

# Default Connection Settings - Two-Device Setup
# VM1 (Server) IP address on bridged network (192.168.0.105)
DEFAULT_SERVER_HOST = '192.168.0.105'  # Change to VM1's actual IP
DEFAULT_SERVER_PORT = 8888

# Default Credentials
DEFAULT_USERNAME = 'student'
DEFAULT_PASSWORD = 'secure123'

# Connection Settings
CONNECTION_TIMEOUT = 10
KEEPALIVE_INTERVAL = 30

# Demo Site URL - Access through VPN or direct (will be blocked)
DEMO_SITE_URL = 'http://192.168.0.105:9000'  # VM1's demo site
DEMO_SITE_PORT = 9000

# GUI Settings
GUI_THEME = 'dark'
GUI_WIDTH = 500
GUI_HEIGHT = 650
