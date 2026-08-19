"""PowerPoker engine.

Player 1 ("P1"): starts with 200 chips, 2 fully hidden hole cards.
Player 2 ("P2"): starts with 300 chips, 2 hole cards but one of them is
    face-up (public knowledge) from the deal onward.
Both share 5 community cards, revealed Hold'em-style (flop/turn/river).
Blinds are fixed at 10/20 and rotate every hand. Standard heads-up betting
order: button (small blind) acts first preflop, the other player acts
first on every later street. Best 5-of-7 wins at showdown.
"""
import random
from .cards import make_deck
from .evaluator import evaluate_best

SMALL_BLIND = 10
BIG_BLIND = 20
STREETS = ["preflop", "flop", "turn", "river"]
REVEAL_COUNT = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}


def _deck_remaining(known_cards):
    known = set(known_cards)
    return [c for c in make_deck() if c not in known]


def _bot_state(actor, hole, community_visible, exposed_card, pot, to_call,
               max_raise, big_blind):
    known_opp = [exposed_card] if (actor == "P1" and exposed_card) else []
    known_cards = hole[actor] + community_visible + ([exposed_card] if actor == "P1" and exposed_card else [])
    return {
        "hole_cards": hole[actor],
        "community": community_visible,
        "known_opp_cards": known_opp,
        "deck_remaining": _deck_remaining(known_cards),
        "pot": pot,
        "to_call": to_call,
        "max_raise": max_raise,
        "big_blind": big_blind,
    }


def _run_betting_round(first_actor, hole, exposed_card, community_visible,
                        stacks, street_contrib, pot, bots, big_blind, log=None):
    acted = {"P1": False, "P2": False}
    actor, other = first_actor, ("P2" if first_actor == "P1" else "P1")
    current_bet = max(street_contrib.values())

    while True:
        if street_contrib["P1"] == street_contrib["P2"] and acted["P1"] and acted["P2"]:
            break
        if stacks["P1"] == 0 and stacks["P2"] == 0:
            break
        if stacks[actor] == 0:
            acted[actor] = True
            actor, other = other, actor
            continue

        to_call = current_bet - street_contrib[actor]
        call_amount = min(to_call, stacks[actor])
        own_room = max(stacks[actor] - call_amount, 0)
        # A raise can never exceed what the opponent could still match — once
        # they're covered (all-in or short-stacked), there's no one left to
        # call any more, so raising further would just donate uncalled chips.
        opp_capacity = street_contrib[other] + stacks[other]
        opp_room = max(opp_capacity - current_bet, 0)
        max_raise = max(min(own_room, opp_room), 0)

        state = _bot_state(actor, hole, community_visible, exposed_card,
                            pot, call_amount, max_raise, big_blind)
        action, amount = bots[actor].act(state)

        if action == "fold":
            if log is not None:
                log.append(f"  {actor} folds. (pot stays {pot})")
            return {"pot": pot, "folded": actor}
        elif action == "check":
            acted[actor] = True
            if log is not None:
                log.append(f"  {actor} checks.")
        elif action == "call":
            pay = min(call_amount, stacks[actor])
            stacks[actor] -= pay
            street_contrib[actor] += pay
            pot += pay
            acted[actor] = True
            if log is not None:
                tag = " (all-in)" if stacks[actor] == 0 else ""
                log.append(f"  {actor} calls {pay}{tag}. pot={pot}, stacks: P1={stacks['P1']} P2={stacks['P2']}")
        elif action == "raise":
            # `amount` from the bot is the extra chips it wants to add on top
            # of the call (already capped at max_raise by the bot).
            raise_add = min(max(amount, 0), max_raise)
            pay = min(call_amount + raise_add, stacks[actor])
            stacks[actor] -= pay
            street_contrib[actor] += pay
            pot += pay
            current_bet = street_contrib[actor]
            acted[actor] = True
            acted[other] = False
            if log is not None:
                tag = " (all-in)" if stacks[actor] == 0 else ""
                log.append(f"  {actor} raises to {street_contrib[actor]} (+{pay}){tag}. pot={pot}, stacks: P1={stacks['P1']} P2={stacks['P2']}")
        else:
            acted[actor] = True

        actor, other = other, actor

    return {"pot": pot, "folded": None}


