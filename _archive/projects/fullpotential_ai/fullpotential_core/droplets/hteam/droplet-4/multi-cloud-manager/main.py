"""
Multi-Cloud Droplet Manager - Entry Point
Droplet #4 - Full Potential AI
FULLY UDC v1.0 COMPLIANT with CODE_STANDARDS organization
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        workers=1,
        reload=False
    )
