# app.py
#
# Unified kiosk app: owner login -> customer ordering -> developer settings.
# Upgraded: professional UI theme + bigger images + SQLite DB + active-order queue display
# Note: This is still your same screen flow and class layout.

import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from tkinter import simpledialog
from pathlib import Path
import threading
import time
from datetime import datetime
import sqlite3
from contextlib import contextmanager
import csv

from drink_runner import make_drink
import gui as teach_gui   # your existing teaching GUI (developer mode)

import sqlite3
from contextlib import contextmanager
from datetime import datetime

# Debug mode - set to True if robot not connected
DEBUG_MODE = False  # Change to True to simulate robot movements

class KioskDB:
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
                drink_key TEXT NOT NULL,
                drink_label TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT
            )
            """)

    def create_order(self, drink_key, drink_label, price):
        now = datetime.now().isoformat(timespec="seconds")
        with self.conn() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO orders(drink_key, drink_label, price, status, created_at) VALUES(?,?,?,?,?)",
                (drink_key, drink_label, float(price), "pending", now),
            )
            return cur.lastrowid

    def set_status(self, order_id, status, error_message=None):
        now = datetime.now().isoformat(timespec="seconds")
        with self.conn() as con:
            if status == "in_progress":
                con.execute("UPDATE orders SET status=?, started_at=? WHERE id=?", (status, now, order_id))
            elif status in ("completed", "failed"):
                con.execute(
                    "UPDATE orders SET status=?, completed_at=?, error_message=? WHERE id=?",
                    (status, now, error_message, order_id),
                )
            else:
                con.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))

    def fetch_recent(self, limit=200):
        with self.conn() as con:
            rows = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

# ---------- Config ----------

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"  # put your juice pictures here
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "kiosk.db"

OWNER_PASSWORD = "0000"     # TODO: move to config file
DEV_PASSWORD = "0000"       # TODO: move to config file

# IMPORTANT:

# - "key" is what your UI uses
# - "runner_key" is what make_drink(...) receives
# If your robot programs use different names, set runner_key accordingly.
DRINK_CATALOG = {
    "mango": {
        "label": "Mango Juice",
        "price": 80,
        "image": IMAGES_DIR / "badham.jpeg",
        "runner_key": "mango",
    },
    "orange": {
        "label": "Orange Juice",
        "price": 70,
        "image": IMAGES_DIR / "grape.jpeg",
        "runner_key": "orange",
    },
}


# ---------- Theme (Professional) ----------

THEME = {
    "bg": "#F5F7FB",
    "panel": "#FFFFFF",
    "text": "#111827",
    "muted": "#6B7280",
    "brand": "#E31B23",      # red-ish (Dominos/KFC vibe)
    "brand2": "#2563EB",     # blue accent
    "success": "#16A34A",
    "danger": "#DC2626",
    "border": "#E5E7EB",
}

FONT_H1 = ("Segoe UI", 20, "bold")
FONT_H2 = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)


# ---------- Database ----------

class KioskDB:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT,
                    drink_key TEXT NOT NULL,
                    drink_label TEXT NOT NULL,
                    price REAL NOT NULL,
                    customer_id INTEGER,
                    instructions TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    phone TEXT UNIQUE,
                    created_at TEXT NOT NULL
                )
            """)

    def log(self, level: str, message: str):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO logs(ts, level, message) VALUES (?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), level, message),
            )

    def create_order(self, batch_id: str, drink_key: str, drink_label: str, price: float, customer_id: int = None, instructions: str = None) -> int:
        # Create order record; keep backwards compatibility when batch_id omitted
        if batch_id is None:
            batch_id = ""
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO orders(batch_id, drink_key, drink_label, price, customer_id, instructions, status, created_at)
                   VALUES(?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (batch_id, drink_key, drink_label, price, customer_id, instructions, now),
            )
            return cur.lastrowid

    def create_or_get_customer(self, phone: str, name: str = None) -> int:
        """Create a new customer by phone or return existing id."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT id FROM customers WHERE phone=?", (phone,)).fetchone()
            if row:
                return row[0]
            cur.execute("INSERT INTO customers(name, phone, created_at) VALUES(?,?,?)", (name, phone, now))
            return cur.lastrowid

    def set_status_in_progress(self, order_id: int):
        with self.connect() as conn:
            conn.execute(
                "UPDATE orders SET status='in_progress', started_at=? WHERE id=?",
                (datetime.now().isoformat(timespec="seconds"), order_id),
            )

    def set_status_completed(self, order_id: int):
        with self.connect() as conn:
            conn.execute(
                "UPDATE orders SET status='completed', completed_at=? WHERE id=?",
                (datetime.now().isoformat(timespec="seconds"), order_id),
            )

    def set_status_failed(self, order_id: int, error_message: str):
        with self.connect() as conn:
            conn.execute(
                "UPDATE orders SET status='failed', completed_at=?, error_message=? WHERE id=?",
                (datetime.now().isoformat(timespec="seconds"), error_message, order_id),
            )

    def fetch_orders(self, limit: int = 200):
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT o.*, c.name as customer_name, c.phone as customer_phone
                   FROM orders o
                   LEFT JOIN customers c ON o.customer_id = c.id
                   ORDER BY o.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def fetch_active_orders(self):
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM orders
                   WHERE status IN ('pending','in_progress')
                   ORDER BY id ASC"""
            ).fetchall()
            return [dict(r) for r in rows]


