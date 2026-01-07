"""
VPN Server Entry Point - Enhanced Version with signal handling
"""

import sys
import os
import signal
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.vpn_server_enhanced import VPNServerEnhanced
from server import config

server_instance = None

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n[SERVER] Shutting down...")
    if server_instance:
        server_instance.shutdown()
    print("[SERVER] Stopped")
    sys.exit(0)

def main():
    """Main entry point for enhanced VPN server"""
    global server_instance
    
    # Register Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 70)
    print("🔒 CUSTOM VPN SERVER - ENHANCED")
    print("=" * 70)
    print(f"Version: 2.0 (Full Networking Features)")
    print(f"Server: {config.HOST}:{config.PORT}")
    print()
    print("Features Enabled:")
    print("  ✅ AES-256 Encryption")
    print("  ✅ RSA-2048 Key Exchange")
    print("  ✅ Client Authentication")
    print("  ✅ Packet Forwarding & Tunneling")
    print("  ✅ Flow Control (TCP-like)")
    print("  ✅ Congestion Management")
    print("  ✅ Connection Multiplexing")
    print("  ✅ Real-time Statistics")
    print()
    print(f"Max clients: {config.MAX_CLIENTS}")
    print(f"Authentication: {'Enabled' if config.REQUIRE_AUTH else 'Disabled'}")
    print("=" * 70)
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    try:
        server_instance = VPNServerEnhanced(config.HOST, config.PORT)
        server_instance.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[SERVER] Keyboard interrupt")
        if server_instance:
            server_instance.shutdown()
    except Exception as e:
        print(f"[SERVER] Error: {e}")
        if server_instance:
            server_instance.shutdown()


if __name__ == '__main__':
    main()
