"""Pure functions for game rules — winner determination, etc.

Kept separate from `state.py` to maintain the rule: state models are
just data containers; rules are functions over them. This separation
makes the rules independently testable and easier to evolve.
"""

from __future__ import annotations

from blackjack_crew.game.state import BLACKJACK_TARGET, GameOutcome, GameState, PlayerType


def determine_outcome(state: GameState) -> GameOutcome:
    """Determine the final outcome of a completed game.

    The winner(s) are the player(s) with the highest total <= 21.
    Multiple players at the same highest qualifying total all share
    the win (declared as a tie).

    Args:
        state: A completed game state (all players finished).

    Returns:
        A `GameOutcome` describing winners, the winning score, and
        whether the result is a tie or all-bust scenario.

    Raises:
        ValueError: If the game state is not yet complete.
    """
    if not state.is_complete:
        raise ValueError("Cannot determine outcome — game is not yet complete.")

    # Collect (player, total) pairs for non-busted players only
    qualifying: list[tuple[PlayerType, int]] = [
        (player_type, state.players[player_type].hand.total)
        for player_type in state.turn_order
        if not state.players[player_type].hand.is_busted
    ]

    if not qualifying:
        # All players busted — no winner
        return GameOutcome(winners=[], winning_score=None, is_tie=False, all_busted=True)

    # Identify the highest score among non-busted players
    highest_score = max(score for _, score in qualifying)
    winners = [player for player, score in qualifying if score == highest_score]

    return GameOutcome(
        winners=winners,
        winning_score=highest_score,
        is_tie=len(winners) > 1,
        all_busted=False,
    )


def is_safe_total(total: int) -> bool:
    """Convenience predicate: True if a total is at or under the Blackjack target."""
    return total <= BLACKJACK_TARGET