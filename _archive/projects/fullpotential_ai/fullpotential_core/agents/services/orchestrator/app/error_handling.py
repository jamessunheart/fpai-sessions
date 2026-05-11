"""Error handling with UDC-compliant responses."""

from fastapi import HTTPException
from typing import Optional, Dict, Any
from .models import ErrorResponse, ErrorDetail
import logging

log = logging.getLogger(__name__)


class OrchestratorError(Exception):
    """Base exception for Orchestrator errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class DropletNotFoundError(OrchestratorError):
    """Raised when requested droplet doesn't exist."""

    def __init__(self, droplet_name: str, available: list[str]):
        super().__init__(
            code="DROPLET_NOT_FOUND",
            message=f"Droplet '{droplet_name}' not found in registry",
            status_code=400,
            details={
                "requested_droplet": droplet_name,
                "available_droplets": available,
            },
        )


class DropletUnreachableError(OrchestratorError):
    """Raised when droplet doesn't respond after retries."""

    def __init__(
        self,
        droplet_name: str,
        target_url: str,
        retry_count: int,
        last_error: str,
        duration_ms: int,
    ):
        super().__init__(
            code="DROPLET_UNREACHABLE",
            message="Target droplet did not respond after retries",
            status_code=503,
            details={
                "droplet_name": droplet_name,
                "target_url": target_url,
                "retry_count": retry_count,
                "last_error": last_error,
                "total_duration_ms": duration_ms,
            },
        )


class TaskTimeoutError(OrchestratorError):
    """Raised when task exceeds timeout."""

    def __init__(self, task_id: str, timeout_seconds: int):
        super().__init__(
            code="TIMEOUT",
            message=f"Task exceeded {timeout_seconds}s timeout",
            status_code=504,
            details={"task_id": task_id, "timeout_seconds": timeout_seconds},
        )


class InvalidRequestError(OrchestratorError):
    """Raised when request is malformed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="INVALID_REQUEST",
            message=message,
            status_code=400,
            details=details,
        )


class RegistryError(OrchestratorError):
    """Raised when Registry interaction fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="REGISTRY_ERROR",
            message=message,
            status_code=502,
            details=details,
        )


class InternalError(OrchestratorError):
    """Raised for unexpected internal errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            status_code=500,
            details=details,
        )


def format_error_response(error: OrchestratorError) -> tuple[ErrorResponse, int]:
    """Convert OrchestratorError to UDC error response."""
    return (
        ErrorResponse(
            error=ErrorDetail(
                code=error.code,
                message=error.message,
                details=error.details if error.details else None,
            )
        ),
        error.status_code,
    )


def error_to_http_exception(error: OrchestratorError) -> HTTPException:
    """Convert OrchestratorError to FastAPI HTTPException."""
    response, status_code = format_error_response(error)
    return HTTPException(status_code=status_code, detail=response.model_dump())
