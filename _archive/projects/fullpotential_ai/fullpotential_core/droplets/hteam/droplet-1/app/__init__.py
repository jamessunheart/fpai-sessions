# app/__init__.py
from fastapi import FastAPI

def create_app():
    """Factory method to create FastAPI app instance."""
    app = FastAPI(title="Full Potential OS", version="v.521-M")

    @app.get("/health")
    async def health():
        """Simple health check endpoint."""
        return {"status": "ok", "version": app.version}

    return app
