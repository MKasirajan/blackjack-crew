"""Terminal rendering via `rich`.

All console output goes through this module — the engine and agent
layers stay output-agnostic. This separation makes it trivial to swap
the UI later (web, GUI, plain stdout) without touching game logic.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from blackjack_crew.game.state import (
    BLACKJACK_TARGET,
    MAX_CARDS_PER_PLAYER,
    GameOutcome,
    GameState,
    PlayerState,
    PlayerType,
)


# A single Console instance shared by the whole UI layer.
console = Console()


# ---------- Player display helpers ----------

_PLAYER_DISPLAY_NAMES: dict[PlayerType, str] = {
    PlayerType.USER: "You",
    PlayerType.ALPHA: "Alpha (Conservative)",
    PlayerType.BETA: "Beta (Aggressive)",
    PlayerType.GAMMA: "Gamma (Strategic)",
}

_PLAYER_COLORS: dict[PlayerType, str] = {
    PlayerType.USER: "bold cyan",
    PlayerType.ALPHA: "bold green",
    PlayerType.BETA: "bold red",
    PlayerType.GAMMA: "bold magenta",
}


def display_name(player: PlayerType) -> str:
    """Return the human-readable display name for a player."""
    return _PLAYER_DISPLAY_NAMES[player]


def colored_name(player: PlayerType) -> Text:
    """Return a Rich Text instance with the player's themed colour."""
    return Text(display_name(player), style=_PLAYER_COLORS[player])


# ---------- Section headers ----------

def render_title(seed: int | None) -> None:
    """Render the game welcome banner."""
    subtitle = "You vs Alpha, Beta, and Gamma — highest total under 21 wins."
    if seed is not None:
        subtitle += f"\n[dim]Reproducible mode — seed: {seed}[/dim]"
    console.print(
        Panel(
            Text.from_markup(
                "[bold]Blackjack Crew[/bold]\n"
                f"[dim]{subtitle}[/dim]",
                justify="center",
            ),
            border_style="cyan",
            padding=(1, 4),
        )
    )


def render_seating() -> None:
    """Announce that the agents have joined the table."""
    console.print()
    console.print("[dim]The Dealer is at the table.[/dim]")
    for player in (PlayerType.ALPHA, PlayerType.BETA, PlayerType.GAMMA):
        console.print(
            f"[dim]{display_name(player)} takes a seat.[/dim]"
        )
    console.print()


def render_turn_header(player: PlayerType) -> None:
    """Render the section header announcing whose turn it is."""
    console.rule(
        Text.assemble(("  ", "default"), colored_name(player), ("'s turn  ", "default")),
        style=_PLAYER_COLORS[player],
    )


# ---------- Hand display ----------

def _hand_summary(player_state: PlayerState) -> str:
    """One-line hand summary: cards, total, draws remaining."""
    cards = (
        ", ".join(str(card) for card in player_state.hand.cards)
        if player_state.hand.cards
        else "(empty)"
    )
    total = player_state.hand.total
    drawn = player_state.hand.cards_drawn
    return f"Hand: {cards}  •  Total: {total}  •  Cards: {drawn}/{MAX_CARDS_PER_PLAYER}"


def render_hand(player: PlayerType, player_state: PlayerState) -> None:
    """Render a one-line hand summary for a player after a state change."""
    summary = _hand_summary(player_state)
    style_marker = ""
    if player_state.hand.is_busted:
        style_marker = "  [bold red]BUSTED[/bold red]"
    elif player_state.hand.total == BLACKJACK_TARGET:
        style_marker = "  [bold green]21![/bold green]"
    console.print(f"  {display_name(player)}  •  {summary}{style_marker}")


# ---------- Action feedback ----------

def render_user_requests_card() -> None:
    console.print("[dim]You ask the Dealer for a card...[/dim]")


def render_agent_requests_card(player: PlayerType) -> None:
    console.print(f"[dim]{display_name(player)} asks the Dealer for a card.[/dim]")


def render_card_dealt(value: int) -> None:
    console.print(f"  [bold yellow]The Dealer draws and reports: {value}[/bold yellow]")


def render_user_stands(total: int) -> None:
    console.print(f"  [cyan]You stand at {total}.[/cyan]")


def render_agent_decision(
    player: PlayerType,
    decision: str,
    reasoning: str,
    total: int,
) -> None:
    """Render an agent's hit/stand decision plus their reasoning."""
    if decision == "hit":
        verb = "hits"
    else:
        verb = f"stands at {total}"
    console.print(f"  {display_name(player)} {verb}.")
    if reasoning:
        console.print(f"     [italic dim]\"{reasoning}\"[/italic dim]")


def render_busted(player: PlayerType, total: int) -> None:
    console.print(f"  [bold red]{display_name(player)} busted at {total}.[/bold red]")


# ---------- Final results ----------

def render_final_standings(state: GameState, outcome: GameOutcome) -> None:
    """Render the closing standings table and the winner announcement."""
    console.print()
    console.rule("  Final Standings  ", style="bold")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Player")
    table.add_column("Hand")
    table.add_column("Total", justify="right")
    table.add_column("Status")

    for player in state.turn_order:
        p_state = state.players[player]
        cards = (
            ", ".join(str(c) for c in p_state.hand.cards) if p_state.hand.cards else "—"
        )
        total_str = str(p_state.hand.total)
        if p_state.hand.is_busted:
            status = "[red]Busted[/red]"
        elif p_state.has_stood:
            status = "Stood"
        else:
            status = "Finished"
        table.add_row(display_name(player), cards, total_str, status)

    console.print(table)
    console.print()

    # Headline outcome panel
    if outcome.all_busted:
        console.print(
            Panel(
                "[bold red]All players busted — no winner this round.[/bold red]",
                border_style="red",
                padding=(0, 2),
            )
        )
    elif outcome.is_tie:
        names = " & ".join(display_name(p) for p in outcome.winners)
        console.print(
            Panel(
                f"[bold yellow]Tie at {outcome.winning_score} — {names}[/bold yellow]",
                border_style="yellow",
                padding=(0, 2),
            )
        )
    else:
        winner = outcome.winners[0]
        console.print(
            Panel(
                Text.assemble(
                    ("Winner: ", "bold"),
                    colored_name(winner),
                    (f"  with {outcome.winning_score}", "bold"),
                ),
                border_style=_PLAYER_COLORS[winner].split()[-1],
                padding=(0, 2),
            )
        )


# ---------- Input prompts ----------

def prompt_user_action(can_draw_more: bool) -> str:
    """Prompt the user for their next action.

    Returns the validated action string: "deal" or "stand". If `can_draw_more`
    is False (user has hit 3 cards or busted), only "stand" is acceptable.
    """
    if not can_draw_more:
        console.print("[dim]You have no more draws available — you must stand.[/dim]")
        Prompt.ask("Press Enter to stand", default="")
        return "stand"

    return Prompt.ask(
        "What would you like to do? [cyan][deal][/cyan] / [cyan][stand][/cyan]",
        choices=["deal", "stand"],
        default="deal",
    )


# ---------- Errors ----------

def render_error(message: str) -> None:
    console.print(
        Panel(
            f"[bold red]{message}[/bold red]",
            title="Error",
            border_style="red",
            padding=(0, 2),
        )
    )