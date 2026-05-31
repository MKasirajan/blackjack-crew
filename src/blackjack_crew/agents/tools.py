"""CrewAI tools — wrappers exposing game-engine functions to agents.

Per the assignment brief, only the Dealer Agent has access to the
card-drawing function. Player Agents must request cards from the
Dealer rather than drawing directly. This module enforces that
constraint by defining tools and the helper that assigns them
only to the Dealer.
"""

from __future__ import annotations

import random

from crewai.tools import tool

from blackjack_crew.game.cards import draw_card as engine_draw_card

# Module-level RNG injection point. The orchestrator can replace this
# with a seeded Random for reproducible tests / demos; production runs
# leave it as None for non-deterministic gameplay.
_rng: random.Random | None = None


def set_rng(rng: random.Random | None) -> None:
    """Inject a seeded RNG for deterministic gameplay (testing/demos).

    Args:
        rng: A `random.Random` instance, or `None` to reset to
            non-deterministic behaviour.
    """
    global _rng
    _rng = rng


@tool("Draw Card")
def draw_card_tool() -> str:
    """Draw a single card with a value between 2 and 11 inclusive.

    Use this tool to deal a card to a player. Returns a string
    describing the drawn card (e.g., "Card drawn: 7").

    Returns:
        A short string describing the card value drawn.
    """
    value = engine_draw_card(rng=_rng)
    return f"Card drawn: {value}"