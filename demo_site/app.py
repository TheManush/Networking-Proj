"""
Demo Website Application
Flask app that simulates geo-restricted content
"""

import sys
import os
from flask import Flask, render_template, request, abort
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_site import config
from demo_site.access_control import AccessControl

app = Flask(__name__, template_folder='../templates')
access_control = AccessControl()


@app.before_request
def check_access():
    """Check if client should have access before serving any page"""
    client_ip = request.remote_addr
    
    allowed, reason = access_control.is_allowed(client_ip)
    
    if not allowed:
        # Simulate connection refused/timeout
        time.sleep(0.5)
        abort(503)


@app.route('/')
def index():
    """Main page - only accessible with proper access"""
    client_ip = request.remote_addr
    return render_template('index.html', client_ip=client_ip)


@app.route('/status')
def status():
    """Status endpoint"""
    return {
        'status': 'online',
        'message': 'Accessed through VPN!',
        'client_ip': request.remote_addr,
        'vpn_status': 'connected'
    }


@app.errorhandler(503)
def service_unavailable(e):
    """Custom error handler"""
    return "", 503


def main():
    """Main entry point for demo website"""
    print("=" * 70)
    print("🌐 GEO-BLOCKED DEMO WEBSITE")
    print("=" * 70)
    print(f"Server starting on: http://{config.HOST}:{config.PORT}")
    print()
    print("Access Control:")
    if config.USE_FILE_BASED_CONTROL:
        print(f"  • File-based control: ENABLED ({config.ACCESS_CONTROL_FILE})")
        access_control.initialize_access_file()
        print("  • Initial state: BLOCKED")
    if config.USE_IP_BLOCKING:
        print(f"  • IP blocking: ENABLED")
        print(f"  • Blocked IPs: {config.BLOCKED_IPS}")
    print()
    print("Demo Flow:")
    print("  1. Try http://localhost:9000 → Error (blocked)")
    print("  2. Connect VPN client → Access enabled")
    print("  3. Refresh browser → Site accessible!")
    print("=" * 70)
    print()
    
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)


if __name__ == '__main__':
    main()
