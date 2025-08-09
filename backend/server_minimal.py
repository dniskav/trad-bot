from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
import json

app = FastAPI(title="Minimal Trading Bot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Minimal Trading Bot API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "message": "Server is running correctly"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔌 WebSocket conectado")
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "data": {
                "status": "connected", 
                "timestamp": datetime.now().isoformat(),
                "message": "WebSocket connected successfully"
            }
        }))
        
        # Keep connection alive
        while True:
            try:
                # Just keep the connection alive
                await websocket.receive_text()
            except WebSocketDisconnect:
                print("🔌 WebSocket desconectado")
                break
    except Exception as e:
        print(f"❌ Error en WebSocket: {e}")
    finally:
        print("🔌 WebSocket cerrado")

if __name__ == "__main__":
    print("🚀 Starting minimal server...")
    uvicorn.run(
        "server_minimal:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 