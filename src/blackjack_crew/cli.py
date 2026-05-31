"""Command-line interface — Typer commands for the Blackjack Crew app.

Two commands today:
    blackjack-crew play [--seed N]   Start a game (optional seed for reproducibility)
    blackjack-crew version           Show the package version
"""

from __future__ import annotations

import typer
from dotenv import load_dotenv

from blackjack_crew import __version__
from blackjack_crew.game.engine import GameConfig, play_game
from blackjack_crew.ui import display

app = typer.Typer(
    name="blackjack-crew",
    help="A simplified Blackjack game powered by a CrewAI agent crew.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def play(
    seed: int | None = typer.Option(
        None,
        "--seed",
        "-s",
        help="Optional seed for reproducible games (deterministic card draws).",
    ),
) -> None:
    """Start a new game of Blackjack against the AI crew."""
    # Load .env before any agent code runs — this is the only entry point.
    load_dotenv()
    try:
        play_game(GameConfig(seed=seed))
    except KeyboardInterrupt:
        display.console.print("\n[dim]Game interrupted. Goodbye.[/dim]")
        raise typer.Exit(code=130) from None


@app.command()
def version() -> None:
    """Show the installed version of blackjack-crew."""
    typer.echo(f"blackjack-crew {__version__}")


if __name__ == "__main__":
    app()