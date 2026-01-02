"""
Queue Manager for ZKBot AKMS
Handles order queue with priority, batching, and wait time estimation
"""

import threading
from typing import List, Optional, Callable
from datetime import datetime, timedelta
from enhanced_models import Order, SystemStatus
from database import Database

class QueueManager:
    def __init__(self, db: Database):
        self.db = db
        self.queue: List[Order] = []
        self.current_order: Optional[Order] = None
        self.is_processing = False
        self.is_paused = False
        self.lock = threading.Lock()
        self.process_thread = None
        self.avg_prep_time = 60.0  # Default 60 seconds
        
        # Callbacks
        self.on_order_start: Optional[Callable] = None
        self.on_order_complete: Optional[Callable] = None
        self.on_order_failed: Optional[Callable] = None
        
        # Load pending orders from database
        self._load_pending_orders()
    
    def _load_pending_orders(self):
        """Load pending orders from database on startup"""
        pending = self.db.get_pending_orders()
        self.queue = [Order.from_dict(order) for order in pending]
        self.db.log("INFO", "QueueManager", f"Loaded {len(self.queue)} pending orders")
    
    def add_order(self, order: Order) -> int:
        """Add order to queue"""
        with self.lock:
            # Create order in database
            order_id = self.db.create_order(
                drink_name=order.drink_name,
                drink_id=order.drink_id,
                price=order.price,
                quantity=order.quantity,
                customer_name=order.customer_name
            )
            order.id = order_id
            order.status = "pending"
            order.created_at = datetime.now().isoformat()
            
            # Add to queue
            self.queue.append(order)
            
            self.db.log("INFO", "QueueManager", 
                       f"Order #{order_id} added: {order.drink_name} x{order.quantity}")
            
            return order_id
    
    def remove_order(self, order_id: int) -> bool:
        """Remove/cancel order from queue"""
        with self.lock:
            for i, order in enumerate(self.queue):
                if order.id == order_id:
                    # Don't cancel if already in progress
                    if self.current_order and self.current_order.id == order_id:
                        return False
                    
                    self.queue.pop(i)
                    self.db.update_order_status(order_id, "cancelled")
                    self.db.log("INFO", "QueueManager", f"Order #{order_id} cancelled")
                    return True
            return False
    
    def get_queue_position(self, order_id: int) -> int:
        """Get position of order in queue (1-indexed)"""
        with self.lock:
            for i, order in enumerate(self.queue):
                if order.id == order_id:
                    return i + 1
            return -1
    
    def get_estimated_wait_time(self, order_id: int) -> float:
        """Get estimated wait time in seconds"""
        position = self.get_queue_position(order_id)
        if position == -1:
            return 0
        
        # Calculate based on position and average prep time
        orders_ahead = position - 1
        if self.current_order:
            orders_ahead += 1
        
        return orders_ahead * self.avg_prep_time
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        with self.lock:
            return len(self.queue)
    
    def get_queue_status(self) -> dict:
        """Get current queue status"""
        with self.lock:
            return {
                'queue_length': len(self.queue),
                'is_processing': self.is_processing,
                'is_paused': self.is_paused,
                'current_order': self.current_order.to_dict() if self.current_order else None,
                'pending_orders': [order.to_dict() for order in self.queue]
            }
    
    def pause_processing(self):
        """Pause queue processing"""
        self.is_paused = True
        self.db.log("WARNING", "QueueManager", "Queue processing paused")
    
    def resume_processing(self):
        """Resume queue processing"""
        self.is_paused = False
        self.db.log("INFO", "QueueManager", "Queue processing resumed")
        if not self.is_processing and len(self.queue) > 0:
            self.start_processing()
    
    def start_processing(self):
        """Start processing queue in background thread"""
        if self.process_thread and self.process_thread.is_alive():
            return
        
        self.process_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.process_thread.start()
        self.db.log("INFO", "QueueManager", "Queue processing started")
    
    def _process_queue(self):
        """Background thread to process queue"""
        self.is_processing = True
        
        while True:
            # Check if paused
            if self.is_paused:
                threading.Event().wait(1)
                continue
            
            # Get next order
            with self.lock:
                if len(self.queue) == 0:
                    self.current_order = None
                    self.is_processing = False
                    break
                
                self.current_order = self.queue.pop(0)
            
            # Process order
            try:
                self.db.log("INFO", "QueueManager", 
                           f"Processing order #{self.current_order.id}")
                
                # Update status to in_progress
                self.db.update_order_status(self.current_order.id, "in_progress")
                self.current_order.status = "in_progress"
                self.current_order.started_at = datetime.now().isoformat()
                
                # Call start callback
                if self.on_order_start:
                    self.on_order_start(self.current_order)
                
                # Order execution happens in callback
                # Wait for completion signal (this is handled by external runner)
                
            except Exception as e:
                self.db.log("ERROR", "QueueManager", 
                           f"Order #{self.current_order.id} failed: {str(e)}")
                self.db.update_order_status(self.current_order.id, "failed", str(e))
                
                if self.on_order_failed:
                    self.on_order_failed(self.current_order, str(e))
    
    def mark_order_completed(self, order_id: int, duration: float = None):
        """Mark order as completed"""
        self.db.update_order_status(order_id, "completed")
        
        # Update average prep time
        if duration:
            self.avg_prep_time = (self.avg_prep_time * 0.8) + (duration * 0.2)
        
        self.db.log("INFO", "QueueManager", f"Order #{order_id} completed")
        
        if self.on_order_complete and self.current_order:
            self.on_order_complete(self.current_order)
    
    def mark_order_failed(self, order_id: int, error_message: str):
        """Mark order as failed"""
        self.db.update_order_status(order_id, "failed", error_message)
        self.db.log("ERROR", "QueueManager", 
                   f"Order #{order_id} failed: {error_message}")
        
        if self.on_order_failed and self.current_order:
            self.on_order_failed(self.current_order, error_message)
    
    def get_system_status(self) -> SystemStatus:
        """Get current system status"""
        with self.lock:
            low_stock = self.db.get_low_stock_ingredients()
            
            return SystemStatus(
                robot_connected=True,  # This should be checked from serial_comm
                robot_busy=self.is_processing and self.current_order is not None,
                current_order_id=self.current_order.id if self.current_order else None,
                queue_length=len(self.queue),
                low_stock_items=[ing['name'] for ing in low_stock]
            )
    
    def clear_queue(self):
        """Clear all pending orders (emergency)"""
        with self.lock:
            for order in self.queue:
                self.db.update_order_status(order.id, "cancelled")
            
            self.queue.clear()
            self.db.log("WARNING", "QueueManager", "Queue cleared")
