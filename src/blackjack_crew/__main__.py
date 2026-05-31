"""Enable `python -m blackjack_crew` as an entry point.

Useful for development/debugging without needing the entry-point script
installed on PATH.
"""

from __future__ import annotations

from blackjack_crew.cli import app

if __name__ == "__main__":
    app()