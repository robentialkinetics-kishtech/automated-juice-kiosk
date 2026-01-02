"""
Analytics Service for ZKBot AKMS
Data collection, analysis, and reporting
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from database import Database
import csv

class AnalyticsService:
    def __init__(self, db: Database):
        self.db = db
    
    def get_today_summary(self) -> Dict:
        """Get today's summary statistics"""
        stats = self.db.get_today_stats()
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_orders': stats.get('total_orders', 0) or 0,
            'completed_orders': stats.get('completed', 0) or 0,
            'failed_orders': stats.get('failed', 0) or 0,
            'pending_orders': (stats.get('total_orders', 0) or 0) - 
                            (stats.get('completed', 0) or 0) - 
                            (stats.get('failed', 0) or 0),
            'revenue': stats.get('revenue', 0) or 0,
            'avg_prep_time': stats.get('avg_time', 0) or 0,
            'success_rate': self._calculate_success_rate(
                stats.get('completed', 0) or 0,
                stats.get('total_orders', 0) or 0
            )
        }
    
    def get_period_summary(self, days: int = 7) -> Dict:
        """Get summary for last N days"""
        orders = self.db.get_order_history(days)
        
        total = len(orders)
        completed = sum(1 for o in orders if o['status'] == 'completed')
        failed = sum(1 for o in orders if o['status'] == 'failed')
        revenue = sum(o['price'] * o['quantity'] for o in orders 
                     if o['status'] == 'completed')
        
        durations = [o['duration'] for o in orders 
                    if o['status'] == 'completed' and o['duration']]
        avg_time = sum(durations) / len(durations) if durations else 0
        
        return {
            'period': f'Last {days} days',
            'total_orders': total,
            'completed_orders': completed,
            'failed_orders': failed,
            'revenue': revenue,
            'avg_prep_time': avg_time,
            'success_rate': self._calculate_success_rate(completed, total)
        }
    
    def get_popular_drinks(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most popular drinks"""
        return self.db.get_popular_drinks(limit)
    
    def get_hourly_distribution(self, days: int = 7) -> Dict[int, int]:
        """Get order distribution by hour of day"""
        orders = self.db.get_order_history(days)
        distribution = {i: 0 for i in range(24)}
        
        for order in orders:
            if order['created_at']:
                hour = datetime.fromisoformat(order['created_at']).hour
                distribution[hour] += 1
        
        return distribution
    
    def get_peak_hours(self, days: int = 7, top_n: int = 3) -> List[Tuple[int, int]]:
        """Get peak hours with order counts"""
        distribution = self.get_hourly_distribution(days)
        sorted_hours = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        return sorted_hours[:top_n]
    
    def get_revenue_by_drink(self) -> List[Dict]:
        """Get revenue breakdown by drink"""
        orders = self.db.get_order_history(30)  # Last 30 days
        
        drink_revenue = {}
        for order in orders:
            if order['status'] == 'completed':
                drink = order['drink_name']
                revenue = order['price'] * order['quantity']
                
                if drink not in drink_revenue:
                    drink_revenue[drink] = {'revenue': 0, 'count': 0}
                
                drink_revenue[drink]['revenue'] += revenue
                drink_revenue[drink]['count'] += order['quantity']
        
        result = []
        for drink, data in drink_revenue.items():
            result.append({
                'drink': drink,
                'revenue': data['revenue'],
                'orders': data['count'],
                'avg_price': data['revenue'] / data['count'] if data['count'] > 0 else 0
            })
        
        return sorted(result, key=lambda x: x['revenue'], reverse=True)
    
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Get daily statistics for last N days"""
        orders = self.db.get_order_history(days)
        
        # Group by date
        daily_data = {}
        for order in orders:
            if order['created_at']:
                date = datetime.fromisoformat(order['created_at']).date().isoformat()
                
                if date not in daily_data:
                    daily_data[date] = {
                        'date': date,
                        'total': 0,
                        'completed': 0,
                        'failed': 0,
                        'revenue': 0
                    }
                
                daily_data[date]['total'] += 1
                if order['status'] == 'completed':
                    daily_data[date]['completed'] += 1
                    daily_data[date]['revenue'] += order['price'] * order['quantity']
                elif order['status'] == 'failed':
                    daily_data[date]['failed'] += 1
        
        return sorted(daily_data.values(), key=lambda x: x['date'])
    
    def get_failure_analysis(self, days: int = 7) -> Dict:
        """Analyze failed orders"""
        orders = self.db.get_order_history(days)
        failed = [o for o in orders if o['status'] == 'failed']
        
        # Group by error message
        error_counts = {}
        for order in failed:
            error = order.get('error_message', 'Unknown error')
            error_counts[error] = error_counts.get(error, 0) + 1
        
        return {
            'total_failed': len(failed),
            'failure_rate': len(failed) / len(orders) * 100 if orders else 0,
            'error_breakdown': error_counts,
            'most_common_error': max(error_counts.items(), key=lambda x: x[1])[0] 
                                if error_counts else None
        }
    
    def get_ingredient_consumption(self, days: int = 7) -> Dict[str, float]:
        """Estimate ingredient consumption"""
        orders = self.db.get_order_history(days)
        completed = [o for o in orders if o['status'] == 'completed']
        
        # Get drinks and their ingredients
        drinks = {d['name']: d for d in self.db.get_all_drinks(enabled_only=False)}
        
        consumption = {}
        for order in completed:
            drink_name = order['drink_name']
            quantity = order['quantity']
            
            if drink_name in drinks:
                drink = drinks[drink_name]
                ingredients = drink['ingredients']
                
                if isinstance(ingredients, str):
                    ingredients = ingredients.split(',')
                
                for ing in ingredients:
                    ing = ing.strip()
                    # Assume 200ml per drink (this should be in drink config)
                    amount = 200 * quantity
                    consumption[ing] = consumption.get(ing, 0) + amount
        
        return consumption
    
    def export_report_csv(self, filepath: str, days: int = 7):
        """Export analytics report to CSV"""
        orders = self.db.get_order_history(days)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Order ID', 'Date', 'Time', 'Drink', 'Quantity', 
                'Price', 'Total', 'Status', 'Duration (s)'
            ])
            
            # Data
            for order in orders:
                created = datetime.fromisoformat(order['created_at']) if order['created_at'] else None
                writer.writerow([
                    order['id'],
                    created.strftime('%Y-%m-%d') if created else '',
                    created.strftime('%H:%M:%S') if created else '',
                    order['drink_name'],
                    order['quantity'],
                    f"₹{order['price']:.2f}",
                    f"₹{order['price'] * order['quantity']:.2f}",
                    order['status'],
                    f"{order['duration']:.1f}" if order['duration'] else ''
                ])
            
            # Summary
            writer.writerow([])
            writer.writerow(['Summary'])
            writer.writerow(['Total Orders', len(orders)])
            writer.writerow(['Completed', sum(1 for o in orders if o['status'] == 'completed')])
            writer.writerow(['Failed', sum(1 for o in orders if o['status'] == 'failed')])
            writer.writerow(['Revenue', f"₹{sum(o['price'] * o['quantity'] for o in orders if o['status'] == 'completed'):.2f}"])
    
    def get_inventory_predictions(self, days_ahead: int = 7) -> Dict[str, Dict]:
        """Predict when ingredients will run out"""
        # Get consumption rate from last 7 days
        consumption = self.get_ingredient_consumption(7)
        daily_rate = {k: v/7 for k, v in consumption.items()}
        
        # Get current levels
        ingredients = self.db.get_all_ingredients()
        
        predictions = {}
        for ing in ingredients:
            name = ing['name']
            current = ing['current_level']
            rate = daily_rate.get(name, 0)
            
            if rate > 0:
                days_remaining = current / rate
                runout_date = (datetime.now() + timedelta(days=days_remaining)).date()
                
                predictions[name] = {
                    'current_level': current,
                    'daily_consumption': rate,
                    'days_remaining': days_remaining,
                    'estimated_runout': runout_date.isoformat(),
                    'needs_refill': days_remaining < days_ahead
                }
            else:
                predictions[name] = {
                    'current_level': current,
                    'daily_consumption': 0,
                    'days_remaining': float('inf'),
                    'estimated_runout': None,
                    'needs_refill': False
                }
        
        return predictions
    
    @staticmethod
    def _calculate_success_rate(completed: int, total: int) -> float:
        """Calculate success rate percentage"""
        return (completed / total * 100) if total > 0 else 0
