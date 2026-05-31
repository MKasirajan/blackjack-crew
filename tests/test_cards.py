"""Tests for the card-drawing function.

The function uses Python's `random` module under the hood. To keep
tests deterministic, we inject a seeded `random.Random` instance and
verify both the value distribution and the boundary conditions.
"""

from __future__ import annotations

import random

import pytest

from blackjack_crew.game.cards import MAX_CARD_VALUE, MIN_CARD_VALUE, draw_card


def test_draw_card_returns_int_in_valid_range() -> None:
    """A card draw must always return an integer in [2, 11] inclusive."""
    for _ in range(1000):
        card = draw_card()
        assert isinstance(card, int)
        assert MIN_CARD_VALUE <= card <= MAX_CARD_VALUE


def test_draw_card_with_seed_is_deterministic() -> None:
    """Same seed must produce same sequence — required for test reproducibility."""
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    sequence_a = [draw_card(rng_a) for _ in range(20)]
    sequence_b = [draw_card(rng_b) for _ in range(20)]
    assert sequence_a == sequence_b


def test_draw_card_covers_full_range_over_many_draws() -> None:
    """Over enough draws, every valid value 2-11 should appear at least once."""
    rng = random.Random(123)
    draws = {draw_card(rng) for _ in range(2000)}
    expected_values = set(range(MIN_CARD_VALUE, MAX_CARD_VALUE + 1))
    assert draws == expected_values


@pytest.mark.parametrize("seed,expected_first", [(0, 8), (1, 4), (42, 3), (100, 4)])
def test_draw_card_seeded_values(seed: int, expected_first: int) -> None:
    """Spot-check specific seeded outputs to guard against accidental rng changes."""
    rng = random.Random(seed)
    assert draw_card(rng) == expected_first