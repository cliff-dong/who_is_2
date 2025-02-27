from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware  # Import CORS Middleware
import uuid
import random
from typing import List, Dict

app = FastAPI()

# ✅ Enable CORS (Fixes frontend connection issues)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

class ConnectionManager:
    """Manages WebSocket connections."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict):
        """Send message to all players in a room."""
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    """Handles WebSocket connections for real-time gameplay."""
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room_id, data)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

@app.get("/create_room")
def create_room():
    """Creates a unique game room."""
    room_id = str(uuid.uuid4())[:8]
    return {"room_id": room_id}

@app.get("/join_room/{room_id}")
def join_room(room_id: str):
    """Checks if a room exists before joining."""
    if room_id in manager.active_connections:
        return {"status": "ok", "room_id": room_id}
    return {"status": "error", "message": "Room does not exist."}

@app.get("/")
def home():
    return {"message": "Who is AI? Game is running!"}
