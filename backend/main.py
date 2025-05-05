from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from backend.poker import PokerGame

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game instance
game: Optional[PokerGame] = None

class StartGameRequest(BaseModel):
    players: List[str]

@app.post("/start")
async def start_game(request: StartGameRequest):
    global game
    game = PokerGame(request.players)
    game.start_game()
    return game.game_state()

@app.get("/state")
async def get_game_state():
    if game is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")
    return game.game_state()

@app.post("/action")
async def player_action(name: str, action: str, amount: Optional[float] = 0):
    if game is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")

    # Validate bet amount
    if action == "bet" and (amount is None or amount <= 0):
        raise HTTPException(status_code=400, detail="Bet amount must be greater than 0.")

    game.set_player_action(name, action, amount)
    round_result = game.play_betting_round()
    state = game.game_state()
    response = {"state": state}

    # Handle fold-win
    if round_result == "win":
        remaining = [p for p in game.players if not p.folded]
        if remaining:
            winner = remaining[0]
            response["showdown"] = {
                "board": [str(c) for c in game.community_cards],
                "results": [{
                    "name": winner.name,
                    "hand": [str(c) for c in winner.hand],
                    "hand_name": "Wins by Fold"
                }],
                "winners": [winner.name]
            }
    # Normal showdown dict returned
    elif isinstance(round_result, dict):
        response["showdown"] = round_result

    return response

@app.post("/next_stage")
async def next_stage():
    if game is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")

    result = game.advance_stage()
    state = game.game_state()
    if result == "continue":
        return state
    # result is a showdown dict
    return {"state": state, "showdown": result}

@app.get("/showdown")
async def showdown():
    if game is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")
    showdown_data = game.showdown()
    game.remove_broke_players()
    return showdown_data

@app.post("/next_hand")
async def next_hand():
    if game is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")
    game.start_new_hand()
    return game.game_state()