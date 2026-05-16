"""Content manager — produces scheduling metadata and the post bundle."""
from __future__ import annotations

from anthropic import Anthropic

from ..config import BRAND_VOICE, DEFAULT_CHANNELS, MODEL
from ..schemas import PostFinal, Research, Schedule
from ..utils import slugify, today_utc

MANAGER_SYSTEM = f"""{BRAND_VOICE}

You are the content manager. You are given the finalized LinkedIn post and the
research that produced it. Produce scheduling metadata:

- title: a short internal title (5-9 words) for tracking. Not posted publicly.
- slug: kebab-case, 4-7 words, derived from the title. Used as a filename.
- suggested_post_time_utc: an ISO 8601 datetime within the next 7 days at the
  best window for a payments / fintech LinkedIn audience. LinkedIn engagement
  on professional B2B content peaks Tue-Thu 13:00-15:00 UTC (08:00-10:00 ET,
  catching morning US East Coast + late afternoon Europe). Avoid Mondays before
  noon UTC and Friday afternoons.
- rationale: one sentence explaining the timing choice.
- channels: ["linkedin"]
- hashtags: same as the post's hashtags, lowercase, no leading #.
"""


def run(client: Anthropic, post: PostFinal, research: Research) -> Schedule:
    user_prompt = f"""Post body:

{post.body}

Hashtags from post: {post.hashtags}

Research topic: {research.topic}
Today is {today_utc()} UTC.

Produce the schedule metadata."""

    response = client.messages.parse(
        model=MODEL,
        max_tokens=2000,
        system=MANAGER_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        output_format=Schedule,
    )
    if response.parsed_output is None:
        raise RuntimeError("Manager could not produce schedule metadata")

    schedule = response.parsed_output
    if not schedule.channels:
        schedule.channels = list(DEFAULT_CHANNELS)
    schedule.slug = slugify(schedule.slug or schedule.title)
    schedule.hashtags = [h.lstrip("#").lower() for h in schedule.hashtags]
    return schedule
