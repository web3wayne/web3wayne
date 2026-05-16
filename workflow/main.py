"""Orchestrator — runs the five-agent content pipeline end to end."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import anthropic

from .agents import editor, graphic, manager, researcher, writer
from .schemas import PostFinal, Research, Schedule, Visuals
from .utils import now_utc_iso, post_dir, today_utc, write_text

log = logging.getLogger("workflow")


def _yaml_str(value: str) -> str:
    """Render a Python string as a double-quoted YAML scalar."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _frontmatter(schedule: Schedule, post: PostFinal) -> str:
    hashtags_yaml = ", ".join(_yaml_str(h) for h in schedule.hashtags)
    channel = schedule.channels[0] if schedule.channels else "linkedin"
    return (
        "---\n"
        f"date: {_yaml_str(today_utc())}\n"
        f"title: {_yaml_str(schedule.title)}\n"
        f"channel: {_yaml_str(channel)}\n"
        f"scheduled_at: {_yaml_str(schedule.suggested_post_time_utc)}\n"
        f"hashtags: [{hashtags_yaml}]\n"
        f"char_count: {post.char_count}\n"
        f"generated_at: {_yaml_str(now_utc_iso())}\n"
        "---\n\n"
    )


def _render_research_md(research: Research, raw_notes: str) -> str:
    parts = ["# Research\n", f"**Topic:** {research.topic}\n", f"**Angle:** {research.angle}\n",
             f"**Why now:** {research.why_now}\n", "## Key points\n"]
    parts += [f"- {p}" for p in research.key_points]
    parts.append("\n## Sources\n")
    parts += [f"- [{s.title}]({s.url}) — {s.summary}" for s in research.sources]
    if research.alternatives_considered:
        parts.append("\n## Alternatives considered\n")
        parts += [f"- {a}" for a in research.alternatives_considered]
    parts.append("\n## Raw research notes\n")
    parts.append(raw_notes)
    return "\n".join(parts) + "\n"


def _render_visuals_md(visuals: Visuals, image_paths: list[Path]) -> str:
    parts = ["# Visual prompts\n"]
    rendered = {p.stem: p.name for p in image_paths}
    for p in visuals.prompts:
        parts.append(f"## Concept {p.id}: {p.concept}\n")
        parts.append(f"**Style notes:** {p.style_notes}\n")
        parts.append(f"**Prompt:**\n\n{p.full_prompt}\n")
        if str(p.id) in rendered:
            parts.append(f"![concept {p.id}]({rendered[str(p.id)]})\n")
    return "\n".join(parts)


def _check_keys() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY is not set — cannot run the pipeline")
        return False
    if not os.environ.get("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY not set — pipeline will produce image prompts only, no PNGs")
    return True


def run_pipeline(repo_root: Path, topic_hint: str | None = None) -> dict:
    client = anthropic.Anthropic()

    log.info("[1/5] researcher: scanning recent stablecoin / payments / crypto news")
    raw_notes, research = researcher.run(client, topic_hint=topic_hint)
    log.info("  picked topic: %s", research.topic)

    log.info("[2/5] writer: drafting LinkedIn post")
    draft = writer.run(client, research)
    log.info("  draft length: %d chars", len(draft.body))

    log.info("[3/5] editor: tightening draft")
    final_post = editor.run(client, draft)
    log.info("  final length: %d chars", final_post.char_count)

    log.info("[4/5] manager: scheduling metadata")
    schedule = manager.run(client, final_post, research)
    log.info("  scheduled: %s", schedule.suggested_post_time_utc)

    out = post_dir(repo_root, today_utc(), schedule.slug)

    log.info("[5/5] graphic: rendering visuals into %s", out)
    visuals, image_paths = graphic.run(client, final_post, research, out / "visuals")
    log.info("  generated %d images, %d prompts", len(image_paths), len(visuals.prompts))

    write_text(out / "research.md", _render_research_md(research, raw_notes))
    write_text(out / "research.json", research.model_dump_json(indent=2))
    write_text(
        out / "post.md",
        _frontmatter(schedule, final_post) + final_post.body + "\n",
    )
    write_text(out / "post.txt", final_post.body + "\n")
    write_text(out / "visuals" / "prompts.md", _render_visuals_md(visuals, image_paths))
    write_text(out / "visuals" / "prompts.json", visuals.model_dump_json(indent=2))
    write_text(out / "schedule.json", schedule.model_dump_json(indent=2))

    readme_lines = [
        f"# {schedule.title}\n",
        f"**Scheduled:** {schedule.suggested_post_time_utc}",
        f"**Channel:** {', '.join(schedule.channels)}",
        f"**Char count:** {final_post.char_count}\n",
        "## Files",
        "- `post.txt` — paste this verbatim to LinkedIn",
        "- `post.md` — same content with frontmatter for archiving",
        "- `research.md` / `research.json` — what the researcher found",
        "- `visuals/prompts.md` — image prompts (and PNGs if rendered)",
        "- `schedule.json` — posting metadata",
        "",
        "## Scheduling rationale",
        schedule.rationale,
    ]
    write_text(out / "README.md", "\n".join(readme_lines) + "\n")

    return {
        "post_dir": str(out.relative_to(repo_root)),
        "title": schedule.title,
        "slug": schedule.slug,
        "date": today_utc(),
        "scheduled_at": schedule.suggested_post_time_utc,
        "char_count": final_post.char_count,
        "image_count": len(image_paths),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic-hint", default=None, help="Optional topic seed for the researcher")
    parser.add_argument("--output-meta", default=None, help="If set, write run metadata JSON here")
    parser.add_argument("--repo-root", default=".", help="Repo root (defaults to CWD)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not _check_keys():
        return 2

    topic_hint = args.topic_hint.strip() if args.topic_hint else None
    if not topic_hint:
        topic_hint = None

    repo_root = Path(args.repo_root).resolve()
    meta = run_pipeline(repo_root, topic_hint=topic_hint)
    log.info("done. output in %s", meta["post_dir"])

    if args.output_meta:
        Path(args.output_meta).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
