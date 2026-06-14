from fastapi import APIRouter

# Create a router for registry endpoints
router = APIRouter()

# Import routes to attach all registry endpoints to this router
from . import routes  # noqa
