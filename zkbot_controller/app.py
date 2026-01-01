# app.py
#
# Unified kiosk app: owner login -> customer ordering -> developer settings.

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import threading
import time

from drink_runner import make_drink
import gui as teach_gui   # your existing teaching GUI (developer mode)


# ---------- Config ----------

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"  # put your juice pictures here

OWNER_PASSWORD = "0000"       # TODO: move to config file
DEV_PASSWORD = "0000"         # TODO: move to config file

DRINK_CATALOG = {
    "mango": {
        "label": "badham juice",
        "price": 80,        # just for UI
        "image": IMAGES_DIR / "badham.jpeg",   # or .jpg
    },
    "orange": {
        "label": "grape Juice",
        "price": 70,
        "image": IMAGES_DIR / "grape.jpeg",
    },
    "grape": {
        "label": "lemon Juice",
        "price": 75,
        "image": IMAGES_DIR / "lemon.jpeg",
    },
    "apple": {
        "label": " rose milk",
        "price": 85,
        "image": IMAGES_DIR / "rose.jpeg",
    },
}


# ---------- Utility ----------

def load_image(path: Path, size=(100, 100)):
    """Lazy import PIL only if images exist; fall back to text-only buttons."""
    try:
        from PIL import Image, ImageTk  # type: ignore
    except ImportError:
        return None

    if not path.exists():
        return None

    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


# ---------- Screens ----------

