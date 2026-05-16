"""Filesystem helpers."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "post"


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def post_dir(root: Path, date: str, slug: str) -> Path:
    d = root / "content" / "posts" / f"{date}-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def collect_text(content_blocks) -> str:
    """Join all text-type blocks from a Claude response.content list."""
    return "\n\n".join(b.text for b in content_blocks if b.type == "text").strip()
