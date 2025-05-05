import random
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from collections import Counter

SUITS = ['♥', '♦', '♣', '♠']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {rank: index for index, rank in enumerate(RANKS, start=2)}

STARTING_BIG_BLINDS = 100


class Card:

    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}{self.suit}"


class Deck:

    def __init__(self):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, num_cards: int) -> List[Card]:
        dealt = self.cards[:num_cards]
        self.cards = self.cards[num_cards:]
        return dealt

    def burn_card(self):
        if self.cards:
            self.cards.pop(0)


class Participant(ABC):

    def __init__(self, name: str):
        self.name = name
        self.hand: List[Card] = []
        self.folded = False

    def receive_cards(self, cards: List[Card]):
        self.hand.extend(cards)

    def fold(self):
        self.folded = True

    def reset(self):
        self.hand.clear()
        self.folded = False
        self.has_acted = False

    @abstractmethod
    def make_action(self, max_bet: float) -> str:
        pass


class Player(Participant):

    def __init__(self, name: str):
        super().__init__(name)
        self.bb = STARTING_BIG_BLINDS
        self.current_bet = 0
        self.is_all_in = False
        self.pending_action: Optional[str] = None
        self.pending_amount: Optional[float] = 0.0
        self.has_acted = False

    def place_bet(self, amount: float) -> float:
        actual_bet = min(amount, self.bb)
        self.bb -= actual_bet
        self.current_bet += actual_bet
        if self.bb == 0:
            self.is_all_in = True
        return actual_bet

    def make_action(self, max_bet: float) -> str:
        self.has_acted = True
        return self.pending_action or "call"

    def reset(self):
        super().reset()
        self.current_bet = 0
        self.is_all_in = False
        self.pending_action = None
        self.pending_amount = 0.0
        self.has_acted = False


class HandEvaluator:

    @staticmethod
    def evaluate_hand(cards: List[Card]) -> tuple:
        values = sorted([RANK_VALUES[card.rank] for card in cards],
                        reverse=True)
        suits = [card.suit for card in cards]
        value_counts = Counter(values)
        suit_counts = Counter(suits)

        is_flush = any(count >= 5 for count in suit_counts.values())
        is_straight, top_card = HandEvaluator.is_straight(values)

        if is_flush and is_straight:
            return (8, [top_card]), "Straight Flush"
        if 4 in value_counts.values():
            four = HandEvaluator.get_rank_by_count(value_counts, 4)
            kickers = HandEvaluator.get_kickers(value_counts, [four])
            return (7, [four] + kickers), "Four of a Kind"
        if 3 in value_counts.values() and 2 in value_counts.values():
            three = HandEvaluator.get_rank_by_count(value_counts, 3)
            pair = HandEvaluator.get_rank_by_count(value_counts, 2)
            return (6, [three, pair]), "Full House"
        if is_flush:
            flush_cards = [
                val for val, suit in sorted(zip(values, suits), reverse=True)
                if suit_counts[suit] >= 5
            ]
            return (5, flush_cards[:5]), "Flush"
        if is_straight:
            return (4, [top_card]), "Straight"
        if 3 in value_counts.values():
            three = HandEvaluator.get_rank_by_count(value_counts, 3)
            kickers = HandEvaluator.get_kickers(value_counts, [three])
            return (3, [three] + kickers[:2]), "Three of a Kind"
        pairs = [val for val, count in value_counts.items() if count == 2]
        if len(pairs) >= 2:
            top_two = sorted(pairs, reverse=True)[:2]
            kicker = HandEvaluator.get_kickers(value_counts, top_two)
            return (2, top_two + kicker[:1]), "Two Pair"
        if len(pairs) == 1:
            pair = pairs[0]
            kickers = HandEvaluator.get_kickers(value_counts, [pair])
            return (1, [pair] + kickers[:3]), "One Pair"
        return (0, values[:5]), "High Card"

    @staticmethod
    def is_straight(values: List[int]) -> tuple:
        values = sorted(set(values), reverse=True)
        for i in range(len(values) - 4):
            if values[i] - values[i + 4] == 4:
                return True, values[i]
        if set([14, 5, 4, 3, 2]).issubset(values):
            return True, 5
        return False, None

    @staticmethod
    def get_rank_by_count(counter: Counter, count: int) -> int:
        return max(k for k, v in counter.items() if v == count)

    @staticmethod
    def get_kickers(counter: Counter, exclude: List[int]) -> List[int]:
        return sorted([k for k in counter if k not in exclude], reverse=True)


