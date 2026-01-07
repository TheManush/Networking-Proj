"""
VPN Client Entry Point
Run this file to start the VPN client
"""

import sys
import os
import tkinter as tk

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.gui.main_window import VPNClientGUI


def main():
    """Main entry point for VPN client"""
    root = tk.Tk()
    app = VPNClientGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
