"""Tests for game state Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blackjack_crew.game.cards import MAX_CARD_VALUE, MIN_CARD_VALUE
from blackjack_crew.game.state import (
    BLACKJACK_TARGET,
    MAX_CARDS_PER_PLAYER,
    Card,
    GameState,
    Hand,
    PlayerState,
    PlayerType,
)


class TestCard:
    def test_valid_card_values_succeed(self) -> None:
        for value in range(MIN_CARD_VALUE, MAX_CARD_VALUE + 1):
            card = Card(value=value)
            assert card.value == value

    def test_card_below_minimum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Card(value=MIN_CARD_VALUE - 1)

    def test_card_above_maximum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Card(value=MAX_CARD_VALUE + 1)


class TestHand:
    def test_empty_hand_has_zero_total(self) -> None:
        hand = Hand()
        assert hand.total == 0
        assert hand.cards_drawn == 0
        assert not hand.is_busted
        assert hand.can_draw_more

    def test_total_sums_card_values(self) -> None:
        hand = Hand(cards=[Card(value=5), Card(value=7), Card(value=3)])
        assert hand.total == 15

    def test_busted_flag_at_22(self) -> None:
        hand = Hand(cards=[Card(value=11), Card(value=11), Card(value=2)])
        assert hand.total == 24
        assert hand.is_busted

    def test_at_target_is_not_busted(self) -> None:
        hand = Hand(cards=[Card(value=11), Card(value=10)])
        assert hand.total == BLACKJACK_TARGET
        assert not hand.is_busted

    def test_can_draw_blocked_at_max_cards(self) -> None:
        hand = Hand(cards=[Card(value=2), Card(value=2), Card(value=2)])
        assert hand.cards_drawn == MAX_CARDS_PER_PLAYER
        assert not hand.can_draw_more

    def test_can_draw_blocked_on_bust(self) -> None:
        hand = Hand(cards=[Card(value=11), Card(value=11)])
        assert hand.is_busted
        assert not hand.can_draw_more

    def test_add_card_succeeds_under_limit(self) -> None:
        hand = Hand(cards=[Card(value=5)])
        hand.add_card(Card(value=6))
        assert hand.cards_drawn == 2
        assert hand.total == 11

    def test_add_card_rejected_at_limit(self) -> None:
        hand = Hand(cards=[Card(value=2), Card(value=2), Card(value=2)])
        with pytest.raises(ValueError, match="maximum"):
            hand.add_card(Card(value=2))


class TestPlayerState:
    def test_default_player_state_is_unfinished(self) -> None:
        player = PlayerState(player_type=PlayerType.USER)
        assert not player.has_finished

    def test_player_finished_after_standing(self) -> None:
        player = PlayerState(player_type=PlayerType.ALPHA, has_stood=True)
        assert player.has_finished

    def test_player_finished_when_busted(self) -> None:
        hand = Hand(cards=[Card(value=11), Card(value=11)])
        player = PlayerState(player_type=PlayerType.BETA, hand=hand)
        assert player.has_finished

    def test_player_finished_at_three_cards(self) -> None:
        hand = Hand(cards=[Card(value=2), Card(value=3), Card(value=4)])
        player = PlayerState(player_type=PlayerType.GAMMA, hand=hand)
        assert player.has_finished


class TestGameState:
    def test_default_game_has_four_players(self) -> None:
        state = GameState()
        assert set(state.players.keys()) == set(PlayerType)
        assert state.current_turn_index == 0
        assert state.current_player == PlayerType.USER

    def test_game_not_complete_at_start(self) -> None:
        state = GameState()
        assert not state.is_complete

    def test_game_complete_when_all_stood(self) -> None:
        state = GameState()
        for player_type in PlayerType:
            state.players[player_type].has_stood = True
        assert state.is_complete

    def test_turn_order_validator_rejects_missing_player(self) -> None:
        with pytest.raises(ValidationError):
            GameState(turn_order=[PlayerType.USER, PlayerType.ALPHA, PlayerType.BETA])

    def test_turn_order_validator_rejects_duplicates(self) -> None:
        with pytest.raises(ValidationError):
            GameState(
                turn_order=[PlayerType.USER, PlayerType.USER, PlayerType.ALPHA, PlayerType.BETA]
            )