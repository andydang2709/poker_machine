from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from poker import PokerGame

# Initialize FastAPI app
app = FastAPI()

# Enable CORS so frontend can talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the poker game
game = PokerGame(["Andy", "Linh"])

@app.get("/start")
def start_game():
    game.start_game()
    return game.game_state()

@app.get("/state")
def get_game_state():
    return game.game_state()

@app.get("/deal_flop")
def deal_flop():
    game.burn_and_deal(3)
    return game.game_state()

@app.get("/deal_turn")
def deal_turn():
    game.burn_and_deal(1)
    return game.game_state()

@app.get("/deal_river")
def deal_river():
    game.burn_and_deal(1)
    return game.game_state()

@app.post("/action")
def player_action(name: str, action: str, amount: Optional[float] = 0):
    game.set_player_action(name, action, amount)

    player = next((p for p in game.players if p.name == name), None)

    showdown_data = None 

    round_result = game.play_betting_round()

    response = {
        "state": game.game_state()
    }

    # 🛠 Handle win due to fold
    if round_result == "win":
        remaining = [p for p in game.players if not p.folded]
        if remaining:
            winner = remaining[0]
            response["showdown"] = {
                "board": game.community_cards,
                "results": [{
                    "name": winner.name,
                    "hand": [str(c) for c in winner.hand],
                    "hand_name": "Wins by Fold"
                }],
                "winners": [winner.name]
            }

    elif isinstance(round_result, dict):  # normal showdown
        response["showdown"] = round_result

    # if showdown_data:
    #     response["showdown"] = showdown_data

    return response

@app.get("/showdown")
def showdown():
    showdown_data = game.showdown()
    game.remove_broke_players()
    return showdown_data

@app.get("/next_hand")
def next_hand():
    game.start_new_hand()
    return game.game_state()