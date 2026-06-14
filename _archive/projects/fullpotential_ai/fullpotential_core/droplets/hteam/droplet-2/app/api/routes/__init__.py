from .health import router as health_router
from .message import router as message_router
from .management import router as management_router
from .emergency import router as emergency_router
from .airtable import router as airtable_router

__all__ = ["health_router", "message_router", "management_router", "emergency_router", "airtable_router"]