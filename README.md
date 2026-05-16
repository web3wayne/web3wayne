- Hi, I'm @web3wayne
- Interested in blockchain, fintech, and entrepreneurship
- Currently learning about smart contracts, tokenization, defi, nfts, leadership, entrepreneurship
- Looking to collaborate on payment solutions
- How to reach me: wayne@eukapay.com

---

## Weekly content pipeline

This repo also runs a five-agent content pipeline that drafts a LinkedIn post
about stablecoins, payments, and crypto every Monday at 14:00 UTC. Output lands
in a PR for review.

### Agents

| Stage | Agent | What it does |
|---|---|---|
| 1 | Researcher | Web-searches the last 7 days for stablecoin / payments / crypto stories, picks the single strongest angle, returns sources |
| 2 | Writer | Drafts a LinkedIn-native post in Wayne's voice — hook, key insight, operator's read |
| 3 | Editor | Tightens, fixes format, enforces LinkedIn character limits and hashtag count |
| 4 | Manager | Picks an optimal post time and produces scheduling metadata |
| 5 | Graphic | Generates three image-prompt concepts and (if `OPENAI_API_KEY` is set) renders PNGs via `gpt-image-1` |

All five agents run on Claude Opus 4.7 with adaptive thinking. Outputs are
typed Pydantic models passed between stages, so each handoff is validated.

### Setup

Add repo secrets:

- `ANTHROPIC_API_KEY` — required
- `OPENAI_API_KEY` — optional; without it the graphic agent outputs prompts only

That's it. The cron is already configured in `.github/workflows/content-pipeline.yml`.

### Running locally

```sh
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...      # optional
python -m workflow.main --topic-hint "stablecoin merchant settlement"
```

Output lands in `content/posts/<date>-<slug>/`.

### Output layout

```
content/posts/2026-05-18-stablecoin-rails-upgrade/
├── README.md           # index for this run
├── post.txt            # paste this to LinkedIn
├── post.md             # post + frontmatter for archiving
├── research.md         # research dump (human-readable)
├── research.json       # structured research data
├── schedule.json       # suggested post time + metadata
└── visuals/
    ├── prompts.md      # 3 image prompts
    ├── prompts.json    # structured prompts
    ├── 1.png           # rendered (if OPENAI_API_KEY set)
    ├── 2.png
    └── 3.png
```

### Tuning the voice

The brand voice and topic guardrails live in `workflow/config.py` — edit
`BRAND_VOICE` to change tone, topics to lean into, and topics to avoid.
Individual agent system prompts live in `workflow/agents/`.

### Manual runs

From the Actions tab, run the `Weekly content pipeline` workflow with an
optional topic hint.
