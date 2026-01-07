"""
VPN Server Core
Handles client connections, encryption, and tunneling
"""

import socket
import threading
import json
import os
import time
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.encryption import EncryptionHandler, RSAHandler
from shared.constants import DEFAULT_BUFFER_SIZE
from . import config
from .auth_handler import AuthHandler


class VPNServer:
    """VPN Server with encryption and authentication"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or config.HOST
        self.port = port or config.PORT
        self.server_socket = None
        self.clients = {}
        self.running = False
        
        # Generate RSA key pair
        self.private_key, self.public_key = RSAHandler.generate_key_pair()
        
        # Initialize handlers
        self.encryption = EncryptionHandler()
        self.auth = AuthHandler()
        
        self._log(f"VPN Server initialized on {self.host}:{self.port}")
    
    def start(self):
        """Start the VPN server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(config.MAX_CLIENTS)
            self.running = True
            
            self._log(f"Server listening on {self.host}:{self.port}")
            self._log("Waiting for client connections...")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    self._log(f"New connection from {address}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        self._log(f"Error accepting connection: {e}", level='ERROR')
        
        except Exception as e:
            self._log(f"Failed to start server: {e}", level='ERROR')
            raise
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle individual client connection"""
        try:
            # Step 1: Send server's public key
            public_pem = RSAHandler.serialize_public_key(self.public_key)
            client_socket.send(public_pem)
            self._log(f"Sent public key to {address}")
            
            # Step 2: Receive encrypted AES key
            encrypted_aes_key = client_socket.recv(512)
            aes_key = RSAHandler.decrypt_rsa(encrypted_aes_key, self.private_key)
            self._log(f"Received and decrypted AES key from {address}")
            
            # Step 3: Receive encrypted authentication
            encrypted_token = client_socket.recv(1024)
            auth_json = self.encryption.decrypt_aes(encrypted_token, aes_key)
            
            # Step 4: Validate credentials
            username, password, timestamp = self.auth.parse_auth_data(auth_json)
            
            if self.auth.validate_credentials(username, password):
                # Authentication successful
                response = self.auth.create_auth_response(
                    success=True,
                    message='VPN tunnel established',
                    server_info={'server_ip': self.host}
                )
                encrypted_response = self.encryption.encrypt_aes(response, aes_key)
                client_socket.send(encrypted_response)
                
                self._log(f"✓ Client {address} authenticated as '{username}'")
                self._log(f"✓ Secure tunnel established with {address}")
                
                # Store client info
                self.clients[address] = {
                    'socket': client_socket,
                    'aes_key': aes_key,
                    'username': username,
                    'authenticated': True,
                    'connected_at': time.time()
                }
                
                # Handle tunnel
                self._handle_tunnel(client_socket, address, aes_key)
            else:
                # Authentication failed
                response = self.auth.create_auth_response(
                    success=False,
                    message='Authentication failed: Invalid credentials'
                )
                encrypted_response = self.encryption.encrypt_aes(response, aes_key)
                client_socket.send(encrypted_response)
                self._log(f"✗ Authentication failed for {address}", level='WARNING')
                client_socket.close()
        
        except Exception as e:
            self._log(f"Error handling client {address}: {e}", level='ERROR')
            if address in self.clients:
                del self.clients[address]
            try:
                client_socket.close()
            except:
                pass
    
    def _handle_tunnel(self, client_socket: socket.socket, address: tuple, aes_key: bytes):
        """Handle VPN tunnel for data transmission"""
        try:
            while self.running:
                # Receive encrypted data
                data = client_socket.recv(DEFAULT_BUFFER_SIZE)
                if not data:
                    break
                
                # Decrypt data
                decrypted_data = self.encryption.decrypt_aes(data, aes_key)
                self._log(f"Received from {address}: {len(decrypted_data)} bytes")
                
                # Send acknowledgment
                ack = json.dumps({
                    'status': 'ok',
                    'timestamp': time.time(),
                    'bytes_received': len(decrypted_data)
                })
                encrypted_ack = self.encryption.encrypt_aes(ack, aes_key)
                client_socket.send(encrypted_ack)
        
        except Exception as e:
            self._log(f"Tunnel error with {address}: {e}", level='ERROR')
        finally:
            self._log(f"Client {address} disconnected")
            if address in self.clients:
                del self.clients[address]
            client_socket.close()
    
    def stop(self):
        """Stop the VPN server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self._log("Server stopped")
    
    def _log(self, message: str, level: str = 'INFO'):
        """Log message with timestamp"""
        if config.VERBOSE_LOGGING or level != 'INFO':
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
