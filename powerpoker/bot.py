"""Heuristic poker bot: Monte-Carlo equity estimate + pot-odds decision rule
with a small bluff frequency. The same bot class/skill plays both seats."""
import random
from .evaluator import evaluate_best


class HeuristicBot:
    def __init__(self, name="bot", trials=1000, bluff_freq=0.04, aggression=0.20, rng=None):
        self.name = name
        self.trials = trials
        self.bluff_freq = bluff_freq
        self.aggression = aggression
        self.rng = rng or random.Random()

    def estimate_equity(self, hole_cards, community, known_opp_cards, deck_remaining):
        """Monte Carlo win probability for hole_cards+community vs a random
        opponent hand (or a hand containing known_opp_cards, e.g. P2's
        exposed card), over random completions of the board."""
        wins = 0.0
        trials = self.trials
        pool = list(deck_remaining)
        n_opp_unknown = 2 - len(known_opp_cards)
        n_board_needed = 5 - len(community)
        need = n_opp_unknown + n_board_needed
        for _ in range(trials):
            draw = self.rng.sample(pool, need)
            opp_unknown = draw[:n_opp_unknown]
            board_fill = draw[n_opp_unknown:]
            opp_hand = list(known_opp_cards) + opp_unknown
            full_board = community + board_fill
            my_best = evaluate_best(hole_cards + full_board)
            opp_best = evaluate_best(opp_hand + full_board)
            if my_best > opp_best:
                wins += 1.0
            elif my_best == opp_best:
                wins += 0.5
        return wins / trials

    def act(self, state):
        """state keys: hole_cards, community, known_opp_cards, deck_remaining,
        pot, to_call, min_raise, max_raise (stack-limited), big_blind.
        Returns (action, amount) where action in fold/check/call/raise and
        amount is the *additional* chips put in for a raise, or the call size."""
        equity = self.estimate_equity(
            state["hole_cards"], state["community"],
            state["known_opp_cards"], state["deck_remaining"],
        )
        pot = state["pot"]
        to_call = state["to_call"]
        pot_odds = to_call / (pot + to_call) if to_call > 0 else 0.0
        bluff = self.rng.random() < self.bluff_freq

        if to_call == 0:
            if state["max_raise"] > 0 and (equity > 0.65 or bluff):
                bet = self._size_bet(pot, state["big_blind"], state["max_raise"])
                if bet > 0:
                    return ("raise", bet)
            return ("check", 0)

        if equity < pot_odds - 0.03 and not bluff:
            return ("fold", 0)

        if state["max_raise"] > 0 and (equity > pot_odds + 0.30 or bluff):
            raise_add = self._size_bet(pot, state["big_blind"], state["max_raise"])
            return ("raise", raise_add)

        return ("call", to_call)

    def _size_bet(self, pot, big_blind, max_raise):
        size = int(pot * self.aggression)
        size = max(big_blind, size)
        return min(size, max_raise)
