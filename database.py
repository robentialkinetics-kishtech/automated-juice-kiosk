"""
Database module for ZKBot Advanced Kiosk Management System
Handles all database operations with SQLite
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str = "data/kiosk.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database with schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Drinks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drinks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    price REAL NOT NULL,
                    recipe_file TEXT NOT NULL,
                    ingredients TEXT,
                    image_path TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT,
                    drink_id INTEGER,
                    drink_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration REAL,
                    error_message TEXT,
                    FOREIGN KEY (drink_id) REFERENCES drinks(id)
                )
            ''')
            
            # Ingredients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingredients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    current_level REAL DEFAULT 100,
                    capacity REAL NOT NULL,
                    unit TEXT DEFAULT 'ml',
                    last_refill TIMESTAMP,
                    min_threshold REAL DEFAULT 20
                )
            ''')
            
            # System logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            ''')
            
            # Maintenance logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintenance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    type TEXT NOT NULL,
                    description TEXT,
                    performed_by TEXT,
                    status TEXT DEFAULT 'completed'
                )
            ''')
            
            # Analytics daily summary
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics_daily (
                    date TEXT PRIMARY KEY,
                    total_orders INTEGER DEFAULT 0,
                    completed_orders INTEGER DEFAULT 0,
                    failed_orders INTEGER DEFAULT 0,
                    revenue REAL DEFAULT 0,
                    popular_drink TEXT,
                    avg_prep_time REAL
                )
            ''')
            
            # Insert default admin user if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password_hash, role)
                VALUES ('admin', '0000', 'admin')
            ''')
            
            # Insert default drinks if not exists
            default_drinks = [
                ('Badham Milk', 70.0, 'juices/badham.json', 'badham,milk', 'assets/images/badham.png'),
                ('Grape Juice', 75.0, 'juices/grape.json', 'grape', 'assets/images/grape.png'),
                ('Lemon Juice', 80.0, 'juices/lemon.json', 'lemon', 'assets/images/lemon.png'),
                ('Rose Milk', 85.0, 'juices/rose.json', 'rose,milk', 'assets/images/rose.png')
            ]
            
            for drink in default_drinks:
                cursor.execute('''
                    INSERT OR IGNORE INTO drinks (name, price, recipe_file, ingredients, image_path)
                    VALUES (?, ?, ?, ?, ?)
                ''', drink)
            
            # Insert default ingredients
            default_ingredients = [
                ('badham', 1000, 'ml'),
                ('grape', 1000, 'ml'),
                ('lemon', 1000, 'ml'),
                ('rose', 1000, 'ml'),
                ('milk', 2000, 'ml'),
                ('cups', 100, 'units')
            ]
            
            for ing in default_ingredients:
                cursor.execute('''
                    INSERT OR IGNORE INTO ingredients (name, capacity, unit, current_level)
                    VALUES (?, ?, ?, ?)
                ''', (ing[0], ing[1], ing[2], ing[1]))
    
    # ORDER OPERATIONS
    def create_order(self, drink_name: str, drink_id: int, price: float, 
                     quantity: int = 1, customer_name: str = None) -> int:
        """Create a new order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (customer_name, drink_id, drink_name, quantity, price, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (customer_name, drink_id, drink_name, quantity, price))
            return cursor.lastrowid
    
    def update_order_status(self, order_id: int, status: str, 
                           error_message: str = None):
        """Update order status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status == 'in_progress':
                cursor.execute('''
                    UPDATE orders SET status = ?, started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, order_id))
            elif status == 'completed':
                cursor.execute('''
                    UPDATE orders 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP,
                        duration = (julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400
                    WHERE id = ?
                ''', (status, order_id))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE orders 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                ''', (status, error_message, order_id))
            else:
                cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM orders 
                WHERE status = 'pending' 
                ORDER BY created_at ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get specific order by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # DRINK OPERATIONS
    def get_all_drinks(self, enabled_only: bool = True) -> List[Dict]:
        """Get all drinks"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute('SELECT * FROM drinks WHERE enabled = 1')
            else:
                cursor.execute('SELECT * FROM drinks')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_drink_by_id(self, drink_id: int) -> Optional[Dict]:
        """Get drink by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM drinks WHERE id = ?', (drink_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_drink_status(self, drink_id: int, enabled: bool):
        """Enable or disable a drink"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE drinks SET enabled = ? WHERE id = ?', 
                         (1 if enabled else 0, drink_id))
    
    # INGREDIENT OPERATIONS
    def get_all_ingredients(self) -> List[Dict]:
        """Get all ingredients"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ingredients')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_ingredient_level(self, name: str, new_level: float):
        """Update ingredient level"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE ingredients SET current_level = ? WHERE name = ?
            ''', (new_level, name))
    
    def refill_ingredient(self, name: str):
        """Refill ingredient to capacity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE ingredients 
                SET current_level = capacity, last_refill = CURRENT_TIMESTAMP
                WHERE name = ?
            ''', (name,))
    
    def get_low_stock_ingredients(self) -> List[Dict]:
        """Get ingredients below minimum threshold"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ingredients 
                WHERE current_level < min_threshold
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    # ANALYTICS OPERATIONS
    def get_today_stats(self) -> Dict:
        """Get today's statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'completed' THEN price * quantity ELSE 0 END) as revenue,
                    AVG(CASE WHEN status = 'completed' THEN duration ELSE NULL END) as avg_time
                FROM orders
                WHERE DATE(created_at) = DATE('now')
            ''')
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def get_popular_drinks(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most popular drinks"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT drink_name, COUNT(*) as count
                FROM orders
                WHERE status = 'completed'
                GROUP BY drink_name
                ORDER BY count DESC
                LIMIT ?
            ''', (limit,))
            return [(row[0], row[1]) for row in cursor.fetchall()]
    
    def get_order_history(self, days: int = 7) -> List[Dict]:
        """Get order history for last N days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM orders
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
            ''', (days,))
            return [dict(row) for row in cursor.fetchall()]
    
    # LOGGING OPERATIONS
    def log(self, level: str, module: str, message: str):
        """Add system log entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_logs (level, module, message)
                VALUES (?, ?, ?)
            ''', (level, module, message))
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent system logs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM system_logs
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_maintenance_log(self, type: str, description: str, performed_by: str):
        """Add maintenance log entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO maintenance_logs (type, description, performed_by)
                VALUES (?, ?, ?)
            ''', (type, description, performed_by))
