"""PydanticAI agent wiring with direct LLM provider support."""
from __future__ import annotations
from typing import Optional
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel

from app.agent.tools import (
    AgentDeps,
    tool_get_plan_sections,
    tool_search_plan_options,
    tool_get_plan_option,
    tool_search_parsed_plan_items,
    tool_match_consumption_to_plan,
    tool_log_consumption,
    tool_get_daily_status,
    tool_correct_consumption,
    tool_delete_consumption,
    tool_build_advice_context,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a warm, supportive personal diet tracking assistant. 🌸
Your job is to help the user track their food consumption against their personalized diet plan.

## Core Rules
- NEVER calculate nutrition or quantities yourself unless a meal is completely unknown to the plan.
- NEVER write directly to Excel — always use the log_consumption tool.
- NEVER fabricate plan options, item names, or quantities — use search tools first.
- If confidence is below threshold, ask the user for confirmation before logging.
- Preserve ambiguity honestly. If you cannot reliably match something, say so.
- Be warm, encouraging, and supportive. Never judgmental.
- The user may write in Persian, English, or a mix — handle both gracefully.
- When the user logs food, always confirm what was logged and show event IDs.
- When uncertain, present best candidates and ask the user to confirm.

## Unknown Meals (not in diet plan)
If the user reports a meal that does not match any plan option or item (confidence below threshold):
1. Acknowledge that the meal isn't in their plan.
2. Estimate the calorie count using your nutritional knowledge — be explicit: "approximately X kcal".
3. Find the closest matching plan item if one exists.
4. Log a consumption entry using log_consumption with:
   - log_type: "item"
   - item_name: the closest plan item name, or a short generic name if nothing is close
   - estimated_calories: your numeric calorie estimate (as a number, not text)
   - notes: "Original meal: [exact user description] — estimated ~X kcal"
5. Clearly tell the user what you logged, the event ID, and the estimated calories.

## Calorie Goal Awareness
Your context below shows the user's daily calorie goal and today's running calorie total.
- When today's total is ≥ 80% of goal: gently remind them they are approaching their limit. ⚠️
- When today's total is ≥ 100% of goal: kindly note they have reached their daily target. 🎯
- If no calorie goal is set, skip these reminders.
- Never be judgmental — frame it as helpful awareness, not criticism.

## Output Formatting (MANDATORY)
- ALWAYS format your responses with markdown and relevant emojis.
- Use **bold** for item names, section headers, and key numbers.
- Use bullet points to list foods, options, or events.
- Use food emojis when listing meals: 🍎 🥗 🥙 🥩 🥛 🍵 🍞 🥚 🧀 🍇
- Use status emojis: ✅ logged, ⚠️ warning, 💬 note, 📊 stats, 🔥 calories, 🎯 goal
- Show calorie estimates when known: "🔥 ~X kcal"
- After logging, show a compact summary table or list of what was logged.

## Logging Flow
1. Use match_consumption_to_plan to understand what the user reported.
2. If confidence >= auto threshold: log directly with log_consumption.
3. If confidence is between confirm and auto: present matches and ask to confirm.
4. If confidence < confirm threshold: treat as unknown meal (see Unknown Meals above).
5. After logging, call get_daily_status to show updated progress.

Always end responses with a friendly, encouraging note. 💕
"""


def _format_daily_status(status: dict, calorie_goal: int = 0, total_calories: float = 0.0) -> str:
    """Compact plain-text summary of today's logs for injection into the system prompt."""
    lines: list[str] = []

    logged_options = status.get("logged_options", [])
    logged_items = status.get("logged_items", [])
    section_coverage = status.get("section_coverage", {})

    if not logged_options and not logged_items:
        lines.append("Nothing logged yet today.")
    else:
        if logged_options:
            lines.append("Logged full options:")
            for ev in logged_options:
                section = ev.get("section", "")
                opt_no = ev.get("option_no", "")
                text = (ev.get("source_option_text") or "")[:80]
                ts = (ev.get("timestamp_local") or "")[:16]
                lines.append(f"  • [{section} option {opt_no}] {text} (at {ts})")

        if logged_items:
            lines.append("Logged individual items:")
            for ev in logged_items:
                item = ev.get("item_name") or ""
                qty = ev.get("consumed_qty_text") or ""
                section = ev.get("section") or ""
                cal = ev.get("estimated_calories")
                cal_str = f" | ~{int(cal)} kcal" if cal else ""
                ts = (ev.get("timestamp_local") or "")[:16]
                lines.append(f"  • {item} {qty} [{section}]{cal_str} (at {ts})")

    uncovered = [
        s for s in ["Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Snack 3"]
        if s not in section_coverage
    ]
    if uncovered:
        lines.append(f"Sections not yet logged: {', '.join(uncovered)}")

    if calorie_goal > 0:
        pct = (total_calories / calorie_goal * 100) if calorie_goal else 0
        lines.append(f"Calories today: ~{int(total_calories)} kcal / {calorie_goal} kcal goal ({pct:.0f}%)")

    return "\n".join(lines)


def create_agent(settings=None) -> Agent:
    if settings is None:
        settings = get_settings()

    base_url = settings.llm_base_url or None

    # pydantic-ai 1.x uses a Provider pattern
    if settings.llm_provider == "openai":
        from pydantic_ai.providers.openai import OpenAIProvider
        model = OpenAIModel(
            settings.llm_model,
            provider=OpenAIProvider(
                api_key=settings.openai_api_key or None,
                base_url=base_url,
            ),
        )
    else:
        from pydantic_ai.providers.anthropic import AnthropicProvider
        model = AnthropicModel(
            settings.llm_model,
            provider=AnthropicProvider(
                api_key=settings.anthropic_api_key or None,
                base_url=base_url,
            ),
        )

    # No static system_prompt — dynamic decorator below injects memory context
    agent = Agent(
        model=model,
        deps_type=AgentDeps,
        output_type=str,
    )

    @agent.system_prompt
    async def build_system_prompt(ctx: RunContext[AgentDeps]) -> str:
        import datetime
        import pytz

        tz = pytz.timezone(ctx.deps.tz)
        now = datetime.datetime.now(tz)
        today_str = now.strftime("%Y-%m-%d")
        now_str = now.strftime("%A, %Y-%m-%d — %H:%M")

        prompt = SYSTEM_PROMPT

        # ── current date/time ────────────────────────────────────────────────
        prompt += f"\n\n## Current date & time\n{now_str} ({ctx.deps.tz})"

        # ── calorie goal ─────────────────────────────────────────────────────
        if ctx.deps.calorie_goal > 0:
            total = ctx.deps.total_calories_today
            goal = ctx.deps.calorie_goal
            pct = total / goal * 100 if goal else 0
            prompt += (
                f"\n\n## Daily calorie goal\n"
                f"Goal: {goal} kcal | Today so far: ~{int(total)} kcal ({pct:.0f}%)"
            )
        else:
            prompt += "\n\n## Daily calorie goal\nNot set — user has not configured a calorie goal yet."

        # ── today's consumption snapshot ─────────────────────────────────────
        try:
            status = tool_get_daily_status(ctx.deps, today_str)
            prompt += "\n\n## Today's consumption so far\n"
            prompt += _format_daily_status(
                status,
                calorie_goal=ctx.deps.calorie_goal,
                total_calories=ctx.deps.total_calories_today,
            )
        except Exception:
            prompt += "\n\n## Today's consumption so far\nNot available (no plan loaded)."

        # ── cross-session memory ─────────────────────────────────────────────
        if ctx.deps.memory_context:
            prompt += (
                "\n\n## What you remember about this user from previous sessions\n"
                + ctx.deps.memory_context
            )

        return prompt

    @agent.tool
    async def get_plan_sections(ctx: RunContext[AgentDeps]) -> list:
        """Returns the meal sections and option counts from the active diet plan."""
        return tool_get_plan_sections(ctx.deps)

    @agent.tool
    async def search_plan_options(
        ctx: RunContext[AgentDeps],
        query: str,
        section_filter: Optional[str] = None,
        limit: int = 5,
    ) -> list:
        """Search for plan options matching a query. Optionally filter by section name."""
        return tool_search_plan_options(ctx.deps, query, section_filter, limit)

    @agent.tool
    async def get_plan_option(
        ctx: RunContext[AgentDeps],
        section: str,
        option_no: int,
    ) -> Optional[dict]:
        """Get the full details of a specific plan option by section and number."""
        return tool_get_plan_option(ctx.deps, section, option_no)

    @agent.tool
    async def search_parsed_plan_items(
        ctx: RunContext[AgentDeps],
        query: str,
        limit: int = 5,
    ) -> list:
        """Search for individual parsed food items within plan options."""
        return tool_search_parsed_plan_items(ctx.deps, query, limit)

    @agent.tool
    async def match_consumption_to_plan(
        ctx: RunContext[AgentDeps],
        user_text: str,
    ) -> dict:
        """Match the user's consumption report to plan options or items. Returns confidence scores."""
        return tool_match_consumption_to_plan(ctx.deps, user_text)

    @agent.tool
    async def log_consumption(
        ctx: RunContext[AgentDeps],
        entries: list,
        raw_user_message: str,
    ) -> dict:
        """Write confirmed consumption entries to the Excel workbook."""
        return tool_log_consumption(ctx.deps, entries, raw_user_message)

    @agent.tool
    async def get_daily_status(
        ctx: RunContext[AgentDeps],
        date: Optional[str] = None,
    ) -> dict:
        """Get today's (or a specific date's) logged consumption and remaining plan amounts."""
        return tool_get_daily_status(ctx.deps, date)

    @agent.tool
    async def correct_consumption(
        ctx: RunContext[AgentDeps],
        event_id: str,
        patch: dict,
    ) -> dict:
        """Correct a previously logged consumption event by event ID."""
        return tool_correct_consumption(ctx.deps, event_id, patch)

    @agent.tool
    async def delete_consumption(
        ctx: RunContext[AgentDeps],
        event_id: str,
    ) -> dict:
        """Delete (mark as deleted) a logged consumption event by event ID."""
        return tool_delete_consumption(ctx.deps, event_id)

    @agent.tool
    async def build_advice_context(
        ctx: RunContext[AgentDeps],
        date: Optional[str] = None,
    ) -> dict:
        """Build a deterministic advice context for today's consumption vs plan."""
        return tool_build_advice_context(ctx.deps, date)

    return agent


_agent_instance: Optional[Agent] = None


def get_agent() -> Agent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_agent()
    return _agent_instance
