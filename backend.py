from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uuid
import random
from typing import List, Dict

app = FastAPI()

# ✅ Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """Manages WebSocket connections."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        """Accepts a WebSocket connection for a player."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        """Removes a disconnected player from the game room."""
        if room_id in self.active_connections and websocket in self.active_connections[room_id]:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict):
        """Sends a message to all players in a room."""
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)

manager = ConnectionManager()

# ✅ Stores game state
games = {}  # {room_id: {"question": str, "answers": {}, "players": {}}}

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    """Handles WebSocket connections for real-time gameplay."""
    await manager.connect(room_id, websocket)

    # ✅ Ensure the player list is initialized
    if room_id not in games:
        games[room_id] = {"question": "", "answers": {}, "players": {}}
    games[room_id]["players"][player_id] = {"id": player_id}

    # ✅ Send the current game state (question, players)
    await websocket.send_json({
        "type": "new_question",
        "question": games[room_id]["question"],
        "players": list(games[room_id]["players"].keys())
    })

    try:
        while True:
            data = await websocket.receive_json()
            if "action" in data:
                if data["action"] == "submit_answer":
                    games[room_id]["answers"][player_id] = data["answer"]
                    # ✅ Broadcast the answer to all players
                    await manager.broadcast(room_id, {
                        "type": "answer_received",
                        "player": player_id,
                        "answer": data["answer"]
                    })
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

@app.get("/create_room")
async def create_room():
    """Creates a game room and starts the game."""
    room_id = str(uuid.uuid4())[:8]
    games[room_id] = {"question": "", "answers": {}, "players": {}}

    # ✅ Automatically start the game with the first question
    await start_game(room_id)
    
    return {"room_id": room_id}

@app.get("/start_game/{room_id}")
async def start_game(room_id: str):
    """Starts the game by sending the first question to all players."""
    questions = [
        "What is the meaning of life?",
        "Describe yourself in one sentence.",
        "If you could be an animal, what would you be?",
        "What is your favorite hobby and why?"
    ]
    
    if room_id not in games:
        return {"error": "Room does not exist."}

    question = random.choice(questions)
    games[room_id]["question"] = question

    # ✅ Broadcast the question to all players
    await manager.broadcast(room_id, {
        "type": "new_question",
        "question": question,
        "players": list(games[room_id]["players"].keys())
    })

    return {"status": "Game started", "question": question}

@app.get("/join_room/{room_id}")
async def join_room(room_id: str):
    """Allows a player to join an existing room and receive the game state."""
    if room_id in games:
        return {
            "status": "ok",
            "room_id": room_id,
            "question": games[room_id]["question"],
            "players": list(games[room_id]["players"].keys())
        }
    return {"status": "error", "message": "Room does not exist."}

@app.get("/")
def home():
    return {"message": "Who is AI? Game is running!"}
