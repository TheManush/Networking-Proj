"""
Authentication Handler
Handles user authentication and credential validation
"""

import json
import time
from typing import Tuple
from . import config


class AuthHandler:
    """Manages authentication for VPN connections"""
    
    @staticmethod
    def validate_credentials(username: str, password: str) -> bool:
        """
        Validate user credentials
        
        Args:
            username: Username to check
            password: Password to check
            
        Returns:
            bool: True if credentials are valid
        """
        if username in config.VALID_CREDENTIALS:
            return config.VALID_CREDENTIALS[username] == password
        return False
    
    @staticmethod
    def parse_auth_data(auth_json: str) -> Tuple[str, str, float]:
        """
        Parse authentication JSON data
        
        Args:
            auth_json: JSON string containing auth data
            
        Returns:
            Tuple of (username, password, timestamp)
        """
        try:
            data = json.loads(auth_json)
            username = data.get('username', '')
            password = data.get('password', '')
            timestamp = data.get('timestamp', time.time())
            return username, password, timestamp
        except Exception:
            return '', '', 0.0
    
    @staticmethod
    def create_auth_response(success: bool, message: str, server_info: dict = None) -> str:
        """
        Create authentication response JSON
        
        Args:
            success: Whether authentication succeeded
            message: Status message
            server_info: Additional server information
            
        Returns:
            str: JSON response string
        """
        response = {
            'status': 'success' if success else 'error',
            'message': message
        }
        
        if server_info:
            response.update(server_info)
            
        return json.dumps(response)
