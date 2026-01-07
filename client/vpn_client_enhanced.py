"""
Enhanced VPN Client Core with Real Tunneling
Implements actual packet forwarding through VPN tunnel
"""

import socket
import json
import os
import time
import sys
import threading
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.encryption import EncryptionHandler, RSAHandler
from shared.constants import DEFAULT_BUFFER_SIZE, ACCESS_CONTROL_FILE
from . import config


class VPNClientEnhanced:
    """
    Enhanced VPN Client with real tunneling capabilities
    Features:
    - Encrypted communication (AES-256 + RSA-2048)
    - Packet forwarding through VPN tunnel
    - Flow control awareness
    - Connection statistics
    - Keepalive mechanism
    """
    
    def __init__(self):
        self.server_host = config.DEFAULT_SERVER_HOST
        self.server_port = config.DEFAULT_SERVER_PORT
        self.socket = None
        self.aes_key = None
        self.server_public_key = None
        self.connected = False
        
        # Initialize encryption handler
        self.encryption = EncryptionHandler()
        
        # Statistics
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'connection_start': 0,
            'last_rtt': 0
        }
        
        # Keepalive thread
        self.keepalive_thread = None
        self.keepalive_running = False
    
    def connect(self, username: str, password: str) -> tuple:
        """
        Connect to VPN server and establish secure tunnel
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Tuple of (success: bool, message: str, server_info: dict)
        """
        try:
            connection_start = time.time()
            
            # Create socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(config.CONNECTION_TIMEOUT)
            
            # Enable TCP keepalive
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Disable Nagle's algorithm for lower latency
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            print(f"[CLIENT] Connecting to {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))
            
            # Step 1: Receive server's public key
            print("[CLIENT] Receiving server public key...")
            public_pem = self.socket.recv(2048)
            self.server_public_key = RSAHandler.load_public_key(public_pem)
            print("[CLIENT] ✓ RSA-2048 public key received")
            
            # Step 2: Generate AES key and encrypt with server's public key
            print("[CLIENT] Generating AES-256 session key...")
            self.aes_key = os.urandom(32)  # 256-bit key
            encrypted_aes_key = RSAHandler.encrypt_rsa(self.aes_key, self.server_public_key)
            # Send with length prefix for reliable transmission
            key_len = len(encrypted_aes_key)
            self.socket.sendall(key_len.to_bytes(4, 'big'))
            self.socket.sendall(encrypted_aes_key)
            print("[CLIENT] ✓ Encrypted session key sent")
            
            # Step 3: Send authentication credentials
            print("[CLIENT] Authenticating...")
            auth_data = json.dumps({
                'username': username,
                'password': password,
                'timestamp': time.time(),
                'client_version': '2.0'
            })
            encrypted_auth = self.encryption.encrypt_aes(auth_data, self.aes_key)
            # Send length first, then data
            auth_len = len(encrypted_auth)
            self.socket.sendall(auth_len.to_bytes(4, 'big'))
            self.socket.sendall(encrypted_auth)
            
            # Step 4: Receive authentication response (with length prefix)
            resp_len_bytes = b''
            while len(resp_len_bytes) < 4:
                chunk = self.socket.recv(4 - len(resp_len_bytes))
                if not chunk:
                    return False, "Connection closed during response length receive", {}
                resp_len_bytes += chunk
            
            if len(resp_len_bytes) != 4:
                return False, "Failed to receive response length", {}
            resp_len = int.from_bytes(resp_len_bytes, 'big')
            
            # Receive all response data
            encrypted_response = b''
            while len(encrypted_response) < resp_len:
                chunk = self.socket.recv(min(resp_len - len(encrypted_response), 4096))
                if not chunk:
                    return False, "Connection closed during response", {}
                encrypted_response += chunk
                
            response = json.loads(self.encryption.decrypt_aes(encrypted_response, self.aes_key))
            
            connection_time = time.time() - connection_start
            
            if response['status'] == 'success':
                self.connected = True
                self.stats['connection_start'] = time.time()
                
                # Start keepalive
                self._start_keepalive()
                
                server_info = response.get('server_info', {})
                features = server_info.get('features', [])
                
                print(f"[CLIENT] ✓ Connected in {connection_time:.3f}s")
                print(f"[CLIENT] Server features: {', '.join(features)}")
                print(f"[CLIENT] Encryption: {server_info.get('encryption', 'AES-256')}")
                print(f"[CLIENT] Key exchange: {server_info.get('key_exchange', 'RSA-2048')}")
                
                return True, response['message'], server_info
            else:
                self.socket.close()
                return False, response['message'], {}
        
        except Exception as e:
            if self.socket:
                self.socket.close()
            return False, f"Connection error: {str(e)}", {}
    
    def disconnect(self):
        """Disconnect from VPN server"""
        print("[CLIENT] Disconnecting...")
        
        # Stop keepalive
        self._stop_keepalive()
        
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        self.aes_key = None
        
        # Print session statistics
        if self.stats['connection_start'] > 0:
            session_duration = time.time() - self.stats['connection_start']
            print(f"[CLIENT] Session duration: {session_duration:.1f}s")
            print(f"[CLIENT] Packets sent: {self.stats['packets_sent']}")
            print(f"[CLIENT] Packets received: {self.stats['packets_received']}")
            print(f"[CLIENT] Data sent: {self.stats['bytes_sent']} bytes")
            print(f"[CLIENT] Data received: {self.stats['bytes_received']} bytes")
    
    def send_data(self, data: str) -> tuple:
        """
        Send encrypted data through VPN tunnel
        
        Args:
            data: Data to send
            
        Returns:
            Tuple of (success: bool, response: dict or error message, rtt: float)
        """
        if not self.connected or not self.socket:
            return False, "Not connected to VPN", 0
        
        try:
            start_time = time.time()
            
            # Encrypt and send with length prefix
            encrypted_data = self.encryption.encrypt_aes(data, self.aes_key)
            data_len = len(encrypted_data)
            self.socket.sendall(data_len.to_bytes(4, 'big'))
            self.socket.sendall(encrypted_data)
            
            self.stats['bytes_sent'] += len(encrypted_data)
            self.stats['packets_sent'] += 1
            
            # Receive acknowledgment with length prefix
            ack_len_bytes = b''
            while len(ack_len_bytes) < 4:
                chunk = self.socket.recv(4 - len(ack_len_bytes))
                if not chunk:
                    return False, "Connection closed during response length receive", 0
                ack_len_bytes += chunk
            
            if len(ack_len_bytes) != 4:
                return False, "Failed to receive response length", 0
            ack_len = int.from_bytes(ack_len_bytes, 'big')
            
            # Receive all acknowledgment data
            encrypted_ack = b''
            while len(encrypted_ack) < ack_len:
                chunk = self.socket.recv(min(ack_len - len(encrypted_ack), 4096))
                if not chunk:
                    return False, "Connection closed during response", 0
                encrypted_ack += chunk
            
            ack = json.loads(self.encryption.decrypt_aes(encrypted_ack, self.aes_key))
            
            self.stats['bytes_received'] += len(encrypted_ack)
            self.stats['packets_received'] += 1
            
            # Calculate RTT
            rtt = time.time() - start_time
            self.stats['last_rtt'] = rtt
            
            return True, ack, rtt
        except Exception as e:
            return False, str(e), 0
    
    def forward_traffic(self, dest_host: str, dest_port: int, data: str = "") -> tuple:
        """
        Forward traffic through VPN tunnel to destination
        
        Args:
            dest_host: Destination hostname/IP
            dest_port: Destination port
            data: Optional data to send
            
        Returns:
            Tuple of (success: bool, response: dict or error message)
        """
        if not self.connected:
            return False, "Not connected to VPN"
        
        try:
            # Send forward request
            forward_request = f"FORWARD:{dest_host}:{dest_port}:{data}"
            success, response, rtt = self.send_data(forward_request)
            
            if success and isinstance(response, dict):
                if response.get('status') == 'success':
                    print(f"[CLIENT] ✓ Traffic forwarded to {dest_host}:{dest_port} (RTT: {rtt*1000:.2f}ms)")
                    return True, response
                else:
                    error = response.get('error', 'Unknown error')
                    print(f"[CLIENT] ✗ Forward failed: {error}")
                    return False, error
            else:
                return False, str(response)
        except Exception as e:
            return False, str(e)
    
    def request_statistics(self) -> dict:
        """Request server statistics"""
        if not self.connected:
            return {}
        
        try:
            success, response, rtt = self.send_data("STATS_REQ")
            if success and isinstance(response, dict):
                return response
            return {}
        except:
            return {}
    
    def _start_keepalive(self):
        """Start keepalive thread"""
        self.keepalive_running = True
        self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self.keepalive_thread.start()
    
    def _stop_keepalive(self):
        """Stop keepalive thread"""
        self.keepalive_running = False
        if self.keepalive_thread:
            self.keepalive_thread.join(timeout=2.0)
    
    def _keepalive_loop(self):
        """Send periodic keepalive packets"""
        while self.keepalive_running and self.connected:
            try:
                time.sleep(config.KEEPALIVE_INTERVAL)
                
                if self.connected:
                    keepalive_data = json.dumps({
                        'type': 'keepalive',
                        'timestamp': time.time()
                    })
                    self.send_data(keepalive_data)
                    print("[CLIENT] ♥ Keepalive sent")
            except:
                pass
    
    def set_server(self, host: str, port: int = None):
        """Set server connection details"""
        self.server_host = host
        if port:
            self.server_port = port
    
    def get_stats(self) -> dict:
        """Get client statistics"""
        stats = self.stats.copy()
        if stats['connection_start'] > 0:
            stats['uptime'] = time.time() - stats['connection_start']
        return stats
