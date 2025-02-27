import random

class Game:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players = {}
        self.current_question = None
        self.answers = {}
        self.votes = {}
        self.rounds = 0

    def add_player(self, player_id: str, name: str, is_ai: bool = False):
        self.players[player_id] = {"name": name, "is_ai": is_ai}

    def start_round(self, question: str):
        self.current_question = question
        self.answers = {}
        self.votes = {}

    def submit_answer(self, player_id: str, answer: str):
        self.answers[player_id] = answer

    def ai_generate_answer(self):
        ai_responses = [
            "Life is a complex neural network of possibilities.",
            "Humans often seek purpose, but do we really need one?",
            "I believe the answer lies in optimization of resources.",
            "Why do you ask? Does it truly matter?",
            "Consciousness is merely a collection of patterns."
        ]
        for player_id, data in self.players.items():
            if data["is_ai"]:
                self.answers[player_id] = random.choice(ai_responses)

    def submit_vote(self, voter_id: str, voted_player_id: str):
        if voter_id in self.players and voted_player_id in self.players:
            self.votes[voter_id] = voted_player_id

    def tally_votes(self):
        vote_counts = {}
        for vote in self.votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        if sorted_votes:
            most_voted_player = sorted_votes[0][0]
            was_ai = self.players[most_voted_player]["is_ai"]
            return {"eliminated": most_voted_player, "was_ai": was_ai}
        return {"eliminated": None, "was_ai": False}
