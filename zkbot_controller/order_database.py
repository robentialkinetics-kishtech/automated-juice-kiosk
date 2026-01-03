"""
Advanced Order Database for Juice Kiosk
Manages customers, orders, products, and analytics
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

from order_models import Order, Customer, OrderItem, OrderStatus, PaymentMethod, JuiceProduct


class AdvancedKioskDB:
    """Enhanced database with customer profiles, order history, analytics"""
    
    def __init__(self, db_path: str = "data/kiosk.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_schema()
    
    @contextmanager
    def conn(self):
        """Database connection context manager"""
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception as e:
            con.rollback()
            raise e
        finally:
            con.close()
    
    def _init_schema(self):
        """Initialize all tables"""
        with self.conn() as con:
            # Customers table
            con.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE,
                    name TEXT,
                    email TEXT,
                    total_orders INTEGER DEFAULT 0,
                    total_spent REAL DEFAULT 0.0,
                    favorite_drinks TEXT,
                    created_at TEXT,
                    last_order_at TEXT
                )
            """)
            
            # Products table
            con.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    price REAL NOT NULL,
                    image_path TEXT,
                    category TEXT,
                    available INTEGER DEFAULT 1,
                    preparation_time INTEGER DEFAULT 2
                )
            """)
            
            # Orders table (enhanced)
            con.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    status TEXT NOT NULL,
                    payment_method TEXT,
                    total_amount REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    estimated_time INTEGER,
                    error_message TEXT,
                    FOREIGN KEY(customer_id) REFERENCES customers(id)
                )
            """)
            
            # Order items table (line items)
            con.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price_per_unit REAL NOT NULL,
                    special_notes TEXT,
                    FOREIGN KEY(order_id) REFERENCES orders(id),
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )
            """)
    
    # ========== CUSTOMER METHODS ==========
    
    def get_or_create_customer(self, phone: str, name: str = "", email: str = "") -> int:
        """Get existing customer or create new one"""
        with self.conn() as con:
            row = con.execute("SELECT id FROM customers WHERE phone = ?", (phone,)).fetchone()
            if row:
                return row['id']
            
            now = datetime.now().isoformat()
            cur = con.cursor()
            cur.execute(
                "INSERT INTO customers(phone, name, email, created_at) VALUES(?,?,?,?)",
                (phone, name, email, now)
            )
            return cur.lastrowid
    
    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Fetch customer details"""
        with self.conn() as con:
            row = con.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
            return dict(row) if row else None
    
    def update_customer(self, customer_id: int, **kwargs):
        """Update customer info"""
        allowed = {'name', 'email', 'favorite_drinks'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        
        with self.conn() as con:
            cols = ", ".join(f"{k}=?" for k in updates.keys())
            con.execute(f"UPDATE customers SET {cols} WHERE id = ?", (*updates.values(), customer_id))
    
    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Fetch customer by phone"""
        with self.conn() as con:
            row = con.execute("SELECT * FROM customers WHERE phone = ?", (phone,)).fetchone()
            return dict(row) if row else None
    
    # ========== PRODUCT METHODS ==========
    
    def add_product(self, name: str, price: float, description: str = "", category: str = "Custom", image_path: str = ""):
        """Add juice product"""
        with self.conn() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO products(name, price, description, category, image_path) VALUES(?,?,?,?,?)",
                (name, price, description, category, image_path)
            )
            return cur.lastrowid
    
    def get_products(self, category: Optional[str] = None) -> List[Dict]:
        """Get all products or by category"""
        with self.conn() as con:
            if category:
                rows = con.execute("SELECT * FROM products WHERE category = ? AND available = 1", (category,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM products WHERE available = 1").fetchall()
            return [dict(r) for r in rows]
    
    def get_all_products(self) -> List[Dict]:
        """Get all products"""
        with self.conn() as con:
            rows = con.execute("SELECT * FROM products").fetchall()
            return [dict(r) for r in rows]
    
    # ========== ORDER METHODS ==========
    
    def create_order(self, customer_id: Optional[int], items: List[Tuple[int, str, int, float]], 
                    total: float, payment_method: str = "cash") -> int:
        """Create new order with items"""
        now = datetime.now().isoformat(timespec="seconds")
        
        with self.conn() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO orders(customer_id, status, payment_method, total_amount, created_at, estimated_time) VALUES(?,?,?,?,?,?)",
                (customer_id, OrderStatus.PENDING.value, payment_method, total, now, 5)
            )
            order_id = cur.lastrowid
            
            # Add items
            for product_id, product_name, qty, price in items:
                cur.execute(
                    "INSERT INTO order_items(order_id, product_id, product_name, quantity, price_per_unit) VALUES(?,?,?,?,?)",
                    (order_id, product_id, product_name, qty, price)
                )
            
            # Update customer stats
            if customer_id:
                con.execute(
                    "UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + ?, last_order_at = ? WHERE id = ?",
                    (total, now, customer_id)
                )
        
        return order_id
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """Fetch order with items"""
        with self.conn() as con:
            order = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not order:
                return None
            
            items = con.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
            
            result = dict(order)
            result['items'] = [dict(i) for i in items]
            return result
    
    def update_order_status(self, order_id: int, status: str, error_msg: str = ""):
        """Update order status"""
        now = datetime.now().isoformat(timespec="seconds")
        
        with self.conn() as con:
            if status == OrderStatus.IN_PROGRESS.value:
                con.execute("UPDATE orders SET status = ?, started_at = ? WHERE id = ?", (status, now, order_id))
            elif status in (OrderStatus.COMPLETED.value, OrderStatus.FAILED.value):
                con.execute(
                    "UPDATE orders SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
                    (status, now, error_msg, order_id)
                )
            else:
                con.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    
    def get_customer_orders(self, customer_id: int, limit: int = 20) -> List[Dict]:
        """Get customer's order history"""
        with self.conn() as con:
            rows = con.execute(
                "SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
                (customer_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]
    
    def get_recent_orders(self, limit: int = 100) -> List[Dict]:
        """Get all recent orders"""
        with self.conn() as con:
            rows = con.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    # ========== ANALYTICS METHODS ==========
    
    def get_analytics(self) -> Dict:
        """Get order analytics"""
        with self.conn() as con:
            total_orders = con.execute("SELECT COUNT(*) as count FROM orders").fetchone()['count']
            total_revenue = con.execute("SELECT SUM(total_amount) as sum FROM orders WHERE status = ?", 
                                       (OrderStatus.COMPLETED.value,)).fetchone()['sum'] or 0.0
            
            # Popular items
            popular = con.execute("""
                SELECT product_name, SUM(quantity) as total_qty 
                FROM order_items 
                GROUP BY product_name 
                ORDER BY total_qty DESC LIMIT 5
            """).fetchall()
            
            return {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'avg_order_value': total_revenue / total_orders if total_orders > 0 else 0,
                'popular_items': [(r['product_name'], r['total_qty']) for r in popular]
            }
