"""
Proactive Sensor Network - Continuously monitors for opportunities.

Sensors detect issues and opportunities across:
- Code quality
- Performance
- Business metrics
- Infrastructure
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger("aria.proactive.sensors")


class SensorPriority(Enum):
    """Priority levels for sensor findings."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class SensorCategory(Enum):
    """Categories of sensors."""
    CODE = "code"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"


@dataclass
class SensorFinding:
    """A finding from a sensor scan."""
    sensor_name: str
    category: SensorCategory
    priority: SensorPriority
    
    title: str
    description: str
    
    # Context
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    
    # Action
    suggested_action: Optional[str] = None
    auto_fixable: bool = False
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.8


class Sensor(ABC):
    """Base class for all sensors."""
    
    def __init__(
        self,
        name: str,
        category: SensorCategory,
        interval_seconds: int = 3600
    ):
        self.name = name
        self.category = category
        self.interval_seconds = interval_seconds
        self.last_scan: Optional[datetime] = None
        self.is_active = True
        self.findings: List[SensorFinding] = []
    
    @abstractmethod
    async def scan(self) -> List[SensorFinding]:
        """Perform a scan and return findings."""
        pass
    
    def should_scan(self) -> bool:
        """Check if it's time to scan."""
        if not self.is_active:
            return False
        if self.last_scan is None:
            return True
        return datetime.now() - self.last_scan > timedelta(seconds=self.interval_seconds)


