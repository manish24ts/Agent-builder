from __future__ import annotations

import os
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
CRICAPI_BASE = "https://api.cricapi.com/v1"
TIMEOUT = 15

VALID_OPERATIONS = {"live", "fixtures", "results"}

_SPORTSDB_SPORT_NAMES: Dict[str, str] = {
    "football": "Soccer",
    "basketball": "Basketball",
    "american_football": "American Football",
    "tennis": "Tennis",
    "baseball": "Baseball",
    "ice_hockey": "Ice Hockey",
}
VALID_SPORTS = {"cricket", *_SPORTSDB_SPORT_NAMES.keys()}



class SportsToolInput(BaseModel):
    """Type-level schema only. All value/enum validation happens in _run_sports_tool."""

    sport: str = Field(
        ..., description="Sport to query: cricket, football, basketball, american_football, tennis, baseball, ice_hockey."
    )
    operation: str = Field(
        "live", description="'live' (in-progress), 'fixtures' (upcoming), or 'results' (recently finished)."
    )
    date: Optional[str] = Field(
        None, description="Date as YYYY-MM-DD. Defaults to today. Used for 'fixtures'/'results'; ignored for cricket."
    )
    league: Optional[str] = Field(None, description="Filter by league/competition name. Optional, non-cricket only.")
    team: Optional[str] = Field(None, description="Filter by team name (partial, case-insensitive). Optional.")



def _get(url: str, params: Optional[dict] = None) -> Any:
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise RuntimeError(f"Network error contacting {url}: {exc}") from exc

    if not response.ok:
        raise RuntimeError(f"Upstream API error {response.status_code} for {url}: {response.text[:200]}")

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON response from {url}: {exc}") from exc


def _matches_filter(text: Optional[str], needle: Optional[str]) -> bool:
    if not needle:
        return True
    return bool(text) and needle.lower() in text.lower()


# ===================================================================================
# TheSportsDB branch (football, basketball, NFL, tennis, baseball, ice hockey)
# ===================================================================================

def _sportsdb_events_for_date(sport_name: str, day: str) -> List[dict]:
    data = _get(f"{SPORTSDB_BASE}/eventsday.php", params={"d": day, "s": sport_name})
    if not isinstance(data, dict):
        return []
    return data.get("events") or []


def _classify_event(event: dict) -> str:
    """Return 'live', 'finished', or 'upcoming' based on TheSportsDB's status/score fields."""
    status = (event.get("strStatus") or "").strip()
    home_score, away_score = event.get("intHomeScore"), event.get("intAwayScore")

    if status in {"Match Finished", "FT", "AOT", "Finished"}:
        return "finished"
    if status in {"", "Not Started", "NS"} and home_score is None and away_score is None:
        return "upcoming"
    if status in {"1H", "2H", "HT", "ET", "Live", "In Progress"} or (
        home_score is not None and status not in {"Match Finished", "FT"}
    ):
        return "live"
    return "upcoming"


def _format_sportsdb_event(event: dict) -> Dict[str, Any]:
    return {
        "league": event.get("strLeague"),
        "home_team": event.get("strHomeTeam"),
        "away_team": event.get("strAwayTeam"),
        "home_score": event.get("intHomeScore"),
        "away_score": event.get("intAwayScore"),
        "status": event.get("strStatus") or "Scheduled",
        "date": event.get("dateEvent"),
        "time": event.get("strTime"),
        "venue": event.get("strVenue"),
    }


def _query_sportsdb(sport: str, operation: str, day: str, league: Optional[str], team: Optional[str]) -> Dict[str, Any]:
    sport_name = _SPORTSDB_SPORT_NAMES[sport]
    events = _sportsdb_events_for_date(sport_name, day)

    bucket = {"live": "live", "fixtures": "upcoming", "results": "finished"}[operation]
    filtered = [
        e
        for e in events
        if isinstance(e, dict)
        and _classify_event(e) == bucket
        and _matches_filter(e.get("strLeague"), league)
        and (_matches_filter(e.get("strHomeTeam"), team) or _matches_filter(e.get("strAwayTeam"), team))
    ]

    return {
        "sport": sport,
        "operation": operation,
        "date": day,
        "match_count": len(filtered),
        "matches": [_format_sportsdb_event(e) for e in filtered],
        "note": "TheSportsDB free tier approximates 'live' via same-day status fields; may lag slightly for fast-changing state.",
    }


# ===================================================================================
# CricAPI branch (cricket)
# ===================================================================================

