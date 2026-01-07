"""
Local HTTP Proxy - Routes traffic through VPN tunnel
Listens on localhost:8080, forwards through VPN to destination
"""

import socket
import threading
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='[PROXY] %(message)s')


class LocalProxy:
    """Simple HTTP proxy that forwards through VPN tunnel"""
    
    def __init__(self, vpn_client, local_port=8080):
        self.vpn_client = vpn_client
        self.local_port = local_port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.proxy_thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start the local proxy server"""
        if self.running:
            return
            
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind(('127.0.0.1', self.local_port))
            self.server_socket.listen(5)
            logging.info(f"Local proxy listening on http://localhost:{self.local_port}")
            logging.info("Configure your browser to use this proxy")
            
            self.proxy_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.proxy_thread.start()
            
        except Exception as e:
            logging.error(f"Failed to start proxy: {e}")
            self.running = False
            
    def stop(self):
        """Stop the proxy server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logging.info("Local proxy stopped")
        
    def _accept_loop(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logging.info(f"Proxy connection from {addr}")
                
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                thread.start()
                
            except Exception as e:
                if self.running:
                    logging.error(f"Accept error: {e}")
                    
    def _handle_client(self, client_socket: socket.socket):
        """Handle a proxy client connection"""
        try:
            # Read HTTP request with timeout
            client_socket.settimeout(5.0)
            request_data = b''
            
            while b'\r\n\r\n' not in request_data:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                if len(request_data) > 100000:  # Limit request size
                    break
                    
            if not request_data:
                return
                
            # Parse request
            request_str = request_data.decode('utf-8', errors='ignore')
            lines = request_str.split('\r\n')
            
            if not lines:
                return
                
            # Parse first line: GET http://host:port/path HTTP/1.1 or GET /path HTTP/1.1
            first_line = lines[0]
            parts = first_line.split()
            
            if len(parts) < 2:
                return
                
            method = parts[0]
            url_or_path = parts[1]
            
            # Parse destination from URL (for proxy requests) or Host header
            host = None
            port = 80
            path = url_or_path
            
            # Check if full URL is in request line (proxy mode)
            if url_or_path.startswith('http://') or url_or_path.startswith('https://'):
                # Parse: http://192.168.0.105:9000/path
                from urllib.parse import urlparse
                parsed = urlparse(url_or_path)
                host = parsed.hostname
                port = parsed.port if parsed.port else (443 if parsed.scheme == 'https' else 80)
                path = parsed.path if parsed.path else '/'
                logging.info(f"📍 Extracted from URL: {host}:{port}{path}")
            
            # Fallback: Parse from Host header
            if not host:
                for line in lines[1:]:
                    if line.lower().startswith('host:'):
                        host_value = line.split(':', 1)[1].strip()
                        # Parse host:port from Host header
                        if ':' in host_value:
                            host, port_str = host_value.rsplit(':', 1)
                            try:
                                port = int(port_str)
                            except:
                                pass
                        else:
                            host = host_value
                        break
            
            # Final fallback
            if not host:
                host = 'localhost'
                port = 9000
                    
            logging.info(f"🔒 Forwarding {method} {path} to {host}:{port} through encrypted VPN tunnel")
            
            # Reconstruct HTTP request with path only (not full URL)
            reconstructed_request = f"{method} {path} HTTP/1.1\r\n"
            for line in lines[1:]:
                if line.strip():  # Skip empty lines
                    reconstructed_request += line + "\r\n"
            reconstructed_request += "\r\n"
            
            # Forward through VPN tunnel (returns raw response bytes)
            success, response = self.vpn_client.forward_traffic(
                host, port, reconstructed_request
            )
            
            if success and response:
                # Response is dict, extract data
                if isinstance(response, dict):
                    response_data = response.get('data', '')
                    if isinstance(response_data, str):
                        # Decode from latin-1 (HTTP response encoding)
                        response_data = response_data.encode('latin-1')
                    client_socket.sendall(response_data)
                    logging.info(f"✓ Response: {len(response_data)} bytes forwarded through VPN")
                else:
                    client_socket.sendall(str(response).encode())
                    logging.info(f"✓ Response received ({len(response)} bytes)")
            else:
                # Send error
                error_response = (
                    b"HTTP/1.1 502 Bad Gateway\r\n"
                    b"Content-Type: text/html\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    b"<h1>VPN Tunnel Error</h1><p>Could not forward request through VPN.</p>"
                )
                client_socket.sendall(error_response)
                logging.error(f"✗ Failed to forward through VPN: {response}")
                
        except socket.timeout:
            logging.error("✗ Timeout reading client request")
        except Exception as e:
            logging.error(f"✗ Proxy error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            try:
                client_socket.close()
            except:
                pass
