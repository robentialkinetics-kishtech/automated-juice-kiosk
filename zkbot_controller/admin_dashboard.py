"""
Admin Dashboard for Order Management and Analytics
View order history, customer details, analytics
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from order_database import AdvancedKioskDB


class AdminDashboard:
    """Admin panel for viewing orders, customers, and analytics"""
    
    def __init__(self, parent: tk.Widget, db: AdvancedKioskDB):
        self.frame = ttk.Frame(parent)
        self.db = db
        
        self._build_ui()
        self._refresh_data()
    
    def _build_ui(self):
        """Build admin dashboard"""
        # Notebook with tabs
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Orders
        self._build_orders_tab(notebook)
        
        # Tab 2: Customers
        self._build_customers_tab(notebook)
        
        # Tab 3: Analytics
        self._build_analytics_tab(notebook)
        
        # Refresh button
        ttk.Button(self.frame, text="🔄 Refresh All", command=self._refresh_data).pack(pady=10)
    
    def _build_orders_tab(self, notebook):
        """Orders management tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📦 Orders")
        
        # Filter frame
        filter_frame = ttk.LabelFrame(tab, text="Filters", padding=10)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(filter_frame, text="Status:").pack(side="left")
        self.status_var = tk.StringVar(value="all")
        status_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.status_var,
            values=["all", "pending", "confirmed", "in_progress", "completed", "failed"],
            state="readonly",
            width=15
        )
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_orders())
        
        ttk.Button(filter_frame, text="Search by Order ID", command=self._search_order).pack(side="left", padx=5)
        
        # Orders table
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.orders_tree = ttk.Treeview(
            table_frame,
            columns=("ID", "Customer", "Items", "Total", "Status", "Created"),
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.orders_tree.yview)
        
        # Column headings
        self.orders_tree.heading("#0", text="ID")
        for col in ("ID", "Customer", "Items", "Total", "Status", "Created"):
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=80)
        
        self.orders_tree.pack(fill="both", expand=True)
        self.orders_tree.bind("<Double-1>", lambda e: self._show_order_details())
    
    def _build_customers_tab(self, notebook):
        """Customers management tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="👥 Customers")
        
        # Search frame
        search_frame = ttk.Frame(tab)
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(search_frame, text="Search by Phone:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search", command=self._search_customer).pack(side="left")
        
        # Customers table
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.customers_tree = ttk.Treeview(
            table_frame,
            columns=("Phone", "Name", "Orders", "Spent", "Joined"),
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.customers_tree.yview)
        
        for col in ("Phone", "Name", "Orders", "Spent", "Joined"):
            self.customers_tree.heading(col, text=col)
            self.customers_tree.column(col, width=80)
        
        self.customers_tree.pack(fill="both", expand=True)
        self.customers_tree.bind("<Double-1>", lambda e: self._show_customer_details())
    
    def _build_analytics_tab(self, notebook):
        """Analytics and reports tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📊 Analytics")
        
        # Metrics frame
        metrics = ttk.LabelFrame(tab, text="Key Metrics", padding=20)
        metrics.pack(fill="x", padx=10, pady=10)
        
        # Create metric cards
        self.metric_frames = {}
        for metric in ["Total Orders", "Revenue", "Avg Order", "Popular Item"]:
            frame = ttk.LabelFrame(metrics, text=metric, padding=15)
            frame.pack(side="left", expand=True, padx=10, fill="both")
            label = ttk.Label(frame, text="$0.00", font=("Arial", 18, "bold"))
            label.pack()
            self.metric_frames[metric] = label
        
        # Popular items
        popular_frame = ttk.LabelFrame(tab, text="Popular Items", padding=10)
        popular_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.popular_text = tk.Text(popular_frame, height=10, width=50)
        self.popular_text.pack(fill="both", expand=True)
    
    def _refresh_data(self):
        """Refresh all data"""
        self._refresh_orders()
        self._refresh_analytics()
    
    def _refresh_orders(self):
        """Refresh orders table"""
        # Clear tree
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        # Fetch orders
        orders = self.db.get_recent_orders(50)
        status_filter = self.status_var.get()
        
        for order in orders:
            if status_filter != "all" and order['status'] != status_filter:
                continue
            
            customer = ""
            if order['customer_id']:
                cust = self.db.get_customer(order['customer_id'])
                customer = cust['name'] or cust['phone'] if cust else ""
            
            items = self.db.conn().__enter__().execute(
                "SELECT COUNT(*) as count FROM order_items WHERE order_id = ?",
                (order['id'],)
            ).fetchone()['count']
            
            self.orders_tree.insert(
                "",
                "end",
                text=str(order['id']),
                values=(
                    order['id'],
                    customer,
                    items,
                    f"${order['total_amount']:.2f}",
                    order['status'],
                    order['created_at'][:10]
                )
            )
    
    def _refresh_analytics(self):
        """Refresh analytics"""
        analytics = self.db.get_analytics()
        
        self.metric_frames["Total Orders"].config(text=str(analytics['total_orders']))
        self.metric_frames["Revenue"].config(text=f"${analytics['total_revenue']:.2f}")
        self.metric_frames["Avg Order"].config(text=f"${analytics['avg_order_value']:.2f}")
        
        if analytics['popular_items']:
            self.metric_frames["Popular Item"].config(text=analytics['popular_items'][0][0])
            
            popular_text = "Top Products:\n" + "\n".join(
                f"{i+1}. {item[0]} (x{item[1]})" 
                for i, item in enumerate(analytics['popular_items'][:5])
            )
            self.popular_text.delete("1.0", "end")
            self.popular_text.insert("1.0", popular_text)
    
    def _show_order_details(self):
        """Show selected order details"""
        selection = self.orders_tree.selection()
        if not selection:
            return
        
        order_id = int(self.orders_tree.item(selection[0])['text'])
        order = self.db.get_order(order_id)
        
        if not order:
            messagebox.showerror("Error", "Order not found")
            return
        
        details = f"""Order #{order['id']}
Status: {order['status']}
Total: ${order['total_amount']:.2f}
Created: {order['created_at']}

Items:
"""
        for item in order['items']:
            details += f"  • {item['product_name']} x{item['quantity']} @ ${item['price_per_unit']:.2f}\n"
        
        messagebox.showinfo("Order Details", details)
    
    def _show_customer_details(self):
        """Show selected customer details"""
        selection = self.customers_tree.selection()
        if not selection:
            return
        
        # Get phone from tree
        phone = self.customers_tree.item(selection[0])['values'][0]
        customer = self.db.get_customer_by_phone(phone)
        
        if not customer:
            messagebox.showerror("Error", "Customer not found")
            return
        
        orders = self.db.get_customer_orders(customer['id'], 5)
        
        details = f"""Customer Profile
Name: {customer['name']}
Phone: {customer['phone']}
Email: {customer['email']}
Total Orders: {customer['total_orders']}
Total Spent: ${customer['total_spent']:.2f}

Recent Orders:
"""
        for order in orders:
            details += f"  • Order #{order['id']}: ${order['total_amount']:.2f} ({order['status']})\n"
        
        messagebox.showinfo("Customer Details", details)
    
    def _search_order(self):
        """Search for order by ID"""
        order_id = simpledialog.askinteger("Search", "Enter Order ID:")
        if order_id:
            self._show_order_details()
    
    def _search_customer(self):
        """Search customer by phone"""
        phone = self.search_var.get().strip()
        if not phone:
            messagebox.showwarning("Input", "Enter phone number")
            return
        
        customer = self.db.get_customer_by_phone(phone)
        if customer:
            self._show_customer_details()
        else:
            messagebox.showinfo("Not Found", "No customer with that phone")
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
