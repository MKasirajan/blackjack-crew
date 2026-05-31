"""Agent factory — converts Persona definitions into configured CrewAI Agents.

Reads the OpenAI model name from environment (via OPENAI_MODEL) and assembles
each agent with the appropriate LLM, tools, and persona. The factory layer
isolates CrewAI's Agent construction from the rest of the codebase, so
framework upgrades or persona tweaks are localised here.
"""

from __future__ import annotations

import os

from crewai import LLM, Agent
from crewai.tools import BaseTool

from blackjack_crew.agents.personas import ALPHA, BETA, DEALER, GAMMA, Persona
from blackjack_crew.agents.tools import draw_card_tool
from blackjack_crew.game.state import PlayerType


# Default tuning for agent LLM calls. gpt-5.5 is a reasoning model — it uses
# internal reasoning tokens before the visible response, so the budget must
# leave room for both. 2000 covers a comfortable margin for short decision
# outputs ("hit"/"stand" + one explanatory sentence).
DEFAULT_MAX_COMPLETION_TOKENS = 2000


def _build_llm() -> LLM:
    """Construct the shared LLM instance used by every agent.

    Reads `OPENAI_MODEL` from environment (with a sensible default). Other
    OpenAI settings (the API key) are picked up automatically by CrewAI
    from the environment via LiteLLM.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-5.5-2026-04-23")
    return LLM(
        model=model,
        max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS,
    )


def _build_agent(persona: Persona, tools: list[BaseTool], llm: LLM) -> Agent:
    """Assemble a CrewAI Agent from a persona, tool set, and LLM."""
    return Agent(
        role=persona.role,
        goal=persona.goal,
        backstory=persona.backstory,
        tools=tools,
        llm=llm,
        verbose=False,  # Suppress CrewAI's internal logging; UI layer handles display
        allow_delegation=False,  # Agents act independently; no inter-agent task delegation
        max_iter=3,  # Cap reasoning iterations per turn — prevents runaway loops
    )


def build_agents() -> dict[str, Agent]:
    """Construct the full set of four agents for a game.

    Returns:
        A dict mapping a string key to the configured Agent:
        - "dealer" → Dealer Agent (has Draw Card tool)
        - "alpha"  → Player Alpha (no tools)
        - "beta"   → Player Beta (no tools)
        - "gamma"  → Player Gamma (no tools)
    """
    llm = _build_llm()
    return {
        "dealer": _build_agent(DEALER, tools=[draw_card_tool], llm=llm),
        PlayerType.ALPHA.value: _build_agent(ALPHA, tools=[], llm=llm),
        PlayerType.BETA.value: _build_agent(BETA, tools=[], llm=llm),
        PlayerType.GAMMA.value: _build_agent(GAMMA, tools=[], llm=llm),
    }