class OwnerLoginPage(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self._build()

    def _build(self):
        tk.Label(self, text="ZKBot Juice Station", font=("Arial", 20, "bold")).pack(pady=20)
        tk.Label(self, text="Owner password").pack(pady=(10, 5))

        self.entry = tk.Entry(self, show="*")
        self.entry.pack()
        self.entry.focus_set()

        tk.Button(self, text="Login", command=self._login).pack(pady=15)

    def _login(self):
        if self.entry.get() == OWNER_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access denied", "Incorrect owner password.")
            self.entry.delete(0, tk.END)


class CustomerPage(tk.Frame):
    def __init__(self, master, on_open_dev):
        super().__init__(master)
        self.on_open_dev = on_open_dev
        self.order = []          # list of juice keys
        self.images = {}
        self.is_running = False  # prevent concurrent orders
        self._build()

    def _build(self):
        # Top bar
        top = tk.Frame(self)
        top.pack(fill="x", pady=5)

        tk.Label(top, text="Select your drinks", font=("Arial", 16, "bold")).pack(side="left", padx=10)

        tk.Button(
            top,
            text="Settings / Developer",
            command=self.on_open_dev
        ).pack(side="right", padx=10)

        # Main area: left = drinks, right = cart
        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_drink_grid(main)
        self._build_cart(main)

    def _build_drink_grid(self, parent):
        frame = tk.Frame(parent)
        frame.pack(side="left", fill="both", expand=True)

        row = 0
        col = 0
        for key, info in DRINK_CATALOG.items():
            card = tk.Frame(frame, borderwidth=1, relief="solid", padx=5, pady=5)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # Load image if possible
            img = load_image(info["image"])
            if img is not None:
                self.images[key] = img    # keep reference
                tk.Label(card, image=img).pack()
            else:
                tk.Label(card, text=info["label"], font=("Arial", 12, "bold")).pack(pady=5)

            tk.Label(card, text=f"₹{info['price']}", font=("Arial", 11)).pack()

            tk.Button(
                card,
                text="Add",
                command=lambda k=key: self.add_to_order(k)
            ).pack(pady=(5, 0))

            col += 1
            if col >= 2:  # 2 columns; change to 3 if you want
                col = 0
                row += 1

    def _build_cart(self, parent):
        frame = tk.Frame(parent, borderwidth=1, relief="solid")
        frame.pack(side="right", fill="y")

        tk.Label(frame, text="Current order", font=("Arial", 14, "bold")).pack(pady=5)

        self.listbox = tk.Listbox(frame, width=25, height=12)
        self.listbox.pack(padx=5, pady=5)

        self.total_label = tk.Label(frame, text="Total: ₹0", font=("Arial", 12))
        self.total_label.pack(pady=(5, 10))

        tk.Button(frame, text="Clear order", command=self.clear_order).pack(pady=2)
        self.start_btn = tk.Button(frame, text="Start making", command=self.start_order)
        self.start_btn.pack(pady=5)

        self.status_var = tk.StringVar(value="Idle")
        tk.Label(frame, textvariable=self.status_var, wraplength=180, fg="green").pack(pady=(10, 5))

    # ----- Order management -----

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

    # ----- Running the order -----

    def start_order(self):
        if self.is_running:
            return
        if not self.order:
            messagebox.showinfo("No items", "Please add at least one drink.")
            return

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.status_var.set("Starting order...")

        # Run drinks in a background thread to keep GUI responsive
        t = threading.Thread(target=self._run_order_thread, daemon=True)
        t.start()

    def _run_order_thread(self):
        try:
            for i, juice_key in enumerate(self.order, start=1):
                info = DRINK_CATALOG.get(juice_key, {})
                name = info.get("label", juice_key)
                self._set_status(f"Making {i}/{len(self.order)}: {name}")
                make_drink(juice_key)  # blocking call

            self._set_status("Order complete. Enjoy your drinks!")
        except Exception as e:
            self._set_status(f"Error: {e}")
            messagebox.showerror("Error", f"Order failed:\n{e}")
        finally:
            self.is_running = False
            self.start_btn.config(state="normal")
            # Optional: auto-clear after completion
            # self.order.clear()
            # self._refresh_cart()

    def _set_status(self, text):
        # Called from worker thread using after()
        def _update():
            self.status_var.set(text)
        self.after(0, _update)


class DeveloperLoginPage(tk.Frame):
    def __init__(self, master, on_success, on_back):
        super().__init__(master)
        self.on_success = on_success
        self.on_back = on_back
        self._build()

    def _build(self):
        tk.Label(self, text="Developer access", font=("Arial", 18, "bold")).pack(pady=20)
        tk.Label(self, text="Password").pack(pady=(10, 5))

        self.entry = tk.Entry(self, show="*")
        self.entry.pack()
        self.entry.focus_set()

        btns = tk.Frame(self)
        btns.pack(pady=15)
        tk.Button(btns, text="Back", command=self.on_back).pack(side="left", padx=5)
        tk.Button(btns, text="Login", command=self._login).pack(side="left", padx=5)

    def _login(self):
        if self.entry.get() == DEV_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access denied", "Incorrect developer password.")
            self.entry.delete(0, tk.END)


class DeveloperPage(tk.Frame):
    def __init__(self, master, on_back):
        super().__init__(master)
        self.on_back = on_back
        self._build()

    def _build(self):
        tk.Label(self, text="Developer / Maintenance", font=("Arial", 18, "bold")).pack(pady=20)

        tk.Button(
            self,
            text="Open Teaching GUI (calibrate & record)",
            command=self._open_teach_gui
        ).pack(pady=5, padx=20, fill="x")

        tk.Button(
            self,
            text="Test Mango Recipe Once",
            command=lambda: self._test_drink("mango"),
        ).pack(pady=5, padx=20, fill="x")

        tk.Button(
            self,
            text="Test Orange Recipe Once",
            command=lambda: self._test_drink("orange"),
        ).pack(pady=5, padx=20, fill="x")

        tk.Button(
            self,
            text="Back to Customer Screen",
            command=self.on_back
        ).pack(pady=20)

        self.status = tk.StringVar(value="Idle")
        tk.Label(self, textvariable=self.status, fg="blue", wraplength=400).pack(pady=5)

    def _open_teach_gui(self):
        # Open your existing teaching GUI in a new window
        top = tk.Toplevel(self)
        top.title("Teaching / Calibration")
        teach_gui.main(top)  # assuming gui.py exposes a main(root) function

    def _test_drink(self, key):
        def worker():
            try:
                self._set_status(f"Running test drink: {key}")
                make_drink(key)
                self._set_status("Test complete.")
            except Exception as e:
                self._set_status(f"Error: {e}")
                messagebox.showerror("Error", str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, text):
        self.status.set(text)


# ---------- App wrapper ----------

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZKBot Juice Kiosk")
        self.geometry("800x500")

        self.container = tk.Frame(self)
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
        self._switch_to(CustomerPage, self.show_dev_login)

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
