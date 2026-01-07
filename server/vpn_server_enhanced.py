"""
Enhanced VPN Server Core with Tunneling and Flow Control
Implements real VPN functionality with packet forwarding
"""

import socket
import threading
import json
import os
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.encryption import EncryptionHandler, RSAHandler
from shared.constants import DEFAULT_BUFFER_SIZE
from . import config
from .auth_handler import AuthHandler
from .tunnel_manager import TunnelManager
from .flow_control import FlowController


class VPNServerEnhanced:
    """
    Enhanced VPN Server with real tunneling capabilities
    Implements:
    - Encrypted tunnels (AES-256 + RSA-2048)
    - Authentication
    - Packet forwarding and routing
    - Flow control and congestion management
    - Connection multiplexing
    """
    
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
        
        # Global statistics
        self.global_stats = {
            'total_connections': 0,
            'active_tunnels': 0,
            'total_bytes_forwarded': 0,
            'uptime_start': time.time()
        }
        
        self._log(f"Enhanced VPN Server initialized on {self.host}:{self.port}")
        self._log("Features: Tunneling, Flow Control, Congestion Management")
    
    def start(self):
        """Start the VPN server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set TCP keepalive
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(config.MAX_CLIENTS)
            self.running = True
            
            self._log(f"Server listening on {self.host}:{self.port}")
            self._log(f"Max clients: {config.MAX_CLIENTS}")
            self._log("="*70)
            self._log("Waiting for client connections...")
            self._log("="*70)
            
            # Start statistics reporter
            stats_thread = threading.Thread(target=self._stats_reporter, daemon=True)
            stats_thread.start()
            
            while self.running:
                try:
                    # Set timeout on accept() for responsive Ctrl+C
                    self.server_socket.settimeout(1.0)
                    client_socket, address = self.server_socket.accept()
                    
                    # Configure socket options
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    
                    self._log(f"📥 New connection from {address}")
                    self.global_stats['total_connections'] += 1
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                
                except socket.timeout:
                    # Expected - allows checking self.running flag
                    continue
                except Exception as e:
                    if self.running:
                        self._log(f"Error accepting connection: {e}", level='ERROR')
        
        except Exception as e:
            self._log(f"Failed to start server: {e}", level='ERROR')
            raise
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle individual client connection with full VPN features"""
        flow_controller = FlowController()
        tunnel_manager = None
        
        try:
            # Step 1: Send server's public key
            public_pem = RSAHandler.serialize_public_key(self.public_key)
            client_socket.sendall(public_pem)
            self._log(f"[{address}] 🔑 Sent RSA public key")
            
            # Step 2: Receive encrypted AES key with length prefix
            key_len_bytes = b''
            while len(key_len_bytes) < 4:
                chunk = client_socket.recv(4 - len(key_len_bytes))
                if not chunk:
                    raise Exception("Connection closed during key length receive")
                key_len_bytes += chunk
            
            if len(key_len_bytes) != 4:
                raise Exception("Failed to receive AES key length")
            key_len = int.from_bytes(key_len_bytes, 'big')
            
            # Receive all encrypted key bytes
            encrypted_aes_key = b''
            while len(encrypted_aes_key) < key_len:
                chunk = client_socket.recv(min(key_len - len(encrypted_aes_key), 4096))
                if not chunk:
                    raise Exception("Connection closed during AES key transfer")
                encrypted_aes_key += chunk
            
            aes_key = RSAHandler.decrypt_rsa(encrypted_aes_key, self.private_key)
            self._log(f"[{address}] 🔐 Received and decrypted AES-256 key")
            
            # Step 3: Receive encrypted authentication with length prefix
            auth_len_bytes = b''
            while len(auth_len_bytes) < 4:
                chunk = client_socket.recv(4 - len(auth_len_bytes))
                if not chunk:
                    raise Exception("Connection closed during auth length receive")
                auth_len_bytes += chunk
            
            auth_len = int.from_bytes(auth_len_bytes, 'big')
            encrypted_token = b''
            while len(encrypted_token) < auth_len:
                chunk = client_socket.recv(min(auth_len - len(encrypted_token), 4096))
                if not chunk:
                    raise Exception("Connection closed during auth")
                encrypted_token += chunk
            auth_json = self.encryption.decrypt_aes(encrypted_token, aes_key)
            
            # Step 4: Validate credentials
            username, password, timestamp = self.auth.parse_auth_data(auth_json)
            
            if self.auth.validate_credentials(username, password):
                # Authentication successful
                response = self.auth.create_auth_response(
                    success=True,
                    message='VPN tunnel established - Full forwarding enabled',
                    server_info={
                        'server_ip': self.host,
                        'features': ['tunneling', 'flow_control', 'encryption'],
                        'encryption': 'AES-256-CBC',
                        'key_exchange': 'RSA-2048-OAEP'
                    }
                )
                encrypted_response = self.encryption.encrypt_aes(response, aes_key)
                # Send with length prefix for reliable transmission
                resp_len = len(encrypted_response)
                client_socket.sendall(resp_len.to_bytes(4, 'big'))
                client_socket.sendall(encrypted_response)
                
                self._log(f"[{address}] ✅ Authenticated as '{username}'")
                self._log(f"[{address}] 🔒 Secure tunnel established")
                self._log(f"[{address}] 📊 Flow control initialized (window: {flow_controller.cwnd} bytes)")
                
                # Initialize tunnel manager
                tunnel_manager = TunnelManager(aes_key, client_socket)
                
                # Store client info
                self.clients[address] = {
                    'socket': client_socket,
                    'aes_key': aes_key,
                    'username': username,
                    'authenticated': True,
                    'connected_at': time.time(),
                    'tunnel_manager': tunnel_manager,
                    'flow_controller': flow_controller
                }
                
                self.global_stats['active_tunnels'] += 1
                
                # Handle tunnel with flow control
                self._handle_tunnel_with_flow_control(
                    client_socket, address, aes_key, 
                    tunnel_manager, flow_controller
                )
            else:
                # Authentication failed
                response = self.auth.create_auth_response(
                    success=False,
                    message='Authentication failed: Invalid credentials'
                )
                encrypted_response = self.encryption.encrypt_aes(response, aes_key)
                client_socket.send(encrypted_response)
                self._log(f"[{address}] ❌ Authentication failed", level='WARNING')
                client_socket.close()
        
        except Exception as e:
            self._log(f"[{address}] Error: {e}", level='ERROR')
        finally:
            # Cleanup
            if tunnel_manager:
                tunnel_manager.stop_tunnel()
            
            if address in self.clients:
                self.global_stats['active_tunnels'] -= 1
                del self.clients[address]
            
            try:
                client_socket.close()
            except:
                pass
            
            self._log(f"[{address}] 🔌 Disconnected")
    
    def shutdown(self):
        """Shutdown server gracefully"""
        self.running = False
        self._log("Server shutting down...")
        
        # Close all client connections
        for address, client_info in list(self.clients.items()):
            try:
                client_info['socket'].close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
    
    def _handle_tunnel_with_flow_control(
        self, 
        client_socket: socket.socket, 
        address: tuple, 
        aes_key: bytes,
        tunnel_manager: TunnelManager,
        flow_controller: FlowController
    ):
        """Handle VPN tunnel with flow control and congestion management"""
        
        # Start tunnel manager (it will handle all socket reading)
        tunnel_manager.start_tunnel()
        
        try:
            # Just wait for tunnel to finish - tunnel_manager handles all communication
            while self.running and tunnel_manager.running:
                time.sleep(1.0)
                # Flow control stats are updated by tunnel_manager as needed
        
        except Exception as e:
            self._log(f"[{address}] Tunnel error: {e}", level='ERROR')
            flow_controller.on_packet_loss()
    
    def _send_statistics(
        self, 
        client_socket: socket.socket, 
        aes_key: bytes,
        tunnel_manager: TunnelManager,
        flow_controller: FlowController
    ):
        """Send current statistics to client"""
        stats = {
            'tunnel_stats': tunnel_manager.get_stats(),
            'flow_control_stats': flow_controller.get_stats(),
            'server_stats': {
                'total_connections': self.global_stats['total_connections'],
                'active_tunnels': self.global_stats['active_tunnels'],
                'total_bytes_forwarded': self.global_stats['total_bytes_forwarded'],
                'uptime_seconds': time.time() - self.global_stats['uptime_start']
            }
        }
        
        stats_json = json.dumps(stats)
        encrypted_stats = self.encryption.encrypt_aes(stats_json, aes_key)
        client_socket.send(encrypted_stats)
    
    def _stats_reporter(self):
        """Periodically report server statistics"""
        while self.running:
            time.sleep(30)  # Report every 30 seconds
            
            uptime = time.time() - self.global_stats['uptime_start']
            self._log("="*70)
            self._log("📊 SERVER STATISTICS")
            self._log(f"   Uptime: {uptime:.0f}s")
            self._log(f"   Total Connections: {self.global_stats['total_connections']}")
            self._log(f"   Active Tunnels: {self.global_stats['active_tunnels']}")
            self._log(f"   Total Data Forwarded: {self.global_stats['total_bytes_forwarded'] / 1024:.2f} KB")
            self._log("="*70)
    
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
