"""Cora Nation - Church of Consciousness Community Hub"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="Cora Nation",
    description="Private Member Association & Church of Consciousness",
    version="1.0.0"
)

# Get the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
async def root():
    """Serve main community homepage"""
    index_path = os.path.join(BASE_DIR, "index.html")
    return FileResponse(index_path)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cora-nation",
        "version": "1.0.0",
        "description": "Church of Consciousness Community Hub"
    }


@app.get("/about")
async def about():
    """About Cora Nation and Church of Consciousness"""
    return {
        "message": "About page - Coming soon",
        "redirect": "/"
    }


@app.get("/membership")
async def membership():
    """Membership application"""
    return {
        "message": "Membership application - Coming soon",
        "redirect": "/"
    }


@app.get("/donate")
async def donate():
    """Donation portal"""
    return {
        "message": "Donation portal - Coming soon",
        "redirect": "/"
    }


@app.get("/portal")
async def member_portal():
    """Member portal (private)"""
    return {
        "message": "Member portal - Coming soon",
        "redirect": "/"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)
