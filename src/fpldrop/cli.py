from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fpldrop.config import load_settings
from fpldrop.fpl import FplError, build_snapshot
from fpldrop.render import render_card
from fpldrop.twitter import TwitterError, post_image

LOG_PATH = Path("logs") / "fpldrop.log"


def _log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"{stamp}  {message}"
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        prog="fpldrop",
        description="Render your FPL team graphic and optionally post it to X.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    publish = sub.add_parser("publish", help="Fetch squad, render graphic, post to X")
    publish.add_argument(
        "--dry-run",
        action="store_true",
        help="Write PNG and print dotted preview; do not post",
    )
    preview = sub.add_parser(
        "preview",
        help="Dotted tweet + pitch preview, write PNG; do not post",
    )
    for extra in (publish, preview):
        extra.add_argument("--gw", type=int, default=None, help="Gameweek number (default: current/next)")
        extra.add_argument(
            "--manager-id",
            type=int,
            default=None,
            help="Override FPL_MANAGER_ID from .env",
        )
        extra.add_argument(
            "--output",
            type=Path,
            default=None,
            help="PNG path (default: output/gw{N}.png)",
        )
    preview.add_argument(
        "--text-only",
        action="store_true",
        help="Skip PNG render; print the dotted preview only",
    )

    args = parser.parse_args(argv)
    if args.command in {"publish", "preview"}:
        return _publish(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _publish(args: argparse.Namespace) -> int:
    settings = load_settings()
    manager_id = args.manager_id or settings.fpl_manager_id

    try:
        snapshot = build_snapshot(
            manager_id,
            gw=args.gw,
            refresh_token=settings.fpl_refresh_token,
            access_token=settings.fpl_access_token,
            oidc_client_id=settings.fpl_oidc_client_id,
            env_path=settings.env_path,
        )
    except FplError as exc:
        _log(f"ERROR FPL: {exc}")
        print(f"FPL error: {exc}", file=sys.stderr)
        return 1

    output = args.output or Path("output") / f"gw{snapshot.gw}.png"
    preview_only = args.command == "preview"
    dry_run = preview_only or getattr(args, "dry_run", False)
    text_only = getattr(args, "text_only", False)

    path = output
    if text_only:
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Text preview for GW{snapshot.gw} · {snapshot.team_name}")
    else:
        print(f"Rendering GW{snapshot.gw} graphic for {snapshot.team_name}...")
        try:
            path = render_card(snapshot, output)
        except Exception as exc:
            _log(f"ERROR render: {exc}")
            print(f"Render error: {exc}", file=sys.stderr)
            print(
                "If Chromium is missing, run: playwright install chromium",
                file=sys.stderr,
            )
            return 1

    caption = snapshot.caption()
    preview = snapshot.preview_block()
    json_path = _save_post_json(snapshot, path, caption, posted=False)
    preview_path = path.with_suffix(".preview.txt")
    preview_path.write_text(preview + "\n", encoding="utf-8")
    if not text_only:
        print(f"Saved {path.resolve()}")
    print(f"Saved {json_path.resolve()}")
    print(f"Saved {preview_path.resolve()}")
    print(preview)
    _log(f"Saved graphic {path}, {json_path}, and {preview_path}")

    if dry_run:
        _log("Preview/dry-run: not posting to X.")
        print("Preview only: not posting to X.")
        return 0

    try:
        tweet_id = post_image(settings, caption, path)
    except TwitterError as exc:
        _log(f"ERROR X: {exc}")
        print(f"X error: {exc}", file=sys.stderr)
        return 1

    _save_post_json(snapshot, path, caption, posted=True, tweet_id=tweet_id or None)
    if tweet_id:
        _log(f"Posted tweet_id={tweet_id}")
        print(f"Posted: https://x.com/i/web/status/{tweet_id}")
    else:
        _log("Posted to X (no tweet id returned).")
        print("Posted to X.")
    return 0


def _save_post_json(
    snapshot: TeamSnapshot,
    image_path: Path,
    caption: str,
    posted: bool,
    tweet_id: str | None = None,
) -> Path:
    json_path = image_path.with_suffix(".json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gw": snapshot.gw,
        "gw_name": snapshot.gw_name,
        "team_name": snapshot.team_name,
        "manager_name": snapshot.manager_name,
        "formation": snapshot.formation,
        "captain": snapshot.captain_name,
        "vice": snapshot.vice_name,
        "chip": snapshot.chip_label,
        "gw_points": snapshot.gw_points,
        "gw_rank": snapshot.gw_rank,
        "overall_rank": snapshot.overall_rank,
        "transfers": snapshot.transfers,
        "caption": caption,
        "image": str(image_path).replace("\\", "/"),
        "posted": posted,
        "tweet_id": tweet_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return json_path


if __name__ == "__main__":
    raise SystemExit(main())
