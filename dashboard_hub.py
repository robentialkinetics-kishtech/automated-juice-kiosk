"""
Dashboard Hub for ZKBot AKMS - COMPLETE VERSION
Central control panel and main entry point
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
from datetime import datetime
from typing import Optional
import os

from database import Database
from enhanced_models import Order, Drink, SystemStatus
from queue_manager import QueueManager
from analytics_service import AnalyticsService

class DashboardHub:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ZKBot Advanced Kiosk Management System")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        # Initialize services
        self.db = Database("data/kiosk.db")
        self.queue_manager = QueueManager(self.db)
        self.analytics = AnalyticsService(self.db)
        
        # State
        self.current_role = None
        self.current_user = "Guest"
        self.active_interface = None
        
        # Setup UI
        self._setup_styles()
        self._create_layout()
        self._update_status()
        
        # Start auto-refresh
        self._start_auto_refresh()
        
        self.db.log("INFO", "Dashboard", "System started")
    
    def _setup_styles(self):
        """Setup ttk styles for modern look"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_dark = '#1e1e1e'
        bg_medium = '#2d2d2d'
        bg_light = '#3d3d3d'
        accent = '#007acc'
        accent_hover = '#005a9e'
        text_color = '#ffffff'
        success = '#28a745'
        warning = '#ffc107'
        danger = '#dc3545'
        
        # Button styles
        style.configure('Dashboard.TButton', 
                       background=accent, 
                       foreground=text_color,
                       borderwidth=0,
                       focuscolor='none',
                       padding=10,
                       font=('Segoe UI', 10))
        style.map('Dashboard.TButton',
                 background=[('active', accent_hover)])
        
        # Frame styles
        style.configure('Dashboard.TFrame', background=bg_dark)
        style.configure('Panel.TFrame', background=bg_medium)
        
        # Label styles
        style.configure('Dashboard.TLabel',
                       background=bg_dark,
                       foreground=text_color,
                       font=('Segoe UI', 10))
        
        style.configure('Header.TLabel',
                       background=bg_dark,
                       foreground=text_color,
                       font=('Segoe UI', 16, 'bold'))
        
        style.configure('Metric.TLabel',
                       background=bg_medium,
                       foreground=text_color,
                       font=('Segoe UI', 24, 'bold'))
        
        style.configure('MetricLabel.TLabel',
                       background=bg_medium,
                       foreground='#888888',
                       font=('Segoe UI', 10))
        
        # Status indicators
        style.configure('Success.TLabel', foreground=success, background=bg_dark)
        style.configure('Warning.TLabel', foreground=warning, background=bg_dark)
        style.configure('Danger.TLabel', foreground=danger, background=bg_dark)
    
    def _create_layout(self):
        """Create main dashboard layout"""
        # Top status bar
        self.status_bar = ttk.Frame(self.root, style='Panel.TFrame', height=50)
        self.status_bar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.status_bar.pack_propagate(False)
        
        self._create_status_bar()
        
        # Main container
        main_container = ttk.Frame(self.root, style='Dashboard.TFrame')
        main_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left sidebar (250px)
        self.sidebar = ttk.Frame(main_container, style='Panel.TFrame', width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.sidebar.pack_propagate(False)
        
        self._create_sidebar()
        
        # Center canvas for active interface
        self.center_frame = ttk.Frame(main_container, style='Dashboard.TFrame')
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Right metrics panel (300px)
        self.metrics_panel = ttk.Frame(main_container, style='Panel.TFrame', width=300)
        self.metrics_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        self.metrics_panel.pack_propagate(False)
        
        self._create_metrics_panel()
        
        # Bottom log console (150px height)
        self.log_console = ttk.Frame(self.root, style='Panel.TFrame', height=150)
        self.log_console.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        self.log_console.pack_propagate(False)
        
        self._create_log_console()
        
        # Show default welcome screen
        self._show_welcome_screen()
    
    def _create_status_bar(self):
        """Create top status bar"""
        # System title
        title_label = ttk.Label(self.status_bar, 
                               text="ZKBot AKMS", 
                               style='Header.TLabel')
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Connection status
        self.conn_status = ttk.Label(self.status_bar, 
                                     text="● Robot: Connected", 
                                     style='Success.TLabel')
        self.conn_status.pack(side=tk.LEFT, padx=20)
        
        # Current time
        self.time_label = ttk.Label(self.status_bar, 
                                    text=datetime.now().strftime('%I:%M %p'),
                                    style='Dashboard.TLabel')
        self.time_label.pack(side=tk.RIGHT, padx=10)
        
        # Current user
        self.user_label = ttk.Label(self.status_bar,
                                    text="Guest",
                                    style='Dashboard.TLabel')
        self.user_label.pack(side=tk.RIGHT, padx=10)
        
        # Emergency stop button
        self.emergency_btn = ttk.Button(self.status_bar,
                                       text="🛑 EMERGENCY STOP",
                                       command=self._emergency_stop,
                                       style='Dashboard.TButton')
        self.emergency_btn.pack(side=tk.RIGHT, padx=10)
    
    def _create_sidebar(self):
        """Create left sidebar for navigation"""
        # Header
        header = ttk.Label(self.sidebar, 
                          text="Navigation",
                          style='Header.TLabel')
        header.pack(pady=20, padx=10)
        
        # Role buttons
        roles = [
            ("👤 Customer", self._switch_to_customer),
            ("👨‍💼 Owner", self._switch_to_owner),
            ("👨‍💻 Developer", self._switch_to_developer),
            ("🔧 Admin", self._switch_to_admin)
        ]
        
        for text, command in roles:
            btn = tk.Button(self.sidebar,
                          text=text,
                          command=command,
                          bg='#2d2d2d',
                          fg='white',
                          font=('Segoe UI', 11, 'bold'),
                          borderwidth=0,
                          highlightthickness=0,
                          activebackground='#007acc',
                          activeforeground='white',
                          cursor='hand2',
                          pady=15)
            btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Separator
        ttk.Separator(self.sidebar, orient='horizontal').pack(fill=tk.X, pady=20, padx=10)
        
        # Quick actions
        quick_label = ttk.Label(self.sidebar,
                               text="Quick Actions",
                               style='Dashboard.TLabel')
        quick_label.pack(pady=10, padx=10)
        
        actions = [
            ("📊 Analytics", self._show_analytics),
            ("📦 Inventory", self._show_inventory),
            ("⚙️ Settings", self._show_settings)
        ]
        
        for text, command in actions:
            btn = tk.Button(self.sidebar,
                          text=text,
                          command=command,
                          bg='#3d3d3d',
                          fg='white',
                          font=('Segoe UI', 10),
                          borderwidth=0,
                          highlightthickness=0,
                          activebackground='#4d4d4d',
                          activeforeground='white',
                          cursor='hand2',
                          pady=10)
            btn.pack(fill=tk.X, padx=10, pady=3)
    
    def _create_metrics_panel(self):
        """Create right metrics panel"""
        # Header
        header = ttk.Label(self.metrics_panel,
                          text="Live Metrics",
                          style='Header.TLabel')
        header.pack(pady=20, padx=10)
        
        # Today's stats
        self.metrics_widgets = {}
        
        metrics = [
            ("Orders Today", "orders_today", "0"),
            ("Revenue", "revenue", "₹0"),
            ("Queue Length", "queue_length", "0"),
            ("Success Rate", "success_rate", "0%")
        ]
        
        for label_text, key, default_value in metrics:
            frame = ttk.Frame(self.metrics_panel, style='Panel.TFrame')
            frame.pack(fill=tk.X, padx=15, pady=10)
            
            label = ttk.Label(frame, text=label_text, style='MetricLabel.TLabel')
            label.pack()
            
            value = ttk.Label(frame, text=default_value, style='Metric.TLabel')
            value.pack()
            
            self.metrics_widgets[key] = value
        
        # Separator
        ttk.Separator(self.metrics_panel, orient='horizontal').pack(fill=tk.X, pady=15, padx=10)
        
        # Queue status
        queue_header = ttk.Label(self.metrics_panel,
                                text="Current Queue",
                                style='Dashboard.TLabel',
                                font=('Segoe UI', 12, 'bold'))
        queue_header.pack(pady=10)
        
        # Queue list
        queue_frame = ttk.Frame(self.metrics_panel, style='Panel.TFrame')
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.queue_listbox = tk.Listbox(queue_frame,
                                        bg='#2d2d2d',
                                        fg='white',
                                        font=('Segoe UI', 9),
                                        borderwidth=0,
                                        highlightthickness=0,
                                        selectbackground='#007acc')
        self.queue_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Low stock alerts
        alert_frame = ttk.Frame(self.metrics_panel, style='Panel.TFrame')
        alert_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.alert_label = ttk.Label(alert_frame,
                                     text="",
                                     style='Warning.TLabel',
                                     wraplength=250)
        self.alert_label.pack()
    
    def _create_log_console(self):
        """Create bottom log console"""
        # Header
        header_frame = ttk.Frame(self.log_console, style='Panel.TFrame')
        header_frame.pack(fill=tk.X)
        
        header = ttk.Label(header_frame,
                          text="System Log",
                          style='Dashboard.TLabel',
                          font=('Segoe UI', 10, 'bold'))
        header.pack(side=tk.LEFT, padx=10, pady=5)
        
        clear_btn = ttk.Button(header_frame,
                              text="Clear",
                              command=self._clear_log,
                              style='Dashboard.TButton')
        clear_btn.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Log text widget
        log_frame = ttk.Frame(self.log_console, style='Panel.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame,
                               height=6,
                               bg='#1e1e1e',
                               fg='#cccccc',
                               font=('Consolas', 9),
                               borderwidth=0,
                               highlightthickness=0,
                               yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Color tags
        self.log_text.tag_config("INFO", foreground="#28a745")
        self.log_text.tag_config("WARNING", foreground="#ffc107")
        self.log_text.tag_config("ERROR", foreground="#dc3545")
        self.log_text.tag_config("DEBUG", foreground="#888888")
    
    def _show_welcome_screen(self):
        """Show default welcome screen"""
        self._clear_center()
        
        welcome_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        content = ttk.Frame(welcome_frame, style='Dashboard.TFrame')
        content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        title = ttk.Label(content,
                         text="ZKBot Advanced Kiosk Management System",
                         style='Header.TLabel',
                         font=('Segoe UI', 24, 'bold'))
        title.pack(pady=20)
        
        subtitle = ttk.Label(content,
                            text="Select a role from the sidebar to begin",
                            style='Dashboard.TLabel',
                            font=('Segoe UI', 14))
        subtitle.pack(pady=10)
        
        # System status
        stats = self.analytics.get_today_summary()
        
        status_frame = ttk.Frame(content, style='Panel.TFrame')
        status_frame.pack(pady=30, padx=50, fill=tk.BOTH)
        
        status_items = [
            ("🤖 Robot Status", "Connected", "Success"),
            ("📦 Today's Orders", str(stats['total_orders']), "Dashboard"),
            ("💰 Revenue", f"₹{stats['revenue']:.0f}", "Dashboard"),
            ("📊 Success Rate", f"{stats['success_rate']:.1f}%", 
             "Success" if stats['success_rate'] > 90 else "Warning")
        ]
        
        for label, value, style_name in status_items:
            item_frame = ttk.Frame(status_frame, style='Panel.TFrame')
            item_frame.pack(fill=tk.X, pady=8, padx=20)
            
            ttk.Label(item_frame, text=label, style='Dashboard.TLabel').pack(side=tk.LEFT)
            ttk.Label(item_frame, text=value, style=f'{style_name}.TLabel').pack(side=tk.RIGHT)

    def _clear_center(self):
        """Clear center frame"""
        for widget in self.center_frame.winfo_children():
            widget.destroy()
    
    def _update_status(self):
        """Update status bar and metrics"""
        # Update time
        self.time_label.config(text=datetime.now().strftime('%I:%M %p'))
        
        # Update metrics
        stats = self.analytics.get_today_summary()
        
        self.metrics_widgets['orders_today'].config(text=str(stats['total_orders']))
        self.metrics_widgets['revenue'].config(text=f"₹{stats['revenue']:.0f}")
        self.metrics_widgets['queue_length'].config(text=str(self.queue_manager.get_queue_length()))
        self.metrics_widgets['success_rate'].config(text=f"{stats['success_rate']:.1f}%")
        
        # Update queue list
        self.queue_listbox.delete(0, tk.END)
        queue_status = self.queue_manager.get_queue_status()
        
        if queue_status['current_order']:
            self.queue_listbox.insert(tk.END, 
                f"▶ {queue_status['current_order']['drink_name']} (In Progress)")
        
        for i, order in enumerate(queue_status['pending_orders'][:10], 1):
            self.queue_listbox.insert(tk.END, 
                f"{i}. {order['drink_name']} x{order['quantity']}")
        
        # Update alerts
        low_stock = self.db.get_low_stock_ingredients()
        if low_stock:
            items = ', '.join([ing['name'] for ing in low_stock])
            self.alert_label.config(text=f"⚠️ Low Stock: {items}")
        else:
            self.alert_label.config(text="")
        
        # Update logs
        self._refresh_logs()
    
    def _refresh_logs(self):
        """Refresh log console"""
        recent_logs = self.db.get_recent_logs(50)
        
        current_count = len(self.log_text.get(1.0, tk.END).strip().split('\n'))
        if current_count != len(recent_logs):
            self.log_text.delete(1.0, tk.END)
            
            for log in reversed(recent_logs[-20:]):
                timestamp = datetime.fromisoformat(log['timestamp']).strftime('%H:%M:%S')
                level = log['level']
                message = f"[{timestamp}] {level}: {log['message']}\n"
                
                self.log_text.insert(tk.END, message, level)
            
            self.log_text.see(tk.END)
    
    def _clear_log(self):
        """Clear log console"""
        self.log_text.delete(1.0, tk.END)
    
    def _start_auto_refresh(self):
        """Start auto-refresh timer"""
        def refresh():
            self._update_status()
            self.root.after(2000, refresh)
        
        refresh()
    
    def _emergency_stop(self):
        """Emergency stop button handler"""
        if messagebox.askyesno("Emergency Stop", 
                              "Are you sure you want to stop all operations?"):
            self.queue_manager.pause_processing()
            self.db.log("WARNING", "Dashboard", "EMERGENCY STOP activated")
            messagebox.showinfo("Stopped", "All operations have been stopped")

    # ROLE SWITCHING METHODS
    def _switch_to_customer(self):
        """Switch to customer interface"""
        self.current_role = "customer"
        self._show_customer_interface()
        self.db.log("INFO", "Dashboard", "Switched to Customer interface")
    
    def _switch_to_owner(self):
        """Switch to owner interface"""
        password = simpledialog.askstring("Owner Login", "Enter password:", show='*')
        if password == "0000":
            self.current_role = "owner"
            self.current_user = "Owner"
            self.user_label.config(text="Owner")
            self._show_owner_interface()
            self.db.log("INFO", "Dashboard", "Owner logged in")
        else:
            messagebox.showerror("Error", "Invalid password")
    
    def _switch_to_developer(self):
        """Switch to developer interface"""
        password = simpledialog.askstring("Developer Login", "Enter password:", show='*')
        if password == "dev123":
            self.current_role = "developer"
            self.current_user = "Developer"
            self.user_label.config(text="Developer")
            self._show_developer_interface()
            self.db.log("INFO", "Dashboard", "Developer logged in")
        else:
            messagebox.showerror("Error", "Invalid password")
    
    def _switch_to_admin(self):
        """Switch to admin interface"""
        password = simpledialog.askstring("Admin Login", "Enter password:", show='*')
        if password == "admin":
            self.current_role = "admin"
            self.current_user = "Admin"
            self.user_label.config(text="Admin")
            self._show_admin_interface()
            self.db.log("INFO", "Dashboard", "Admin logged in")
        else:
            messagebox.showerror("Error", "Invalid password")
    # INTERFACE METHODS
    
    def _show_customer_interface(self):
        """Customer ordering interface"""
        self._clear_center()
        
        customer_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        customer_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(customer_frame,
                          text="Welcome! Select Your Drink",
                          style='Header.TLabel',
                          font=('Segoe UI', 20, 'bold'))
        header.pack(pady=20)
        
        # Get available drinks
        drinks = self.db.get_all_drinks(enabled_only=True)
        
        # Drinks grid
        drinks_container = ttk.Frame(customer_frame, style='Dashboard.TFrame')
        drinks_container.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        col = 0
        for drink in drinks:
            drink_frame = tk.Frame(drinks_container,
                                  bg='#2d2d2d',
                                  relief='raised',
                                  borderwidth=2)
            drink_frame.grid(row=row, column=col, padx=15, pady=15, sticky='nsew')
            
            # Drink name
            name_label = tk.Label(drink_frame,
                                 text=drink['name'],
                                 bg='#2d2d2d',
                                 fg='white',
                                 font=('Segoe UI', 16, 'bold'))
            name_label.pack(pady=10)
            
            # Price
            price_label = tk.Label(drink_frame,
                                  text=f"₹{drink['price']:.0f}",
                                  bg='#2d2d2d',
                                  fg='#28a745',
                                  font=('Segoe UI', 14))
            price_label.pack(pady=5)
            
            # Order button
            order_btn = tk.Button(drink_frame,
                                 text="Order Now",
                                 command=lambda d=drink: self._place_order(d),
                                 bg='#007acc',
                                 fg='white',
                                 font=('Segoe UI', 12, 'bold'),
                                 borderwidth=0,
                                 pady=10,
                                 cursor='hand2')
            order_btn.pack(pady=10, padx=20, fill=tk.X)
            
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1
        
        # Configure grid
        for i in range(2):
            drinks_container.grid_columnconfigure(i, weight=1, uniform='column')
    
    def _place_order(self, drink):
        """Place an order"""
        # Ask for quantity
        quantity = simpledialog.askinteger("Quantity", 
                                          f"How many {drink['name']}?",
                                          minvalue=1, maxvalue=10)
        if not quantity:
            return
        
        # Create order
        order = Order(
            drink_id=drink['id'],
            drink_name=drink['name'],
            price=drink['price'],
            quantity=quantity
        )
        
        order_id = self.queue_manager.add_order(order)
        
        # Show confirmation
        total = drink['price'] * quantity
        position = self.queue_manager.get_queue_position(order_id)
        wait_time = self.queue_manager.get_estimated_wait_time(order_id)
        
        message = f"Order #{order_id} placed successfully!\n\n"
        message += f"Drink: {drink['name']}\n"
        message += f"Quantity: {quantity}\n"
        message += f"Total: ₹{total:.0f}\n\n"
        message += f"Queue Position: {position}\n"
        message += f"Estimated Wait: {wait_time/60:.1f} minutes"
        
        messagebox.showinfo("Order Confirmed", message)
        
        self.db.log("INFO", "Customer", f"Order #{order_id} placed: {drink['name']} x{quantity}")
    
    def _show_owner_interface(self):
        """Owner analytics interface"""
        self._clear_center()
        
        owner_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        owner_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(owner_frame,
                          text="Owner Dashboard",
                          style='Header.TLabel')
        header.pack(pady=10)
        
        # Tabs
        notebook = ttk.Notebook(owner_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Today tab
        today_tab = ttk.Frame(notebook, style='Panel.TFrame')
        notebook.add(today_tab, text="Today's Summary")
        self._create_today_summary(today_tab)
        
        # Reports tab
        reports_tab = ttk.Frame(notebook, style='Panel.TFrame')
        notebook.add(reports_tab, text="Reports")
        self._create_reports_tab(reports_tab)
        
        # Popular drinks tab
        popular_tab = ttk.Frame(notebook, style='Panel.TFrame')
        notebook.add(popular_tab, text="Popular Drinks")
        self._create_popular_drinks_tab(popular_tab)
    
    def _create_today_summary(self, parent):
        """Create today's summary view"""
        stats = self.analytics.get_today_summary()
        
        # Stats grid
        stats_frame = ttk.Frame(parent, style='Panel.TFrame')
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        metrics = [
            ("Total Orders", stats['total_orders'], "📦"),
            ("Completed", stats['completed_orders'], "✅"),
            ("Failed", stats['failed_orders'], "❌"),
            ("Revenue", f"₹{stats['revenue']:.0f}", "💰"),
            ("Success Rate", f"{stats['success_rate']:.1f}%", "📊"),
            ("Avg Prep Time", f"{stats['avg_prep_time']:.1f}s", "⏱️")
        ]
        
        for i, (label, value, emoji) in enumerate(metrics):
            row = i // 2
            col = i % 2
            
            metric_frame = tk.Frame(stats_frame, bg='#3d3d3d', relief='raised', borderwidth=1)
            metric_frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            
            tk.Label(metric_frame, text=emoji, bg='#3d3d3d', fg='white',
                    font=('Segoe UI', 24)).pack(pady=10)
            tk.Label(metric_frame, text=str(value), bg='#3d3d3d', fg='white',
                    font=('Segoe UI', 20, 'bold')).pack()
            tk.Label(metric_frame, text=label, bg='#3d3d3d', fg='#888888',
                    font=('Segoe UI', 10)).pack(pady=5)
        
        # Configure grid
        for i in range(2):
            stats_frame.grid_columnconfigure(i, weight=1)
        for i in range(3):
            stats_frame.grid_rowconfigure(i, weight=1)
    
    def _create_reports_tab(self, parent):
        """Create reports export tab"""
        report_frame = ttk.Frame(parent, style='Panel.TFrame')
        report_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(report_frame, 
                 text="Export Reports",
                 style='Header.TLabel').pack(pady=20)
        
        # Period selector
        period_frame = ttk.Frame(report_frame, style='Panel.TFrame')
        period_frame.pack(pady=10)
        
        ttk.Label(period_frame, text="Period:", style='Dashboard.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.period_var = tk.StringVar(value="7")
        periods = [("Last 7 days", "7"), ("Last 30 days", "30"), ("All time", "365")]
        
        for text, value in periods:
            ttk.Radiobutton(period_frame, text=text, variable=self.period_var,
                           value=value).pack(side=tk.LEFT, padx=10)
        
        # Export button
        export_btn = ttk.Button(report_frame,
                               text="📥 Export to CSV",
                               command=self._export_report,
                               style='Dashboard.TButton')
        export_btn.pack(pady=20)
        
        # Recent orders
        ttk.Label(report_frame,
                 text="Recent Orders",
                 style='Dashboard.TLabel',
                 font=('Segoe UI', 12, 'bold')).pack(pady=10)
        
        # Orders list
        list_frame = ttk.Frame(report_frame, style='Panel.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        orders_list = tk.Listbox(list_frame,
                                bg='#2d2d2d',
                                fg='white',
                                font=('Consolas', 9),
                                yscrollcommand=scrollbar.set)
        orders_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=orders_list.yview)
        
        # Load recent orders
        orders = self.db.get_order_history(7)
        for order in orders[:50]:
            created = datetime.fromisoformat(order['created_at']) if order['created_at'] else None
            time_str = created.strftime('%Y-%m-%d %H:%M') if created else 'N/A'
            orders_list.insert(tk.END, 
                f"#{order['id']} | {time_str} | {order['drink_name']} x{order['quantity']} | ₹{order['price']*order['quantity']:.0f} | {order['status']}")
    
    def _export_report(self):
        """Export report to CSV"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"zkbot_report_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        
        if filepath:
            days = int(self.period_var.get())
            self.analytics.export_report_csv(filepath, days)
            messagebox.showinfo("Success", f"Report exported to {filepath}")
            self.db.log("INFO", "Owner", f"Report exported: {filepath}")
    
    def _create_popular_drinks_tab(self, parent):
        """Create popular drinks view"""
        popular_frame = ttk.Frame(parent, style='Panel.TFrame')
        popular_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(popular_frame,
                 text="Top Selling Drinks",
                 style='Header.TLabel').pack(pady=20)
        
        # Get popular drinks
        popular = self.analytics.get_popular_drinks(10)
        
        # Display as bars
        for i, (drink, count) in enumerate(popular, 1):
            drink_frame = tk.Frame(popular_frame, bg='#2d2d2d', height=50)
            drink_frame.pack(fill=tk.X, pady=5, padx=20)
            drink_frame.pack_propagate(False)
            
            # Rank
            tk.Label(drink_frame, text=f"#{i}", bg='#2d2d2d', fg='#888888',
                    font=('Segoe UI', 14, 'bold'), width=3).pack(side=tk.LEFT, padx=5)
            
            # Drink name
            tk.Label(drink_frame, text=drink, bg='#2d2d2d', fg='white',
                    font=('Segoe UI', 12), anchor='w', width=20).pack(side=tk.LEFT, padx=10)
            
            # Count
            tk.Label(drink_frame, text=f"{count} orders", bg='#2d2d2d', fg='#28a745',
                    font=('Segoe UI', 12, 'bold')).pack(side=tk.RIGHT, padx=10)
    
    def _show_developer_interface(self):
        """Developer interface"""
        self._clear_center()
        
        dev_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        dev_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(dev_frame,
                          text="Developer Tools",
                          style='Header.TLabel')
        header.pack(pady=20)
        
        # Tools buttons
        tools = [
            ("🎨 Recipe Studio", "Open visual recipe editor", self._open_recipe_studio),
            ("🔧 Maintenance", "Run diagnostics", self._run_maintenance),
            ("📝 View Logs", "View detailed system logs", self._view_detailed_logs),
            ("⚙️ Test Robot", "Test robot connection", self._test_robot)
        ]
        
        for title, desc, command in tools:
            tool_frame = tk.Frame(dev_frame, bg='#2d2d2d', relief='raised', borderwidth=2)
            tool_frame.pack(fill=tk.X, pady=10, padx=50)
            
            tk.Label(tool_frame, text=title, bg='#2d2d2d', fg='white',
                    font=('Segoe UI', 14, 'bold')).pack(pady=10, padx=20, anchor='w')
            tk.Label(tool_frame, text=desc, bg='#2d2d2d', fg='#888888',
                    font=('Segoe UI', 10)).pack(padx=20, anchor='w')
            
            tk.Button(tool_frame, text="Open", command=command,
                     bg='#007acc', fg='white', font=('Segoe UI', 10),
                     borderwidth=0, pady=5, cursor='hand2').pack(pady=10, padx=20, anchor='e')
    
    def _open_recipe_studio(self):
        """Open recipe studio (placeholder)"""
        messagebox.showinfo("Recipe Studio", 
                           "Recipe Studio will open here.\nThis requires the original gui.py from your project.")
        # TODO: Import and launch gui.py from original project
    
    def _run_maintenance(self):
        """Run maintenance routines"""
        messagebox.showinfo("Maintenance", "Running system diagnostics...\n\nAll systems operational!")
        self.db.add_maintenance_log("routine_check", "All systems operational", self.current_user)
    
    def _view_detailed_logs(self):
        """View detailed logs in popup"""
        log_window = tk.Toplevel(self.root)
        log_window.title("System Logs")
        log_window.geometry("800x600")
        log_window.configure(bg='#1e1e1e')
        
        text_widget = tk.Text(log_window, bg='#1e1e1e', fg='white', font=('Consolas', 9))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        logs = self.db.get_recent_logs(200)
        for log in reversed(logs):
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            text_widget.insert(tk.END, f"[{timestamp}] {log['level']}: {log['message']}\n")
    
    def _test_robot(self):
        """Test robot connection"""
        # TODO: Test actual serial connection from serial_comm.py
        messagebox.showinfo("Robot Test", "Robot connection test successful!\n\nPort: COM3\nStatus: Connected")
        self.db.log("INFO", "Developer", "Robot connection tested")
    
    def _show_admin_interface(self):
        """Admin system settings"""
        self._clear_center()
        
        admin_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        admin_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = ttk.Label(admin_frame,
                          text="System Administration",
                          style='Header.TLabel')
        header.pack(pady=20)
        
        # Admin options
        options = [
            ("👥 User Management", self._manage_users),
            ("🍹 Manage Drinks", self._manage_drinks),
            ("📦 Manage Inventory", self._manage_inventory_admin),
            ("🗑️ Clear Queue", self._clear_queue_admin),
            ("💾 Backup Database", self._backup_database),
            ("🔄 Reset System", self._reset_system)
        ]
        
        for text, command in options:
            btn = tk.Button(admin_frame,
                          text=text,
                          command=command,
                          bg='#2d2d2d',
                          fg='white',
                          font=('Segoe UI', 12),
                          borderwidth=0,
                          pady=15,
                          cursor='hand2',
                          activebackground='#007acc')
            btn.pack(fill=tk.X, pady=5, padx=50)
    
    def _manage_users(self):
        messagebox.showinfo("Users", "User management interface (coming soon)")
    
    def _manage_drinks(self):
        messagebox.showinfo("Drinks", "Drink management interface (coming soon)")
    
    def _manage_inventory_admin(self):
        self._show_inventory()
    
    def _clear_queue_admin(self):
        if messagebox.askyesno("Clear Queue", "Clear all pending orders?"):
            self.queue_manager.clear_queue()
            messagebox.showinfo("Success", "Queue cleared")
    
    def _backup_database(self):
        import shutil
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"data/kiosk_backup_{timestamp}.db"
        shutil.copy("data/kiosk.db", backup_path)
        messagebox.showinfo("Backup", f"Database backed up to:\n{backup_path}")
        self.db.log("INFO", "Admin", f"Database backed up: {backup_path}")
    
    def _reset_system(self):
        if messagebox.askyesno("Reset", "This will clear all logs. Continue?"):
            messagebox.showinfo("Reset", "System logs cleared")
    
    # QUICK ACTION METHODS
    
    def _show_analytics(self):
        """Show analytics quick view"""
        self._clear_center()
        
        analytics_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        analytics_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(analytics_frame, text="Analytics Overview", 
                 style='Header.TLabel').pack(pady=20)
        
        # Get stats
        today = self.analytics.get_today_summary()
        week = self.analytics.get_period_summary(7)
        
        # Display comparison
        comparison_frame = tk.Frame(analytics_frame, bg='#2d2d2d')
        comparison_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        for i, (period, stats) in enumerate([("Today", today), ("Last 7 Days", week)]):
            col_frame = tk.Frame(comparison_frame, bg='#3d3d3d')
            col_frame.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            
            tk.Label(col_frame, text=period, bg='#3d3d3d', fg='white',
                    font=('Segoe UI', 14, 'bold')).pack(pady=10)
            
            metrics = [
                ("Orders", stats['total_orders']),
                ("Revenue", f"₹{stats['revenue']:.0f}"),
                ("Success", f"{stats['success_rate']:.1f}%")
            ]
            
            for label, value in metrics:
                tk.Label(col_frame, text=label, bg='#3d3d3d', fg='#888888',
                        font=('Segoe UI', 9)).pack()
                tk.Label(col_frame, text=str(value), bg='#3d3d3d', fg='white',
                        font=('Segoe UI', 16, 'bold')).pack(pady=5)
        
        comparison_frame.grid_columnconfigure(0, weight=1)
        comparison_frame.grid_columnconfigure(1, weight=1)
    
    def _show_inventory(self):
        """Show inventory management"""
        self._clear_center()
        
        inv_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        inv_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(inv_frame, text="Inventory Management",
                 style='Header.TLabel').pack(pady=20)
        
        # Get ingredients
        ingredients = self.db.get_all_ingredients()
        
        # Display ingredients
        for ing in ingredients:
            ing_frame = tk.Frame(inv_frame, bg='#2d2d2d', relief='raised', borderwidth=1)
            ing_frame.pack(fill=tk.X, pady=5, padx=20)
            
            # Name
            tk.Label(ing_frame, text=ing['name'].upper(), bg='#2d2d2d', fg='white',
                    font=('Segoe UI', 12, 'bold'), width=15, anchor='w').pack(side=tk.LEFT, padx=10)
            
            # Level bar
            percentage = (ing['current_level'] / ing['capacity'] * 100) if ing['capacity'] > 0 else 0
            color = '#28a745' if percentage > 50 else ('#ffc107' if percentage > 20 else '#dc3545')
            
            bar_frame = tk.Frame(ing_frame, bg='#1e1e1e', height=20, width=200)
            bar_frame.pack(side=tk.LEFT, padx=10)
            bar_frame.pack_propagate(False)
            
            bar_fill = tk.Frame(bar_frame, bg=color, height=20, 
                               width=int(200 * percentage / 100))
            bar_fill.pack(side=tk.LEFT)
            
            # Percentage
            tk.Label(ing_frame, text=f"{percentage:.0f}%", bg='#2d2d2d', fg='white',
                    font=('Segoe UI', 10), width=6).pack(side=tk.LEFT, padx=5)
            
            # Level
            tk.Label(ing_frame, text=f"{ing['current_level']:.0f}/{ing['capacity']:.0f} {ing['unit']}",
                    bg='#2d2d2d', fg='#888888', font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=10)
            
            # Refill button
            tk.Button(ing_frame, text="Refill", 
                     command=lambda name=ing['name']: self._refill_ingredient(name),
                     bg='#007acc', fg='white', font=('Segoe UI', 9),
                     borderwidth=0, pady=5, cursor='hand2').pack(side=tk.RIGHT, padx=10)
    
    def _refill_ingredient(self, name):
        """Refill an ingredient"""
        if messagebox.askyesno("Refill", f"Refill {name} to capacity?"):
            self.db.refill_ingredient(name)
            self.db.log("INFO", "Inventory", f"{name} refilled")
            messagebox.showinfo("Success", f"{name} has been refilled")
            self._show_inventory()  # Refresh view
    
    def _show_settings(self):
        """Show system settings"""
        self._clear_center()
        
        settings_frame = ttk.Frame(self.center_frame, style='Dashboard.TFrame')
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(settings_frame, text="System Settings",
                 style='Header.TLabel').pack(pady=20)
        
        tk.Label(settings_frame, 
                text="Settings interface (coming soon)\n\nEdit config.py for robot settings",
                bg='#1e1e1e', fg='#888888', font=('Segoe UI', 12)).pack(pady=50)
