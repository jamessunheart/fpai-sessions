"""
Orchestrator Client
Per INTEGRATION_GUIDE.md - ALL inter-droplet communication goes through Orchestrator 10
Located in services/ per CODE_STANDARDS.md
Filename: app/services/orchestrator.py
"""

import httpx
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.config import settings
from app.utils.logging import get_logger
from app.models.udc import TaskCreate # Import the new model

log = get_logger(__name__)


class OrchestratorClient:
    """
    HTTP client for Orchestrator 10 communication.
    Compliant with the new UDC API reference.
    """
    
    def __init__(self):
        """Initialize Orchestrator client"""
        self.orchestrator_url = settings.orchestrator_url
        self.timeout = settings.orchestrator_timeout
        log.info("orchestrator_client_initialized", url=self.orchestrator_url)
    
    def _create_udc_envelope(
        self,
        payload: Dict[str, Any],
        message_type: str = "command"
    ) -> Dict[str, Any]:
        """
        Creates a standard UDC envelope for a given payload.
        """
        return {
            "message_type": message_type,
            "payload": payload,
            "source": f"droplet-{settings.id}",
            "target": "droplet-10",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": str(uuid.uuid4()),
            "udc_version": "1.0"
        }

    async def _send_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A generic method to send HTTP requests to the orchestrator."""
        url = f"{self.orchestrator_url}{endpoint}"
        headers = {"Authorization": f"Bearer {settings.get_orchestrator_jwt()}"}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, json=data, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            log.error("orchestrator_timeout", endpoint=endpoint, timeout=self.timeout)
        except httpx.HTTPStatusError as e:
            log.error(
                "orchestrator_http_error",
                endpoint=endpoint,
                status_code=e.response.status_code,
                response=e.response.text
            )
        except Exception as e:
            log.error("orchestrator_error", endpoint=endpoint, error=str(e))
        
        return None

    async def create_task(self, task: TaskCreate) -> Optional[Dict[str, Any]]:
        """
        Submits a new task to the orchestrator.
        
        Args:
            task: A TaskCreate Pydantic model instance.
            
        Returns:
            The orchestrator's response or None on failure.
        """
        log.info("creating_task", task_type=task.task_type, capability=task.required_capability)
        udc_envelope = self._create_udc_envelope(payload=task.dict())
        return await self._send_request("POST", "/tasks", udc_envelope)

    async def send_message(self, target_droplet_id: int, message_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sends a direct message to another droplet via the orchestrator.
        This can be used for routing responses back (e.g., to the Voice droplet).

        Args:
            target_droplet_id: The ID of the target droplet.
            message_payload: The data to send in the message.
        
        Returns:
            The orchestrator's response or None on failure.
        """
        log.info("sending_message", target_droplet_id=target_droplet_id)
        
        # The payload for a /message request is the UDC message itself,
        # but with the target set to the final destination droplet.
        message_envelope = {
            "message_type": "command",
            "payload": message_payload,
            "source": f"droplet-{settings.id}",
            "target": f"droplet-{target_droplet_id}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": str(uuid.uuid4()),
            "udc_version": "1.0"
        }
        return await self._send_request("POST", "/message", message_envelope)

    async def send_to_droplet(
        self,
        target_droplet_id: int,
        message_type: str,
        payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Sends a request to a target droplet via orchestrator's /send endpoint.
        
        Args:
            target_droplet_id: The ID of the target droplet.
            message_type: Type of message (e.g., "command").
            payload: The payload data to send.
        
        Returns:
            The orchestrator's response or None on failure.
        """
        log.info("sending_to_droplet", target_droplet_id=target_droplet_id, message_type=message_type)
        
        # Create UDC envelope for /send endpoint
        message_envelope = {
            "message_type": message_type,
            "payload": payload,
            "source": int(settings.id),
            "target": target_droplet_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": str(uuid.uuid4())
        }
        print(message_envelope)
        # Use /send endpoint with query parameters
        endpoint = f"/message"
        return await self._send_request("POST", endpoint, message_envelope)

    async def send_via_orchestrator(
        self,
        target_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        route_back: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a request to a target droplet via orchestrator.
        This is the main method used by chat.py for routing requests.
        
        Args:
            target_id: Target droplet ID (as string)
            action: Endpoint to call (e.g., "/getAll", "/status")
            data: Optional data payload for POST requests
            route_back: Optional route_back parameter for responses
            
        Returns:
            Response from target droplet or None on failure
        """
        log.info(
            "sending_via_orchestrator",
            target_id=target_id,
            action=action,
            has_data=data is not None
        )
        
        # Build payload
        payload = {
            "action": action
        }
        
        if data:
            payload["data"] = data
        
        if route_back:
            payload["route_back"] = route_back
        
        # Send to target droplet via orchestrator
        return await self.send_to_droplet(
            target_droplet_id=int(target_id),
            message_type="command",
            payload=payload
        )

    async def query_multiple_droplets(
        self,
        queries: list,
        route_back: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute multiple queries in parallel.
        Used for "all droplets" type requests.
        
        Args:
            queries: List of query dicts with droplet, endpoint, etc.
            route_back: Optional route_back parameter
            
        Returns:
            Dict mapping droplet_key to result
        """
        import asyncio
        
        tasks = []
        droplet_keys = []
        
        for query in queries:
            droplet_id = query['droplet'].split('_')[1]
            endpoint = query['endpoint']
            data = query.get('extracted_data', {})
            
            tasks.append(
                self.send_via_orchestrator(
                    target_id=droplet_id,
                    action=f"/{endpoint}",
                    data=data if data else None,
                    route_back=route_back
                )
            )
            droplet_keys.append(query['droplet'])
        
        # Execute all queries in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build combined response
        combined = {}
        for i, result in enumerate(results):
            droplet_key = droplet_keys[i]
            if isinstance(result, Exception):
                log.error(f"Query failed for {droplet_key}: {result}")
                combined[droplet_key] = {"error": str(result)}
            else:
                combined[droplet_key] = result
        
        return combined

    async def check_orchestrator_health(self) -> bool:
        """
        Check if Orchestrator is reachable.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.orchestrator_url}/health")
                return response.status_code == 200
        except Exception as e:
            log.warning("orchestrator_health_check_failed", error=str(e))
            return False


# Global orchestrator client instance
orchestrator_client = OrchestratorClient()