"""Tests for game rules — winner determination, tie handling, all-bust."""

from __future__ import annotations

import pytest

from blackjack_crew.game.rules import determine_outcome, is_safe_total
from blackjack_crew.game.state import BLACKJACK_TARGET, Card, GameState, Hand, PlayerType


def _build_finished_game(
    user_cards: list[int],
    alpha_cards: list[int],
    beta_cards: list[int],
    gamma_cards: list[int],
) -> GameState:
    """Helper: build a game state where everyone has stood with the given cards."""
    state = GameState()
    hands = {
        PlayerType.USER: user_cards,
        PlayerType.ALPHA: alpha_cards,
        PlayerType.BETA: beta_cards,
        PlayerType.GAMMA: gamma_cards,
    }
    for player_type, card_values in hands.items():
        state.players[player_type].hand = Hand(cards=[Card(value=v) for v in card_values])
        state.players[player_type].has_stood = True
    return state


class TestDetermineOutcome:
    def test_single_clear_winner(self) -> None:
        state = _build_finished_game(
            user_cards=[10, 10],  # 20
            alpha_cards=[5, 6],  # 11
            beta_cards=[7, 8],  # 15
            gamma_cards=[9, 9],  # 18
        )
        outcome = determine_outcome(state)
        assert outcome.winners == [PlayerType.USER]
        assert outcome.winning_score == 20
        assert not outcome.is_tie
        assert not outcome.all_busted

    def test_tie_between_two_players(self) -> None:
        state = _build_finished_game(
            user_cards=[10, 10],  # 20
            alpha_cards=[10, 10],  # 20
            beta_cards=[5, 5],  # 10
            gamma_cards=[6, 6],  # 12
        )
        outcome = determine_outcome(state)
        assert set(outcome.winners) == {PlayerType.USER, PlayerType.ALPHA}
        assert outcome.winning_score == 20
        assert outcome.is_tie
        assert not outcome.all_busted

    def test_all_players_busted(self) -> None:
        state = _build_finished_game(
            user_cards=[11, 11, 2],  # 24
            alpha_cards=[10, 10, 5],  # 25
            beta_cards=[9, 9, 9],  # 27
            gamma_cards=[11, 11],  # 22
        )
        outcome = determine_outcome(state)
        assert outcome.winners == []
        assert outcome.winning_score is None
        assert outcome.all_busted

    def test_winner_at_21_beats_lower_scores(self) -> None:
        state = _build_finished_game(
            user_cards=[10, 11],  # 21
            alpha_cards=[10, 10],  # 20
            beta_cards=[9, 9],  # 18
            gamma_cards=[5, 5],  # 10
        )
        outcome = determine_outcome(state)
        assert outcome.winners == [PlayerType.USER]
        assert outcome.winning_score == BLACKJACK_TARGET

    def test_busted_players_excluded_from_winner_pool(self) -> None:
        state = _build_finished_game(
            user_cards=[11, 11, 2],  # 24 — busted
            alpha_cards=[10, 8],  # 18 — eligible
            beta_cards=[11, 11],  # 22 — busted
            gamma_cards=[7, 7],  # 14 — eligible
        )
        outcome = determine_outcome(state)
        assert outcome.winners == [PlayerType.ALPHA]
        assert outcome.winning_score == 18

    def test_incomplete_game_raises(self) -> None:
        state = GameState()
        # No one has stood yet
        with pytest.raises(ValueError, match="not yet complete"):
            determine_outcome(state)

    def test_outcome_summary_messages(self) -> None:
        single_winner = _build_finished_game([10, 10], [5, 5], [5, 5], [5, 5])
        assert "Winner: User" in determine_outcome(single_winner).summary

        tie = _build_finished_game([10, 10], [10, 10], [5, 5], [5, 5])
        tie_outcome = determine_outcome(tie)
        assert "Tie at 20" in tie_outcome.summary

        all_bust = _build_finished_game([11, 11, 2], [11, 11, 2], [11, 11, 2], [11, 11, 2])
        assert "All players busted" in determine_outcome(all_bust).summary


def test_is_safe_total() -> None:
    assert is_safe_total(0)
    assert is_safe_total(BLACKJACK_TARGET)
    assert not is_safe_total(BLACKJACK_TARGET + 1)