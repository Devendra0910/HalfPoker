"""Run PowerPoker self-play simulations with identical-skill heuristic bots
in both seats, to check whether the 200/hidden-hidden vs 300/hidden-exposed
asymmetry is balanced.

Usage:
  python3 simulate.py hands 20000      # independent hands, stacks reset each time
  python3 simulate.py matches 2000     # full sessions played to bust-out
"""
import random
import sys
import time

sys.path.insert(0, ".")
from halfpoker.bot import HeuristicBot
from halfpoker.game import play_hand, BIG_BLIND

P1_START = 500
P2_START = 1000
MAX_HANDS_PER_MATCH = 1000


def simulate_hands(n, seed=0):
    rng = random.Random(seed)
    bot_p1 = HeuristicBot("P1", rng=rng)
    bot_p2 = HeuristicBot("P2", rng=rng)

    wins = {"P1": 0, "P2": 0, "split": 0}
    showdowns = 0
    button = "P1"
    for i in range(n):
        result = play_hand({"P1": P1_START, "P2": P2_START}, button, bot_p1, bot_p2, rng=rng)
        wins[result["winner"]] += 1
        if result["went_to_showdown"]:
            showdowns += 1
        button = "P2" if button == "P1" else "P1"

    print(f"\n=== Hand-level results over {n} independent hands ===")
    print(f"P1 win rate:    {wins['P1']/n:.4f}")
    print(f"P2 win rate:    {wins['P2']/n:.4f}")
    print(f"Split rate:     {wins['split']/n:.4f}")
    print(f"Showdown rate:  {showdowns/n:.4f}")


def simulate_matches(n, seed=1):
    rng = random.Random(seed)
    bot_p1 = HeuristicBot("P1", rng=rng)
    bot_p2 = HeuristicBot("P2", rng=rng)

    match_wins = {"P1": 0, "P2": 0, "draw": 0}
    hand_counts = []

    for m in range(n):
        stacks = {"P1": P1_START, "P2": P2_START}
        button = "P1" if m % 2 == 0 else "P2"  # alternate who opens button across matches
        hands_played = 0
        for h in range(MAX_HANDS_PER_MATCH):
            if stacks["P1"] < BIG_BLIND or stacks["P2"] < BIG_BLIND:
                break
            result = play_hand(stacks, button, bot_p1, bot_p2, rng=rng)
            stacks = result["final_stacks"]
            button = "P2" if button == "P1" else "P1"
            hands_played += 1
        hand_counts.append(hands_played)

        if stacks["P1"] < BIG_BLIND and stacks["P2"] < BIG_BLIND:
            match_wins["draw"] += 1
        elif stacks["P1"] < BIG_BLIND:
            match_wins["P2"] += 1
        elif stacks["P2"] < BIG_BLIND:
            match_wins["P1"] += 1
        else:
            # hit hand cap without a bust-out; call it by chip lead
            if stacks["P1"] > stacks["P2"]:
                match_wins["P1"] += 1
            elif stacks["P2"] > stacks["P1"]:
                match_wins["P2"] += 1
            else:
                match_wins["draw"] += 1

    avg_hands = sum(hand_counts) / len(hand_counts)
    print(f"\n=== Match-level results over {n} sessions (bust-out or {MAX_HANDS_PER_MATCH}-hand cap) ===")
    print(f"P1 match win rate: {match_wins['P1']/n:.4f}")
    print(f"P2 match win rate: {match_wins['P2']/n:.4f}")
    print(f"Draw rate:         {match_wins['draw']/n:.4f}")
    print(f"Avg hands/match:   {avg_hands:.1f}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "hands"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    t0 = time.time()
    if mode == "hands":
        simulate_hands(n)
    elif mode == "matches":
        simulate_matches(n)
    else:
        print("usage: simulate.py [hands|matches] N")
        sys.exit(1)
    print(f"(took {time.time()-t0:.1f}s)")
