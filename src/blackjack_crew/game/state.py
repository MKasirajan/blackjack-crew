"""Pydantic models for game state.

Represents the full state of a Blackjack game at any point in time:
all four players' hands, whose turn it is, who's finished, and the
final outcome. The state is fully serialisable (Pydantic), so we can
log it, persist it, or pass it across the agent boundary cleanly.

Game rules embedded in this module:
    - Each player draws up to 3 cards (per brief).
    - Score over 21 is a bust.
    - Highest score under or equal to 21 wins.
    - Ties between players at the same winning score are declared
      explicitly rather than broken arbitrarily.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, computed_field, field_validator

from blackjack_crew.game.cards import MAX_CARD_VALUE, MIN_CARD_VALUE

# Game constants
BLACKJACK_TARGET: int = 21
MAX_CARDS_PER_PLAYER: int = 3


class PlayerType(str, Enum):
    """Identifies a player in the game.

    The user is one of four players. The three AI players each have a
    distinct persona and decision style, exposed through their agent
    definitions in the `agents` subpackage.
    """

    USER = "user"
    ALPHA = "alpha"  # Conservative — stands early
    BETA = "beta"  # Aggressive — pushes for higher hands
    GAMMA = "gamma"  # Strategic — probability-aware


class Card(BaseModel):
    """A single card with an integer value in [2, 11].

    The brief specifies cards are just integers between 2 and 11; we
    wrap that in a Pydantic model for validation and to leave a clean
    extension point (suits, face cards, etc.) without refactoring
    every call site.
    """

    value: int = Field(ge=MIN_CARD_VALUE, le=MAX_CARD_VALUE)

    def __str__(self) -> str:
        return str(self.value)


class Hand(BaseModel):
    """A player's hand — the ordered list of cards they've drawn."""

    cards: list[Card] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        """Sum of all card values in the hand."""
        return sum(card.value for card in self.cards)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_busted(self) -> bool:
        """True if the hand total exceeds 21."""
        return self.total > BLACKJACK_TARGET

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cards_drawn(self) -> int:
        """How many cards have been drawn so far."""
        return len(self.cards)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_draw_more(self) -> bool:
        """True if the player has remaining draws (under the 3-card limit) and isn't busted."""
        return self.cards_drawn < MAX_CARDS_PER_PLAYER and not self.is_busted

    def add_card(self, card: Card) -> None:
        """Append a card to the hand. Mutates in place."""
        if self.cards_drawn >= MAX_CARDS_PER_PLAYER:
            raise ValueError(
                f"Hand already has the maximum {MAX_CARDS_PER_PLAYER} cards; cannot draw more."
            )
        self.cards.append(card)


class PlayerState(BaseModel):
    """The state of a single player — their hand and whether they've finished."""

    player_type: PlayerType
    hand: Hand = Field(default_factory=Hand)
    has_stood: bool = False  # True once the player explicitly stands

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_finished(self) -> bool:
        """A player is finished if they've stood, busted, or hit the 3-card limit."""
        return self.has_stood or self.hand.is_busted or self.hand.cards_drawn >= MAX_CARDS_PER_PLAYER


class GameOutcome(BaseModel):
    """The final result of a completed game."""

    winners: list[PlayerType]  # Multiple if tied at the top
    winning_score: int | None  # None if all busted
    is_tie: bool
    all_busted: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> str:
        """Human-readable one-line outcome summary."""
        if self.all_busted:
            return "All players busted — no winner."
        if self.is_tie:
            names = ", ".join(p.value.title() for p in self.winners)
            return f"Tie at {self.winning_score} between: {names}."
        return f"Winner: {self.winners[0].value.title()} with {self.winning_score}."


class GameState(BaseModel):
    """The complete state of a game at any point in time.

    Construction creates an empty game with all four players present
    and empty hands. Use the `engine` module to progress the game state
    through draws and turn transitions.
    """

    players: dict[PlayerType, PlayerState] = Field(
        default_factory=lambda: {
            player_type: PlayerState(player_type=player_type) for player_type in PlayerType
        }
    )
    turn_order: list[PlayerType] = Field(
        default_factory=lambda: [PlayerType.USER, PlayerType.ALPHA, PlayerType.BETA, PlayerType.GAMMA]
    )
    current_turn_index: int = 0
    outcome: GameOutcome | None = None  # Set when the game completes

    @field_validator("turn_order")
    @classmethod
    def _validate_turn_order(cls, value: list[PlayerType]) -> list[PlayerType]:
        if len(value) != len(set(value)):
            raise ValueError("turn_order must contain each player exactly once.")
        if set(value) != set(PlayerType):
            raise ValueError("turn_order must contain all four player types.")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def current_player(self) -> PlayerType:
        """The player whose turn it is now."""
        return self.turn_order[self.current_turn_index]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete(self) -> bool:
        """True if all players have finished their turns."""
        return all(self.players[p].has_finished for p in self.turn_order)