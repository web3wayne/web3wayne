"""Content research agent — web-searches recent stablecoin/payment/crypto news."""
from __future__ import annotations

from anthropic import Anthropic

from ..config import BRAND_VOICE, MODEL
from ..schemas import Research
from ..utils import collect_text, today_utc

RESEARCHER_SYSTEM = f"""{BRAND_VOICE}

You are the research agent. Your job is to find the single most interesting
stablecoin / payments / crypto story worth posting about this week.

Process:
1. Search the web for news, announcements, regulatory actions, on-chain data,
   and primary reporting from the last 7 days.
2. Cast a wide net first (5-8 searches), then narrow to the single strongest
   story. Look for things that have clear "so what" for payment operators
   — not just price moves or speculation.
3. Verify with at least 2-3 credible sources (official announcements, primary
   reporting from Bloomberg / Reuters / The Block / CoinDesk / Decrypt,
   regulatory filings, project blog posts, on-chain data).

Output format — return a research dump in this structure:

# Picked topic
[One sentence stating the topic]

# Angle
[2-3 sentences on the specific take — what makes this worth posting]

# Why now
[1-2 sentences on timeliness — what happened in the last 7 days]

# Key points
- [point 1 with specifics — numbers, names, mechanics]
- [point 2]
- [point 3]
- [optional more]

# Sources
- [Source title] — [URL] — [why this matters]
- [Source title] — [URL] — [why this matters]
- ...

# Alternatives considered
- [Topic A — why not picked]
- [Topic B — why not picked]
"""

STRUCTURER_SYSTEM = """You're given research notes. Extract them into the
structured schema. Preserve source URLs verbatim — do not invent or modify
them. Keep specifics (numbers, names, dates) in key_points."""


def research_raw(client: Anthropic, topic_hint: str | None = None) -> str:
    today = today_utc()
    user_prompt = (
        f"Today is {today}. Research the most interesting stablecoin, payments, "
        f"or crypto-infrastructure story from the past 7 days that's worth a "
        f"LinkedIn post for a payments-focused audience. Use web search."
    )
    if topic_hint:
        user_prompt += f"\n\nTopic hint from the operator (consider but don't force it): {topic_hint}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=RESEARCHER_SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        tools=[{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 8,
        }],
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = collect_text(response.content)
    if not text:
        raise RuntimeError("Researcher produced no text output")
    return text


def structure(client: Anthropic, raw_notes: str) -> Research:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=STRUCTURER_SYSTEM,
        messages=[{"role": "user", "content": f"Research notes:\n\n{raw_notes}"}],
        output_format=Research,
    )
    if response.parsed_output is None:
        raise RuntimeError("Structurer could not parse research into schema")
    return response.parsed_output


def run(client: Anthropic, topic_hint: str | None = None) -> tuple[str, Research]:
    raw = research_raw(client, topic_hint)
    structured = structure(client, raw)
    return raw, structured
