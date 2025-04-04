from fastapi import FastAPI, WebSocket, Request, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()
BASE = Path(__file__).parent.resolve()

# CORS (for web/public agent access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount public directory
app.mount("/public", StaticFiles(directory=BASE / "public"), name="public")

# File search
@app.get("/files")
def search_files(q: str = ""):
    base = BASE / "public"
    return {
        "matches": [str(p.relative_to(base)) for p in base.rglob("*") if q.lower() in p.name.lower()]
    }

# Read a file
@app.get("/files/{filename}")
def read_file(filename: str):
    file_path = BASE / "public" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# Tools endpoint
@app.post("/tools")
async def run_tool(request: Request):
    data = await request.json()
    task = data.get("task")
    if task == "summarize":
        text = data.get("text", "")
        return {"summary": text[:150] + "..." if len(text) > 150 else text}
    return {"error": "Tool not recognized"}

# WebSocket echo (agent interface)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"[Agent Echo] {data}")
    except WebSocketDisconnect:
        print("Client disconnected normally")
    except Exception as e:
        print(f"Error in WebSocket connection: {str(e)}")
