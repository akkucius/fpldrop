from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(".env")
DEFAULT_MANAGER_ID = 4703066
DEFAULT_OIDC_CLIENT_ID = "bfcbaf69-aade-4c1b-8f00-c1cb8a193030"
OIDC_TOKEN_URL = "https://account.premierleague.com/as/token"


@dataclass
class Settings:
    fpl_manager_id: int
    fpl_refresh_token: str | None
    fpl_access_token: str | None
    fpl_oidc_client_id: str
    env_path: Path
    x_api_key: str | None
    x_api_secret: str | None
    x_access_token: str | None
    x_access_token_secret: str | None

    def require_x(self) -> tuple[str, str, str, str]:
        keys = (
            self.x_api_key,
            self.x_api_secret,
            self.x_access_token,
            self.x_access_token_secret,
        )
        if not all(keys):
            raise SystemExit(
                "X API keys are missing. Copy .env.example to .env and fill "
                "X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, and "
                "X_ACCESS_TOKEN_SECRET. Dry-run does not need these."
            )
        return keys  # type: ignore[return-value]


def load_settings() -> Settings:
    load_dotenv(ENV_PATH if ENV_PATH.exists() else None)
    raw_id = os.getenv("FPL_MANAGER_ID", "").strip()
    return Settings(
        fpl_manager_id=int(raw_id) if raw_id else DEFAULT_MANAGER_ID,
        fpl_refresh_token=parse_refresh_token(_optional("FPL_REFRESH_TOKEN")),
        fpl_access_token=_optional("FPL_ACCESS_TOKEN"),
        fpl_oidc_client_id=_optional("FPL_OIDC_CLIENT_ID") or DEFAULT_OIDC_CLIENT_ID,
        env_path=ENV_PATH,
        x_api_key=_optional("X_API_KEY"),
        x_api_secret=_optional("X_API_SECRET"),
        x_access_token=_optional("X_ACCESS_TOKEN"),
        x_access_token_secret=_optional("X_ACCESS_TOKEN_SECRET"),
    )


def parse_refresh_token(pasted: str | None) -> str | None:
    if not pasted:
        return None
    trimmed = pasted.strip().strip("'\"")
    try:
        parsed = json.loads(trimmed)
        if isinstance(parsed, dict) and isinstance(parsed.get("refresh_token"), str):
            return parsed["refresh_token"]
    except json.JSONDecodeError:
        pass
    return trimmed or None


def persist_refresh_token(token: str, env_path: Path = ENV_PATH) -> None:
    line = f"FPL_REFRESH_TOKEN={token}"
    if not env_path.exists():
        env_path.write_text(line + "\n", encoding="utf-8")
        return
    existing = env_path.read_text(encoding="utf-8")
    if re.search(r"^FPL_REFRESH_TOKEN=", existing, flags=re.MULTILINE):
        updated = re.sub(
            r"^FPL_REFRESH_TOKEN=.*$",
            line,
            existing,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        sep = "" if existing.endswith("\n") or existing == "" else "\n"
        updated = f"{existing}{sep}{line}\n"
    env_path.write_text(updated, encoding="utf-8")


def _optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None