class CodeQualitySensor(Sensor):
    """Detects code quality issues."""
    
    def __init__(self):
        super().__init__(
            name="code_quality",
            category=SensorCategory.CODE,
            interval_seconds=3600  # Every hour
        )
        self.workspace = os.getenv("WORKSPACE_ROOT", "/Users/jamessunheart/FPAI_Cockpit")
    
    async def scan(self) -> List[SensorFinding]:
        """Scan for code quality issues."""
        findings = []
        
        # Check for common issues
        findings.extend(await self._check_todos())
        findings.extend(await self._check_large_files())
        findings.extend(await self._check_duplicates())
        findings.extend(await self._check_complexity())
        
        self.last_scan = datetime.now()
        self.findings = findings
        return findings
    
    async def _check_todos(self) -> List[SensorFinding]:
        """Find TODO/FIXME comments."""
        findings = []
        import subprocess
        
        try:
            result = subprocess.run(
                ["grep", "-rn", "-E", "(TODO|FIXME|HACK|XXX)", 
                 "--include=*.py", "--include=*.js", "--include=*.ts",
                 self.workspace],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            lines = result.stdout.strip().split('\n')[:20]  # Limit results
            
            for line in lines:
                if not line:
                    continue
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    file_path, line_num, content = parts
                    findings.append(SensorFinding(
                        sensor_name=self.name,
                        category=self.category,
                        priority=SensorPriority.LOW,
                        title="Unresolved TODO",
                        description=content.strip()[:100],
                        file_path=file_path,
                        line_number=int(line_num),
                        suggested_action="Review and resolve this TODO",
                        auto_fixable=False
                    ))
        except Exception as e:
            logger.error(f"TODO check failed: {e}")
        
        return findings[:10]  # Limit to top 10
    
    async def _check_large_files(self) -> List[SensorFinding]:
        """Find unusually large files."""
        findings = []
        threshold = 1000  # lines
        
        for root, _, files in os.walk(self.workspace):
            if any(skip in root for skip in [".git", "node_modules", "__pycache__", ".venv"]):
                continue
            
            for filename in files:
                if not filename.endswith(('.py', '.js', '.ts')):
                    continue
                
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r') as f:
                        lines = sum(1 for _ in f)
                    
                    if lines > threshold:
                        findings.append(SensorFinding(
                            sensor_name=self.name,
                            category=self.category,
                            priority=SensorPriority.MEDIUM,
                            title="Large file detected",
                            description=f"{filename} has {lines} lines",
                            file_path=file_path,
                            metric_value=lines,
                            threshold=threshold,
                            suggested_action="Consider splitting into smaller modules",
                            auto_fixable=False
                        ))
                except:
                    pass
        
        return findings[:5]
    
    async def _check_duplicates(self) -> List[SensorFinding]:
        """Find potential duplicate code (simplified)."""
        # This is a simplified check - real duplicate detection is complex
        return []
    
    async def _check_complexity(self) -> List[SensorFinding]:
        """Check for complex functions (simplified)."""
        # Would use cyclomatic complexity analysis
        return []


class PerformanceSensor(Sensor):
    """Monitors performance metrics."""
    
    def __init__(self):
        super().__init__(
            name="performance",
            category=SensorCategory.PERFORMANCE,
            interval_seconds=300  # Every 5 minutes
        )
    
    async def scan(self) -> List[SensorFinding]:
        """Scan for performance issues."""
        findings = []
        
        findings.extend(await self._check_endpoint_latency())
        findings.extend(await self._check_error_rates())
        findings.extend(await self._check_resource_usage())
        
        self.last_scan = datetime.now()
        self.findings = findings
        return findings
    
    async def _check_endpoint_latency(self) -> List[SensorFinding]:
        """Check API endpoint latency."""
        import httpx
        import time
        
        endpoints = [
            ("Aria Command Health", "http://localhost:8750/health"),
            ("AI Brain Health", "http://localhost:8101/health"),
        ]
        
        findings = []
        threshold_ms = 500
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, url in endpoints:
                try:
                    start = time.time()
                    response = await client.get(url)
                    latency_ms = (time.time() - start) * 1000
                    
                    if latency_ms > threshold_ms:
                        findings.append(SensorFinding(
                            sensor_name=self.name,
                            category=self.category,
                            priority=SensorPriority.MEDIUM if latency_ms < 1000 else SensorPriority.HIGH,
                            title=f"Slow endpoint: {name}",
                            description=f"Response time: {latency_ms:.0f}ms (threshold: {threshold_ms}ms)",
                            metric_value=latency_ms,
                            threshold=threshold_ms,
                            suggested_action="Investigate endpoint performance"
                        ))
                except Exception as e:
                    findings.append(SensorFinding(
                        sensor_name=self.name,
                        category=self.category,
                        priority=SensorPriority.HIGH,
                        title=f"Endpoint unreachable: {name}",
                        description=str(e)[:100],
                        suggested_action="Check service status"
                    ))
        
        return findings
    
    async def _check_error_rates(self) -> List[SensorFinding]:
        """Check for elevated error rates."""
        # Would integrate with logging/metrics system
        return []
    
    async def _check_resource_usage(self) -> List[SensorFinding]:
        """Check system resource usage."""
        findings = []
        
        try:
            import psutil
            
            # Memory
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                findings.append(SensorFinding(
                    sensor_name=self.name,
                    category=self.category,
                    priority=SensorPriority.HIGH if memory.percent > 90 else SensorPriority.MEDIUM,
                    title="High memory usage",
                    description=f"Memory at {memory.percent}%",
                    metric_value=memory.percent,
                    threshold=85,
                    suggested_action="Free up memory or scale resources"
                ))
            
            # Disk
            disk = psutil.disk_usage('/')
            if disk.percent > 85:
                findings.append(SensorFinding(
                    sensor_name=self.name,
                    category=self.category,
                    priority=SensorPriority.HIGH if disk.percent > 95 else SensorPriority.MEDIUM,
                    title="High disk usage",
                    description=f"Disk at {disk.percent}%",
                    metric_value=disk.percent,
                    threshold=85,
                    suggested_action="Clean up disk space"
                ))
        except ImportError:
            pass
        
        return findings


class BusinessSensor(Sensor):
    """Monitors business metrics."""
    
    def __init__(self):
        super().__init__(
            name="business",
            category=SensorCategory.BUSINESS,
            interval_seconds=1800  # Every 30 minutes
        )
    
    async def scan(self) -> List[SensorFinding]:
        """Scan for business metric issues."""
        findings = []
        
        findings.extend(await self._check_trading_positions())
        findings.extend(await self._check_revenue_metrics())
        
        self.last_scan = datetime.now()
        self.findings = findings
        return findings
    
    async def _check_trading_positions(self) -> List[SensorFinding]:
        """Check trading positions for issues."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://198.54.123.234:8601/api/positions")
                if response.status_code == 200:
                    data = response.json()
                    positions = data.get("positions", [])
                    
                    findings = []
                    for pos in positions:
                        pnl_pct = pos.get("pnl_percentage", 0)
                        
                        if pnl_pct < -10:
                            findings.append(SensorFinding(
                                sensor_name=self.name,
                                category=self.category,
                                priority=SensorPriority.HIGH,
                                title=f"Large loss: {pos.get('asset', 'Unknown')}",
                                description=f"Position down {abs(pnl_pct):.1f}%",
                                metric_value=pnl_pct,
                                threshold=-10,
                                suggested_action="Review position and stop loss"
                            ))
                    
                    return findings
        except:
            pass
        
        return []
    
    async def _check_revenue_metrics(self) -> List[SensorFinding]:
        """Check revenue and cost metrics."""
        # Would integrate with revenue tracking
        return []


class InfrastructureSensor(Sensor):
    """Monitors infrastructure health."""
    
    def __init__(self):
        super().__init__(
            name="infrastructure",
            category=SensorCategory.INFRASTRUCTURE,
            interval_seconds=120  # Every 2 minutes
        )
    
    async def scan(self) -> List[SensorFinding]:
        """Scan infrastructure for issues."""
        findings = []
        
        findings.extend(await self._check_server_health())
        findings.extend(await self._check_service_status())
        
        self.last_scan = datetime.now()
        self.findings = findings
        return findings
    
    async def _check_server_health(self) -> List[SensorFinding]:
        """Check server health."""
        import httpx
        
        servers = [
            ("Primary (198.54.123.234)", "http://198.54.123.234:8601/health"),
            ("Secondary (local)", "http://localhost:8750/health"),
        ]
        
        findings = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, url in servers:
                try:
                    response = await client.get(url)
                    if response.status_code != 200:
                        findings.append(SensorFinding(
                            sensor_name=self.name,
                            category=self.category,
                            priority=SensorPriority.HIGH,
                            title=f"Server unhealthy: {name}",
                            description=f"Health check returned {response.status_code}",
                            suggested_action="Investigate server issues"
                        ))
                except Exception as e:
                    findings.append(SensorFinding(
                        sensor_name=self.name,
                        category=self.category,
                        priority=SensorPriority.CRITICAL,
                        title=f"Server unreachable: {name}",
                        description=str(e)[:100],
                        suggested_action="Check server connectivity and status"
                    ))
        
        return findings
    
    async def _check_service_status(self) -> List[SensorFinding]:
        """Check critical service status."""
        # Would check systemd services
        return []


class SensorNetwork:
    """Manages all sensors and aggregates findings."""
    
    def __init__(self):
        self.sensors: List[Sensor] = [
            CodeQualitySensor(),
            PerformanceSensor(),
            BusinessSensor(),
            InfrastructureSensor()
        ]
        self.all_findings: List[SensorFinding] = []
        self.last_full_scan: Optional[datetime] = None
    
    async def scan_all(self) -> List[SensorFinding]:
        """Run all sensors and aggregate findings."""
        all_findings = []
        
        for sensor in self.sensors:
            if sensor.should_scan():
                try:
                    findings = await sensor.scan()
                    all_findings.extend(findings)
                except Exception as e:
                    logger.error(f"Sensor {sensor.name} failed: {e}")
        
        # Sort by priority
        all_findings.sort(key=lambda f: f.priority.value, reverse=True)
        
        self.all_findings = all_findings
        self.last_full_scan = datetime.now()
        
        return all_findings
    
    async def scan_category(self, category: SensorCategory) -> List[SensorFinding]:
        """Scan only sensors in a specific category."""
        findings = []
        
        for sensor in self.sensors:
            if sensor.category == category:
                try:
                    findings.extend(await sensor.scan())
                except Exception as e:
                    logger.error(f"Sensor {sensor.name} failed: {e}")
        
        return findings
    
    def get_critical_findings(self) -> List[SensorFinding]:
        """Get only critical and high priority findings."""
        return [f for f in self.all_findings 
                if f.priority in [SensorPriority.CRITICAL, SensorPriority.HIGH]]
    
    def get_auto_fixable(self) -> List[SensorFinding]:
        """Get findings that can be auto-fixed."""
        return [f for f in self.all_findings if f.auto_fixable]


# Singleton instance
_network: Optional[SensorNetwork] = None

def get_sensor_network() -> SensorNetwork:
    """Get or create sensor network instance."""
    global _network
    if _network is None:
        _network = SensorNetwork()
    return _network


