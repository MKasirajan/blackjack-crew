"""Crew assembly — the public interface to the agent layer.

The `BlackjackCrew` class holds the four configured agents and provides
the methods the orchestrator calls each turn:

    - `request_card_for(player)` — Dealer draws a card for a named player
    - `decide_for(player, game_summary)` — Player agent decides hit/stand

This is the only module outside `agents/` that the orchestrator imports
from — keeping CrewAI-specific types behind a clean boundary.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Literal

from crewai import Agent, Crew, Task

from blackjack_crew.agents.factory import build_agents
from blackjack_crew.agents.tools import set_rng
from blackjack_crew.game.state import MAX_CARDS_PER_PLAYER, PlayerType

Decision = Literal["hit", "stand"]


@dataclass
class CardDrawResult:
    """Result of asking the Dealer for a card."""

    value: int
    raw_response: str


@dataclass
class DecisionResult:
    """Result of asking a Player Agent for their next move."""

    decision: Decision
    reasoning: str
    raw_response: str


class BlackjackCrew:
    """The agent crew — holds the four agents and orchestrates LLM calls.

    Owned by the orchestrator; one instance per game. Stateless between
    calls (the game state lives in `engine.py`).
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        """Construct the crew with all four agents configured.

        Args:
            rng: Optional seeded RNG; injected into the card-drawing tool
                for deterministic gameplay. None for normal gameplay.
        """
        set_rng(rng)
        self._agents = build_agents()
        # Hold a Crew object so the construct exists for inspection/debug,
        # even though we drive task execution directly per turn.
        self._crew = Crew(
            agents=list(self._agents.values()),
            tasks=[],  # Tasks built per-turn; this Crew is a holder, not an executor
            verbose=False,
        )

    @property
    def dealer(self) -> Agent:
        return self._agents["dealer"]

    def player(self, player_type: PlayerType) -> Agent:
        """Return the Agent for a given player type (alpha/beta/gamma)."""
        if player_type == PlayerType.USER:
            raise ValueError("The USER is not an agent.")
        return self._agents[player_type.value]

    def request_card_for(self, requesting_player: PlayerType) -> CardDrawResult:
        """Ask the Dealer Agent to draw a card for a named player.

        Args:
            requesting_player: Which player the card is for. Used in the
                task description so the Dealer's response references the
                right player.

        Returns:
            A `CardDrawResult` with the integer card value parsed from
            the Dealer's tool output, plus the raw LLM response.

        Raises:
            ValueError: If the Dealer's response cannot be parsed for
                a card value in [2, 11].
        """
        task = Task(
            description=(
                f"{requesting_player.value.title()} has asked for a card. "
                "Use the Draw Card tool exactly once and report the value drawn. "
                "Reply with the card value only."
            ),
            expected_output="A single card value between 2 and 11.",
            agent=self.dealer,
        )
        raw_response = str(task.execute_sync().raw).strip()
        value = self._parse_card_value(raw_response)
        return CardDrawResult(value=value, raw_response=raw_response)

    def decide_for(
        self,
        player_type: PlayerType,
        current_total: int,
        cards_drawn: int,
    ) -> DecisionResult:
        """Ask a Player Agent to decide hit or stand.

        Args:
            player_type: Which player is deciding (alpha/beta/gamma).
            current_total: The player's current hand total.
            cards_drawn: How many cards they've drawn so far.

        Returns:
            A `DecisionResult` with the parsed decision (`"hit"` or
            `"stand"`), the agent's one-sentence reasoning, and the
            raw LLM response.

        Raises:
            ValueError: If the response doesn't clearly indicate hit
                or stand.
        """
        agent = self.player(player_type)
        cards_remaining = MAX_CARDS_PER_PLAYER - cards_drawn
        task = Task(
            description=(
                f"Your current hand total is {current_total}. "
                f"You have drawn {cards_drawn} card(s); you may draw up to "
                f"{cards_remaining} more (3 maximum per game). "
                "Decide whether to HIT (draw another card) or STAND (keep your total). "
                "Reply with exactly two lines:\n"
                "Line 1: HIT or STAND\n"
                "Line 2: One short sentence explaining why."
            ),
            expected_output="HIT or STAND on the first line, then a one-sentence reason.",
            agent=agent,
        )
        raw_response = str(task.execute_sync().raw).strip()
        decision, reasoning = self._parse_decision(raw_response)
        return DecisionResult(
            decision=decision,
            reasoning=reasoning,
            raw_response=raw_response,
        )

    @staticmethod
    def _parse_card_value(response: str) -> int:
        """Extract the integer card value (2-11) from the Dealer's response."""
        # The tool returns "Card drawn: N" or the agent may reply with just "N".
        # Match the first integer in [2, 11] anywhere in the response.
        for match in re.finditer(r"\d+", response):
            value = int(match.group())
            if 2 <= value <= 11:
                return value
        raise ValueError(
            f"Dealer response did not contain a valid card value in [2, 11]: "
            f"{response!r}"
        )

    @staticmethod
    def _parse_decision(response: str) -> tuple[Decision, str]:
        """Parse a player agent's hit/stand reply into (decision, reasoning)."""
        lines = [line.strip() for line in response.strip().splitlines() if line.strip()]
        if not lines:
            raise ValueError(f"Player response was empty: {response!r}")

        first = lines[0].upper()
        if "HIT" in first and "STAND" not in first:
            decision: Decision = "hit"
        elif "STAND" in first:
            decision = "stand"
        else:
            # Fallback: scan the whole response for the first clear keyword.
            up = response.upper()
            hit_pos = up.find("HIT")
            stand_pos = up.find("STAND")
            if hit_pos == -1 and stand_pos == -1:
                raise ValueError(
                    f"Could not parse HIT or STAND from response: {response!r}"
                )
            if stand_pos == -1 or (0 <= hit_pos < stand_pos):
                decision = "hit"
            else:
                decision = "stand"

        reasoning = " ".join(lines[1:]) if len(lines) > 1 else ""
        return decision, reasoning