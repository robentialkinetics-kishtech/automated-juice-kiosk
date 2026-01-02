"""
Enhanced data models for ZKBot AKMS
Extended from original models.py with additional features
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class Step:
    """Represents a single robot movement step"""
    cmd: str = "G01"  # G00 or G01
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    F: float = 20.0   # Feed rate
    delay: float = 0.5
    DO0: int = 90     # End effector angle (0-180)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Step':
        return cls(**data)
    
    def validate(self) -> bool:
        """Validate step parameters"""
        if self.cmd not in ["G00", "G01"]:
            return False
        if not (-200 <= self.X <= 200 and -200 <= self.Y <= 200):
            return False
        if not (-50 <= self.Z <= 250):
            return False
        if not (0 <= self.DO0 <= 180):
            return False
        if self.F <= 0:
            return False
        return True

@dataclass
class Program:
    """Represents a sequence of steps"""
    name: str = "Untitled"
    description: str = ""
    steps: List[Step] = field(default_factory=list)
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_step(self, step: Step):
        """Add a step to the program"""
        if step.validate():
            self.steps.append(step)
            self.modified_at = datetime.now().isoformat()
        else:
            raise ValueError("Invalid step parameters")
    
    def insert_step(self, index: int, step: Step):
        """Insert step at specific index"""
        if step.validate():
            self.steps.insert(index, step)
            self.modified_at = datetime.now().isoformat()
        else:
            raise ValueError("Invalid step parameters")
    
    def remove_step(self, index: int):
        """Remove step at index"""
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
            self.modified_at = datetime.now().isoformat()
    
    def update_step(self, index: int, step: Step):
        """Update step at index"""
        if 0 <= index < len(self.steps) and step.validate():
            self.steps[index] = step
            self.modified_at = datetime.now().isoformat()
    
    def get_duration(self) -> float:
        """Calculate estimated duration in seconds"""
        total_time = 0
        for step in self.steps:
            total_time += step.delay
        return total_time
    
    def save(self, filepath: str):
        """Save program to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.modified_at = datetime.now().isoformat()
        
        data = {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'steps': [step.to_dict() for step in self.steps]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'Program':
        """Load program from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle old format (just array of steps)
        if isinstance(data, list):
            steps = [Step.from_dict(step) for step in data]
            return cls(
                name=os.path.basename(filepath).replace('.json', ''),
                steps=steps
            )
        
        # Handle new format (with metadata)
        steps = [Step.from_dict(step) for step in data.get('steps', [])]
        return cls(
            name=data.get('name', 'Untitled'),
            description=data.get('description', ''),
            steps=steps,
            version=data.get('version', '1.0'),
            created_at=data.get('created_at', datetime.now().isoformat()),
            modified_at=data.get('modified_at', datetime.now().isoformat())
        )
    
    def clone(self, new_name: str) -> 'Program':
        """Create a copy of the program"""
        return Program(
            name=new_name,
            description=f"Cloned from {self.name}",
            steps=[Step.from_dict(step.to_dict()) for step in self.steps],
            version="1.0",
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat()
        )
    
    def merge(self, other: 'Program'):
        """Merge another program's steps into this one"""
        self.steps.extend(other.steps)
        self.modified_at = datetime.now().isoformat()
    
    def optimize(self):
        """Optimize program by removing redundant steps"""
        optimized = []
        prev_step = None
        
        for step in self.steps:
            if prev_step is None:
                optimized.append(step)
            elif (step.X != prev_step.X or 
                  step.Y != prev_step.Y or 
                  step.Z != prev_step.Z or
                  step.DO0 != prev_step.DO0):
                optimized.append(step)
            prev_step = step
        
        self.steps = optimized
        self.modified_at = datetime.now().isoformat()

@dataclass
class Order:
    """Represents a customer order"""
    id: Optional[int] = None
    customer_name: Optional[str] = None
    drink_id: int = 0
    drink_name: str = ""
    quantity: int = 1
    price: float = 0.0
    status: str = "pending"
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Order':
        return cls(**data)
    
    def get_total(self) -> float:
        """Calculate total price"""
        return self.price * self.quantity

@dataclass
class SystemStatus:
    """Represents current system status"""
    robot_connected: bool = False
    robot_busy: bool = False
    current_order_id: Optional[int] = None
    queue_length: int = 0
    low_stock_items: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    last_maintenance: Optional[str] = None
    uptime: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return (self.robot_connected and 
                not self.errors and 
                len(self.low_stock_items) == 0)

@dataclass
class Ingredient:
    """Represents an ingredient"""
    id: Optional[int] = None
    name: str = ""
    current_level: float = 100.0
    capacity: float = 1000.0
    unit: str = "ml"
    last_refill: Optional[str] = None
    min_threshold: float = 20.0
    
    def get_percentage(self) -> float:
        """Get current level as percentage"""
        return (self.current_level / self.capacity) * 100 if self.capacity > 0 else 0
    
    def is_low(self) -> bool:
        """Check if ingredient is low"""
        return self.get_percentage() < self.min_threshold
    
    def consume(self, amount: float) -> bool:
        """Consume ingredient amount"""
        if self.current_level >= amount:
            self.current_level -= amount
            return True
        return False
    
    def refill(self):
        """Refill to capacity"""
        self.current_level = self.capacity
        self.last_refill = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Drink:
    """Represents a drink menu item"""
    id: Optional[int] = None
    name: str = ""
    price: float = 0.0
    recipe_file: str = ""
    ingredients: List[str] = field(default_factory=list)
    image_path: str = ""
    enabled: bool = True
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['ingredients'] = ','.join(self.ingredients) if isinstance(self.ingredients, list) else self.ingredients
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Drink':
        if 'ingredients' in data and isinstance(data['ingredients'], str):
            data['ingredients'] = data['ingredients'].split(',') if data['ingredients'] else []
        return cls(**data)
