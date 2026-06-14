"""Full Potential Main Hub - Central directory for all services"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Full Potential Hub", version="1.0.0")

# Get the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
async def root():
    """Serve main hub landing page"""
    index_path = os.path.join(BASE_DIR, "index.html")
    return FileResponse(index_path)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "full-potential-hub",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
