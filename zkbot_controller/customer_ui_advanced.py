"""
Advanced Customer UI for Juice Kiosk
Modern ordering interface with cart, checkout, payment
Similar to KFC/Domino's ordering systems
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import threading

from order_models import Order, OrderItem, PaymentMethod, OrderStatus
from order_database import AdvancedKioskDB


class AdvancedCustomerUI:
    """Enhanced customer ordering interface"""
    
    def __init__(self, parent: tk.Widget, db: AdvancedKioskDB, images_dir: Path):
        self.frame = ttk.Frame(parent)
        self.db = db
        self.images_dir = Path(images_dir)
        
        # Current state
        self.current_customer_id: Optional[int] = None
        self.cart: List[OrderItem] = []
        self.products = db.get_all_products()
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the complete ordering interface"""
        # Header with login
        header = ttk.Frame(self.frame)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header, text="🍹 JUICE KIOSK", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Login/Register", command=self._show_customer_login).pack(side="right")
        self.customer_label = ttk.Label(header, text="Guest", font=("Arial", 10))
        self.customer_label.pack(side="right", padx=10)
        
        # Main container
        main = ttk.Frame(self.frame)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Products panel (left)
        self._build_products_panel(main)
        
        # Cart panel (right)
        self._build_cart_panel(main)
    
    def _build_products_panel(self, parent):
        """Product grid display"""
        panel = ttk.LabelFrame(parent, text="Our Juices", padding=10)
        panel.pack(side="left", fill="both", expand=True, padx=5)
        
        # Category buttons
        categories = set(p.get('category', 'Custom') for p in self.products)
        cat_frame = ttk.Frame(panel)
        cat_frame.pack(fill="x", pady=10)
        
        ttk.Button(cat_frame, text="All", command=lambda: self._show_products()).pack(side="left", padx=2)
        for cat in sorted(categories):
            ttk.Button(cat_frame, text=cat, command=lambda c=cat: self._show_products(c)).pack(side="left", padx=2)
        
        # Product grid
        self.products_frame = ttk.Frame(panel)
        self.products_frame.pack(fill="both", expand=True)
        self._show_products()
    
    def _show_products(self, category: Optional[str] = None):
        """Display products in grid"""
        for widget in self.products_frame.winfo_children():
            widget.destroy()
        
        products = [p for p in self.products if category is None or p['category'] == category]
        
        # 2x2 grid
        for idx, prod in enumerate(products):
            row, col = divmod(idx, 2)
            card = self._create_product_card(self.products_frame, prod)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
    
    def _create_product_card(self, parent, product: Dict) -> ttk.Frame:
        """Create a product card widget"""
        card = ttk.LabelFrame(parent, text=product['name'], padding=10)
        
        # Image placeholder
        img_label = ttk.Label(card, text="🥤", font=("Arial", 32))
        img_label.pack(pady=10)
        
        # Price
        ttk.Label(card, text=f"${product['price']:.2f}", font=("Arial", 14, "bold")).pack()
        
        # Description
        if product.get('description'):
            ttk.Label(card, text=product['description'], wraplength=150, justify="center").pack()
        
        # Quantity selector
        qty_frame = ttk.Frame(card)
        qty_frame.pack(pady=10)
        ttk.Label(qty_frame, text="Qty:").pack(side="left")
        qty_var = tk.IntVar(value=1)
        ttk.Spinbox(qty_frame, from_=1, to=10, textvariable=qty_var, width=3).pack(side="left")
        
        # Add to cart button
        ttk.Button(
            card, 
            text="Add to Cart", 
            command=lambda: self._add_to_cart(product, qty_var.get())
        ).pack(fill="x", pady=5)
        
        return card
    
    def _add_to_cart(self, product: Dict, quantity: int):
        """Add item to cart"""
        if quantity <= 0:
            messagebox.showerror("Invalid", "Quantity must be > 0")
            return
        
        item = OrderItem(
            product_id=product['id'],
            product_name=product['name'],
            quantity=quantity,
            price_per_unit=product['price']
        )
        self.cart.append(item)
        self._update_cart_display()
        messagebox.showinfo("Success", f"Added {quantity}x {product['name']} to cart")
    
    def _build_cart_panel(self, parent):
        """Shopping cart display and checkout"""
        panel = ttk.LabelFrame(parent, text="🛒 Your Order", padding=10)
        panel.pack(side="right", fill="both", padx=5, ipadx=10)
        
        # Cart items
        self.cart_display = tk.Text(panel, height=12, width=30, state="disabled")
        self.cart_display.pack(fill="both", expand=True, pady=5)
        
        # Totals
        totals = ttk.Frame(panel)
        totals.pack(fill="x", pady=10)
        
        ttk.Label(totals, text="Subtotal:", font=("Arial", 10)).pack(anchor="e")
        self.subtotal_label = ttk.Label(totals, text="$0.00", font=("Arial", 11, "bold"))
        self.subtotal_label.pack(anchor="e")
        
        ttk.Label(totals, text="Total:", font=("Arial", 12, "bold")).pack(anchor="e")
        self.total_label = ttk.Label(totals, text="$0.00", font=("Arial", 14, "bold"))
        self.total_label.pack(anchor="e")
        
        # Action buttons
        btn_frame = ttk.Frame(panel)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="Clear Cart", command=self._clear_cart).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Checkout", command=self._checkout).pack(fill="x", pady=2)
    
    def _update_cart_display(self):
        """Update cart display"""
        self.cart_display.config(state="normal")
        self.cart_display.delete("1.0", "end")
        
        for item in self.cart:
            text = f"{item.quantity}x {item.product_name}\n  ${item.total_price:.2f}\n"
            self.cart_display.insert("end", text)
        
        self.cart_display.config(state="disabled")
        
        # Update totals
        subtotal = sum(item.total_price for item in self.cart)
        self.subtotal_label.config(text=f"${subtotal:.2f}")
        self.total_label.config(text=f"${subtotal:.2f}")
    
    def _clear_cart(self):
        """Clear shopping cart"""
        if messagebox.askyesno("Confirm", "Clear cart?"):
            self.cart = []
            self._update_cart_display()
    
    def _checkout(self):
        """Proceed to checkout"""
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add items first!")
            return
        
        # Create order
        items_data = [(item.product_id, item.product_name, item.quantity, item.price_per_unit) 
                     for item in self.cart]
        total = sum(item.total_price for item in self.cart)
        
        order_id = self.db.create_order(self.current_customer_id, items_data, total, "cash")
        self.db.update_order_status(order_id, "confirmed")
        
        messagebox.showinfo(
            "Order Placed!", 
            f"Order #{order_id}\nTotal: ${total:.2f}\nEstimated time: 5 min"
        )
        
        self.cart = []
        self._update_cart_display()
    
    def _show_customer_login(self):
        """Show login/register dialog"""
        dialog = tk.Toplevel()
        dialog.title("Login / Register")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Phone Number:", font=("Arial", 10)).pack(pady=5)
        phone_entry = ttk.Entry(dialog, width=30)
        phone_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Name (Optional):", font=("Arial", 10)).pack(pady=5)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Email (Optional):", font=("Arial", 10)).pack(pady=5)
        email_entry = ttk.Entry(dialog, width=30)
        email_entry.pack(pady=5)
        
        def login():
            phone = phone_entry.get().strip()
            if not phone:
                messagebox.showerror("Error", "Phone required!")
                return
            
            name = name_entry.get().strip()
            email = email_entry.get().strip()
            
            self.current_customer_id = self.db.get_or_create_customer(phone, name, email)
            customer = self.db.get_customer(self.current_customer_id)
            
            self.customer_label.config(text=f"👤 {customer['name'] or phone}")
            dialog.destroy()
            messagebox.showinfo("Success", f"Welcome back, {customer['name'] or 'Guest'}!")
        
        ttk.Button(dialog, text="Login", command=login).pack(pady=20)
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