# ---------- Utility ----------

def load_image(path: Path, size=(240, 240)):  # BIGGER
    try:
        from PIL import Image, ImageTk  # type: ignore
    except ImportError:
        return None
    if not path.exists():
        return None
    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

def money(x: float) -> str:
    return f"₹{int(x)}"


# ---------- Screens ----------

class OwnerLoginPage(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master, bg=THEME["bg"])
        self.on_success = on_success
        self._build()

    def _build(self):
        wrapper = tk.Frame(self, bg=THEME["bg"])
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrapper, text="ZKBot Juice Station", font=FONT_H1, bg=THEME["bg"], fg=THEME["text"]).pack(pady=(0, 8))
        tk.Label(wrapper, text="Owner Login", font=FONT_BODY, bg=THEME["bg"], fg=THEME["muted"]).pack(pady=(0, 24))

        card = tk.Frame(wrapper, bg=THEME["panel"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(padx=20, pady=10)

        tk.Label(card, text="Enter owner password", font=FONT_BODY, bg=THEME["panel"], fg=THEME["text"]).pack(pady=(18, 8), padx=24)

        self.entry = tk.Entry(card, show="•", font=("Segoe UI", 13), width=22, relief="solid", bd=1)
        self.entry.pack(pady=(0, 14), padx=24)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._login())

        tk.Button(
            card, text="Login", command=self._login,
            bg=THEME["brand"], fg="white", font=FONT_H2,
            relief="flat", padx=30, pady=10, cursor="hand2",
            activebackground=THEME["brand"]
        ).pack(pady=(0, 18), padx=24, fill="x")

    def _login(self):
        if self.entry.get() == OWNER_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access denied", "Incorrect owner password.")
            self.entry.delete(0, tk.END)


class CustomerPage(tk.Frame):
    def __init__(self, master, on_open_dev, db: KioskDB):
        super().__init__(master, bg="#F5F7FB")
        self.on_open_dev = on_open_dev
        self.db = db

        self.order = []          # cart drink keys
        self.active_orders = []  # list of dicts: {id, key, label}
        self.images = {}
        self.is_running = False

        self._build()

    def _build(self):
        # Top bar (professional)
        top = tk.Frame(self, bg="#E31B23", height=70)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="ZKBot Juice Station", font=("Segoe UI", 18, "bold"),
                 bg="#E31B23", fg="white").pack(side="left", padx=18)

        tk.Button(top, text="Order History", command=self._show_history,
                  bg="white", fg="#E31B23", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="right", padx=12)

        tk.Button(top, text="Developer", command=self.on_open_dev,
                  bg="white", fg="#E31B23", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="right", padx=12)

        # Main split
        main = tk.Frame(self, bg="#F5F7FB")
        main.pack(fill="both", expand=True, padx=16, pady=16)

        left = tk.Frame(main, bg="#F5F7FB")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(main, bg="white", width=380, highlightbackground="#E5E7EB", highlightthickness=1)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        tk.Label(left, text="Tap a drink to add to cart", font=("Segoe UI", 11),
                 bg="#F5F7FB", fg="#6B7280").pack(anchor="w", pady=(0, 12))

        self._build_drink_grid(left)
        self._build_cart(right)

        self._refresh_cart()
        self._refresh_active_list_loop()

    def _build_drink_grid(self, parent):
        grid = tk.Frame(parent, bg="#F5F7FB")
        grid.pack(fill="both", expand=True)

        row = col = 0
        for key, info in DRINK_CATALOG.items():
            card = tk.Frame(grid, bg="white", highlightbackground="#E5E7EB", highlightthickness=1)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            img = load_image(info["image"], size=(160, 160))
            if img is not None:
                self.images[key] = img
                tk.Label(card, image=img, bg="white").pack(pady=(10, 4))
            else:
                tk.Label(card, text=info["label"], font=("Segoe UI", 12, "bold"), bg="white").pack(pady=20)

            tk.Label(card, text=info["label"], font=("Segoe UI", 11, "bold"), bg="white", fg="#111827").pack()
            tk.Label(card, text=f"₹{info['price']}", font=("Segoe UI", 11, "bold"), bg="white", fg="#16A34A").pack(pady=(1, 8))

            tk.Button(card, text="Add",
                      command=lambda k=key: self.add_to_order(k),
                      bg="#2563EB", fg="white", relief="flat",
                      font=("Segoe UI", 10, "bold"), padx=8, pady=6).pack(padx=10, pady=(0, 10), fill="x")

            col += 1
            if col >= 2:
                col = 0
                row += 1

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def _build_cart(self, parent):
        tk.Label(parent, text="Your Cart", font=("Segoe UI", 14, "bold"), bg="white", fg="#111827").pack(pady=(14, 6))

        self.listbox = tk.Listbox(parent, height=10, font=("Segoe UI", 11), bd=0,
                      highlightthickness=1, highlightbackground="#E5E7EB")
        self.listbox.pack(padx=12, pady=(0, 10), fill="x")

        # --- Customer details ---
        tk.Label(parent, text="Name:", bg="white", fg="#6B7280", font=FONT_SMALL).pack(padx=12, anchor="w")
        self.name_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.name_var, font=FONT_BODY).pack(padx=12, pady=(0,6), fill="x")

        tk.Label(parent, text="Phone (optional):", bg="white", fg="#6B7280", font=FONT_SMALL).pack(padx=12, anchor="w")
        self.phone_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.phone_var, font=FONT_BODY).pack(padx=12, pady=(0,6), fill="x")

        tk.Label(parent, text="Instructions:", bg="white", fg="#6B7280", font=FONT_SMALL).pack(padx=12, anchor="w")
        self.instr_var = tk.StringVar()
        tk.Entry(parent, textvariable=self.instr_var, font=FONT_BODY).pack(padx=12, pady=(0,8), fill="x")

        self.total_label = tk.Label(parent, text="Total: ₹0", font=("Segoe UI", 13, "bold"),
                        bg="white", fg="#111827")
        self.total_label.pack(padx=12, anchor="w", pady=(0, 10))

        tk.Button(parent, text="Clear order", command=self.clear_order,
                  bg="#DC2626", fg="white", relief="flat",
                  font=("Segoe UI", 11, "bold"), pady=10).pack(padx=12, pady=(0, 8), fill="x")

        self.start_btn = tk.Button(parent, text="Start making", command=self.start_order,
                                   bg="#16A34A", fg="white", relief="flat",
                                   font=("Segoe UI", 12, "bold"), pady=12)
        self.start_btn.pack(padx=12, pady=(0, 10), fill="x")

        ttk.Separator(parent).pack(fill="x", padx=12, pady=10)

        tk.Label(parent, text="Active Orders (auto-clears when done)", font=("Segoe UI", 10),
                 bg="white", fg="#6B7280").pack(padx=12, anchor="w")

        self.active_box = tk.Listbox(parent, height=7, font=("Segoe UI", 10), bd=0,
                                     highlightthickness=1, highlightbackground="#E5E7EB")
        self.active_box.pack(padx=12, pady=(6, 10), fill="both", expand=True)

        self.status_var = tk.StringVar(value="Idle")
        tk.Label(parent, textvariable=self.status_var, bg="white", fg="#2563EB",
                 font=("Segoe UI", 10), wraplength=340).pack(padx=12, anchor="w", pady=(0, 12))

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
        # collect customer data
        name = (self.name_var.get() or "").strip()
        phone = (self.phone_var.get() or "").strip()
        instr = (self.instr_var.get() or "").strip()

        customer_id = None
        if phone:
            try:
                customer_id = self.db.create_or_get_customer(phone, name)
            except Exception:
                customer_id = None

        # create a batch id for this group of orders
        batch_id = datetime.now().strftime("%Y%m%d%H%M%S")

        created_ids = []
        for juice_key in self.order:
            info = DRINK_CATALOG[juice_key]
            order_id = self.db.create_order(batch_id, juice_key, info["label"], info["price"], customer_id, instr)
            self.active_orders.append({"id": order_id, "key": juice_key, "label": info["label"]})
            created_ids.append(order_id)

        # clear the UI cart but keep customer info
        self.order.clear()
        self._refresh_cart()

        if not self.is_running:
            self.is_running = True
            self.start_btn.config(state="disabled")
            threading.Thread(target=self._run_active_queue_thread, daemon=True).start()

        message = f"Orders added: {', '.join('#'+str(i) for i in created_ids)}"
        if phone:
            message += f"\nCustomer: {name} ({phone})"
        if instr:
            message += f"\nInstructions: {instr}"
        messagebox.showinfo("Order Placed", message)

    def _run_active_queue_thread(self):
        try:
            while self.active_orders:
                current = self.active_orders[0]
                oid = current["id"]
                label = current["label"]
                runner_key = DRINK_CATALOG[current["key"]].get("runner_key", current["key"])

                self._set_status(f"Making #{oid}: {label}")
                self.db.set_status(oid, "in_progress")

                try:
                    if DEBUG_MODE:
                        # Simulate robot movement in debug mode
                        self._set_status(f"[DEBUG] Simulating #{oid}: {label}")
                        time.sleep(2)
                    else:
                        make_drink(runner_key)  # blocking
                    
                    self.db.set_status(oid, "completed")
                    self._set_status(f"✓ Completed #{oid}: {label}")
                except FileNotFoundError as fnf_error:
                    error_msg = f"Program file not found: {str(fnf_error)}"
                    self._set_status(error_msg)
                    self.db.set_status(oid, "failed", error_msg)
                    self.after(0, lambda em=error_msg: messagebox.showerror("File Error", em))
                except Exception as drink_error:
                    error_msg = f"Robot error: {str(drink_error)}\n\nMake sure:\n1. Robot is powered ON\n2. COM3 port is correct\n3. USB cable is connected"
                    self._set_status(error_msg)
                    self.db.set_status(oid, "failed", str(drink_error))
                    self.after(0, lambda em=error_msg: messagebox.showerror("Drink Error", em))
                
                self.active_orders.pop(0)
                time.sleep(1)

        except Exception as e:
            error_msg = f"Queue error: {str(e)}"
            if self.active_orders:
                fail = self.active_orders.pop(0)
                self.db.set_status(fail["id"], "failed", error_msg)
            self._set_status(error_msg)
            self.after(0, lambda em=error_msg: messagebox.showerror("Error", em))
        finally:
            self.is_running = False
            self.after(0, lambda: self.start_btn.config(state="normal"))
            self._set_status("Idle")

    def _set_status(self, text):
        # Thread-safe UI update via after() [web:36]
        self.after(0, lambda: self.status_var.set(text))

    def _refresh_active_list_loop(self):
        self.active_box.delete(0, tk.END)
        if not self.active_orders:
            self.active_box.insert(tk.END, "No active orders.")
        else:
            for i, o in enumerate(self.active_orders, start=1):
                tag = "NOW" if i == 1 and self.is_running else "NEXT"
                self.active_box.insert(tk.END, f"{tag}  #{o['id']}  {o['label']}")
        self.after(500, self._refresh_active_list_loop)

    def _show_history(self):
        rows = self.db.fetch_recent(limit=200)

        win = tk.Toplevel(self)
        win.title("Order History")
        win.geometry("900x500")
        # Filter area
        filter_frame = tk.Frame(win)
        filter_frame.pack(fill="x", padx=8, pady=6)

        tk.Label(filter_frame, text="Filter by phone:").pack(side="left", padx=(6,4))
        phone_var = tk.StringVar()
        tk.Entry(filter_frame, textvariable=phone_var, width=18).pack(side="left")

        def reload_tree():
            for i in tree.get_children():
                tree.delete(i)
            all_rows = self.db.fetch_recent(limit=2000)
            phone = (phone_var.get() or "").strip()
            if phone:
                all_rows = [r for r in all_rows if (r.get("customer_phone") or "") == phone]
            for r in all_rows:
                tree.insert("", "end", values=(
                    r["id"], r.get("customer_name") or "", r.get("customer_phone") or "",
                    r["drink_label"], r["price"], r["status"],
                    r["created_at"], r.get("started_at") or "", r.get("completed_at") or ""
                ))

        tk.Button(filter_frame, text="Filter", command=reload_tree).pack(side="left", padx=6)
        tk.Button(filter_frame, text="Clear", command=lambda: (phone_var.set(""), reload_tree())).pack(side="left")

        cols = ("id", "customer", "phone", "drink_label", "price", "status", "created_at", "started_at", "completed_at")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="w")
        tree.column("drink_label", width=220)
        tree.pack(fill="both", expand=True)

        reload_tree()

        def export_csv():
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id","drink_key","drink_label","price","status","created_at","started_at","completed_at","error_message"])
                for r in self.db.fetch_recent(limit=5000):
                    w.writerow([
                        r["id"], r["drink_key"], r["drink_label"], r["price"], r["status"],
                        r["created_at"], r.get("started_at"), r.get("completed_at"), r.get("error_message")
                    ])
            messagebox.showinfo("Exported", path)

        tk.Button(win, text="Export CSV", command=export_csv).pack(pady=8)

