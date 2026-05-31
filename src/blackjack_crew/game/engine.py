"""Game engine — the orchestrator that drives the game loop.

This module is the only place where the game/, agents/, and ui/ layers
meet. It holds no rules (those live in `rules.py`) and no LLM logic
(that lives in `agents/crew.py`); it just sequences turns, applies
the rules each turn, and renders the result.

The engine is intentionally synchronous and turn-based. Async/parallel
agent decisions would be possible but add complexity unwarranted by
the assignment scope.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from blackjack_crew.agents.crew import BlackjackCrew
from blackjack_crew.game.rules import determine_outcome
from blackjack_crew.game.state import (
    Card,
    GameOutcome,
    GameState,
    PlayerType,
)
from blackjack_crew.ui import display


@dataclass
class GameConfig:
    """Configuration for a single game run."""

    seed: int | None = None


def play_game(config: GameConfig | None = None) -> GameOutcome:
    """Play one complete game end-to-end.

    Args:
        config: Optional `GameConfig` controlling determinism via seed.

    Returns:
        The final `GameOutcome` describing the result.
    """
    cfg = config or GameConfig()

# Seed Python's global random state if requested. This affects every
    # subsequent `random.randint` call across the process — including
    # the card-drawing tool's, even when CrewAI re-imports the tool.
    if cfg.seed is not None:
        random.seed(cfg.seed)

    display.render_title(seed=cfg.seed)
    display.render_seating()

    state = GameState()
    crew = BlackjackCrew()

    for player in state.turn_order:
        display.render_turn_header(player)
        if player == PlayerType.USER:
            _play_user_turn(state, crew, player)
        else:
            _play_agent_turn(state, crew, player)

    outcome = determine_outcome(state)
    state.outcome = outcome
    display.render_final_standings(state, outcome)
    return outcome


# ---------- Per-player turn handlers ----------

def _play_user_turn(state: GameState, crew: BlackjackCrew, player: PlayerType) -> None:
    """Drive the user's interactive turn until they stand, bust, or hit the 3-card limit."""
    p_state = state.players[player]
    display.render_hand(player, p_state)

    while not p_state.has_finished:
        action = display.prompt_user_action(can_draw_more=p_state.hand.can_draw_more)

        if action == "stand":
            p_state.has_stood = True
            display.render_user_stands(p_state.hand.total)
            break

        # action == "deal"
        display.render_user_requests_card()
        try:
            result = crew.request_card_for(player)
        except Exception as exc:
            display.render_error(f"Dealer failed to draw a card: {exc}")
            # Treat dealer failure as a forced stand — game continues
            p_state.has_stood = True
            break

        display.render_card_dealt(result.value)
        p_state.hand.add_card(Card(value=result.value))
        display.render_hand(player, p_state)

        if p_state.hand.is_busted:
            display.render_busted(player, p_state.hand.total)
            break


def _play_agent_turn(state: GameState, crew: BlackjackCrew, player: PlayerType) -> None:
    """Drive an AI player's turn — agent decides hit or stand each step."""
    p_state = state.players[player]
    display.render_hand(player, p_state)

    while not p_state.has_finished:
        try:
            decision_result = crew.decide_for(
                player_type=player,
                current_total=p_state.hand.total,
                cards_drawn=p_state.hand.cards_drawn,
            )
        except Exception as exc:
            display.render_error(
                f"{display.display_name(player)} failed to decide: {exc}. Forcing stand."
            )
            p_state.has_stood = True
            break

        if decision_result.decision == "stand":
            p_state.has_stood = True
            display.render_agent_decision(
                player,
                "stand",
                decision_result.reasoning,
                p_state.hand.total,
            )
            break

        # decision == "hit"
        display.render_agent_decision(
            player,
            "hit",
            decision_result.reasoning,
            p_state.hand.total,
        )

        if not p_state.hand.can_draw_more:
            # Agent wanted to hit but has no draws left — force stand.
            p_state.has_stood = True
            break

        display.render_agent_requests_card(player)
        try:
            card_result = crew.request_card_for(player)
        except Exception as exc:
            display.render_error(f"Dealer failed to draw for {display.display_name(player)}: {exc}")
            p_state.has_stood = True
            break

        display.render_card_dealt(card_result.value)
        p_state.hand.add_card(Card(value=card_result.value))
        display.render_hand(player, p_state)

        if p_state.hand.is_busted:
            display.render_busted(player, p_state.hand.total)
            break