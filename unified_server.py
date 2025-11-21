import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Import the existing apps
# We need to make sure the paths are correct for imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.weibo_agent_frontend import app as agent_app
from workflow.workflow_frontend import app as workflow_app

app = FastAPI(title="WeiboBot Unified Server", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict to frontend domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the existing applications
# We use /api/agent and /api/workflow to avoid conflict with frontend routes /agent and /workflow
app.mount("/api/agent", agent_app)
app.mount("/api/workflow", workflow_app)

# Serve the new frontend
# Assuming the frontend will be built to 'web/dist'
FRONTEND_DIR = Path(__file__).resolve().parent / "web" / "dist"

@app.get("/health")
def health_check():
    return {"status": "ok"}

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    
    # Catch-all route for SPA
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # If it's a file that exists, serve it (though assets are already mounted)
        # This is just a fallback
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise serve index.html
        return FileResponse(FRONTEND_DIR / "index.html")

if __name__ == "__main__":
    host = os.getenv("UNIFIED_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("UNIFIED_SERVER_PORT", "8000"))
    print(f"Starting Unified Server at http://{host}:{port}")
    print(f"Agent API available at http://{host}:{port}/api/agent/docs")
    print(f"Workflow API available at http://{host}:{port}/api/workflow/docs")
    uvicorn.run(app, host=host, port=port)
