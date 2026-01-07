"""
Tunnel Manager
Handles actual packet forwarding and traffic routing through VPN
"""

import socket
import threading
import select
import time
import json
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.encryption import EncryptionHandler
from shared.constants import DEFAULT_BUFFER_SIZE


class TunnelManager:
    """
    Manages VPN tunnel - forwards traffic between client and destination
    Implements actual packet forwarding and routing
    """
    
    def __init__(self, aes_key: bytes, client_socket: socket.socket):
        self.aes_key = aes_key
        self.client_socket = client_socket
        self.encryption = EncryptionHandler()
        self.running = False
        self.forwarding_threads = []
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'connections': 0
        }
    
    def start_tunnel(self):
        """Start tunnel forwarding"""
        self.running = True
        
        # Set socket timeout for recv operations
        self.client_socket.settimeout(1.0)
        
        # Start listening for forwarding requests
        tunnel_thread = threading.Thread(target=self._tunnel_loop, daemon=True)
        tunnel_thread.start()
    
    def _tunnel_loop(self):
        """Main tunnel loop - handles forwarding requests from client"""
        try:
            while self.running:
                # Wait for data from client with timeout
                ready = select.select([self.client_socket], [], [], 1.0)
                
                if ready[0]:
                    try:
                        # Receive length prefix (4 bytes) - loop to ensure we get all 4
                        req_len_bytes = b''
                        while len(req_len_bytes) < 4:
                            chunk = self.client_socket.recv(4 - len(req_len_bytes))
                            if not chunk:
                                print(f"[TUNNEL] Connection closed while receiving length prefix")
                                break
                            req_len_bytes += chunk
                        
                        if len(req_len_bytes) != 4:
                            print(f"[TUNNEL] Incomplete length prefix: got {len(req_len_bytes)} bytes")
                            break
                        
                        req_len = int.from_bytes(req_len_bytes, 'big')
                        print(f"[TUNNEL] Expecting {req_len} bytes of encrypted data")
                        
                        # Sanity check: reject absurdly large messages
                        if req_len > 10 * 1024 * 1024:  # 10MB max
                            print(f"[TUNNEL] Message too large: {req_len} bytes, skipping")
                            continue
                        
                        # Receive all request data
                        encrypted_data = b''
                        while len(encrypted_data) < req_len:
                            chunk = self.client_socket.recv(min(req_len - len(encrypted_data), 4096))
                            if not chunk:
                                print(f"[TUNNEL] Connection closed while receiving data (got {len(encrypted_data)}/{req_len})")
                                break
                            encrypted_data += chunk
                        
                        if len(encrypted_data) != req_len:
                            print(f"[TUNNEL] Incomplete data: expected {req_len}, got {len(encrypted_data)}")
                            continue
                        
                        print(f"[TUNNEL] Received complete encrypted message: {len(encrypted_data)} bytes")
                    except socket.timeout:
                        print(f"[TUNNEL] Recv timeout, continuing...")
                        continue
                    except Exception as recv_error:
                        print(f"[TUNNEL] Receive error: {recv_error}")
                        break
                    
                    # Decrypt request
                    try:
                        request_data = self.encryption.decrypt_aes(encrypted_data, self.aes_key)
                        print(f"[TUNNEL] Decrypted request: {request_data[:100]}...")  # First 100 chars
                    except Exception as decrypt_error:
                        print(f"[TUNNEL] Decryption failed: {decrypt_error}")
                        print(f"[TUNNEL] Encrypted data length: {len(encrypted_data)}, data sample: {encrypted_data[:32].hex()}")
                        # Try to recover by continuing instead of breaking
                        continue
                    
                    # Check if it's a JSON message (keepalive, stats, etc.)
                    try:
                        import json
                        msg = json.loads(request_data)
                        if msg.get('type') == 'keepalive':
                            self._handle_keepalive()
                            continue
                        elif msg.get('type') == 'stats_request':
                            self._handle_stats_request()
                            continue
                    except:
                        pass  # Not JSON, process as command
                    
                    # Parse forwarding request (format: "FORWARD:host:port:data")
                    if request_data.startswith('FORWARD:'):
                        self._handle_forward_request(request_data)
                    elif request_data.startswith('CONNECT:'):
                        self._handle_connect_request(request_data)
                    elif request_data.startswith('STATS_REQ'):
                        self._handle_stats_request()
                    else:
                        # Unknown packet type
                        self._handle_data_packet(request_data)
        
        except Exception as e:
            print(f"[TUNNEL] Error in tunnel loop: {e}")
        finally:
            self.stop_tunnel()
    
    def _handle_forward_request(self, request: str):
        """
        Handle traffic forwarding request
        Format: FORWARD:destination_host:destination_port:data
        """
        try:
            parts = request.split(':', 3)
            if len(parts) >= 3:
                dest_host = parts[1]
                dest_port = int(parts[2])
                data = parts[3] if len(parts) > 3 else ""
                
                print(f"[TUNNEL] Forwarding to {dest_host}:{dest_port}, data length: {len(data)}")
                
                # Create connection to destination
                dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                dest_socket.settimeout(10)
                dest_socket.connect((dest_host, dest_port))
                
                self.stats['connections'] += 1
                
                # Send data if provided
                if data:
                    dest_socket.sendall(data.encode())
                    self.stats['bytes_sent'] += len(data)
                    self.stats['packets_sent'] += 1
                
                # Receive response
                response = dest_socket.recv(DEFAULT_BUFFER_SIZE)
                self.stats['bytes_received'] += len(response)
                self.stats['packets_received'] += 1
                
                print(f"[TUNNEL] Received {len(response)} bytes from {dest_host}:{dest_port}")
                
                # Send encrypted response back to client as JSON
                # Use latin-1 for HTTP responses (supports all byte values)
                response_json = json.dumps({
                    'status': 'success',
                    'data': response.decode('latin-1')
                })
                encrypted_response = self.encryption.encrypt_aes(
                    response_json,
                    self.aes_key
                )
                
                # Send with length prefix
                resp_len = len(encrypted_response)
                print(f"[TUNNEL] Sending response: {resp_len} encrypted bytes")
                try:
                    self.client_socket.sendall(resp_len.to_bytes(4, 'big'))
                    self.client_socket.sendall(encrypted_response)
                    print(f"[TUNNEL] Response sent successfully")
                except Exception as send_err:
                    print(f"[TUNNEL] Failed to send response: {send_err}")
                    raise
                
                dest_socket.close()
        
        except Exception as e:
            print(f"[TUNNEL] Forward error: {e}")
            error_json = json.dumps({
                'status': 'error',
                'error': str(e)
            })
            encrypted_error = self.encryption.encrypt_aes(error_json, self.aes_key)
            
            # Send with length prefix
            err_len = len(encrypted_error)
            self.client_socket.sendall(err_len.to_bytes(4, 'big'))
            self.client_socket.sendall(encrypted_error)
    
    def _handle_connect_request(self, request: str):
        """
        Handle persistent connection request
        Creates bidirectional forwarding
        """
        try:
            # Format: CONNECT:host:port
            parts = request.split(':')
            dest_host = parts[1]
            dest_port = int(parts[2])
            
            # Create destination socket
            dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest_socket.connect((dest_host, dest_port))
            
            self.stats['connections'] += 1
            
            # Send success response
            success_msg = "CONNECT_OK"
            encrypted_msg = self.encryption.encrypt_aes(success_msg, self.aes_key)
            self.client_socket.send(encrypted_msg)
            
            # Start bidirectional forwarding
            self._forward_bidirectional(dest_socket)
        
        except Exception as e:
            error_msg = f"CONNECT_ERROR:{str(e)}"
            encrypted_error = self.encryption.encrypt_aes(error_msg, self.aes_key)
            self.client_socket.send(encrypted_error)
    
    def _forward_bidirectional(self, dest_socket: socket.socket):
        """
        Forward traffic bidirectionally between client and destination
        This is the core of VPN tunneling
        """
        # Thread 1: Client -> Destination
        def forward_to_dest():
            try:
                while self.running:
                    encrypted_data = self.client_socket.recv(DEFAULT_BUFFER_SIZE)
                    if not encrypted_data:
                        break
                    
                    # Decrypt and forward
                    plain_data = self.encryption.decrypt_aes(encrypted_data, self.aes_key)
                    dest_socket.send(plain_data.encode())
                    
                    self.stats['bytes_sent'] += len(plain_data)
                    self.stats['packets_sent'] += 1
            except:
                pass
            finally:
                dest_socket.close()
        
        # Thread 2: Destination -> Client
        def forward_to_client():
            try:
                while self.running:
                    data = dest_socket.recv(DEFAULT_BUFFER_SIZE)
                    if not data:
                        break
                    
                    # Encrypt and forward
                    encrypted_data = self.encryption.encrypt_aes(
                        data.decode('utf-8', errors='ignore'),
                        self.aes_key
                    )
                    self.client_socket.send(encrypted_data)
                    
                    self.stats['bytes_received'] += len(data)
                    self.stats['packets_received'] += 1
            except:
                pass
            finally:
                self.client_socket.close()
        
        # Start both forwarding threads
        t1 = threading.Thread(target=forward_to_dest, daemon=True)
        t2 = threading.Thread(target=forward_to_client, daemon=True)
        
        t1.start()
        t2.start()
        
        self.forwarding_threads.extend([t1, t2])
    
    def _handle_data_packet(self, data: str):
        """Handle regular data packet (for statistics, keepalive, etc.)"""
        self.stats['packets_received'] += 1
        
        # Echo back acknowledgment with length prefix
        ack_json = json.dumps({'status': 'ack', 'size': len(data)})
        encrypted_ack = self.encryption.encrypt_aes(ack_json, self.aes_key)
        
        ack_len = len(encrypted_ack)
        self.client_socket.sendall(ack_len.to_bytes(4, 'big'))
        self.client_socket.sendall(encrypted_ack)
    
    def _handle_keepalive(self):
        """Handle keepalive packet"""
        # Send keepalive acknowledgment
        ack_json = json.dumps({'status': 'ok', 'type': 'keepalive_ack'})
        encrypted_ack = self.encryption.encrypt_aes(ack_json, self.aes_key)
        
        ack_len = len(encrypted_ack)
        self.client_socket.sendall(ack_len.to_bytes(4, 'big'))
        self.client_socket.sendall(encrypted_ack)
    
    def _handle_stats_request(self):
        """Handle statistics request"""
        stats_json = json.dumps(self.stats)
        encrypted_stats = self.encryption.encrypt_aes(stats_json, self.aes_key)
        
        stats_len = len(encrypted_stats)
        self.client_socket.sendall(stats_len.to_bytes(4, 'big'))
        self.client_socket.sendall(encrypted_stats)
    
    def stop_tunnel(self):
        """Stop tunnel and cleanup"""
        self.running = False
        
        # Wait for forwarding threads to finish
        for thread in self.forwarding_threads:
            thread.join(timeout=1.0)
    
    def get_stats(self) -> dict:
        """Get tunnel statistics"""
        return self.stats.copy()