def play_hand(stacks, button, bot_p1, bot_p2, rng=None, log=None):
    """Play one hand. `stacks` = {'P1': int, 'P2': int} (mutated copy used
    internally; original dict is not mutated). `button` = 'P1' or 'P2'
    (button posts the small blind). Pass a list for `log` to get a
    human-readable play-by-play appended to it. Returns a result dict."""
    rng = rng or random
    stacks = dict(stacks)
    original = dict(stacks)

    deck = make_deck()
    rng.shuffle(deck)
    hole = {
        "P1": [deck.pop(), deck.pop()],
        "P2": [deck.pop(), deck.pop()],
    }
    exposed_card = hole["P2"][1]  # P2's second card is public
    community = [deck.pop() for _ in range(5)]

    bots = {"P1": bot_p1, "P2": bot_p2}
    sb, bb = button, ("P2" if button == "P1" else "P1")

    sb_amt = min(SMALL_BLIND, stacks[sb])
    bb_amt = min(BIG_BLIND, stacks[bb])
    stacks[sb] -= sb_amt
    stacks[bb] -= bb_amt
    pot = sb_amt + bb_amt

    if log is not None:
        from .cards import cards_str
        log.append(f"Button/SB: {sb} (posts {sb_amt})   BB: {bb} (posts {bb_amt})")
        log.append(f"P1 hole: {cards_str(hole['P1'])} (hidden)")
        log.append(f"P2 hole: {cards_str(hole['P2'][:1])} (hidden) + {cards_str(hole['P2'][1:])} (EXPOSED)")
        log.append(f"Starting stacks: P1={original['P1']} P2={original['P2']}   pot after blinds={pot}")

    folded = None
    for i, street in enumerate(STREETS):
        community_visible = community[:REVEAL_COUNT[street]]
        if street == "preflop":
            street_contrib = {sb: sb_amt, bb: bb_amt}
            first_actor = sb
        else:
            street_contrib = {"P1": 0, "P2": 0}
            first_actor = bb

        if stacks["P1"] == 0 and stacks["P2"] == 0:
            if log is not None:
                log.append(f"-- {street} -- (both all-in, dealing on)")
            continue  # both all-in, just keep dealing streets to showdown

        if log is not None:
            from .cards import cards_str
            board = f" | board: {cards_str(community_visible)}" if community_visible else ""
            log.append(f"-- {street} --{board}")

        result = _run_betting_round(first_actor, hole, exposed_card,
                                     community_visible, stacks, street_contrib,
                                     pot, bots, BIG_BLIND, log=log)
        pot = result["pot"]
        if result["folded"]:
            folded = result["folded"]
            break

    if folded:
        winner_seat = "P2" if folded == "P1" else "P1"
        stacks[winner_seat] += pot
        went_to_showdown = False
        winner = winner_seat
        if log is not None:
            log.append(f"=> {folded} folded. {winner_seat} wins pot of {pot}.")
    else:
        p1_best = evaluate_best(hole["P1"] + community)
        p2_best = evaluate_best(hole["P2"] + community)
        went_to_showdown = True
        if p1_best > p2_best:
            stacks["P1"] += pot
            winner = "P1"
        elif p2_best > p1_best:
            stacks["P2"] += pot
            winner = "P2"
        else:
            half = pot // 2
            stacks["P1"] += half
            stacks["P2"] += pot - half
            winner = "split"
        if log is not None:
            from .cards import cards_str
            log.append(f"-- showdown -- board: {cards_str(community)}")
            log.append(f"  P1 shows {cards_str(hole['P1'])} -> best hand {p1_best}")
            log.append(f"  P2 shows {cards_str(hole['P2'])} -> best hand {p2_best}")
            if winner == "split":
                log.append(f"=> Split pot of {pot} (tie).")
            else:
                log.append(f"=> {winner} wins pot of {pot}.")

    deltas = {s: stacks[s] - original[s] for s in ("P1", "P2")}
    return {
        "winner": winner,
        "pot": pot,
        "deltas": deltas,
        "final_stacks": stacks,
        "went_to_showdown": went_to_showdown,
        "hole": hole,
        "community": community,
    }
