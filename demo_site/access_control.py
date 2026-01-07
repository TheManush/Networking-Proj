"""
Access Control Handler
Manages IP-based and file-based access control
"""

import os
from . import config


class AccessControl:
    """Handles access control for demo site"""
    
    @staticmethod
    def is_allowed(client_ip: str) -> tuple:
        """
        Check if client is allowed to access the site
        
        Args:
            client_ip: Client's IP address
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check IP-based blocking
        if config.USE_IP_BLOCKING:
            # First check if explicitly blocked
            if client_ip in config.BLOCKED_IPS:
                return False, f"IP {client_ip} is blocked (geo-restricted)"
            
            # Then check if in allowed list (VPN server IP or localhost)
            if hasattr(config, 'ALLOWED_IPS'):
                if client_ip not in config.ALLOWED_IPS:
                    return False, f"IP {client_ip} not authorized"
        
        # Check file-based control (fallback for single-device demo)
        if config.USE_FILE_BASED_CONTROL:
            status = AccessControl._check_vpn_file()
            if status != 'allowed':
                return False, "VPN not connected"
        
        return True, "Access granted"
    
    @staticmethod
    def _check_vpn_file() -> str:
        """Check VPN access control file"""
        try:
            if os.path.exists(config.ACCESS_CONTROL_FILE):
                with open(config.ACCESS_CONTROL_FILE, 'r') as f:
                    return f.read().strip().lower()
        except:
            pass
        return 'blocked'
    
    @staticmethod
    def initialize_access_file():
        """Initialize access control file as blocked"""
        try:
            with open(config.ACCESS_CONTROL_FILE, 'w') as f:
                f.write('blocked')
        except:
            pass
