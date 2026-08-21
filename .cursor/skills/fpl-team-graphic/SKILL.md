---
name: fpl-team-graphic
description: >-
  Designs and updates the FPL pitch graphic and X caption for Bruno Mars XI.
  Use when editing team_card.html, render.py, captions, kits, colors, formation
  layout, GW posts, or when the user asks to restyle the FPL team image.
---

# FPL team graphic design

Source of truth: [src/fpl_x/templates/team_card.html](../../src/fpl_x/templates/team_card.html).
Preview with `output/gw1.png` after a dry-run. Match the official FPL pitch screenshot look (kits, name plate, fixture, C/V), not player-headshot circles.

## Visual system

- Card: 1080px wide, background `#37003c`
- Accent: `#00ff87` (FPL green) for brand label and GW badge
- Pitch: striped `#1f8f4a` / `#187e40`, faint 18-yard boxes
- Type: Outfit, white on purple; name plates `rgba(20, 8, 28, 0.88)`
- Kits: `shirt_{team_code}-66.webp` from FPL CDN; badge fallback `t{code}.png`
- Captain: gold `C` badge; vice: grey `V`
- Rows: GKP, DEF, MID, FWD (formation from starter counts), then Substitutes
- Header: team name, manager, formation, GW badge
- Footer: Value · Bank · gameweek name
- Do not put URLs on the graphic or in the caption (X bills URL posts higher)

## Caption

Keep this shape (no link):

```
Here's my GW{n} Team

(C) {captain}
🎯 10k
Formation {formation}

All the best guys! Let's go.

#FPL #FPLCommunity
```

Optional extra lines only when true: `Chip: …`, `Transfers: n`. Defined in `TeamSnapshot.caption()` in [src/fpl_x/fpl.py](../../src/fpl_x/fpl.py).

## Change workflow

1. Edit the HTML/CSS template or caption builder
2. Dry-run from Git Bash: `.venv/Scripts/python.exe -m fpl_x publish --dry-run`
3. Open `output/gw{N}.png` and check kits, C/V, formation, truncation
4. Do not post to X unless the user asks

## Constraints

- Pre-deadline fetch needs `FPL_ACCESS_TOKEN` (oidc `access_token` field, not `id_token`)
- After deadline, public picks work without a token
- Never commit `.env` or paste tokens into chat