class HistoryWindow(tk.Toplevel):
    def __init__(self, parent, db: KioskDB):
        super().__init__(parent)
        self.db = db
        self.title("Order History")
        self.geometry("900x520")
        self.configure(bg=THEME["bg"])
        self._build()
        self._load()

    def _build(self):
        header = tk.Frame(self, bg=THEME["brand2"], height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="Order History", font=FONT_H2, bg=THEME["brand2"], fg="white").pack(side="left", padx=14)

        tk.Button(
            header, text="Export CSV", command=self._export_csv,
            bg="white", fg=THEME["brand2"], font=FONT_SMALL,
            relief="flat", padx=12, pady=6, cursor="hand2"
        ).pack(side="right", padx=12)

        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=12)

        cols = ("id", "batch_id", "drink_label", "price", "status", "created_at", "started_at", "completed_at")
        self.tree = ttk.Treeview(body, columns=cols, show="headings", height=16)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor="w")
        self.tree.column("drink_label", width=220)
        self.tree.column("created_at", width=160)
        self.tree.column("started_at", width=160)
        self.tree.column("completed_at", width=160)

        vs = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

    def _load(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        rows = self.db.fetch_orders(limit=500)
        for r in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r.get("batch_id", ""),
                    r["drink_label"],
                    money(float(r["price"])),
                    r["status"],
                    r["created_at"],
                    r.get("started_at") or "",
                    r.get("completed_at") or "",
                ),
            )

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not path:
            return

        rows = self.db.fetch_orders(limit=5000)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "batch_id", "drink_key", "drink_label", "price", "status", "created_at", "started_at", "completed_at", "error_message"])
            for r in rows:
                w.writerow([
                    r["id"],
                    r.get("batch_id", ""),
                    r.get("drink_key", ""),
                    r.get("drink_label", ""),
                    r.get("price", ""),
                    r.get("status", ""),
                    r.get("created_at", ""),
                    r.get("started_at", ""),
                    r.get("completed_at", ""),
                    r.get("error_message", ""),
                ])

        messagebox.showinfo("Exported", f"Saved:\n{path}")


