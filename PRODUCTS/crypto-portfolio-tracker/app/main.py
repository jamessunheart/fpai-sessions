"""
Crypto Portfolio Tracker - Main Application
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.routers import money

# Create FastAPI app
app = FastAPI(
    title="Crypto Portfolio Tracker",
    description="Professional crypto portfolio tracking and management",
    version="1.0.0"
)

# Set up templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Include routers
app.include_router(money.router, tags=["Treasury"])

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to dashboard"""
    return """
    <html>
        <head>
            <title>Crypto Portfolio Tracker</title>
            <meta http-equiv="refresh" content="0;url=/dashboard/money">
        </head>
        <body>
            <p>Redirecting to dashboard...</p>
        </body>
    </html>
    """

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "crypto-portfolio-tracker"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
