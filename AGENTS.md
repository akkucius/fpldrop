# Agent instructions — fpldrop

Personal Python CLI (`fpldrop`) for **Bruno Mars XI** (FPL manager `4703066`). It fetches the squad, renders a pitch graphic, and can post that image to X. Run by hand on this Windows PC, typically once or twice a week.

Read this file first. For graphic/caption work, also follow `.cursor/skills/fpl-team-graphic/SKILL.md`.

## Stack

- Python 3.11+, src layout (`src/fpldrop`), installable via `pip install -e .`
- httpx (FPL API), Jinja2 + Playwright Chromium (PNG), tweepy OAuth 1.0a (X)
- Config: `.env` via python-dotenv. Template: `.env.example`

## Commands (Git Bash)

`python` is not on PATH. Use the venv interpreter with **forward slashes**. Do not use `.\.venv\Scripts\python.exe` in Git Bash (backslashes are escapes).

```bash
.venv/Scripts/python.exe -m fpldrop preview
.venv/Scripts/python.exe -m fpldrop preview --text-only
.venv/Scripts/python.exe -m fpldrop publish --dry-run
.venv/Scripts/python.exe -m fpldrop publish
```

`preview` / `--dry-run` never post. They print a dotted tweet + pitch preview and write `output/gw{N}.preview.txt`. Full preview also writes the PNG. `--text-only` skips the graphic for a fast check.

A live `publish` (only when the user asks) uploads the PNG, tweets the caption, then writes `posted` / `tweet_id` into the JSON sidecar. The CLI reconfigures stdout to UTF-8 so the 🎯 caption does not crash Windows cp1252 before the tweet.

Setup (once): `py -3 -m venv .venv`, then install editable package and Chromium as in `README.md`.

## Layout

| Path | Role |
|---|---|
| `src/fpldrop/cli.py` | `publish` CLI |
| `src/fpldrop/fpl.py` | FPL fetch, `TeamSnapshot`, caption |
| `src/fpldrop/render.py` | HTML → PNG (Playwright, 1080×1800 viewport) |
| `src/fpldrop/twitter.py` | Media upload + tweet |
| `src/fpldrop/config.py` | `.env` settings |
| `src/fpldrop/templates/team_card.html` | Pitch graphic (visual source of truth) |
| `output/gw{N}.png` | Generated card (gitignored) |
| `output/gw{N}.json` | Caption, team metadata, `posted`, `tweet_id` |
| `output/gw{N}.preview.txt` | Dotted tweet + pitch preview |
| `logs/fpldrop.log` | UTC success/error lines |

Pipeline: `build_snapshot` → `render_card` → `snapshot.caption()` → optional `post_image`.

## FPL vs X

- **After deadline:** public picks. Token not required.
- **Before deadline:** `FPL_ACCESS_TOKEN` in `.env` (OIDC `access_token`, not `id_token` or `refresh_token`). Token lasts a few hours. How to copy it: `README.md`. Refresh-token exchange against FPL OIDC does not work; do not try to “fix” posting by wiring refresh.
- X posting is **OAuth 1.0a only**: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`. Ignore Bearer and OAuth 2.0 client credentials.
- Dry-run does not need X keys or credits.

## X credits (pay-per-use)

Credits live on [console.x.com](https://console.x.com) for the X app **Bruno Mars XI**. A **$5** balance was added on 23 Aug 2026. X Premium / Grok / other X AI plans do **not** add these credits.

- Image post **without a URL** ≈ **$0.015**. Do not put URLs on the graphic or in the caption.
- First live post succeeded the same day (GW1, tweet `2091475250529898563`). The pipeline is proven; still default to `--dry-run`.
- `402 Payment Required` / `credits depleted` means the PNG/JSON were saved but X refused the tweet. Tell the user to buy credits at [console.x.com/pricing](https://console.x.com/pricing). Do not invent a workaround (browser bots, unofficial schedulers).

## Hard rules

- Never commit `.env`. Never paste tokens, refresh tokens, or X keys into chat or files that will be committed.
- Do not post to X unless the user explicitly asks. Default to `--dry-run`.
- Do not put URLs on the graphic or in the caption (X bills URL posts higher).
- Caption shape is defined in `TeamSnapshot.caption()`; keep the scores recap. No em dashes in posted text.
- Graphic look: FPL pitch style (kits, name plate, per-player points, C/V, Points/Transfers pills). Not player-headshot circles. Colors and layout: the team-graphic skill.
- Keep changes small. This is a one-manager personal tool, not a multi-tenant product.

## After graphic or caption edits

1. Preview from Git Bash: `.venv/Scripts/python.exe -m fpldrop preview`
2. Check the dotted block / `output/gw{N}.preview.txt`, then open `output/gw{N}.png`
3. Confirm kits, C/V, points, pills, truncation
4. Stop there unless the user asked to tweet.
