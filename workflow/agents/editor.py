"""Editor agent — tightens the draft and enforces format constraints."""
from __future__ import annotations

from anthropic import Anthropic

from ..config import (
    BRAND_VOICE,
    LINKEDIN_ABOVE_FOLD,
    LINKEDIN_HARD_MAX,
    LINKEDIN_TARGET_MAX,
    LINKEDIN_TARGET_MIN,
    MODEL,
)
from ..schemas import PostDraft, PostFinal

EDITOR_SYSTEM = f"""{BRAND_VOICE}

You are the editor agent. You receive a draft LinkedIn post and tighten it.

Your edits should:
- Strengthen the hook in the first {LINKEDIN_ABOVE_FOLD} characters
- Cut filler, hedging, and redundant sentences
- Replace vague claims with specifics where possible (you can keep specifics
  from the draft; don't invent new ones)
- Fix any markdown that snuck in (LinkedIn renders plain text only)
- Enforce length: total post must be {LINKEDIN_TARGET_MIN}-{LINKEDIN_TARGET_MAX}
  chars, absolute hard cap {LINKEDIN_HARD_MAX}
- Enforce hashtag count: 3-5, lowercase, on the last line
- Remove LinkedIn cliches: rocket emojis, "humbled to share", three-line
  breaks between every sentence, generic "thoughts?" sign-offs
- Preserve the writer's voice. If the draft is already tight, change little.

Return the final body, the hook (first line or two), the cleaned hashtag list,
the precise character count, and a list of edits you applied (3-7 bullets).
"""


def _enforce_constraints(post: PostFinal) -> list[str]:
    """Quick post-hoc check. Returns any violations as strings."""
    issues: list[str] = []
    if post.char_count > LINKEDIN_HARD_MAX:
        issues.append(f"Body is {post.char_count} chars, exceeds hard max {LINKEDIN_HARD_MAX}")
    if len(post.hashtags) < 3:
        issues.append(f"Only {len(post.hashtags)} hashtags, need at least 3")
    if len(post.hashtags) > 5:
        issues.append(f"{len(post.hashtags)} hashtags, max is 5")
    actual_len = len(post.body)
    if abs(actual_len - post.char_count) > 5:
        issues.append(
            f"Reported char_count {post.char_count} doesn't match actual {actual_len}"
        )
    return issues


def run(client: Anthropic, draft: PostDraft, max_retries: int = 2) -> PostFinal:
    feedback: str | None = None
    last: PostFinal | None = None

    for attempt in range(max_retries + 1):
        user_parts = [
            f"Draft body:\n\n{draft.body}",
            f"\nWriter's hook: {draft.hook}",
            f"\nWriter's hashtags: {' '.join('#' + h.lstrip('#') for h in draft.hashtags)}",
            f"\nWriter's rationale: {draft.rationale}",
        ]
        if feedback:
            user_parts.append(f"\n\nPrior attempt had these issues — fix them:\n{feedback}")

        response = client.messages.parse(
            model=MODEL,
            max_tokens=4000,
            system=EDITOR_SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
            output_format=PostFinal,
        )
        if response.parsed_output is None:
            raise RuntimeError("Editor could not produce a final post")

        last = response.parsed_output
        last.char_count = len(last.body)
        issues = _enforce_constraints(last)
        if not issues:
            return last
        feedback = "\n".join(f"- {i}" for i in issues)

    assert last is not None
    return last
