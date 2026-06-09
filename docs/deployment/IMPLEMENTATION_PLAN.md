# God Mode Dashboard Implementation Plan

## Phase 1: Data Visualization Foundation (Week 1)

### 1.1 Treasury Analytics Chart Component

**File**: `SERVICES/team-hub/app/static/components/treasury-chart.js`

```javascript
class TreasuryChart {
  constructor(container) {
    this.container = container;
    this.chart = null;
    this.timeframe = '30d';
  }

  async loadData() {
    const response = await fetch(`/api/treasury/analytics?timeframe=${this.timeframe}`);
    const data = await response.json();

    this.render(data);
  }

  render(data) {
    const ctx = this.container.querySelector('canvas').getContext('2d');

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.timestamps.map(ts => new Date(ts).toLocaleDateString()),
        datasets: [{
          label: 'Portfolio Value',
          data: data.portfolio_value,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4
        }, {
          label: 'Drawdown',
          data: data.drawdown,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          tension: 0.4,
          yAxisID: 'y1'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Portfolio Value ($)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Drawdown (%)'
            },
            grid: {
              drawOnChartArea: false,
            },
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              afterLabel: function(context) {
                return `PnL: ${data.pnl[context.dataIndex].toFixed(2)}`;
              }
            }
          }
        }
      }
    });
  }
}
```

**File**: `SERVICES/team-hub/app/main.py` (Add endpoint)

```python
@app.get("/api/treasury/analytics")
async def get_treasury_analytics(timeframe: str = "30d", current_user: auth.CurrentUser = Depends(auth.require_admin)):
    """Get treasury analytics for charts"""

    # Calculate date range
    days = int(timeframe.replace('d', ''))
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get historical data (implement this)
    historical_data = await get_historical_treasury_data(start_date, end_date)

    # Calculate metrics
    portfolio_values = []
    drawdowns = []
    pnl_values = []
    timestamps = []

    current_value = historical_data[0]['total_value'] if historical_data else 373261.36

    for entry in historical_data:
        portfolio_values.append(entry['total_value'])
        pnl_values.append(entry['pnl'])
        timestamps.append(entry['timestamp'])

        # Calculate drawdown
        peak = max(portfolio_values)
        drawdown_pct = (entry['total_value'] - peak) / peak * 100
        drawdowns.append(drawdown_pct)

    return {
        "portfolio_value": portfolio_values,
        "drawdown": drawdowns,
        "pnl": pnl_values,
        "timestamps": timestamps,
        "timeframe": timeframe
    }
```

### 1.2 Alert System Backend

**File**: `SERVICES/team-hub/app/alerts.py`

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import json
import os
from pathlib import Path

@dataclass
class Alert:
    id: str
    type: str
    severity: str
    title: str
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