def _cricapi_key() -> str:
    key = os.environ.get("CRICAPI_KEY")
    if not key:
        raise RuntimeError(
            "CRICAPI_KEY is not set. Sign up for a free key at https://cricapi.com and add "
            "CRICAPI_KEY=your_key to backend/.env to enable cricket scores."
        )
    return key


def _format_cricapi_match(match: dict) -> Dict[str, Any]:
    return {
        "match_name": match.get("name"),
        "teams": match.get("teams"),
        "status": match.get("status"),
        "match_type": match.get("matchType"),
        "venue": match.get("venue"),
        "date": match.get("date"),
        "score": match.get("score"),  # list of {inning, r, w, o}
    }


def _classify_cricapi_match(match: dict) -> str:
    if match.get("matchEnded"):
        return "finished"
    if match.get("matchStarted"):
        return "live"
    return "upcoming"


def _query_cricapi(operation: str, team: Optional[str]) -> Dict[str, Any]:
    key = _cricapi_key()
    data = _get(f"{CRICAPI_BASE}/currentMatches", params={"apikey": key, "offset": 0})

    if not isinstance(data, dict) or data.get("status") != "success":
        status = data.get("status") if isinstance(data, dict) else "unknown"
        message = data.get("message", "unknown error") if isinstance(data, dict) else "malformed response"
        raise RuntimeError(f"CricAPI error: {status} — {message}")

    matches = data.get("data") or []
    bucket = {"live": "live", "fixtures": "upcoming", "results": "finished"}[operation]

    filtered = [
        m
        for m in matches
        if isinstance(m, dict)
        and _classify_cricapi_match(m) == bucket
        and _matches_filter(", ".join(m.get("teams") or []), team)
    ]

    return {
        "sport": "cricket",
        "operation": operation,
        "match_count": len(filtered),
        "matches": [_format_cricapi_match(m) for m in filtered],
        "note": "CricAPI's currentMatches endpoint covers live, recently finished, and near-term matches (not a full future schedule).",
    }



def _validate_inputs(sport: str, operation: str, date: Optional[str]) -> None:
    """Raise RuntimeError (always caught by the caller) for any invalid enum or format."""
    if sport not in VALID_SPORTS:
        raise RuntimeError(f"Unsupported sport '{sport}'. Valid options: {sorted(VALID_SPORTS)}.")
    if operation not in VALID_OPERATIONS:
        raise RuntimeError(f"Unsupported operation '{operation}'. Valid options: {sorted(VALID_OPERATIONS)}.")
    if date is not None:
        try:
            date_cls.fromisoformat(date)
        except ValueError as exc:
            raise RuntimeError(f"'date' must be in YYYY-MM-DD format, got '{date}'.") from exc



def _run_sports_tool(
    sport: str,
    operation: str = "live",
    date: Optional[str] = None,
    league: Optional[str] = None,
    team: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch live scores, upcoming fixtures, or recent results for a given sport.

    Guaranteed never to raise: every failure mode — invalid sport/operation, missing
    API key, network errors, malformed upstream JSON, unexpected exceptions — is
    caught here and returned as {"success": False, "error": "..."}, so a bad or
    unexpected LLM tool call can never crash the agent process.
    """
    try:
        sport_norm = (sport or "").strip().lower()
        operation_norm = (operation or "live").strip().lower()
        _validate_inputs(sport_norm, operation_norm, date)

        day = date or date_cls.today().isoformat()

        if sport_norm == "cricket":
            result = _query_cricapi(operation_norm, team)
        else:
            result = _query_sportsdb(sport_norm, operation_norm, day, league, team)

        return {"success": True, **result}

    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 — absolute last line of defense
        return {"success": False, "error": f"Unexpected error fetching '{sport}' {operation}: {exc}"}


sports_tool = StructuredTool.from_function(
    func=_run_sports_tool,
    name="sports_tool",
    description=(
        "Gets live scores, upcoming fixtures, or recent results for sports"
        "sport: 'cricket' (via CricAPI, needs free CRICAPI_KEY in backend/.env), 'football', 'basketball', "
        "'american_football', 'tennis', 'baseball', 'ice_hockey'. "
        "operation: 'live' (in-progress matches), 'fixtures' (upcoming), 'results' (recently finished). "
        "Optional 'date' (YYYY-MM-DD, defaults to today, non-cricket only), 'league', and 'team' filters. "
        "Always check 'success' in the response before using the data — on failure it returns a "
        "descriptive 'error' field instead of crashing."
    ),
    args_schema=SportsToolInput,
    return_direct=False,
    handle_tool_error=True,
)