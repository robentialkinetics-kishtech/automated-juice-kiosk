"""
Advanced Juice Kiosk - Unified Application
Combined interface for customer ordering, order history, and admin management
Similar to KFC/Domino's ordering systems with database integration
"""

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import threading
from datetime import datetime

# Import advanced modules
from order_database import AdvancedKioskDB
from order_models import OrderStatus, PaymentMethod
from customer_ui_advanced import AdvancedCustomerUI
from admin_dashboard import AdminDashboard
from drink_runner import make_drink
import gui as teach_gui

# ========== CONFIG ==========

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "kiosk.db"

OWNER_PASSWORD = "0000"
DEV_PASSWORD = "0000"

# Juice Products Database
DRINK_CATALOG = {
    "mango": {
        "label": "Mango Juice",
        "price": 80,
        "image": IMAGES_DIR / "badham.jpeg",
        "description": "Fresh tropical mango",
        "category": "Tropical",
        "runner_key": "mango",
    },
    "orange": {
        "label": "Orange Juice",
        "price": 70,
        "image": IMAGES_DIR / "grape.jpeg",
        "description": "Citrus refreshment",
        "category": "Citrus",
        "runner_key": "orange",
    },
    "grape": {
        "label": "Grape Juice",
        "price": 75,
        "image": IMAGES_DIR / "lemon.jpeg",
        "description": "Sweet and tangy",
        "category": "Berry",
        "runner_key": "grape",
    },
    "apple": {
        "label": "Rose Milk",
        "price": 85,
        "image": IMAGES_DIR / "rose.jpeg",
        "description": "Creamy specialty drink",
        "category": "Special",
        "runner_key": "apple",
    },
}

# UI Theme (KFC/Domino's style)
THEME = {
    "bg": "#F5F7FB",
    "panel": "#FFFFFF",
    "text": "#111827",
    "muted": "#6B7280",
    "brand": "#E31B23",  # Red accent
    "brand2": "#2563EB",  # Blue accent
    "success": "#16A34A",
    "danger": "#DC2626",
    "border": "#E5E7EB",
}


# ========== MAIN APPLICATION ==========

class AdvancedJuiceKiosk:
    """Main application combining customer UI, admin dashboard, and developer interface"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🍹 Advanced Juice Kiosk System")
        self.root.geometry("1400x800")
        self.root.configure(bg=THEME["bg"])
        
        # Initialize database
        self.db = AdvancedKioskDB(str(DB_PATH))
        self._initialize_products()
        
        # Current state
        self.logged_in_role = None  # "customer", "owner", "developer"
        self.current_order_processing = None
        
        # Show login screen
        self._show_login_screen()
    
    def _initialize_products(self):
        """Initialize products in database"""
        try:
            existing = self.db.get_all_products()
            if not existing:
                for key, drink in DRINK_CATALOG.items():
                    self.db.add_product(
                        name=drink['label'],
                        price=drink['price'],
                        description=drink.get('description', ''),
                        category=drink.get('category', 'Custom'),
                        image_path=str(drink['image'])
                    )
        except Exception as e:
            print(f"Error initializing products: {e}")
    
    def _show_login_screen(self):
        """Show role selection and login"""
        self._clear_window()
        
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="🍹 Advanced Juice Kiosk", font=("Arial", 24, "bold")).pack(pady=20)
        ttk.Label(frame, text="Select Your Role:", font=("Arial", 14)).pack(pady=10)
        
        # Customer button
        ttk.Button(
            frame,
            text="🛒 Customer - Order Juices",
            command=self._login_as_customer,
            width=30
        ).pack(pady=10, ipady=15)
        
        # Owner button
        ttk.Button(
            frame,
            text="👔 Owner - View Orders & Analytics",
            command=lambda: self._login_as_owner(),
            width=30
        ).pack(pady=10, ipady=15)
        
        # Developer button
        ttk.Button(
            frame,
            text="⚙️ Developer - Settings & Control",
            command=lambda: self._login_as_developer(),
            width=30
        ).pack(pady=10, ipady=15)
    
    def _login_as_customer(self):
        """Show customer ordering interface"""
        self.logged_in_role = "customer"
        self._clear_window()
        
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header, text="🍹 Juice Ordering", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Logout", command=self._show_login_screen).pack(side="right")
        
        # Customer UI
        customer_ui = AdvancedCustomerUI(self.root, self.db, IMAGES_DIR)
        customer_ui.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _login_as_owner(self):
        """Show admin dashboard"""
        password = self._ask_password("Owner Access", "Enter owner password:")
        if password != OWNER_PASSWORD:
            messagebox.showerror("Error", "Invalid password")
            return
        
        self.logged_in_role = "owner"
        self._clear_window()
        
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header, text="📊 Admin Dashboard", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Logout", command=self._show_login_screen).pack(side="right")
        
        # Admin dashboard
        admin = AdminDashboard(self.root, self.db)
        admin.pack(fill="both", expand=True)
    
    def _login_as_developer(self):
        """Show developer/teaching interface"""
        password = self._ask_password("Developer Access", "Enter developer password:")
        if password != DEV_PASSWORD:
            messagebox.showerror("Error", "Invalid password")
            return
        
        self.logged_in_role = "developer"
        self._clear_window()
        
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header, text="⚙️ Developer Mode", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Logout", command=self._show_login_screen).pack(side="right")
        
        # Teacher GUI (original)
        try:
            teacher = teach_gui.MainWindow(self.root)
            teacher.pack(fill="both", expand=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load developer interface: {e}")
            self._show_login_screen()
    
    def _ask_password(self, title: str, prompt: str) -> str:
        """Ask for password"""
        from tkinter.simpledialog import askstring
        return askstring(title, prompt, show="*") or ""
    
    def _clear_window(self):
        """Clear all widgets from window"""
        for widget in self.root.winfo_children():
            widget.destroy()


# ========== ENTRY POINT ==========

def main():
    root = tk.Tk()
    app = AdvancedJuiceKiosk(root)
    root.mainloop()


if __name__ == "__main__":
    main()
