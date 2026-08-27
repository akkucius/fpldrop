---
name: fpl-team-graphic
description: >-
  Designs and updates the FPL pitch graphic and X caption for Bruno Mars XI.
  Use when editing team_card.html, render.py, captions, kits, colors, formation
  layout, GW posts, or when the user asks to restyle the FPL team image.
---

# FPL team graphic design

Source of truth: [src/fpldrop/templates/team_card.html](../../src/fpldrop/templates/team_card.html).
Preview with `output/gw1.png` after a dry-run. Match the official FPL pitch look (kits, name plate, points, C/V), not player-headshot circles. Recap layout follows the 2022 GW scores post: name stack + points under each kit, Points/Transfers pills on the pitch.

## Visual system

- Card: 1080px wide, background `#37003c`
- Accent: `#00ff87` (FPL green) for brand label, GW badge, points pills, played bar
- Pitch: striped `#1f8f4a` / `#187e40`, faint 18-yard boxes
- Type: Outfit, white on purple; name plates `rgba(20, 8, 28, 0.88)`
- Kits: `shirt_{team_code}-66.webp` from FPL CDN; badge fallback `t{code}.png`
- Captain: gold `C` badge; vice: grey `V`
- Player stack: kit → name → GW points (captain already multiplied) → green bar if they played, muted bar if not
- Pitch pills: `{n} Points` (green border) and `{n} Transfers` (white border)
- Rows: GKP, DEF, MID, FWD (formation from starter counts), then Substitutes
- Header: team name, manager, formation, GW badge
- Footer: Value · Bank · gameweek name
- Do not put URLs on the graphic or in the caption (X bills URL posts higher)

## Caption

Keep this scores-recap shape (no link). Catchy line + reply CTA are generated in `TeamSnapshot.caption()`:

```
Here's my GW{n} Scores

📈 OR : {overall rank}
📉 GR : {gameweek rank}
📍 GW{n} : {points}
©️ Captain : {captain}
🎯 Target : 10k

{one-line verdict}

What's your score? Drop it below 👇

#FPL #FPLCommunity #EPL #GW{n}
```

Optional extra line only when true: `Chip: ...`. Do not add URLs. Do not use em dashes in the caption. Verdict is short and first-person (good week / okay / not a good GW) and may say who blanked.

## Change workflow

1. Edit the HTML/CSS template or caption builder
2. Preview from Git Bash: `.venv/Scripts/python.exe -m fpldrop preview`
3. Check the dotted block in the terminal / `output/gw{N}.preview.txt`, then open `output/gw{N}.png`
4. Do not post to X unless the user asks

## Constraints

- Per-player points come from `/event/{gw}/live/` (not bootstrap `event_points`, which is only the current GW)
- Pre-deadline fetch needs `FPL_ACCESS_TOKEN` (oidc `access_token` field, not `id_token`)
- After deadline, public picks work without a token
- Never commit `.env` or paste tokens into chat
