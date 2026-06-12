"""
N8N CLIENT - Motion Layer
=========================

Connects Aria to n8n for workflow automation.

n8n is the "motion layer" - it executes actions based on rules.
Rules live in /core (versioned, auditable). n8n is muscle, not brain.

Usage:
    from integrations.n8n_client import get_n8n_client
    
    client = get_n8n_client()
    
    # Trigger a workflow
    await client.trigger_webhook("metric-alert", {"metric": "stress", "value": 75})
    
    # Check workflow status
    status = await client.get_workflow_status("coherence-guardian")
"""

import os
import logging
import httpx
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger("aria.integrations.n8n")


@dataclass
class N8NConfig:
    """N8N connection configuration."""
    base_url: str
    api_key: Optional[str] = None
    enabled: bool = True


class N8NClient:
    """
    Client for n8n workflow operations.
    
    Handles:
    - Triggering webhooks
    - Checking workflow status
    - Managing automations
    """
    
    def __init__(self, config: Optional[N8NConfig] = None):
        self.config = config or self._load_config()
        self.enabled = self.config.enabled
    
    def _load_config(self) -> N8NConfig:
        """Load config from environment."""
        base_url = os.getenv("N8N_URL", "http://162.0.208.88:5678")
        api_key = os.getenv("N8N_API_KEY", "")  # Optional - for secured instances
        enabled = True  # n8n is now deployed
        
        return N8NConfig(base_url=base_url, api_key=api_key, enabled=enabled)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-N8N-API-KEY"] = self.config.api_key
        return headers
    
    # ═══════════════════════════════════════════════════════════════════
    # WEBHOOK TRIGGERS
    # ═══════════════════════════════════════════════════════════════════
    
    async def trigger_webhook(
        self,
        webhook_path: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger an n8n webhook.
        
        Args:
            webhook_path: The webhook path (e.g., "metric-alert")
            payload: Data to send to the webhook
        
        Returns:
            Response from n8n
        """
        if not self.enabled:
            return {"status": "disabled", "message": "n8n integration not enabled"}
        
        url = f"{self.config.base_url}/webhook/{webhook_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30
                )
                
                if response.status_code == 200:
                    return {
                        "status": "triggered",
                        "response": response.json() if response.content else {}
                    }
                else:
                    return {
                        "status": "error",
                        "code": response.status_code,
                        "message": response.text
                    }
        except Exception as e:
            logger.error(f"Failed to trigger webhook {webhook_path}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def trigger_test_webhook(
        self,
        webhook_path: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger an n8n test webhook (for workflows in test mode).
        """
        if not self.enabled:
            return {"status": "disabled"}
        
        url = f"{self.config.base_url}/webhook-test/{webhook_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30
                )
                return {
                    "status": "triggered" if response.status_code == 200 else "error",
                    "code": response.status_code
                }
        except Exception as e:
            logger.error(f"Failed to trigger test webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    # ═══════════════════════════════════════════════════════════════════
    # WORKFLOW MANAGEMENT (requires API key)
    # ═══════════════════════════════════════════════════════════════════
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows (requires API key)."""
        if not self.enabled or not self.config.api_key:
            return []
        
        url = f"{self.config.base_url}/api/v1/workflows"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json().get("data", [])
                return []
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow."""
        if not self.enabled or not self.config.api_key:
            return None
        
        url = f"{self.config.base_url}/api/v1/workflows/{workflow_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return None
    
    async def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow."""
        if not self.enabled or not self.config.api_key:
            return False
        
        url = f"{self.config.base_url}/api/v1/workflows/{workflow_id}/activate"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    timeout=10
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to activate workflow: {e}")
            return False
    
    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """Deactivate a workflow."""
        if not self.enabled or not self.config.api_key:
            return False
        
        url = f"{self.config.base_url}/api/v1/workflows/{workflow_id}/deactivate"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    timeout=10
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to deactivate workflow: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # PREDEFINED WEBHOOK TRIGGERS
    # ═══════════════════════════════════════════════════════════════════
    
    async def alert_metric_threshold(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: str = "warning"
    ) -> Dict[str, Any]:
        """Trigger alert for metric threshold crossing."""
        return await self.trigger_webhook("metric-alert", {
            "metric": metric_name,
            "value": current_value,
            "threshold": threshold,
            "severity": severity,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        })
    
    async def alert_coherence_drop(
        self,
        current_coherence: float,
        baseline: float
    ) -> Dict[str, Any]:
        """Trigger alert for coherence drop below baseline."""
        return await self.trigger_webhook("coherence-alert", {
            "current": current_coherence,
            "baseline": baseline,
            "delta": current_coherence - baseline,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        })
    
    async def notify_steward(
        self,
        message: str,
        channel: str = "telegram",
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Send notification to steward via n8n."""
        return await self.trigger_webhook("notify-steward", {
            "message": message,
            "channel": channel,
            "priority": priority,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        })
    
    async def log_governance_event(
        self,
        event_type: str,
        action: str,
        result: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log governance event via n8n."""
        return await self.trigger_webhook("governance-log", {
            "event_type": event_type,
            "action": action,
            "result": result,
            "details": details,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        })
    
    # ═══════════════════════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════════════════════
    
    async def health_check(self) -> Dict[str, Any]:
        """Check n8n health."""
        if not self.enabled:
            return {"status": "disabled"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.base_url}/healthz",
                    timeout=5
                )
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "code": response.status_code
                }
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get n8n connection status."""
        health = await self.health_check()
        return {
            "enabled": self.enabled,
            "base_url": self.config.base_url,
            "has_api_key": bool(self.config.api_key),
            "health": health
        }


# Singleton instance
_n8n_client: Optional[N8NClient] = None


def get_n8n_client() -> N8NClient:
    """Get the singleton N8NClient instance."""
    global _n8n_client
    if _n8n_client is None:
        _n8n_client = N8NClient()
    return _n8n_client


