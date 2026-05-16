"""Graphic agent — generates image prompts and optionally renders them."""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from anthropic import Anthropic

from ..config import MODEL
from ..schemas import PostFinal, Research, VisualPrompt, Visuals

log = logging.getLogger(__name__)

GRAPHIC_SYSTEM = """You are the graphic agent. Given a LinkedIn post about
stablecoins, payments, or crypto, produce exactly three visual concept prompts
suitable for image generation (DALL-E / gpt-image-1 / Midjourney / Imagen).

Style direction across all three:
- Editorial / financial-publication aesthetic. Think The Information, Stratechery,
  Bloomberg graphics — not crypto-bro neon.
- Clean composition, strong focal point, lots of negative space, restrained palette.
- Muted professional palette: slate, ivory, deep navy, accent of one warm color
  (terracotta, amber, or muted gold).
- No literal logos, no recognizable brand marks, no faces of real people.
- No text inside the image (LinkedIn renders the headline; the image is visual).
- Photorealistic-or-illustration is fine; pick one direction per concept and commit.

The three concepts should be meaningfully different — give the operator real choice.
Suggested mix:
  1. Conceptual / metaphorical (abstract visualization of the idea)
  2. Object-based (a physical object photographed editorial-style that evokes the topic)
  3. Diagrammatic / data-viz feel (clean infographic or system illustration)

For each, produce:
- A one-line concept
- A detailed prompt (~80-150 words) that a generation model can follow directly,
  including composition, lighting, palette, framing, mood
- Style notes (palette hex codes if relevant, framing, mood)
"""


def generate_prompts(client: Anthropic, post: PostFinal, research: Research) -> Visuals:
    user_prompt = f"""Post body:

{post.body}

Topic: {research.topic}
Angle: {research.angle}

Produce three visual prompts."""

    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=GRAPHIC_SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": user_prompt}],
        output_format=Visuals,
    )
    if response.parsed_output is None:
        raise RuntimeError("Graphic agent could not produce prompts")
    return response.parsed_output


def render_images(prompts: list[VisualPrompt], out_dir: Path) -> list[Path]:
    """Render each prompt via OpenAI gpt-image-1. Returns paths of generated files.
    Returns empty list if OPENAI_API_KEY is missing or generation fails."""
    if not os.environ.get("OPENAI_API_KEY"):
        log.info("OPENAI_API_KEY not set — skipping image generation, prompts only")
        return []

    try:
        from openai import OpenAI
    except ImportError:
        log.warning("openai package not installed — skipping image generation")
        return []

    client = OpenAI()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for p in prompts:
        try:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=p.full_prompt,
                size="1024x1024",
                n=1,
            )
            b64 = result.data[0].b64_json
            if not b64:
                log.warning("Image %d returned no b64 data, skipping", p.id)
                continue
            path = out_dir / f"{p.id}.png"
            path.write_bytes(base64.b64decode(b64))
            paths.append(path)
            log.info("Generated image %d -> %s", p.id, path)
        except Exception as exc:
            log.warning("Image %d failed: %s", p.id, exc)
            continue

    return paths


def run(
    client: Anthropic,
    post: PostFinal,
    research: Research,
    out_dir: Path,
) -> tuple[Visuals, list[Path]]:
    visuals = generate_prompts(client, post, research)
    image_paths = render_images(visuals.prompts, out_dir)
    return visuals, image_paths
