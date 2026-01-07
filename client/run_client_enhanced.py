"""
VPN Client Entry Point - Enhanced Version
"""

import sys
import os
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.gui.main_window_enhanced import VPNClientGUIEnhanced


def main():
    """Main entry point"""
    root = tk.Tk()
    app = VPNClientGUIEnhanced(root)
    root.mainloop()


if __name__ == '__main__':
    main()
