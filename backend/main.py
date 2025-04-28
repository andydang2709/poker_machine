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
    game.post_blinds()
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
    if player:
        player.has_acted = True

    # 👇 Main logic
    showdown_data = None

    if game.all_players_acted():
        stage_result = game.advance_stage()

        if isinstance(stage_result, dict):  # if final_showdown returned a dict
            showdown_data = stage_result
    else:
        game.next_turn()

    response = {
        "state": game.game_state()
    }

    if showdown_data:
        response["showdown"] = showdown_data  # ✅ tell frontend showdown happened

    return response

@app.get("/showdown")
def showdown():
    showdown_data = game.final_showdown()
    game.remove_broke_players()
    return showdown_data

@app.get("/next_hand")
def next_hand():
    game.start_game()
    game.post_blinds()
    return game.game_state()