"""CrewAI tools — wrappers exposing game-engine functions to agents.

Per the assignment brief, only the Dealer Agent has access to the
card-drawing function. Player Agents must request cards from the
Dealer rather than drawing directly. This module enforces that
constraint by defining tools and the helper that assigns them
only to the Dealer.

Caching note: CrewAI caches tool results by default for identical
arguments. For a stochastic tool like card-drawing, that's incorrect —
every invocation must produce a fresh draw. We disable caching by
providing a `cache_function` that always returns False, ensuring each
call executes the underlying function.

Seeding: Python's process-wide `random` module is seeded by the engine
at game start when `--seed` is passed. The seeded global state is
shared by every subsequent `random.randint` call across the process,
including ours.
"""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool

from blackjack_crew.game.cards import draw_card as engine_draw_card


def _never_cache(*_args: Any, **_kwargs: Any) -> bool:
    """Cache predicate that always disables caching for this tool.

    Required because the default CrewAI cache policy serves the cached
    result for zero-argument tools — wrong for a stochastic draw.
    """
    return False


class DrawCardTool(BaseTool):
    """Draw a single card. Only the Dealer Agent should have this tool."""

    name: str = "Draw Card"
    description: str = (
        "Draw a single card with a value between 2 and 11 inclusive. "
        "Use this tool to deal a card to a player. Returns a string "
        "describing the card value drawn, e.g. 'Card drawn: 7'."
    )
    cache_function: Any = _never_cache

    def _run(self) -> str:
        value = engine_draw_card()
        return f"Card drawn: {value}"


# Singleton instance — all agents share this tool registration.
draw_card_tool = DrawCardTool()