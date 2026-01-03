"""
Order Management Models for Advanced Juice Kiosk
Supports customer profiles, order history, analytics
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentMethod(Enum):
    CASH = "cash"
    CARD = "card"
    DIGITAL = "digital"


@dataclass
class JuiceProduct:
    """Juice product definition"""
    id: int
    name: str
    description: str
    price: float
    image_path: str
    category: str  # "Tropical", "Berry", "Citrus", "Custom"
    available: bool = True
    preparation_time: int = 2  # seconds


@dataclass
class Customer:
    """Customer profile"""
    id: Optional[int] = None
    phone: str = ""
    name: str = ""
    email: str = ""
    total_orders: int = 0
    total_spent: float = 0.0
    favorite_drinks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_order_at: Optional[str] = None


@dataclass
class OrderItem:
    """Individual item in an order"""
    product_id: int
    product_name: str
    quantity: int
    price_per_unit: float
    special_notes: str = ""
    
    @property
    def total_price(self):
        return self.price_per_unit * self.quantity


@dataclass
class Order:
    """Complete order"""
    id: Optional[int] = None
    customer_id: Optional[int] = None
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    payment_method: Optional[PaymentMethod] = None
    total_amount: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_time: int = 5  # minutes
    error_message: str = ""
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)
    
    def calculate_total(self):
        self.total_amount = sum(item.total_price for item in self.items)
        return self.total_amount


@dataclass
class OrderHistory:
    """Analytics for order tracking"""
    total_orders: int = 0
    total_revenue: float = 0.0
    avg_order_value: float = 0.0
    popular_items: List[tuple] = field(default_factory=list)  # (item_name, count)
    orders_by_hour: dict = field(default_factory=dict)
    peak_hours: List[int] = field(default_factory=list)