class AlertEngine:
    def __init__(self):
        self.alerts_file = Path("/opt/fpai/team-hub/alerts.json")
        self.alerts_file.parent.mkdir(exist_ok=True)
        self.rules = self.load_rules()

    def load_rules(self) -> Dict[str, Any]:
        """Load alert rules configuration"""
        rules_file = Path("/opt/fpai/team-hub/alert_rules.json")
        if rules_file.exists():
            with open(rules_file) as f:
                return json.load(f)
        return self.get_default_rules()

    def get_default_rules(self) -> Dict[str, Any]:
        return {
            "LIQUIDATION_RISK": {
                "threshold": 0.05,  # 5% from liquidation
                "severity": "CRITICAL",
                "channels": ["dashboard", "email"],
                "cooldown": 3600  # 1 hour
            },
            "TREASURY_RUNWAY": {
                "threshold": 30,  # days
                "severity": "ALERT",
                "channels": ["dashboard"]
            },
            "GPU_UTILIZATION": {
                "threshold": 0.3,  # 30% utilization
                "severity": "WARNING",
                "channels": ["dashboard"]
            }
        }

    async def check_treasury_alerts(self, treasury_data: Dict[str, Any]) -> List[Alert]:
        """Check treasury data for alert conditions"""
        alerts = []

        # Liquidation risk check
        for position in treasury_data.get("leveraged_positions", []):
            distance_pct = position.get("liquidation_distance_percent", 100)
            rule = self.rules.get("LIQUIDATION_RISK", {})

            if distance_pct <= (rule.get("threshold", 0.05) * 100):
                alerts.append(Alert(
                    id=f"liq_{position['asset']}_{int(datetime.utcnow().timestamp())}",
                    type="LIQUIDATION_RISK",
                    severity=rule.get("severity", "CRITICAL"),
                    title=f"{position['asset']} Liquidation Risk",
                    message=f"{position['asset']} position is {distance_pct:.1f}% from liquidation price",
                    context={
                        "asset": position["asset"],
                        "distance_percent": distance_pct,
                        "current_price": position["current_price"],
                        "liquidation_price": position["liquidation_price"]
                    },
                    timestamp=datetime.utcnow()
                ))

        # Runway check
        runway_days = treasury_data.get("runway_days", 365)
        rule = self.rules.get("TREASURY_RUNWAY", {})

        if runway_days <= rule.get("threshold", 30):
            alerts.append(Alert(
                id=f"runway_{int(datetime.utcnow().timestamp())}",
                type="TREASURY_RUNWAY",
                severity=rule.get("severity", "ALERT"),
                title="Low Treasury Runway",
                message=f"Treasury runway is {runway_days} days - consider cost reduction",
                context={
                    "runway_days": runway_days,
                    "burn_rate": treasury_data.get("burn_rate", 0),
                    "threshold": rule.get("threshold", 30)
                },
                timestamp=datetime.utcnow()
            ))

        return alerts

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts"""
        all_alerts = self.load_alerts()
        active = [a for a in all_alerts if not a.get("resolved", False)]
        return active

    def load_alerts(self) -> List[Dict[str, Any]]:
        """Load alerts from storage"""
        if self.alerts_file.exists():
            with open(self.alerts_file) as f:
                return json.load(f)
        return []

    def save_alerts(self, alerts: List[Dict[str, Any]]):
        """Save alerts to storage"""
        with open(self.alerts_file, 'w') as f:
            json.dump(alerts, f, indent=2, default=str)
```

### 1.3 Mobile Layout Update

**File**: `SERVICES/team-hub/app/static/index.html` (Add mobile styles)

```html
<!-- Add to <head> -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
/* Mobile-first responsive design */
@media (max-width: 768px) {
  .consciousness-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
  }

  .consciousness-panel {
    padding: 0.75rem;
  }

  .panel-title {
    font-size: 0.875rem;
  }

  .metric-value {
    font-size: 1.25rem;
  }

  .alerts-mobile {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.95);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding: 1rem;
    z-index: 1000;
  }

  .mobile-nav {
    display: flex;
    justify-content: space-around;
    padding: 0.5rem;
    background: rgba(0, 0, 0, 0.9);
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 999;
  }
}

/* Touch interactions */
.touch-target {
  min-height: 44px;
  min-width: 44px;
}

.swipe-container {
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}

.swipe-panel {
  scroll-snap-align: start;
  flex-shrink: 0;
  width: 100vw;
}
</style>
```

## Phase 2: Intelligence Enhancement (Week 3)

### 2.1 Actionable Diamonds System

**File**: `SERVICES/team-hub/app/diamonds.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

@dataclass
class Evidence:
    source: str
    confidence: float
    data: Dict[str, Any]
    explanation: str

@dataclass
class DiamondAction:
    id: str
    label: str
    action_type: str  # 'EXECUTE', 'REVIEW', 'MONITOR', 'IGNORE'
    payload: Dict[str, Any]
    estimated_value: float
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'
    requires_approval: bool = False

@dataclass
class IntelligenceDiamond:
    id: str
    title: str
    insight: str
    confidence: float
    category: str
    actions: List[DiamondAction]
    context: Dict[str, Any]
    evidence: List[Evidence]
    timestamp: datetime
    user_rating: Optional[str] = None  # 'useful', 'noise', 'action_taken'
    outcome: Optional[Dict[str, Any]] = None

class DiamondEngine:
    def __init__(self):
        self.diamonds_file = Path("/opt/fpai/team-hub/diamonds.json")

    async def generate_actionable_diamond(self, insight_data: Dict[str, Any]) -> IntelligenceDiamond:
        """Convert raw insight into actionable diamond"""

        # Analyze the insight
        analysis = await self.analyze_insight(insight_data)

        # Generate specific actions
        actions = await self.generate_actions(analysis)

        # Gather evidence
        evidence = await self.gather_evidence(analysis)

        diamond = IntelligenceDiamond(
            id=f"diamond_{int(datetime.utcnow().timestamp())}_{hash(insight_data['content']) % 1000}",
            title=self.generate_title(analysis),
            insight=insight_data['content'],
            confidence=insight_data.get('confidence', 0.5),
            category=insight_data.get('category', 'general'),
            actions=actions,
            context={
                'data_source': insight_data.get('source', 'unknown'),
                'time_horizon': self.determine_time_horizon(analysis),
                'impact_level': self.assess_impact(analysis)
            },
            evidence=evidence,
            timestamp=datetime.utcnow()
        )

        return diamond

    async def generate_actions(self, analysis: Dict[str, Any]) -> List[DiamondAction]:
        """Generate specific, executable actions based on insight analysis"""

        actions = []

        insight_type = analysis.get('type')

        if insight_type == 'liquidation_risk':
            actions.append(DiamondAction(
                id=f"reduce_{analysis['asset']}_exposure",
                label=f"Reduce {analysis['asset']} exposure by 20%",
                action_type="EXECUTE",
                payload={
                    "action": "adjust_position",
                    "asset": analysis['asset'],
                    "reduction_percent": 20,
                    "reason": "Reduce liquidation risk"
                },
                estimated_value=analysis.get('potential_savings', 0),
                risk_level="MEDIUM",
                requires_approval=True
            ))

        elif insight_type == 'gpu_inefficiency':
            actions.append(DiamondAction(
                id="schedule_gpu_shutdown",
                label="Schedule GPU shutdown during low utilization",
                action_type="EXECUTE",
                payload={
                    "action": "schedule_shutdown",
                    "gpu_id": analysis['gpu_id'],
                    "schedule": analysis['optimal_schedule']
                },
                estimated_value=analysis.get('cost_savings', 0),
                risk_level="LOW"
            ))

        elif insight_type == 'treasury_runway':
            actions.append(DiamondAction(
                id="optimize_costs",
                label="Review and optimize monthly costs",
                action_type="REVIEW",
                payload={
                    "action": "cost_analysis",
                    "focus_area": "gpu_compute"
                },
                estimated_value=analysis.get('runway_extension_days', 0) * analysis.get('daily_burn', 0),
                risk_level="LOW"
            ))

        return actions

    def generate_title(self, analysis: Dict[str, Any]) -> str:
        """Generate a clear, actionable title"""
        titles = {
            'liquidation_risk': f"{analysis['asset']} Liquidation Risk: Act Now",
            'gpu_inefficiency': f"GPU Cost Optimization: Save ${analysis.get('cost_savings', 0):.0f}/month",
            'treasury_runway': f"Extend Treasury Runway {analysis.get('runway_extension_days', 0)} Days",
            'intelligence_opportunity': f"Intelligence ROI: {analysis.get('multiplier', 1):.1f}x Return"
        }

        return titles.get(analysis.get('type', 'general'), "Strategic Insight Available")

    async def analyze_insight(self, insight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze raw insight to determine type and parameters"""

        content = insight_data.get('content', '').lower()

        if 'liquidation' in content or 'risk' in content:
            # Extract asset and risk level from content
            return {
                'type': 'liquidation_risk',
                'asset': self.extract_asset_from_content(content),
                'risk_level': 'HIGH',
                'potential_savings': 10000  # Example value
            }

        elif 'gpu' in content or 'utilization' in content:
            return {
                'type': 'gpu_inefficiency',
                'gpu_id': self.extract_gpu_from_content(content),
                'cost_savings': 500,
                'optimal_schedule': 'off-peak hours'
            }

        elif 'runway' in content or 'treasury' in content:
            return {
                'type': 'treasury_runway',
                'runway_extension_days': 30,
                'daily_burn': 1200
            }

        return {'type': 'general'}

    def extract_asset_from_content(self, content: str) -> str:
        """Extract asset symbol from insight content"""
        # Simple extraction - could be enhanced with NLP
        assets = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        for asset in assets:
            if asset in content.upper():
                return asset
        return 'UNKNOWN'
