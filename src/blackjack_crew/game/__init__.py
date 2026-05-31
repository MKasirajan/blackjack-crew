"""Game engine — pure Python, no LLM dependencies.

This subpackage contains the deterministic game logic: card drawing,
hand scoring, state representation, and the game loop orchestration.
It has no knowledge of CrewAI, OpenAI, or any agent framework — those
live in the `agents` subpackage and consume the engine through its
public API.
"""