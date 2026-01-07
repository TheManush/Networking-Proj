"""
VPN Client Core
Handles connection to VPN server and encryption
"""

import socket
import json
import os
import time
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.encryption import EncryptionHandler, RSAHandler
from shared.constants import DEFAULT_BUFFER_SIZE, ACCESS_CONTROL_FILE
from . import config


class VPNClient:
    """VPN Client with encryption and authentication"""
    
    def __init__(self):
        self.server_host = config.DEFAULT_SERVER_HOST
        self.server_port = config.DEFAULT_SERVER_PORT
        self.socket = None
        self.aes_key = None
        self.server_public_key = None
        self.connected = False
        
        # Initialize encryption handler
        self.encryption = EncryptionHandler()
    
    def connect(self, username: str, password: str) -> tuple:
        """
        Connect to VPN server and establish secure tunnel
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(config.CONNECTION_TIMEOUT)
            self.socket.connect((self.server_host, self.server_port))
            
            # Step 1: Receive server's public key
            public_pem = self.socket.recv(2048)
            self.server_public_key = RSAHandler.load_public_key(public_pem)
            
            # Step 2: Generate AES key and encrypt with server's public key
            self.aes_key = os.urandom(32)  # 256-bit key
            encrypted_aes_key = RSAHandler.encrypt_rsa(self.aes_key, self.server_public_key)
            self.socket.send(encrypted_aes_key)
            
            # Step 3: Send authentication credentials
            auth_data = json.dumps({
                'username': username,
                'password': password,
                'timestamp': time.time()
            })
            encrypted_auth = self.encryption.encrypt_aes(auth_data, self.aes_key)
            self.socket.send(encrypted_auth)
            
            # Step 4: Receive authentication response
            encrypted_response = self.socket.recv(1024)
            response = json.loads(self.encryption.decrypt_aes(encrypted_response, self.aes_key))
            
            if response['status'] == 'success':
                self.connected = True
                self._update_access_control('allowed')
                return True, response['message']
            else:
                self.socket.close()
                return False, response['message']
        
        except Exception as e:
            if self.socket:
                self.socket.close()
            return False, f"Connection error: {str(e)}"
    
    def disconnect(self):
        """Disconnect from VPN server"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        self.aes_key = None
        self._update_access_control('blocked')
    
    def send_data(self, data: str) -> tuple:
        """
        Send encrypted data through VPN tunnel
        
        Args:
            data: Data to send
            
        Returns:
            Tuple of (success: bool, response: dict or error message)
        """
        if not self.connected or not self.socket:
            return False, "Not connected to VPN"
        
        try:
            encrypted_data = self.encryption.encrypt_aes(data, self.aes_key)
            self.socket.send(encrypted_data)
            
            # Receive acknowledgment
            encrypted_ack = self.socket.recv(1024)
            ack = json.loads(self.encryption.decrypt_aes(encrypted_ack, self.aes_key))
            return True, ack
        except Exception as e:
            return False, str(e)
    
    def _update_access_control(self, status: str):
        """Update access control file for demo site"""
        try:
            with open(ACCESS_CONTROL_FILE, 'w') as f:
                f.write(status)
        except:
            pass
    
    def set_server(self, host: str, port: int = None):
        """Set server connection details"""
        self.server_host = host
        if port:
            self.server_port = port
