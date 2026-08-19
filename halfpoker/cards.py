"""Card and deck primitives. A card is a (rank, suit) tuple:
rank in 2..14 (14 = Ace), suit in 0..3.
"""
import random

RANK_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}
SUIT_STR = {0: "s", 1: "h", 2: "d", 3: "c"}


def make_deck():
    return [(r, s) for r in range(2, 15) for s in range(4)]


def card_str(c):
    r, s = c
    return f"{RANK_STR.get(r, str(r))}{SUIT_STR[s]}"


def cards_str(cards):
    return " ".join(card_str(c) for c in cards)


def new_shuffled_deck(rng=None):
    deck = make_deck()
    (rng or random).shuffle(deck)
    return deck
