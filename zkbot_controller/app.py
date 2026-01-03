# app.py
#
# Advanced Juice Kiosk - Professional UI with Order History & Developer Mode
# Features: Order management, order history database, professional theme, developer interface

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from drink_runner import make_drink
import gui as teach_gui


# ---------- Config ----------

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "kiosk.db"

OWNER_PASSWORD = "0000"
DEV_PASSWORD = "0000"

# Only juices with program files
DRINK_CATALOG = {
    "mango": {
        "label": "Badham Juice",
        "price": 80,
        "image": IMAGES_DIR / "badham.jpeg",
    },
    "orange": {
        "label": "Grape Juice",
        "price": 70,
        "image": IMAGES_DIR / "grape.jpeg",
    },
}

# Professional Theme (KFC/Domino's style)
THEME = {
    "bg": "#F5F7FB",
    "panel": "#FFFFFF",
    "text": "#111827",
    "muted": "#6B7280",
    "brand": "#E31B23",      # red (KFC vibe)
    "brand2": "#2563EB",     # blue accent
    "success": "#16A34A",
    "danger": "#DC2626",
    "border": "#E5E7EB",
}

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)


# ---------- Database ----------

class KioskDB:
    """SQLite database for order history"""
    def __init__(self, db_path="data/kiosk.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init()

    @contextmanager
    def conn(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init(self):
        with self.conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                customer_phone TEXT,
                items TEXT,
                total_price REAL,
                status TEXT,
                created_at TEXT,
                completed_at TEXT
            )
            """)

    def create_order(self, customer_name, customer_phone, items_dict, total_price):
        """items_dict = {juice_key: quantity}"""
        items_str = ", ".join([f"{DRINK_CATALOG[k]['label']} x{v}" for k, v in items_dict.items()])
        created_at = datetime.now().isoformat(timespec="seconds")
        
        with self.conn() as con:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO orders(customer_name, customer_phone, items, total_price, status, created_at)
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (customer_name or "Guest", customer_phone or "", items_str, total_price, "pending", created_at)
            )
            return cur.lastrowid

    def complete_order(self, order_id):
        completed_at = datetime.now().isoformat(timespec="seconds")
        with self.conn() as con:
            con.execute(
                "UPDATE orders SET status=?, completed_at=? WHERE id=?",
                ("completed", completed_at, order_id)
            )

    def get_recent_orders(self, limit=50):
        with self.conn() as con:
            rows = con.execute(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def fail_order(self, order_id, error_msg):
        with self.conn() as con:
            con.execute(
                "UPDATE orders SET status=? WHERE id=?",
                ("failed", order_id)
            )


# ---------- Utility ----------

def load_image(path: Path, size=(100, 100)):
    """Load image from path, return PhotoImage or None"""
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None

    if not path.exists():
        return None

    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


# ---------- UI Screens ----------

class OwnerLoginPage(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master, bg=THEME["bg"])
        self.on_success = on_success
        self._build()

    def _build(self):
        frame = tk.Frame(self, bg=THEME["bg"])
        frame.pack(fill="both", expand=True, padx=40, pady=60)

        tk.Label(frame, text="🍹 ZKBot Juice Kiosk", font=("Segoe UI", 28, "bold"),
                 bg=THEME["bg"], fg=THEME["brand"]).pack(pady=20)

        tk.Label(frame, text="Owner Access Required", font=FONT_TITLE,
                 bg=THEME["bg"], fg=THEME["text"]).pack(pady=20)

        tk.Label(frame, text="Enter Password:", font=FONT_BODY,
                 bg=THEME["bg"], fg=THEME["muted"]).pack(pady=(10, 5))

        self.entry = tk.Entry(frame, show="*", font=FONT_BODY, width=25)
        self.entry.pack(pady=10)
        self.entry.focus_set()

        tk.Button(frame, text="Login", command=self._login, font=FONT_BODY,
                  bg=THEME["brand"], fg="white", padx=40, pady=10, relief="flat").pack(pady=20)

    def _login(self):
        if self.entry.get() == OWNER_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access Denied", "Incorrect password")
            self.entry.delete(0, tk.END)


class CustomerPage(tk.Frame):
    def __init__(self, master, on_open_dev, db: KioskDB):
        super().__init__(master, bg=THEME["bg"])
        self.on_open_dev = on_open_dev
        self.db = db
        self.order = []          # list of juice keys
        self.order_id = None     # current order ID in DB
        self.images = {}
        self.is_running = False
        self._build()

    def _build(self):
        # Top bar
        top = tk.Frame(self, bg=THEME["brand"], height=70)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="🍹 ZKBot Juice Station", font=("Segoe UI", 18, "bold"),
                 bg=THEME["brand"], fg="white").pack(side="left", padx=18, pady=10)

        tk.Button(top, text="Order History", command=self._show_history,
                  bg="white", fg=THEME["brand"], relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="right", padx=8)

        tk.Button(top, text="Developer", command=self.on_open_dev,
                  bg="white", fg=THEME["brand"], relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="right", padx=8)

        # Main content
        main = tk.Frame(self, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=16, pady=16)

        left = tk.Frame(main, bg=THEME["bg"])
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(main, bg=THEME["panel"], width=380, 
                        highlightbackground=THEME["border"], highlightthickness=1)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        tk.Label(left, text="Tap a drink to add to cart", font=FONT_SMALL,
                 bg=THEME["bg"], fg=THEME["muted"]).pack(anchor="w", pady=(0, 12))

        self._build_drink_grid(left)
        self._build_cart(right)

    def _build_drink_grid(self, parent):
        grid = tk.Frame(parent, bg=THEME["bg"])
        grid.pack(fill="both", expand=True)

        row = col = 0
        for key, info in DRINK_CATALOG.items():
            card = tk.Frame(grid, bg=THEME["panel"], 
                           highlightbackground=THEME["border"], highlightthickness=1)
            card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")

            img = load_image(info["image"], size=(160, 160))
            if img is not None:
                self.images[key] = img
                tk.Label(card, image=img, bg=THEME["panel"]).pack(pady=(12, 6))
            else:
                tk.Label(card, text=info["label"], font=("Segoe UI", 11, "bold"),
                        bg=THEME["panel"]).pack(pady=30)

            tk.Label(card, text=info["label"], font=("Segoe UI", 11, "bold"),
                    bg=THEME["panel"], fg=THEME["text"]).pack()
            tk.Label(card, text=f"₹{info['price']}", font=("Segoe UI", 11, "bold"),
                    bg=THEME["panel"], fg=THEME["success"]).pack(pady=(2, 8))

            tk.Button(card, text="Add", command=lambda k=key: self.add_to_order(k),
                     bg=THEME["brand2"], fg="white", relief="flat",
                     font=("Segoe UI", 10, "bold"), padx=8, pady=6).pack(padx=10, pady=(0, 10), fill="x")

            col += 1
            if col >= 2:
                col = 0
                row += 1

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def _build_cart(self, parent):
        tk.Label(parent, text="Your Cart", font=("Segoe UI", 14, "bold"),
                bg=THEME["panel"], fg=THEME["text"]).pack(pady=(14, 6))

        self.listbox = tk.Listbox(parent, height=10, font=FONT_SMALL, bd=0,
                                 highlightthickness=1, highlightbackground=THEME["border"])
        self.listbox.pack(padx=12, pady=(0, 10), fill="x")

        # Customer details
        tk.Label(parent, text="Name:", bg=THEME["panel"], fg=THEME["muted"], 
                font=FONT_SMALL).pack(padx=12, anchor="w")
        self.name_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.name_var, font=FONT_BODY).pack(padx=12, pady=(0, 6), fill="x")

        tk.Label(parent, text="Phone (optional):", bg=THEME["panel"], fg=THEME["muted"], 
                font=FONT_SMALL).pack(padx=12, anchor="w")
        self.phone_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.phone_var, font=FONT_BODY).pack(padx=12, pady=(0, 6), fill="x")

        # Total
        self.total_label = tk.Label(parent, text="Total: ₹0", font=("Segoe UI", 13, "bold"),
                                   bg=THEME["panel"], fg=THEME["text"])
        self.total_label.pack(padx=12, anchor="w", pady=(0, 10))

        # Buttons
        tk.Button(parent, text="Clear order", command=self.clear_order,
                 bg=THEME["danger"], fg="white", relief="flat",
                 font=("Segoe UI", 11, "bold"), pady=10).pack(padx=12, pady=(0, 8), fill="x")

        self.start_btn = tk.Button(parent, text="Start making", command=self.start_order,
                                  bg=THEME["success"], fg="white", relief="flat",
                                  font=("Segoe UI", 12, "bold"), pady=12)
        self.start_btn.pack(padx=12, pady=(0, 10), fill="x")

        ttk.Separator(parent).pack(fill="x", padx=12, pady=10)

        self.status_var = tk.StringVar(value="Idle")
        tk.Label(parent, textvariable=self.status_var, bg=THEME["panel"], 
                fg=THEME["brand2"], font=("Segoe UI", 10), wraplength=340).pack(padx=12, anchor="w", pady=(0, 12))

    def add_to_order(self, juice_key: str):
        if self.is_running:
            return
        self.order.append(juice_key)
        self._refresh_cart()

    def clear_order(self):
        if self.is_running:
            return
        self.order.clear()
        self._refresh_cart()

    def _refresh_cart(self):
        self.listbox.delete(0, tk.END)
        total = 0
        for idx, key in enumerate(self.order, start=1):
            info = DRINK_CATALOG.get(key, {})
            label = info.get("label", key)
            price = info.get("price", 0)
            total += price
            self.listbox.insert(tk.END, f"{idx}. {label} (₹{price})")
        self.total_label.config(text=f"Total: ₹{total}")

    def start_order(self):
        if self.is_running:
            return
        if not self.order:
            messagebox.showinfo("No items", "Please add at least one drink.")
            return

        # Collect order items
        items_dict = {}
        for key in self.order:
            items_dict[key] = items_dict.get(key, 0) + 1

        total = sum(DRINK_CATALOG[k]["price"] * v for k, v in items_dict.items())
        name = self.name_var.get().strip() or "Guest"
        phone = self.phone_var.get().strip() or ""

        # Save to database
        self.order_id = self.db.create_order(name, phone, items_dict, total)

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.status_var.set("Starting order...")
        self._process_next_drink()

    def _process_next_drink(self):
        """Process drinks one by one on main thread"""
        if not self.order:
            # All done
            self.db.complete_order(self.order_id)
            self.is_running = False
            self.start_btn.config(state="normal")
            self.status_var.set("✓ Order complete!")
            self.order.clear()
            self._refresh_cart()
            messagebox.showinfo("Success", "Your order is ready. Enjoy!")
            return

        juice_key = self.order.pop(0)
        info = DRINK_CATALOG.get(juice_key, {})
        name = info.get("label", juice_key)

        self.status_var.set(f"Making: {name}...")

        try:
            make_drink(juice_key)  # Main thread call
            self.status_var.set(f"✓ {name}")
            self._refresh_cart()
            self.after(1000, self._process_next_drink)

        except Exception as e:
            self.db.fail_order(self.order_id, str(e))
            self.is_running = False
            self.start_btn.config(state="normal")
            self.status_var.set(f"❌ Error")
            messagebox.showerror("Robot Error", 
                f"Failed to make {name}:\n{e}\n\n" +
                "Check:\n1. Robot is powered ON\n2. USB connected\n3. COM port correct")

    def _show_history(self):
        """Show order history window"""
        history_window = tk.Toplevel(self)
        history_window.title("Order History")
        history_window.geometry("700x500")

        tk.Label(history_window, text="Recent Orders", font=FONT_TITLE).pack(pady=10)

        # Create treeview
        tree = ttk.Treeview(history_window, columns=("ID", "Name", "Items", "Total", "Status", "Time"), 
                           height=20)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("ID", anchor=tk.W, width=40)
        tree.column("Name", anchor=tk.W, width=100)
        tree.column("Items", anchor=tk.W, width=200)
        tree.column("Total", anchor=tk.W, width=60)
        tree.column("Status", anchor=tk.W, width=80)
        tree.column("Time", anchor=tk.W, width=120)

        tree.heading("#0", text="", anchor=tk.W)
        tree.heading("ID", text="ID", anchor=tk.W)
        tree.heading("Name", text="Customer", anchor=tk.W)
        tree.heading("Items", text="Items", anchor=tk.W)
        tree.heading("Total", text="Total", anchor=tk.W)
        tree.heading("Status", text="Status", anchor=tk.W)
        tree.heading("Time", text="Time", anchor=tk.W)

        # Populate data
        orders = self.db.get_recent_orders()
        for order in orders:
            status_icon = "✓" if order["status"] == "completed" else "⏳" if order["status"] == "pending" else "❌"
            tree.insert("", tk.END, values=(
                order["id"],
                order["customer_name"],
                order["items"],
                f"₹{order['total_price']}",
                f"{status_icon} {order['status']}",
                order["created_at"]
            ))


class DeveloperLoginPage(tk.Frame):
    def __init__(self, master, on_success, on_back):
        super().__init__(master, bg=THEME["bg"])
        self.on_success = on_success
        self.on_back = on_back
        self._build()

    def _build(self):
        frame = tk.Frame(self, bg=THEME["bg"])
        frame.pack(fill="both", expand=True, padx=40, pady=60)

        tk.Label(frame, text="Developer Access", font=("Segoe UI", 24, "bold"),
                bg=THEME["bg"], fg=THEME["brand"]).pack(pady=20)

        tk.Label(frame, text="Password:", font=FONT_BODY,
                bg=THEME["bg"], fg=THEME["text"]).pack(pady=10)

        self.entry = tk.Entry(frame, show="*", font=FONT_BODY, width=25)
        self.entry.pack(pady=10)
        self.entry.focus_set()

        btns = tk.Frame(frame, bg=THEME["bg"])
        btns.pack(pady=20)

        tk.Button(btns, text="Back", command=self.on_back, font=FONT_BODY,
                 bg=THEME["muted"], fg="white", padx=20, pady=8, relief="flat").pack(side="left", padx=5)
        tk.Button(btns, text="Login", command=self._login, font=FONT_BODY,
                 bg=THEME["brand"], fg="white", padx=20, pady=8, relief="flat").pack(side="left", padx=5)

    def _login(self):
        if self.entry.get() == DEV_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access Denied", "Incorrect password")
            self.entry.delete(0, tk.END)


class DeveloperPage(tk.Frame):
    def __init__(self, master, on_back):
        super().__init__(master, bg=THEME["bg"])
        self.on_back = on_back
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=THEME["brand"], height=70)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="⚙️ Developer / Maintenance", font=("Segoe UI", 18, "bold"),
                bg=THEME["brand"], fg="white").pack(side="left", padx=18, pady=10)

        tk.Button(top, text="Back", command=self.on_back, bg="white", 
                 fg=THEME["brand"], relief="flat", font=("Segoe UI", 10, "bold"), 
                 padx=14, pady=8).pack(side="right", padx=8)

        main = tk.Frame(self, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Button(main, text="📝 Open Teaching GUI (Calibrate & Record)", 
                 command=self._open_teach_gui, bg=THEME["panel"], fg=THEME["text"],
                 font=FONT_BODY, padx=20, pady=15, relief="solid", 
                 bd=1).pack(fill="x", pady=10)

        tk.Button(main, text="🧪 Test Mango Recipe", 
                 command=lambda: self._test_drink("mango"), bg=THEME["panel"], 
                 fg=THEME["text"], font=FONT_BODY, padx=20, pady=15, relief="solid", 
                 bd=1).pack(fill="x", pady=10)

        tk.Button(main, text="🧪 Test Orange Recipe", 
                 command=lambda: self._test_drink("orange"), bg=THEME["panel"], 
                 fg=THEME["text"], font=FONT_BODY, padx=20, pady=15, relief="solid", 
                 bd=1).pack(fill="x", pady=10)

        self.status_var = tk.StringVar(value="Idle")
        tk.Label(main, textvariable=self.status_var, font=FONT_BODY,
                bg=THEME["bg"], fg=THEME["brand2"], wraplength=500).pack(pady=20)

    def _open_teach_gui(self):
        top = tk.Toplevel(self)
        top.title("Teaching GUI")
        teach_gui.main(top)

    def _test_drink(self, key):
        try:
            self.status_var.set(f"Testing {key}... (DO NOT STOP)")
            self.update()
            make_drink(key)
            self.status_var.set(f"✓ Test complete: {key}")
        except Exception as e:
            self.status_var.set(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))


# ---------- Main App ----------

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🍹 ZKBot Juice Kiosk")
        self.geometry("1000x650")
        self.configure(bg=THEME["bg"])

        self.db = KioskDB(str(DB_PATH))

        self.container = tk.Frame(self, bg=THEME["bg"])
        self.container.pack(fill="both", expand=True)

        self.current_frame = None
        self.show_owner_login()

    def _switch_to(self, frame_class, *args, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self.container, *args, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

    def show_owner_login(self):
        self._switch_to(OwnerLoginPage, self.show_customer)

    def show_customer(self):
        self._switch_to(CustomerPage, self.show_dev_login, self.db)

    def show_dev_login(self):
        self._switch_to(DeveloperLoginPage, self.show_developer, self.show_customer)

    def show_developer(self):
        self._switch_to(DeveloperPage, self.show_customer)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
