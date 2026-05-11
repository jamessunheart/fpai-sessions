from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
from pathlib import Path

app = FastAPI(title="God Mode Dashboard")

# Setup paths
BASE_DIR = Path(__file__).parent
SYSTEM_MAP_PATH = BASE_DIR / "system_map.json"

# Setup templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def load_system_map():
    if SYSTEM_MAP_PATH.exists():
        with open(SYSTEM_MAP_PATH, "r") as f:
            data = json.load(f)
            # Rewrite localhost to server IP
            if "integration_points" in data:
                for key, url in data["integration_points"].items():
                    data["integration_points"][key] = url.replace("localhost", "198.54.123.234")
            return data
    return {"error": "System map not found"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    system_map = load_system_map()
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "system_map": system_map}
    )

if __name__ == "__main__":
    import uvicorn
    print("⚡ God Mode Active on http://localhost:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888)

