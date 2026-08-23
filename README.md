# fpldrop

Share your FPL team each gameweek with a proper pitch graphic and a ready caption. It posts to X today, and other social apps will follow.

Python CLI for **Bruno Mars XI** (FPL manager `4703066`). Built for one or two posts a week, run by hand on this machine.

```bash
.venv/Scripts/python.exe -m fpldrop publish --dry-run
.venv/Scripts/python.exe -m fpldrop publish
```

`--dry-run` writes `output/gw{N}.png` and `output/gw{N}.json` (caption + team details). Nothing is sent to X.

A real `publish` (no `--dry-run`) uploads the PNG and tweets the caption. After a successful post the JSON sidecar sets `posted: true` and `tweet_id`. Errors and successes also go to `logs/fpldrop.log`.

The first live post worked on 23 Aug 2026 (GW1): https://x.com/i/web/status/2091475250529898563

Use **Git Bash** with forward slashes. `python` is not on PATH; `.\.venv\Scripts\python.exe` breaks in bash because backslashes are escapes.

## What you need

### This PC

- Python 3.11+ (`py -3`)
- Playwright Chromium (installed once below)

A small AWS EC2 instance is not worth it for weekly posts. The FPL access token also expires in hours, so a server would still need a fresh login.

### FPL

- Manager ID is `4703066`
- **After the gameweek deadline:** public picks, no token
- **Before the deadline:** FPL does not accept email/password for the API. Put `FPL_ACCESS_TOKEN` in `.env` (never commit it, never paste it in chat):
  1. Log in at [fantasy.premierleague.com](https://fantasy.premierleague.com) and open Pick Team
  2. DevTools → Console. If Chrome blocks paste, type `allow pasting` first
  3. Run this so the token **prints** (copy it from the console output):

```js
JSON.parse(localStorage.getItem("oidc.user:https://account.premierleague.com/as:bfcbaf69-aade-4c1b-8f00-c1cb8a193030")).access_token
```

  4. Paste into `FPL_ACCESS_TOKEN=` in `.env`

Copy **`access_token`**, not `id_token` and not `refresh_token`. The access token lasts a few hours. FPL refresh-token exchange does not work for this login, so do not rely on `FPL_REFRESH_TOKEN`.

### X (only required to post)

Pay-per-use at [console.x.com](https://console.x.com). A Bearer token cannot create posts. X Premium, Grok, and other X AI plans do **not** add Developer Console credits.

This project already has **$5 API credits** loaded (X app **Bruno Mars XI**). One image post with **no URL** in the caption is about **$0.015**. At one or two posts a week, $5 lasts a long time.

If X returns **`402 Payment Required` / `credits depleted`**, the graphic still saved locally but nothing was tweeted. Top up at [console.x.com/pricing](https://console.x.com/pricing) (Billing → Buy credits). Leave auto-recharge off unless you want it.

1. X account with a verified phone number
2. [console.x.com](https://console.x.com) → Project + App, **Read and Write**
3. API credit balance (currently $5)
4. OAuth 1.0a keys into `.env`: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

Ignore Bearer and OAuth 2.0 Client ID/Secret. This script uses OAuth 1.0a only.

## Setup

From the `fpldrop` repo root:

```bash
py -3 -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/python.exe -m playwright install chromium
cp .env.example .env
```

Edit `.env`: manager ID is already set. Add `FPL_ACCESS_TOKEN` for pre-deadline posts, and the four X keys when you are ready to tweet.

## Usage

```bash
.venv/Scripts/python.exe -m fpldrop publish --dry-run
.venv/Scripts/python.exe -m fpldrop publish --dry-run --gw 1
.venv/Scripts/python.exe -m fpldrop publish
```

`--gw` defaults to the current or next FPL gameweek. Open `output/gw{N}.png` and `output/gw{N}.json` before a real post.

Caption shape (no link):

```
Here's my GW1 Team

(C) Mbeumo
🎯 10k
Formation 4-4-2

All the best guys! Let's go.

#FPL #FPLCommunity
```

The CLI sets stdout to UTF-8 so that caption emoji prints on Windows (cp1252 used to crash before the tweet).

## Layout

| Path | Role |
|---|---|
| `src/fpldrop/fpl.py` | FPL fetch (public picks or authenticated `my-team`) |
| `src/fpldrop/render.py` | HTML pitch card → PNG (Playwright) |
| `src/fpldrop/twitter.py` | OAuth 1.0a media upload + post |
| `src/fpldrop/cli.py` | `publish` command |
| `src/fpldrop/templates/team_card.html` | Graphic design |
| `.env.example` | Env template (copy to `.env`) |
| `logs/fpldrop.log` | Success and error lines from each run |
| `.cursor/skills/fpl-team-graphic/` | Design skill for later graphic tweaks |

`.env`, `output/*.png`, and generated sidecars are gitignored. Do not commit tokens or generated team sheets.