```

## Phase 3: Integration & Testing (Week 5)

### 3.1 Integration Test Suite

**File**: `tests/test_god_mode_enhancements.py`

```python
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

class TestGodModeEnhancements:
    @pytest.mark.asyncio
    async def test_treasury_analytics_endpoint(self):
        """Test treasury analytics API returns proper chart data"""
        from app.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Mock authenticated user
        with patch('app.auth.require_admin', return_value=Mock(id="test_user")):
            response = client.get("/api/treasury/analytics?timeframe=30d")

            assert response.status_code == 200
            data = response.json()

            assert "portfolio_value" in data
            assert "drawdown" in data
            assert "pnl" in data
            assert "timestamps" in data
            assert len(data["portfolio_value"]) > 0

    @pytest.mark.asyncio
    async def test_alert_engine_liquidation_detection(self):
        """Test alert engine detects liquidation risk"""
        from app.alerts import AlertEngine, Alert

        engine = AlertEngine()

        # Mock treasury data with high liquidation risk
        treasury_data = {
            "leveraged_positions": [{
                "asset": "BTC",
                "liquidation_distance_percent": 3.0,  # 3% from liquidation
                "current_price": 89707.7,
                "liquidation_price": 72559
            }]
        }

        alerts = await engine.check_treasury_alerts(treasury_data)

        assert len(alerts) > 0
        alert = alerts[0]
        assert alert.type == "LIQUIDATION_RISK"
        assert alert.severity == "CRITICAL"
        assert "BTC" in alert.title

    @pytest.mark.asyncio
    async def test_diamond_action_generation(self):
        """Test diamond engine generates actionable insights"""
        from app.diamonds import DiamondEngine, IntelligenceDiamond

        engine = DiamondEngine()

        # Mock insight data
        insight_data = {
            "content": "BTC position is approaching liquidation price. Distance: 3.0%",
            "confidence": 0.85,
            "category": "risk",
            "source": "treasury_monitor"
        }

        diamond = await engine.generate_actionable_diamond(insight_data)

        assert isinstance(diamond, IntelligenceDiamond)
        assert "BTC" in diamond.title
        assert "Liquidation" in diamond.title
        assert len(diamond.actions) > 0

        # Check first action is executable
        action = diamond.actions[0]
        assert action.action_type in ["EXECUTE", "REVIEW", "MONITOR"]
        assert "payload" in action.__dict__
        assert isinstance(action.estimated_value, (int, float))

    @pytest.mark.asyncio
    async def test_mobile_layout_responsive(self):
        """Test mobile layout renders correctly"""
        # This would test the HTML/CSS rendering
        # For now, just verify mobile classes exist in template
        pass

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test dashboard performance with concurrent users"""
        import aiohttp
        import asyncio

        async def fetch_dashboard(session, user_id):
            async with session.get(f"http://localhost:8355/dashboard?user={user_id}") as response:
                return response.status

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_dashboard(session, f"user_{i}") for i in range(10)]
            results = await asyncio.gather(*tasks)

            # All requests should succeed
            assert all(status == 200 for status in results)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Deployment Checklist

### Pre-Deployment
- [ ] Run full test suite
- [ ] Backup current dashboard
- [ ] Verify API endpoints respond
- [ ] Test mobile layout on devices

### Deployment Steps
1. Deploy backend API changes
2. Deploy frontend component updates
3. Update nginx configuration if needed
4. Restart services
5. Verify all endpoints work
6. Test mobile responsiveness

### Post-Deployment
- [ ] Monitor error logs for 24 hours
- [ ] Verify alert system triggers correctly
- [ ] Test diamond action execution
- [ ] Check chart loading performance
- [ ] Validate mobile experience












