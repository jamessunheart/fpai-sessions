from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

# Import our existing librarian logic
# We need to add the parent directory to sys.path to import research_librarian
import sys
sys.path.append(str(Path(__file__).parent))
import research_librarian

app = FastAPI(title="Research Librarian Dashboard")

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
INCOMING_DIR = BASE_DIR / "_incoming"
PUBLISH_DIR = research_librarian.PUBLISH_DIR

# Ensure directories exist
if not INCOMING_DIR.exists():
    INCOMING_DIR.mkdir(parents=True)

# Models
class ApprovalRequest(BaseModel):
    filename: str
    new_filename: Optional[str] = None

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return TEMPLATES.TemplateResponse("review_dashboard.html", {"request": request})

@app.get("/api/files")
async def list_files():
    """List all files in the incoming directory."""
    files = []
    if INCOMING_DIR.exists():
        for f in INCOMING_DIR.iterdir():
            if f.is_file() and f.name != ".gitkeep":
                # Get AI analysis for each file
                # Note: In a real app, we might want to cache this or do it async
                # because doing it on-the-fly for all files is slow.
                # For now, we'll return the file list and let the frontend request analysis individually
                files.append({
                    "name": f.name,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "type": f.suffix
                })
    return {"files": files}

@app.get("/api/analyze/{filename}")
async def analyze_file(filename: str):
    """Run AI analysis on a specific file."""
    file_path = INCOMING_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    llm = research_librarian.LLMClient()
    text = research_librarian.extract_text(file_path)
    analysis = llm.analyze_paper(text)
    
    return analysis

@app.get("/api/preview/{filename}")
async def preview_file(filename: str):
    """Serve the raw file for preview (PDF/Text)."""
    file_path = INCOMING_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.post("/api/approve")
async def approve_file(data: ApprovalRequest):
    """Approve and publish a file."""
    src = INCOMING_DIR / data.filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    final_name = data.new_filename if data.new_filename else data.filename
    
    # Ensure valid extension is kept
    if not final_name.endswith(src.suffix):
        final_name += src.suffix
        
    if not PUBLISH_DIR.exists():
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        
    dest = PUBLISH_DIR / final_name
    
    # Move file
    shutil.move(str(src), str(dest))
    
    # Trigger index update
    research_librarian.update_index()
    
    return {"status": "success", "published_path": str(dest.relative_to(research_librarian.WORKSPACE_ROOT))}

@app.post("/api/delete/{filename}")
async def delete_file(filename: str):
    """Delete a file from inbox."""
    src = INCOMING_DIR / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    os.remove(src)
    return {"status": "deleted"}

@app.post("/api/scan")
async def scan_system():
    """Trigger a system scan."""
    llm = research_librarian.LLMClient()
    research_librarian.scan_system_mode(llm)
    return {"status": "scan_complete"}

if __name__ == "__main__":
    print("📚 Librarian Dashboard running at http://localhost:8081")
    uvicorn.run(app, host="0.0.0.0", port=8081)

