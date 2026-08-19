"""Standard poker hand evaluation. evaluate_best(cards) picks the best
5-card hand out of any number (>=5) of cards, returning a comparable tuple
(bigger tuple = better hand). Category indices: 8=straight flush, 7=quads,
6=full house, 5=flush, 4=straight, 3=trips, 2=two pair, 1=pair, 0=high card.

Direct O(n) evaluation (no 5-card-subset enumeration): compute the best
counts-based hand, the best plain straight, and the best flush/straight-flush
independently, then take the max — correct because those three cover all
hand categories and tuple ordering already ranks categories correctly.
"""


def _best_straight(sorted_unique_ranks_desc):
    """sorted_unique_ranks_desc: distinct ranks, high to low. Returns high
    card of best straight, or None."""
    rfs = sorted_unique_ranks_desc
    if 14 in rfs:
        rfs = rfs + [1]  # ace also plays low (wheel)
    for i in range(len(rfs) - 4):
        window = rfs[i:i + 5]
        if window[0] - window[4] == 4 and len(set(window)) == 5:
            return window[0]
    return None


def evaluate_best(cards):
    """cards: iterable of >=5 (rank,suit) tuples. Returns best comparable tuple."""
    cards = list(cards)
    ranks = [c[0] for c in cards]
    suits = [c[1] for c in cards]

    rank_count = [0] * 15
    for r in ranks:
        rank_count[r] += 1
    suit_count = [0] * 4
    for s in suits:
        suit_count[s] += 1

    counts = sorted(
        ((cnt, r) for r, cnt in enumerate(rank_count) if cnt > 0),
        key=lambda x: (-x[0], -x[1]),
    )

    top_count, top_rank = counts[0]
    if top_count == 4:
        kicker = max(r for r in ranks if r != top_rank)
        counts_hand = (7, top_rank, kicker)
    elif top_count == 3 and len(counts) > 1 and counts[1][0] >= 2:
        counts_hand = (6, top_rank, counts[1][1])
    elif top_count == 3:
        kickers = sorted((r for r in ranks if r != top_rank), reverse=True)[:2]
        counts_hand = (3, top_rank) + tuple(kickers)
    elif top_count == 2 and len(counts) > 1 and counts[1][0] == 2:
        pair_hi, pair_lo = top_rank, counts[1][1]
        kicker = max(r for r in ranks if r != pair_hi and r != pair_lo)
        counts_hand = (2, pair_hi, pair_lo, kicker)
    elif top_count == 2:
        kickers = sorted((r for r in ranks if r != top_rank), reverse=True)[:3]
        counts_hand = (1, top_rank) + tuple(kickers)
    else:
        counts_hand = (0,) + tuple(sorted(ranks, reverse=True)[:5])

    best = counts_hand

    unique_desc = sorted(set(ranks), reverse=True)
    if len(unique_desc) >= 5:
        straight_high = _best_straight(unique_desc)
        if straight_high is not None:
            straight_hand = (4, straight_high)
            if straight_hand > best:
                best = straight_hand

    flush_suit = None
    for s in range(4):
        if suit_count[s] >= 5:
            flush_suit = s
            break
    if flush_suit is not None:
        flush_ranks = sorted((r for r, s in zip(ranks, suits) if s == flush_suit), reverse=True)
        sf_high = _best_straight(flush_ranks) if len(flush_ranks) >= 5 else None
        flush_hand = (8, sf_high) if sf_high is not None else (5,) + tuple(flush_ranks[:5])
        if flush_hand > best:
            best = flush_hand

    return best
