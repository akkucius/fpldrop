from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from fpldrop.config import (
    DEFAULT_OIDC_CLIENT_ID,
    OIDC_TOKEN_URL,
    persist_refresh_token,
)

FPL_BASE = "https://fantasy.premierleague.com/api"
SHIRT_BASE = "https://fantasy.premierleague.com/dist/img/shirts/standard"
BADGE_BASE = "https://resources.premierleague.com/premierleague/badges/70"
SHIRT_VARIANT = "66"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

ELEMENT_TYPE_ROWS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
CHIP_LABELS = {
    "wildcard": "Wildcard",
    "freehit": "Free Hit",
    "bboost": "Bench Boost",
    "3xc": "Triple Captain",
    "manager": "Assistant Manager",
}


@dataclass
class PlayerCard:
    element_id: int
    web_name: str
    team_short: str
    shirt_url: str
    badge_url: str
    element_type: int
    pick_position: int
    is_captain: bool
    is_vice: bool
    is_bench: bool
    multiplier: int
    fixture: str
    price: str
    event_points: int
    total_points: int
    minutes: int = 0

    @property
    def row_key(self) -> str:
        return ELEMENT_TYPE_ROWS.get(self.element_type, "MID")

    @property
    def display_points(self) -> int:
        if self.multiplier > 1:
            return self.event_points * self.multiplier
        return self.event_points

    @property
    def played(self) -> bool:
        return self.minutes > 0


@dataclass
class TeamSnapshot:
    manager_id: int
    team_name: str
    manager_name: str
    gw: int
    gw_name: str
    formation: str
    overall_rank: int | None
    overall_points: int
    gw_points: int | None
    gw_rank: int | None
    team_value: str
    bank: str
    transfers: int
    transfer_cost: int
    chip: str | None
    chip_label: str | None
    points_on_bench: int | None
    captain_name: str
    vice_name: str
    starters: dict[str, list[PlayerCard]] = field(default_factory=dict)
    bench: list[PlayerCard] = field(default_factory=list)

    def caption(self) -> str:
        lines = [f"Here's my GW{self.gw} Scores", ""]
        if self.overall_rank is not None:
            lines.append(f"📈 OR : {self.overall_rank:,}")
        if self.gw_rank is not None:
            lines.append(f"📉 GR : {self.gw_rank:,}")
        if self.gw_points is not None:
            lines.append(f"📍 GW{self.gw} : {self.gw_points}")
        lines.append(f"©️ Captain : {self.captain_name}")
        lines.append("🎯 Target : 10k")
        if self.chip_label:
            lines.append(f"Chip: {self.chip_label}")
        lines.extend(["", self._catchy_blurb(), "", f"#FPL #FPLCommunity #EPL #GW{self.gw}"])
        return "\n".join(lines)

    def _catchy_blurb(self) -> str:
        cta = "What's your score? Drop it below 👇"
        quiet = self._quiet_line()
        pts = self.gw_points

        if pts is None:
            return f"Team is in. Let's see how this one goes.\n\n{cta}"

        if pts >= 80:
            line = f"What a week. {self.captain_name} was on one."
        elif pts >= 65:
            line = f"Happy with {pts}. Still chasing that 10k."
        elif pts >= 50:
            line = "Okay GW. Nothing special."
        elif self.gw == 1:
            line = "Not a good start in FPL."
        else:
            line = "Not a good GW."

        if quiet and pts < 65:
            line = f"{line} {quiet}"
        if pts < 50:
            line = f"{line} Moving on."

        return f"{line}\n\n{cta}"

    def _quiet_line(self) -> str:
        names = self._quiet_starters()
        if not names:
            return ""
        if len(names) == 1:
            return f"{names[0]} blanked."
        return f"{names[0]} and {names[1]} blanked."

    def _quiet_starters(self) -> list[str]:
        starters = [player for row in self.starters.values() for player in row]
        quiet = [
            player
            for player in starters
            if player.display_points <= 1 and not player.is_captain
        ]
        quiet.sort(key=lambda player: (player.display_points, player.pick_position))
        return [player.web_name for player in quiet[:2]]

    def preview_block(self) -> str:
        width = 46
        rule = "·" * width
        title = " TWEET PREVIEW "
        pitch = " PITCH PREVIEW "
        lines = [
            rule,
            f"{title:·^{width}}",
            rule,
            self.caption(),
            rule,
            f"{pitch:·^{width}}",
            rule,
        ]
        pills = []
        if self.gw_points is not None:
            pills.append(f"{self.gw_points} Points")
        pills.append(f"{self.transfers} Transfers")
        lines.append("  " + "     ".join(pills))
        lines.append("")
        for row_key in ("GKP", "DEF", "MID", "FWD"):
            row = self.starters.get(row_key) or []
            if not row:
                continue
            lines.append("  " + "   ".join(_preview_player(player) for player in row))
        if self.bench:
            lines.append("")
            lines.append("  Substitutes")
            lines.append("  " + "   ".join(_preview_player(player) for player in self.bench))
        lines.extend(
            [
                rule,
                f"  {self.team_name} · {self.formation} · GW{self.gw}",
                rule,
            ]
        )
        return "\n".join(lines)


