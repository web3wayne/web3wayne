"""Pydantic models passed between agents."""
from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str
    summary: str = Field(description="1-2 sentence summary of why this source matters")


class Research(BaseModel):
    topic: str = Field(description="The specific topic the post will cover")
    angle: str = Field(description="The hook angle — what makes this worth posting about now")
    why_now: str = Field(description="Why this topic is timely (last 7 days context)")
    key_points: list[str] = Field(min_length=3, max_length=6)
    sources: list[Source] = Field(min_length=2, max_length=8)
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Other topics that were considered but not picked",
    )


class PostDraft(BaseModel):
    body: str = Field(description="Full post body including hashtags, ready to paste into LinkedIn")
    hook: str = Field(description="First 1-2 lines of body, repeated for clarity")
    hashtags: list[str] = Field(min_length=3, max_length=5)
    rationale: str = Field(description="Why this hook and angle work for the audience")


class PostFinal(BaseModel):
    body: str
    hook: str
    hashtags: list[str]
    char_count: int
    edits_applied: list[str] = Field(description="What the editor changed and why")


class VisualPrompt(BaseModel):
    id: int
    concept: str = Field(description="One-line concept for this visual")
    full_prompt: str = Field(description="Detailed prompt ready for image generation")
    style_notes: str = Field(description="Palette, composition, mood")


class Visuals(BaseModel):
    prompts: list[VisualPrompt] = Field(min_length=3, max_length=3)


class Schedule(BaseModel):
    title: str = Field(description="Internal title for tracking, not posted")
    slug: str = Field(description="kebab-case slug for filenames and branches")
    suggested_post_time_utc: str = Field(description="ISO 8601 timestamp")
    rationale: str = Field(description="Why this timing for this audience")
    channels: list[str]
    hashtags: list[str]