class DeveloperLoginPage(tk.Frame):
    def __init__(self, master, on_success, on_back):
        super().__init__(master, bg=THEME["bg"])
        self.on_success = on_success
        self.on_back = on_back
        self._build()

    def _build(self):
        wrapper = tk.Frame(self, bg=THEME["bg"])
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrapper, text="Developer access", font=FONT_H1, bg=THEME["bg"], fg=THEME["text"]).pack(pady=(0, 10))
        tk.Label(wrapper, text="Password required", font=FONT_BODY, bg=THEME["bg"], fg=THEME["muted"]).pack(pady=(0, 20))

        card = tk.Frame(wrapper, bg=THEME["panel"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack()

        tk.Label(card, text="Developer password", font=FONT_BODY, bg=THEME["panel"], fg=THEME["text"]).pack(pady=(16, 6), padx=20)

        self.entry = tk.Entry(card, show="•", font=("Segoe UI", 13), width=22, relief="solid", bd=1)
        self.entry.pack(pady=(0, 12), padx=20)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._login())

        btns = tk.Frame(card, bg=THEME["panel"])
        btns.pack(pady=(0, 16), padx=20, fill="x")

        tk.Button(btns, text="Back", command=self.on_back, bg=THEME["border"], fg=THEME["text"],
                  font=FONT_BODY, relief="flat", padx=12, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(btns, text="Login", command=self._login, bg=THEME["brand2"], fg="white",
                  font=FONT_BODY, relief="flat", padx=12, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _login(self):
        if self.entry.get() == DEV_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access denied", "Incorrect developer password.")
            self.entry.delete(0, tk.END)


class DeveloperPage(tk.Frame):
    def __init__(self, master, on_back):
        super().__init__(master, bg=THEME["bg"])
        self.on_back = on_back
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=THEME["text"], height=64)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="Developer / Maintenance", font=FONT_H2, bg=THEME["text"], fg="white").pack(side="left", padx=18)
        tk.Button(top, text="Back", command=self.on_back, bg="white", fg=THEME["text"],
                  font=FONT_SMALL, relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=12)

        content = tk.Frame(self, bg=THEME["bg"])
        content.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(content, text="Tools", font=FONT_H2, bg=THEME["bg"], fg=THEME["text"]).pack(anchor="w", pady=(0, 10))

        self.status = tk.StringVar(value="Idle")
        tk.Label(content, textvariable=self.status, font=FONT_SMALL, bg=THEME["bg"], fg=THEME["muted"]).pack(anchor="w", pady=(0, 10))

        def tool_button(text, cmd):
            return tk.Button(content, text=text, command=cmd, bg=THEME["panel"], fg=THEME["text"],
                             font=FONT_BODY, relief="flat", padx=14, pady=12, cursor="hand2",
                             highlightbackground=THEME["border"], highlightthickness=1)

        tool_button("Open Teaching GUI (calibrate & record)", self._open_teach_gui).pack(fill="x", pady=6)
        tool_button("Test Mango Recipe Once", lambda: self._test_drink("mango")).pack(fill="x", pady=6)
        tool_button("Test Orange Recipe Once", lambda: self._test_drink("orange")).pack(fill="x", pady=6)
        tool_button("Test Grape Recipe Once", lambda: self._test_drink("grape")).pack(fill="x", pady=6)
        tool_button("Test Apple Recipe Once", lambda: self._test_drink("apple")).pack(fill="x", pady=6)

    def _open_teach_gui(self):
        top = tk.Toplevel(self)
        top.title("Teaching / Calibration")
        top.geometry("1100x700")

        # Works with either gui.main(root) OR gui.MainWindow(master=root)
        if hasattr(teach_gui, "main") and callable(getattr(teach_gui, "main")):
            teach_gui.main(top)
        elif hasattr(teach_gui, "MainWindow"):
            teach_gui.MainWindow(master=top)
        else:
            messagebox.showerror("Developer tool", "gui.py doesn't expose main(...) or MainWindow.")
            top.destroy()

    def _test_drink(self, key):
        def worker():
            try:
                self._set_status(f"Testing: {key}")
                make_drink(DRINK_CATALOG[key].get("runner_key", key))
                self._set_status("Test complete.")
            except Exception as e:
                self._set_status(f"Error: {e}")
                messagebox.showerror("Error", str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, text):
        self.after(0, lambda: self.status.set(text))


# ---------- App wrapper ----------

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZKBot Juice Kiosk")
        self.geometry("1300x820")
        self.configure(bg=THEME["bg"])

        DATA_DIR.mkdir(exist_ok=True)

        self.db = KioskDB(DB_PATH)

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
        self._switch_to(
            DeveloperLoginPage,
            self.show_developer,
            self.show_customer,
        )

    def show_developer(self):
        self._switch_to(DeveloperPage, self.show_customer)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