def _preview_player(player: PlayerCard) -> str:
    mark = "(C) " if player.is_captain else "(V) " if player.is_vice else ""
    return f"{mark}{player.web_name} {player.display_points}"


class FplError(RuntimeError):
    pass


class FplClient:
    def __init__(
        self,
        timeout: float = 30.0,
        refresh_token: str | None = None,
        access_token: str | None = None,
        oidc_client_id: str = DEFAULT_OIDC_CLIENT_ID,
        env_path: Path | None = None,
    ) -> None:
        self._http = httpx.Client(
            headers=HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )
        self._refresh_token = refresh_token
        self._oidc_client_id = oidc_client_id
        self._env_path = env_path
        self._access_token = access_token

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> FplClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def bootstrap(self) -> dict:
        return self._get("/bootstrap-static/")

    def entry(self, manager_id: int) -> dict:
        return self._get(f"/entry/{manager_id}/")

    def picks(self, manager_id: int, gw: int) -> dict:
        return self._get(f"/entry/{manager_id}/event/{gw}/picks/")

    def fixtures(self, gw: int) -> list[dict]:
        data = self._get("/fixtures/", params={"event": gw})
        if not isinstance(data, list):
            raise FplError("Unexpected fixtures payload")
        return data

    def live(self, gw: int) -> dict:
        data = self._get(f"/event/{gw}/live/")
        if not isinstance(data, dict):
            raise FplError("Unexpected live points payload")
        return data

    def my_team(self, manager_id: int) -> dict:
        self._ensure_access_token()
        return self._get(f"/my-team/{manager_id}/", authenticated=True)

    def _ensure_access_token(self) -> None:
        if self._access_token:
            return
        if not self._refresh_token:
            raise FplError(
                "Picks are not public yet (before the gameweek deadline). "
                "In DevTools, copy the access_token field from the oidc.user "
                "row (not id_token, not refresh_token) into FPL_ACCESS_TOKEN "
                "in .env. That token works until it expires."
            )
        self._assert_looks_like_refresh_token(self._refresh_token)
        body = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._oidc_client_id,
        }
        try:
            response = self._http.post(
                OIDC_TOKEN_URL,
                data=body,
                headers={
                    **HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            payload = response.json()
        except httpx.HTTPError as exc:
            raise FplError(f"Could not reach FPL login: {exc}") from exc
        except ValueError as exc:
            raise FplError("FPL login returned a non-JSON response") from exc

        if response.status_code >= 400 or not payload.get("access_token"):
            detail = payload.get("error_description") or payload.get("error") or response.text
            raise FplError(
                f"FPL token refresh failed ({response.status_code}): {detail}. "
                "Copy a fresh refresh_token from the FPL site localStorage."
            )

        self._access_token = payload["access_token"]
        rotated = payload.get("refresh_token")
        if rotated and rotated != self._refresh_token:
            self._refresh_token = rotated
            if self._env_path:
                persist_refresh_token(rotated, self._env_path)

    def _get(
        self,
        path: str,
        params: dict | None = None,
        authenticated: bool = False,
    ) -> dict | list:
        url = f"{FPL_BASE}{path}"
        headers = dict(HEADERS)
        if authenticated:
            headers["X-API-Authorization"] = f"Bearer {self._access_token}"
        try:
            response = self._http.get(url, params=params, headers=headers)
            if authenticated and response.status_code in {401, 403}:
                self._access_token = None
                self._ensure_access_token()
                headers["X-API-Authorization"] = f"Bearer {self._access_token}"
                response = self._http.get(url, params=params, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                raise FplError(
                    f"FPL returned 404 for {path}. The gameweek may not be "
                    "available yet (picks are public after the deadline)."
                ) from exc
            raise FplError(f"FPL request failed ({status}) for {path}") from exc
        except httpx.HTTPError as exc:
            raise FplError(f"Could not reach FPL API: {exc}") from exc
        return response.json()

    @staticmethod
    def _assert_looks_like_refresh_token(token: str) -> None:
        if token.count(".") < 2:
            return
        payload = token.split(".")[1]
        pad = "=" * (-len(payload) % 4)
        try:
            claims = json.loads(base64.urlsafe_b64decode(payload + pad))
        except (ValueError, json.JSONDecodeError):
            return
        if "aud" in claims or claims.get("token_use") in {"id", "access"}:
            raise FplError(
                "FPL_REFRESH_TOKEN looks like an id_token or access_token, "
                "not refresh_token. In DevTools, open the oidc.user row, "
                "copy the refresh_token field only, and replace the value in .env."
            )


def resolve_gameweek(bootstrap: dict, requested: int | None) -> int:
    if requested is not None:
        return requested
    events = bootstrap.get("events") or []
    current = next((event for event in events if event.get("is_current")), None)
    if current:
        return int(current["id"])
    nxt = next((event for event in events if event.get("is_next")), None)
    if nxt:
        return int(nxt["id"])
    finished = [event for event in events if event.get("finished")]
    if finished:
        return int(finished[-1]["id"])
    raise FplError("Could not determine the current FPL gameweek.")


def build_snapshot(
    manager_id: int,
    gw: int | None = None,
    client: FplClient | None = None,
    refresh_token: str | None = None,
    access_token: str | None = None,
    oidc_client_id: str = DEFAULT_OIDC_CLIENT_ID,
    env_path: Path | None = None,
) -> TeamSnapshot:
    own_client = client is None
    client = client or FplClient(
        refresh_token=refresh_token,
        access_token=access_token,
        oidc_client_id=oidc_client_id,
        env_path=env_path,
    )
    try:
        bootstrap = client.bootstrap()
        event_id = resolve_gameweek(bootstrap, gw)
        entry = client.entry(manager_id)
        fixtures = client.fixtures(event_id)
        picks_payload = _load_picks(client, manager_id, event_id, entry)
        live_stats = _live_stats(client, event_id)
        return assemble_snapshot(
            manager_id=manager_id,
            gw=event_id,
            bootstrap=bootstrap,
            entry=entry,
            picks_payload=picks_payload,
            fixtures=fixtures,
            live_stats=live_stats,
        )
    finally:
        if own_client:
            client.close()


def _load_picks(client: FplClient, manager_id: int, gw: int, entry: dict) -> dict:
    try:
        payload = client.picks(manager_id, gw)
        if payload.get("picks"):
            return payload
    except FplError:
        pass
    my_team = client.my_team(manager_id)
    return _my_team_as_picks(my_team, entry)


def _live_stats(client: FplClient, gw: int) -> dict[int, dict]:
    try:
        payload = client.live(gw)
    except FplError:
        return {}
    stats: dict[int, dict] = {}
    for item in payload.get("elements") or []:
        try:
            stats[int(item["id"])] = item.get("stats") or {}
        except (KeyError, TypeError, ValueError):
            continue
    return stats


def _my_team_as_picks(my_team: dict, entry: dict) -> dict:
    active = None
    for chip in my_team.get("chips") or []:
        status = str(chip.get("status_for_entry") or "").lower()
        if status == "active":
            active = chip.get("name")
            break
    transfers = my_team.get("transfers") or {}
    return {
        "active_chip": active,
        "picks": my_team.get("picks") or [],
        "entry_history": {
            "event_transfers": transfers.get("made") or 0,
            "event_transfers_cost": 0,
            "bank": transfers.get("bank"),
            "value": transfers.get("value"),
            "total_points": entry.get("summary_overall_points"),
            "overall_rank": entry.get("summary_overall_rank"),
            "points": entry.get("summary_event_points"),
            "rank": entry.get("summary_event_rank"),
        },
    }


def assemble_snapshot(
    manager_id: int,
    gw: int,
    bootstrap: dict,
    entry: dict,
    picks_payload: dict,
    fixtures: list[dict],
    live_stats: dict[int, dict] | None = None,
) -> TeamSnapshot:
    elements = {item["id"]: item for item in bootstrap.get("elements") or []}
    teams = {item["id"]: item for item in bootstrap.get("teams") or []}
    events = {item["id"]: item for item in bootstrap.get("events") or []}
    event = events.get(gw, {})
    history = picks_payload.get("entry_history") or {}
    picks = picks_payload.get("picks") or []
    if not picks:
        raise FplError("No picks returned for this gameweek.")

    players: list[PlayerCard] = []
    for pick in picks:
        element = elements.get(pick["element"])
        if not element:
            continue
        team = teams.get(element["team"], {})
        is_gk = int(element.get("element_type") or 0) == 1
        stats = (live_stats or {}).get(int(element["id"])) or {}
        if stats:
            event_points = int(stats.get("total_points") or 0)
            minutes = int(stats.get("minutes") or 0)
        else:
            event_points = int(element.get("event_points") or 0)
            minutes = 0
        players.append(
            PlayerCard(
                element_id=element["id"],
                web_name=element.get("web_name") or element.get("second_name") or "?",
                team_short=team.get("short_name") or "?",
                shirt_url=_shirt_url(int(team.get("code") or 0), is_gk),
                badge_url=_badge_url(int(team.get("code") or 0)),
                element_type=int(element.get("element_type") or 0),
                pick_position=int(pick.get("position") or 0),
                is_captain=bool(pick.get("is_captain")),
                is_vice=bool(pick.get("is_vice_captain")),
                is_bench=int(pick.get("position") or 0) >= 12,
                multiplier=int(pick.get("multiplier") or 0),
                fixture=_fixture_label(int(element["team"]), fixtures, teams),
                price=_money(int(element.get("now_cost") or 0)),
                event_points=event_points,
                total_points=int(element.get("total_points") or 0),
                minutes=minutes,
            )
        )

    starters = [player for player in players if not player.is_bench]
    bench = [player for player in players if player.is_bench]
    rows: dict[str, list[PlayerCard]] = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
    for player in starters:
        rows.setdefault(player.row_key, []).append(player)

    formation = f"{len(rows['DEF'])}-{len(rows['MID'])}-{len(rows['FWD'])}"
    captain = next((player for player in players if player.is_captain), None)
    vice = next((player for player in players if player.is_vice), None)
    chip = picks_payload.get("active_chip")
    chip_label = (
        CHIP_LABELS.get(str(chip).lower(), str(chip).replace("_", " ").title())
        if chip
        else None
    )

    manager_name = " ".join(
        part
        for part in (
            entry.get("player_first_name") or "",
            entry.get("player_last_name") or "",
        )
        if part
    ).strip() or "Manager"

    return TeamSnapshot(
        manager_id=manager_id,
        team_name=entry.get("name") or "FPL Team",
        manager_name=manager_name,
        gw=gw,
        gw_name=event.get("name") or f"Gameweek {gw}",
        formation=formation,
        overall_rank=_optional_int(
            history.get("overall_rank") or entry.get("summary_overall_rank")
        ),
        overall_points=int(
            history.get("total_points") or entry.get("summary_overall_points") or 0
        ),
        gw_points=_optional_int(
            history.get("points")
            if "points" in history
            else entry.get("summary_event_points")
        ),
        gw_rank=_optional_int(history.get("rank") or entry.get("summary_event_rank")),
        team_value=_money(
            int(history.get("value") or entry.get("last_deadline_value") or 0)
        ),
        bank=_money(int(history.get("bank") or entry.get("last_deadline_bank") or 0)),
        transfers=int(history.get("event_transfers") or 0),
        transfer_cost=int(history.get("event_transfers_cost") or 0),
        chip=chip,
        chip_label=chip_label,
        points_on_bench=_optional_int(history.get("points_on_bench")),
        captain_name=captain.web_name if captain else "-",
        vice_name=vice.web_name if vice else "-",
        starters=rows,
        bench=bench,
    )


def _shirt_url(team_code: int, is_gk: bool) -> str:
    del is_gk  # FPL currently ships one kit asset per club code
    return f"{SHIRT_BASE}/shirt_{team_code}-{SHIRT_VARIANT}.webp"


def _badge_url(team_code: int) -> str:
    return f"{BADGE_BASE}/t{team_code}.png"


def _fixture_label(team_id: int, fixtures: list[dict], teams: dict) -> str:
    labels: list[str] = []
    for fixture in fixtures:
        if fixture.get("team_h") == team_id:
            opp = teams.get(fixture.get("team_a"), {})
            labels.append(f"{opp.get('short_name', '?')} (H)")
        elif fixture.get("team_a") == team_id:
            opp = teams.get(fixture.get("team_h"), {})
            labels.append(f"{opp.get('short_name', '?')} (A)")
    return ", ".join(labels) if labels else "-"


def _money(tenths: int) -> str:
    return f"£{tenths / 10:.1f}m"


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
