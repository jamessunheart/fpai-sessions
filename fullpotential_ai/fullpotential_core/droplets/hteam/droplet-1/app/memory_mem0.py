from __future__ import annotations
import os
import time
import requests
from typing import Optional


class MemoryMem0:
    """
    Mem0 API adapter for persistent memory storage.
    
    Handles interaction with the Mem0 API for storing, reflecting, and managing
    memories with proper authentication and request formatting.
    
    Reference: https://docs.mem0.ai/api-reference/memory/add-memories
    """

    BASE_URL = "https://api.mem0.ai/v1"
    DEFAULT_USER_ID = "default_user"
    REQUEST_TIMEOUT = 15

    def __init__(
        self,
        api_key: Optional[str] = None,
        org_id: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """Initialize the Mem0 client with API credentials."""
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MEM0_API_KEY environment variable is not set. "
                "Get your API key from https://app.mem0.ai/dashboard/api-keys"
            )
        
        self.org_id = org_id or os.getenv("MEM0_ORG_ID")
        self.project_id = project_id or os.getenv("MEM0_PROJECT_ID")
        
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def _post(self, endpoint: str, data: dict, params: Optional[dict] = None) -> dict:
        """
        Make a POST request to the Mem0 API.
        
        Args:
            endpoint: API endpoint path (e.g., "memories")
            data: JSON payload for the request body
            params: Query parameters for the request
            
        Returns:
            Parsed JSON response from the API
            
        Raises:
            HTTPError: If the API request fails
        """
        url = f"{self.BASE_URL}/{endpoint}"
        query_params = params or {}
        
        # Add org_id and project_id as query parameters if available
        if self.org_id:
            query_params["org_id"] = self.org_id
        if self.project_id:
            query_params["project_id"] = self.project_id
        
        response = requests.post(
            url,
            headers=self.headers,
            json=data,
            params=query_params,
            timeout=self.REQUEST_TIMEOUT
        )
        
        if not response.ok:
            self._handle_error(response)
        
        response.raise_for_status()
        return response.json()

    def _handle_error(self, response: requests.Response) -> None:
        """Handle API errors with appropriate error messages."""
        if response.status_code == 401:
            error_msg = (
                "HTTP 401: Invalid API key. "
                "Please verify your MEM0_API_KEY is correct. "
                "Get your API key from https://app.mem0.ai/dashboard/api-keys"
            )
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
        
        raise requests.exceptions.HTTPError(error_msg, response=response)

    def _normalize_identifier(self, value: Optional[str]) -> Optional[str]:
        """Normalize identifier by stripping whitespace."""
        return value.strip() if value and value.strip() else None

    def _build_identifier_params(
        self,
        user_id: Optional[str],
        agent_id: Optional[str],
        app_id: Optional[str]
    ) -> tuple[dict, dict]:
        """
        Build identifier parameters for both payload and query params.
        
        The API requires at least one identifier (user_id, agent_id, or app_id)
        and validates them as query parameters (filters).
        
        Returns:
            Tuple of (payload_dict, query_params_dict) with identifier fields
        """
        payload = {}
        query_params = {}
        
        # Check identifiers in priority order
        if user_id := self._normalize_identifier(user_id):
            payload["user_id"] = user_id
            query_params["user_id"] = user_id
        elif agent_id := self._normalize_identifier(agent_id):
            payload["agent_id"] = agent_id
            query_params["agent_id"] = agent_id
        elif app_id := self._normalize_identifier(app_id):
            payload["app_id"] = app_id
            query_params["app_id"] = app_id
        else:
            # Use default if none provided
            payload["user_id"] = self.DEFAULT_USER_ID
            query_params["user_id"] = self.DEFAULT_USER_ID
        
        return payload, query_params

    def store(
        self,
        role: str,
        content: str,
        tags: Optional[list] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        version: Optional[str] = None
    ) -> dict:
        """
        Store a memory in Mem0.
        
        Args:
            role: Message role (e.g., "user", "assistant")
            content: Message content to store
            tags: Optional list of tags for categorization
            user_id: Optional user identifier (required if agent_id/app_id not provided)
            agent_id: Optional agent identifier
            app_id: Optional application identifier
            version: Optional API version ("v2" recommended, default is "v1")
            
        Returns:
            API response containing stored memory data
        """
        # Build payload with messages
        payload = {
            "messages": [{"role": role, "content": content}],
            "metadata": {"ts": time.time()}
        }
        
        # Add identifier to both payload and query params (required by API)
        identifier_payload, query_params = self._build_identifier_params(
            user_id, agent_id, app_id
        )
        payload.update(identifier_payload)
        
        # Add optional fields
        if version:
            payload["version"] = version
        
        if self.org_id:
            payload["org_id"] = self.org_id
        if self.project_id:
            payload["project_id"] = self.project_id
        
        if tags:
            payload["metadata"]["tags"] = tags

        return self._post("memories", payload, params=query_params)

    def reflect(
        self,
        summary: str,
        insights: list[str],
        decisions: list[str],
        user_id: Optional[str] = None
    ) -> dict:
        """
        Store a reflection in Mem0.
        
        Args:
            summary: Reflection summary
            insights: List of insights
            decisions: List of decisions
            user_id: Optional user identifier
            
        Returns:
            API response containing stored reflection
        """
        text = (
            f"Reflection:\n"
            f"Summary: {summary}\n"
            f"Insights: {insights}\n"
            f"Decisions: {decisions}"
        )
        return self.store("reflection", text, tags=["reflection"], user_id=user_id)

    def intent(
        self,
        intent: str,
        horizon_min: int,
        tags: Optional[list] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        Store an intent in Mem0.
        
        Args:
            intent: Intent description
            horizon_min: Time horizon in minutes
            tags: Optional list of tags (defaults to ["intent"])
            user_id: Optional user identifier
            
        Returns:
            API response containing stored intent
        """
        text = f"Intent: {intent} (horizon {horizon_min}m)"
        return self.store(
            "intent",
            text,
            tags=tags or ["intent"],
            user_id=user_id
        )
