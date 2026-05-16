"""Writer agent — turns research into a LinkedIn-native draft post."""
from __future__ import annotations

from anthropic import Anthropic

from ..config import (
    BRAND_VOICE,
    LINKEDIN_ABOVE_FOLD,
    LINKEDIN_TARGET_MAX,
    LINKEDIN_TARGET_MIN,
    MODEL,
)
from ..schemas import PostDraft, Research

WRITER_SYSTEM = f"""{BRAND_VOICE}

You are the writer agent. Turn research into a LinkedIn post.

Format rules (LinkedIn-native, paste-ready plain text):
- Target {LINKEDIN_TARGET_MIN}-{LINKEDIN_TARGET_MAX} characters total, including hashtags.
- First {LINKEDIN_ABOVE_FOLD} chars (the "above the fold" preview on mobile) must
  carry the hook. Open with a concrete claim, surprising fact, or sharp question
  — not a setup sentence.
- Plain text only. No markdown (** or _). LinkedIn strips them.
- Short paragraphs (1-3 sentences). Use line breaks for rhythm.
- One specific insight per paragraph. No filler.
- End with 3-5 hashtags on the last line, lowercase, space-separated:
  e.g. "#stablecoins #payments #fintech"
- No emojis unless one genuinely earns its place (rare — skip by default).
- No "thoughts?" or "what do you think?" — invite engagement through the content
  itself, not a tacked-on question.

Structure to consider (not a template — adapt to the story):
1. Hook — concrete observation or claim
2. Context — what just happened, with specifics
3. Operator's read — what this actually means for payment businesses
4. Forward look or open question — what to watch next

Voice reminders:
- Write like someone who's actually building, not commenting from the sidelines.
- If you don't have a real insight, say less. Brevity beats padding.
"""


def run(client: Anthropic, research: Research) -> PostDraft:
    sources_block = "\n".join(
        f"- {s.title} ({s.url}) — {s.summary}" for s in research.sources
    )
    user_prompt = f"""Topic: {research.topic}

Angle: {research.angle}

Why now: {research.why_now}

Key points to draw from:
{chr(10).join(f"- {p}" for p in research.key_points)}

Sources:
{sources_block}

Write the LinkedIn post. Return body, hook, hashtags, and a short rationale
for why this hook works."""

    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=WRITER_SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": user_prompt}],
        output_format=PostDraft,
    )
    if response.parsed_output is None:
        raise RuntimeError("Writer could not produce a draft")
    return response.parsed_output
