"""Pure tournament-scheduling logic — no DB or FastAPI dependency.

Generates a round-robin-ish schedule for a group of players such that no pair of
players ever shares a table twice, using a randomized backtracking search.
"""

import random
from itertools import combinations


def _form_round(
    player_ids: list[int],
    played_together: set[tuple[int, int]],
    games_per_round: int,
) -> list[list[int]] | None:
    """
    Backtracking search: partition player_ids into games_per_round tables of 4
    such that no pair appears in played_together or is used twice within this round.
    Returns None if no valid partition exists.
    """

    def backtrack(
        available: list[int],
        tables: list[list[int]],
        round_pairs: set[tuple[int, int]],
    ) -> list[list[int]] | None:
        if len(tables) == games_per_round:
            return tables
        if len(available) < 4:
            return None

        all_pairs = played_together | round_pairs
        anchor = available[0]
        rest = available[1:]

        # Only consider players anchor hasn't met
        cands = [p for p in rest if (min(anchor, p), max(anchor, p)) not in all_pairs]

        # Only triples where every internal pair is also fresh
        valid_triples = [
            t
            for t in combinations(cands, 3)
            if all(
                (min(t[i], t[j]), max(t[i], t[j])) not in all_pairs
                for i in range(3)
                for j in range(i + 1, 3)
            )
        ]
        random.shuffle(valid_triples)

        for triple in valid_triples:
            table = [anchor] + list(triple)
            new_round_pairs = round_pairs | {
                (min(table[i], table[j]), max(table[i], table[j]))
                for i in range(4)
                for j in range(i + 1, 4)
            }
            new_available = [p for p in rest if p not in triple]
            result = backtrack(new_available, tables + [table], new_round_pairs)
            if result is not None:
                return result

        return None

    shuffled = player_ids[:]
    random.shuffle(shuffled)
    return backtrack(shuffled, [], set())


def generate_schedule(group_player_ids: list[int], num_rounds: int) -> list[list[list[int]]]:
    """
    Generate a round schedule for one group. Each round is a list of tables (list of 4 player ids).
    Hard guarantee: no pair ever shares a table twice across all rounds.
    Raises ValueError if the requested number of rounds is mathematically impossible.
    """
    n = len(group_player_ids)
    games_per_round = n // 4
    if games_per_round == 0:
        return []

    # Each player has n-1 possible partners, uses 3 per round → upper bound
    max_possible = (n - 1) // 3
    if num_rounds > max_possible:
        raise ValueError(
            f"Mit {n} Spielern sind maximal {max_possible} Runden ohne Paar-Wiederholung möglich "
            f"(angefordert: {num_rounds})"
        )

    # Retry outer loop: different initial shuffles escape local dead-ends
    for _ in range(500):
        played_together: set[tuple[int, int]] = set()
        all_rounds: list[list[list[int]]] = []
        failed = False

        for _ in range(num_rounds):
            tables = _form_round(group_player_ids, played_together, games_per_round)
            if tables is None:
                failed = True
                break
            for table in tables:
                for i in range(4):
                    for j in range(i + 1, 4):
                        played_together.add((min(table[i], table[j]), max(table[i], table[j])))
            all_rounds.append(tables)

        if not failed:
            return all_rounds

    raise ValueError("Konnte keinen gültigen Spielplan generieren — bitte Rundenanzahl reduzieren")
