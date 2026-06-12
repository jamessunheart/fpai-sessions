"""
Monitor Agent - Specialized agent for system health monitoring.

Uses Ollama (local, free) for fast, always-on monitoring.
"""

import logging
import time
from datetime import datetime

from .base import Agent, AgentSpecialty, Task, AgentOpinion, ExecutionResult

logger = logging.getLogger("aria.agents.monitor")


class MonitorAgent(Agent):
    """
    Monitor Agent - Monitors system health and performance.
    
    Strengths:
    - Fast response (local model)
    - Always available
    - Resource-efficient
    - Continuous monitoring
    """
    
    def __init__(self):
        super().__init__(
            name="monitor",
            specialty=AgentSpecialty.MONITOR,
            model="ollama/llama3.2",  # Local, fast, free
            description="Monitors system health and detects issues"
        )
        
        self.system_prompt = """You are the Monitor Agent in the ARIA Sovereign system.
Your role is to assess system health and detect issues.

Core responsibilities:
1. Monitor service health
2. Detect anomalies
3. Track resource usage
4. Alert on issues

Health indicators:
- Service response times
- Error rates
- Resource utilization (CPU, memory, disk)
- API availability
- Database connectivity

Output your assessment as JSON:
{
    "healthy": true/false,
    "confidence": 0.0-1.0,
    "issues_detected": [{"severity": "critical/warning/info", "description": "..."}],
    "resource_status": {"cpu": "ok/warning/critical", "memory": "...", "disk": "..."},
    "recommendations": ["action1"],
    "summary": "brief status"
}"""
        
        # Lower threshold for faster decisions
        self.confidence_threshold = 0.6
    
    async def evaluate(self, task: Task) -> AgentOpinion:
        """Evaluate system health status."""
        start_time = time.time()
        
        try:
            # Get system status
            health_data = await self._get_system_health()
            
            prompt = f"""Assess system health based on this data:

{health_data}

Task context: {task.description}

Provide your assessment as JSON."""

            response = await self._call_llm(prompt, self.system_prompt)
            
            assessment = self._parse_assessment(response)
            
            confidence = assessment.get("confidence", 0.7)
            
            # Check for critical issues
            critical = [i for i in assessment.get("issues_detected", []) 
                       if i.get("severity") == "critical"]
            warnings = [i for i in assessment.get("issues_detected", []) 
                       if i.get("severity") == "warning"]
            
            if critical:
                recommendation = "reject"
                confidence *= 0.3
            elif warnings:
                recommendation = "modify"
                confidence *= 0.7
            elif assessment.get("healthy", True):
                recommendation = "approve"
            else:
                recommendation = "defer"
            
            concerns = [f"[{i.get('severity', '').upper()}] {i.get('description', '')}" 
                       for i in assessment.get("issues_detected", [])]
            
            opinion = AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=min(confidence, 1.0),
                recommendation=recommendation,
                reasoning=assessment.get("summary", "Health check complete"),
                concerns=concerns[:5],
                suggestions=assessment.get("recommendations", [])[:3],
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
            
            self.total_evaluations += 1
            self.last_action = datetime.now()
            
            return opinion
            
        except Exception as e:
            logger.error(f"Monitor evaluation failed: {e}")
            # Monitor should be conservative on failure
            return AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=0.4,
                recommendation="defer",
                reasoning=f"Health check failed: {str(e)}",
                concerns=["Could not complete health assessment"],
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def execute(self, task: Task) -> ExecutionResult:
        """Execute a monitoring/health check task."""
        start_time = datetime.now()
        
        try:
            self._current_tasks += 1
            
            # Run health checks
            health = await self._get_system_health()
            
            self.total_executions += 1
            self.last_action = datetime.now()
            
            return ExecutionResult(
                task_id=task.id,
                success=True,
                output=health,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
            
        except Exception as e:
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error=str(e),
                started_at=start_time
            )
        finally:
            self._current_tasks -= 1
    
    async def _get_system_health(self) -> str:
        """Get current system health data."""
        import asyncio
        
        health_parts = []
        
        # Check local resources
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_parts.append(f"""Local System (Secondary Server):
- CPU: {cpu}%
- Memory: {memory.percent}% ({memory.available // (1024**3)}GB available)
- Disk: {disk.percent}% ({disk.free // (1024**3)}GB free)""")
        except ImportError:
            health_parts.append("psutil not available for local metrics")
        except Exception as e:
            health_parts.append(f"Local metrics error: {e}")
        
        # Check key services
        import httpx
        
        services = [
            ("AI Brain", "http://localhost:8101/health"),
            ("Aria Command", "http://localhost:8750/health"),
            ("Ollama", "http://localhost:11434/api/tags"),
        ]
        
        health_parts.append("\nService Status:")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in services:
                try:
                    response = await client.get(url)
                    status = "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
                except httpx.TimeoutException:
                    status = "TIMEOUT"
                except Exception as e:
                    status = f"ERROR: {str(e)[:30]}"
                
                health_parts.append(f"- {name}: {status}")
        
        # Check primary server
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://198.54.123.234:8601/health")
                primary_status = "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
        except:
            primary_status = "UNREACHABLE"
        
        health_parts.append(f"\nPrimary Server: {primary_status}")
        
        return "\n".join(health_parts)
    
    def _parse_assessment(self, response: str) -> dict:
        """Parse health assessment response."""
        import json
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            return json.loads(json_str)
        except:
            return {
                "healthy": True,
                "confidence": 0.6,
                "summary": "Assessment parsed from text",
                "issues_detected": []
            }


