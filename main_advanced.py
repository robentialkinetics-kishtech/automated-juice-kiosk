"""
Main entry point for ZKBot Advanced Kiosk Management System
Run this file to start the application
"""

import tkinter as tk
from tkinter import messagebox
import os
import sys

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)
os.makedirs("assets/images", exist_ok=True)
os.makedirs("assets/sounds", exist_ok=True)
os.makedirs("programs/juices", exist_ok=True)
os.makedirs("programs/common", exist_ok=True)

# Import after directory creation
try:
    from dashboard_hub import DashboardHub
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required files are in the same directory")
    sys.exit(1)

def main():
    """Main entry point"""
    try:
        root = tk.Tk()
        app = DashboardHub(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Application crashed: {e}")
        raise

if __name__ == "__main__":
    main()
