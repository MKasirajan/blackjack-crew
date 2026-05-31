"""Card-drawing function — the local Python tool the brief specifies.

Per the assignment brief:
    "A local Python function is provided that simulates drawing a card
    by returning a random number between 2 and 11."

This module is the canonical implementation. The Dealer Agent wraps
this function as a CrewAI tool; the user (and other AI players) cannot
call it directly — they must ask the Dealer.
"""

from __future__ import annotations

import random

# Per the brief — card values are integers between 2 and 11 inclusive.
MIN_CARD_VALUE: int = 2
MAX_CARD_VALUE: int = 11


def draw_card(rng: random.Random | None = None) -> int:
    """Draw a single card.

    Args:
        rng: Optional `random.Random` instance for deterministic draws
            (used in testing). If `None`, the module-level random state
            is used, giving non-deterministic gameplay as intended.

    Returns:
        Integer in `[MIN_CARD_VALUE, MAX_CARD_VALUE]` inclusive.

    Examples:
        Non-deterministic (production):

            >>> card = draw_card()
            >>> 2 <= card <= 11
            True

        Deterministic (testing):

            >>> import random
            >>> rng = random.Random(42)
            >>> draw_card(rng)
            2
    """
    generator = rng if rng is not None else random
    return generator.randint(MIN_CARD_VALUE, MAX_CARD_VALUE)