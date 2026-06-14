#!/usr/bin/env python3
"""
I MATCH Revenue Tracker
Monitors matches, conversions, and revenue in real-time
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List

class IMatchRevenueTracker:
    """Track I MATCH revenue metrics"""
    
    def __init__(self, api_url="http://198.54.123.234:8401"):
        self.api_url = api_url
        
    def get_current_stats(self) -> Dict:
        """Get current system state from I MATCH API"""
        try:
            response = requests.get(f"{self.api_url}/state", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return {}
    
    def calculate_revenue_metrics(self, stats: Dict) -> Dict:
        """Calculate revenue metrics from stats"""
        
        # Extract data
        customers = stats.get("customers_total", 0)
        providers = stats.get("providers_total", 0)
        matches = stats.get("matches_total", 0)
        revenue_usd = stats.get("revenue_total_usd", 0.0)
        
        # Revenue projections based on matches
        # Assume: $400/match average, 15% close rate
        avg_match_value = 400
        close_rate = 0.15
        
        potential_revenue = matches * avg_match_value * close_rate
        actual_revenue = revenue_usd
        conversion_rate = (actual_revenue / potential_revenue * 100) if potential_revenue > 0 else 0
        
        # Month 1 target: 10 matches = $600 revenue (15% close)
        # Month 6 target: 100 matches = $6,000 revenue
        month1_target_matches = 10
        month1_target_revenue = month1_target_matches * avg_match_value * close_rate
        
        month6_target_matches = 100
        month6_target_revenue = month6_target_matches * avg_match_value * close_rate
        
        # Progress to targets
        match_progress = (matches / month1_target_matches * 100) if month1_target_matches > 0 else 0
        revenue_progress = (actual_revenue / month1_target_revenue * 100) if month1_target_revenue > 0 else 0
        
        return {
            "current": {
                "customers": customers,
                "providers": providers,
                "matches": matches,
                "actual_revenue": actual_revenue,
                "potential_revenue": round(potential_revenue, 2)
            },
            "metrics": {
                "avg_match_value": avg_match_value,
                "close_rate_pct": close_rate * 100,
                "conversion_rate_pct": round(conversion_rate, 2)
            },
            "targets": {
                "month1_matches": month1_target_matches,
                "month1_revenue": month1_target_revenue,
                "month6_matches": month6_target_matches,
                "month6_revenue": month6_target_revenue
            },
            "progress": {
                "match_progress_pct": round(min(match_progress, 100), 1),
                "revenue_progress_pct": round(min(revenue_progress, 100), 1)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def print_dashboard(self):
        """Print revenue dashboard to console"""
        print("\n" + "="*60)
        print("I MATCH REVENUE DASHBOARD")
        print("="*60)
        
        stats = self.get_current_stats()
        if not stats:
            print("❌ Unable to fetch stats from I MATCH API")
            return
        
        metrics = self.calculate_revenue_metrics(stats)
        
        print("\n📊 CURRENT STATE:")
        print(f"  Customers: {metrics['current']['customers']}")
        print(f"  Providers: {metrics['current']['providers']}")
        print(f"  Matches: {metrics['current']['matches']}")
        print(f"  Actual Revenue: ${metrics['current']['actual_revenue']:.2f}")
        print(f"  Potential Revenue: ${metrics['current']['potential_revenue']:.2f}")
        
        print("\n💰 REVENUE METRICS:")
        print(f"  Avg Match Value: ${metrics['metrics']['avg_match_value']}")
        print(f"  Close Rate: {metrics['metrics']['close_rate_pct']}%")
        print(f"  Conversion: {metrics['metrics']['conversion_rate_pct']}%")
        
        print("\n🎯 TARGETS:")
        print(f"  Month 1: {metrics['targets']['month1_matches']} matches → ${metrics['targets']['month1_revenue']:.0f} revenue")
        print(f"  Month 6: {metrics['targets']['month6_matches']} matches → ${metrics['targets']['month6_revenue']:.0f} revenue")
        
        print("\n📈 PROGRESS:")
        print(f"  Match Progress: {metrics['progress']['match_progress_pct']}%")
        print(f"  Revenue Progress: {metrics['progress']['revenue_progress_pct']}%")
        
        # Progress bar
        match_bar = "█" * int(metrics['progress']['match_progress_pct'] / 10) + "░" * (10 - int(metrics['progress']['match_progress_pct'] / 10))
        revenue_bar = "█" * int(metrics['progress']['revenue_progress_pct'] / 10) + "░" * (10 - int(metrics['progress']['revenue_progress_pct'] / 10))
        
        print(f"\n  Matches:  [{match_bar}] {metrics['progress']['match_progress_pct']}%")
        print(f"  Revenue:  [{revenue_bar}] {metrics['progress']['revenue_progress_pct']}%")
        
        print("\n" + "="*60)
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        return metrics
    
    def save_snapshot(self, metrics: Dict, filepath="/tmp/imatch_revenue_snapshot.json"):
        """Save revenue snapshot to file"""
        with open(filepath, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"✅ Snapshot saved to {filepath}")

if __name__ == "__main__":
    tracker = IMatchRevenueTracker()
    metrics = tracker.print_dashboard()
    if metrics:
        tracker.save_snapshot(metrics)
