"""
VPN Server Entry Point
Run this file to start the VPN server
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.vpn_server_core import VPNServer
from server import config


def main():
    """Main entry point for VPN server"""
    print("=" * 70)
    print("🔒 CUSTOM VPN SERVER")
    print("=" * 70)
    print(f"Starting server on {config.HOST}:{config.PORT}")
    print(f"Max clients: {config.MAX_CLIENTS}")
    print(f"Authentication: {'Enabled' if config.REQUIRE_AUTH else 'Disabled'}")
    print("=" * 70)
    print()
    
    server = VPNServer(config.HOST, config.PORT)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n")
        print("=" * 70)
        print("Shutting down server...")
        print("=" * 70)
        server.stop()
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