class PokerGame:
    def __init__(self, 
                 player_names: List[str],
                 small_blind_amount: float = 0.5,
                 big_blind_amount: float = 1.0):
        self.players = [Player(name) for name in player_names]
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0.0
        self.max_bet = 0.0
        self.dealer_idx = 0
        self.current_turn = 0
        self.current_stage = "preflop"
        self.small_blind_amount = small_blind_amount
        self.big_blind_amount = big_blind_amount

    def reset_game(self):
        self.deck = Deck()
        self.community_cards.clear()
        self.pot = 0.0
        self.current_stage = "preflop"
        self.current_turn = 0
        self.max_bet = 0.0
        self.dealer_idx = 0
        for player in self.players:
            player.reset()
            player.bb = STARTING_BIG_BLINDS

    def start_game(self):
        self.reset_game()
        self.start_new_hand()

    def start_new_hand(self):
        self.deck = Deck()
        self.community_cards.clear()
        self.pot = 0.0
        self.current_stage = "preflop"
        self.max_bet = 0.0
        for player in self.players:
            player.reset()
        self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
        self.deal_hole_cards()
        self.post_blinds()
        self.reset_actions()
        self.current_turn = (self.dealer_idx + 1) % len(self.players)

    def deal_hole_cards(self):
        for player in self.players:
            player.receive_cards(self.deck.deal(2))

    def burn_and_deal(self, num: int):
        self.deck.burn_card()
        self.community_cards.extend(self.deck.deal(num))

    def post_blinds(self):
        sb_player = self.players[(self.dealer_idx + 1) % len(self.players)]
        bb_player = self.players[(self.dealer_idx + 2) % len(self.players)]
        self.pot += sb_player.place_bet(self.small_blind_amount)
        self.pot += bb_player.place_bet(self.big_blind_amount)
        self.max_bet = bb_player.current_bet

    def active_players(self) -> List[Player]:
        return [p for p in self.players if not p.folded]

    def set_player_action(self, name: str, action: str, amount: float = 0):
        player = next((p for p in self.players if p.name == name), None)
        if player:
            player.pending_action = action
            player.pending_amount = amount

    def reset_actions(self):
        for player in self.players:
            player.has_acted = False

    def advance_stage(self):
        if self.current_stage == "preflop":
            self.burn_and_deal(3)
            self.current_stage = "flop"
        elif self.current_stage == "flop":
            self.burn_and_deal(1)
            self.current_stage = "turn"
        elif self.current_stage == "turn":
            self.burn_and_deal(1)
            self.current_stage = "river"
        elif self.current_stage == "river":
            return self.showdown()
        self.reset_bets()
        self.reset_actions()
        self.max_bet = 0.0
        self.current_turn = (self.dealer_idx + 1) % len(self.players)
        while self.players[self.current_turn].folded or self.players[
                self.current_turn].is_all_in:
            self.current_turn = (self.current_turn + 1) % len(self.players)
        return "continue"

    def play_betting_round(self) -> Optional[Dict]:
        player = self.players[self.current_turn]
        if player.folded or player.is_all_in:
            self.next_turn()
            return "waiting"

        action = player.make_action(self.max_bet)

        if action == 'fold':
            player.fold()
            if self.check_instant_win():
                return "win"

        elif action == 'bet':
            desired_total = player.pending_amount
            additional_bet = desired_total - player.current_bet
            if additional_bet <= 0:
                player.pending_action = None
                player.pending_amount = 0.0
                return "waiting"
            if desired_total > self.max_bet:
                self.max_bet = desired_total
            actual_bet = player.place_bet(additional_bet)
            self.pot += actual_bet
            player.pending_action = None
            player.pending_amount = 0.0

        elif action == 'call':
            call_amount = self.max_bet - player.current_bet
            if call_amount > 0:
                actual_call = player.place_bet(call_amount)
                self.pot += actual_call
            player.current_bet = self.max_bet
            player.pending_action = None
            player.pending_amount = 0.0

        elif action == 'check':
            # Only allowed if no additional bet is required
            if player.current_bet == self.max_bet:
                player.has_acted = True
            else:
                # Invalid check, skip action
                player.pending_action = None
                player.pending_amount = 0.0
                return "waiting"

        if action in ['bet', 'call']:
            player.has_acted = True

        if self.betting_done():
            return self.advance_stage()
        self.next_turn()
        return "waiting"

    def next_turn(self):
        active = [p for p in self.players if not p.folded and not p.is_all_in]
        if not active:
            return
        next_idx = (self.current_turn + 1) % len(self.players)
        while self.players[next_idx].folded or self.players[next_idx].is_all_in:
            next_idx = (next_idx + 1) % len(self.players)
        self.current_turn = next_idx

    def betting_done(self) -> bool:
        active = [p for p in self.players if not p.folded and not p.is_all_in]
        if not active:
            return True
        max_bet = max(p.current_bet for p in active)
        return all((p.current_bet == max_bet or p.is_all_in) and p.has_acted
                   for p in active)

    def reset_bets(self):
        for p in self.players:
            p.current_bet = 0

    def check_instant_win(self) -> bool:
        active = self.active_players()
        if len(active) == 1:
            active[0].bb += self.pot
            return True
        return False

    def showdown(self) -> Dict:
        board = [str(card) for card in self.community_cards]
        best_score = (-1, [])
        winners = []
        results = []
        for player in self.players:
            if player.folded:
                continue
            combined = player.hand + self.community_cards
            score, hand_name = HandEvaluator.evaluate_hand(combined)
            hand = [str(card) for card in player.hand]
            results.append({
                "name": player.name,
                "hand": hand,
                "hand_name": hand_name
            })
            if score > best_score:
                best_score = score
                winners = [player]
            elif score == best_score:
                winners.append(player)
        winner_names = [w.name for w in winners]
        split_pot = self.pot / len(winners)
        for w in winners:
            w.bb += split_pot
        self.pot = 0
        return {"board": board, "results": results, "winners": winner_names}

    def remove_broke_players(self):
        self.players = [p for p in self.players if p.bb > 0]

    def game_state(self) -> Dict:
        small_blind_idx = (self.dealer_idx + 1) % len(self.players)
        big_blind_idx = (self.dealer_idx + 2) % len(self.players)
        return {
            "pot":
            round(self.pot, 1),
            "community_cards": [str(card) for card in self.community_cards],
            "players": [{
                "name": p.name,
                "bb": round(p.bb, 1),
                "hand": [str(card) for card in p.hand],
                "folded": p.folded,
                "is_all_in": p.is_all_in,
                "is_small_blind": idx == small_blind_idx,
                "is_big_blind": idx == big_blind_idx,
            } for idx, p in enumerate(self.players)],
            "current_stage":
            self.current_stage,
            "current_turn":
            self.players[self.current_turn].name if self.players else None,
        }

    def find_first_active_player(self) -> int:
        for idx, p in enumerate(self.players):
            if not p.folded and not p.is_all_in:
                return idx
        return 0
