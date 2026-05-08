from __future__ import annotations

import itertools


def combos(leg_indexes: list[int], pick: int) -> list[tuple[int, ...]]:
    return list(itertools.combinations(leg_indexes, pick))

