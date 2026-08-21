# Agent instructions — fpl-x

Personal Python CLI for **Bruno Mars XI** (FPL manager `4703066`). It fetches the squad, renders a pitch graphic, and can post that image to X. Run by hand on this Windows PC, typically once or twice a week.

Read this file first. For graphic/caption work, also follow `.cursor/skills/fpl-team-graphic/SKILL.md`.

## Stack

- Python 3.11+, src layout (`src/fpl_x`), installable via `pip install -e .`
- httpx (FPL API), Jinja2 + Playwright Chromium (PNG), tweepy OAuth 1.0a (X)
- Config: `.env` via python-dotenv. Template: `.env.example`

## Commands (Git Bash)

`python` is not on PATH. Use the venv interpreter with **forward slashes**. Do not use `.\.venv\Scripts\python.exe` in Git Bash (backslashes are escapes).

```bash
.venv/Scripts/python.exe -m fpl_x publish --dry-run
.venv/Scripts/python.exe -m fpl_x publish --dry-run --gw 1
.venv/Scripts/python.exe -m fpl_x publish
```

`--dry-run` writes `output/gw{N}.png` and `output/gw{N}.json`. Nothing is posted to X.

Setup (once): `py -3 -m venv .venv`, then install editable package and Chromium as in `README.md`.

## Layout

| Path | Role |
|---|---|
| `src/fpl_x/cli.py` | `publish` CLI |
| `src/fpl_x/fpl.py` | FPL fetch, `TeamSnapshot`, caption |
| `src/fpl_x/render.py` | HTML → PNG (Playwright, 1080×1800 viewport) |
| `src/fpl_x/twitter.py` | Media upload + tweet |
| `src/fpl_x/config.py` | `.env` settings |
| `src/fpl_x/templates/team_card.html` | Pitch graphic (visual source of truth) |
| `output/gw{N}.png` | Generated card (gitignored) |
| `output/gw{N}.json` | Caption and team metadata from that run |

Pipeline: `build_snapshot` → `render_card` → `snapshot.caption()` → optional `post_image`.

## FPL vs X

- **After deadline:** public picks. Token not required.
- **Before deadline:** `FPL_ACCESS_TOKEN` in `.env` (OIDC `access_token`, not `id_token`). Token lasts a few hours. How to copy it: `README.md`.
- X keys (`X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`) are only needed for a real post. Dry-run does not need them.

## Hard rules

- Never commit `.env`. Never paste tokens, refresh tokens, or X keys into chat or files that will be committed.
- Do not post to X unless the user explicitly asks. Default to `--dry-run`.
- Do not put URLs on the graphic or in the caption (X bills URL posts higher).
- Caption shape is defined in `TeamSnapshot.caption()` — keep that shape (GW line, captain, formation, optional chip/transfers, hashtags).
- Graphic look: official FPL pitch style (kits, name plate, fixture, C/V). Not player-headshot circles. Colors and layout: the team-graphic skill.
- Keep changes small. This is a one-manager personal tool, not a multi-tenant product.

## After graphic or caption edits

1. Dry-run from Git Bash.
2. Open `output/gw{N}.png` and check kits, C/V, formation, truncation.
3. Stop there unless the user asked to tweet.
