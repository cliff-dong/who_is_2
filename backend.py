from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uuid
import random
from typing import List, Dict

app = FastAPI()

# ✅ Enable CORS to allow frontend requests
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
games = {}  # {room_id: {"question": str, "players": {}, "answers": {}, "votes": {}}}

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    """Handles WebSocket connections for real-time gameplay."""
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "action" in data:
                if data["action"] == "submit_answer":
                    games[room_id]["answers"][player_id] = data["answer"]
                    await manager.broadcast(room_id, {"type": "answer_submitted", "player": player_id})
                elif data["action"] == "submit_vote":
                    games[room_id]["votes"][player_id] = data["vote"]
                    await manager.broadcast(room_id, {"type": "vote_submitted", "player": player_id})
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

@app.get("/create_room")
async def create_room():
    """Creates a game room and starts the game."""
    room_id = str(uuid.uuid4())[:8]
    games[room_id] = {"question": "", "players": {}, "answers": {}, "votes": {}}

    # ✅ Automatically start the game with the first question
    await start_game(room_id)
    
    return {"room_id": room_id}

@app.get("/start_game/{room_id}")
async def start_game(room_id: str):
    """Starts the game by sending the first question."""
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

    message = {"type": "new_question", "question": question}
    await manager.broadcast(room_id, message)  # ✅ Send question to all players

    return {"status": "Game started", "question": question}

@app.get("/join_room/{room_id}")
def join_room(room_id: str):
    """Checks if a room exists before joining."""
    if room_id in games:
        return {"status": "ok", "room_id": room_id, "question": games[room_id]["question"]}
    return {"status": "error", "message": "Room does not exist."}

@app.post("/submit_answer")
async def submit_answer(room_id: str, player_id: str, answer: str):
    """Stores a player's answer and broadcasts it."""
    if room_id not in games:
        return {"error": "Room does not exist."}
    
    games[room_id]["answers"][player_id] = answer
    await manager.broadcast(room_id, {"type": "answer_received", "player": player_id, "answer": answer})

    return {"status": "Answer submitted"}

@app.post("/submit_vote")
async def submit_vote(room_id: str, voter_id: str, voted_player_id: str):
    """Records a player's vote and determines elimination."""
    if room_id not in games:
        return {"error": "Room does not exist."}
    
    games[room_id]["votes"][voter_id] = voted_player_id

    # Tally votes
    vote_counts = {}
    for vote in games[room_id]["votes"].values():
        vote_counts[vote] = vote_counts.get(vote, 0) + 1

    most_voted_player = max(vote_counts, key=vote_counts.get)

    await manager.broadcast(room_id, {
        "type": "elimination",
        "eliminated": most_voted_player,
        "message": f"Player {most_voted_player} has been eliminated!"
    })

    return {"status": "Vote submitted", "eliminated": most_voted_player}

@app.get("/")
def home():
    return {"message": "Who is AI? Game is running!"}
