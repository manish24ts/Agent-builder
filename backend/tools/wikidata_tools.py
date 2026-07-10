"""
wikidata_tools.py — Structured factual lookups from Wikidata's knowledge graph.
--------------------------------------------------------------------------------
Implemented directly against Wikidata's public REST API (wbsearchentities +
wbgetentities). langchain_community's old WikidataQueryRun/WikidataAPIWrapper
integration was removed upstream, so this avoids that dependency entirely and
only needs `requests`, which the project already depends on.
"""

from __future__ import annotations

from typing import Optional

import requests
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
TIMEOUT = 15
MAX_RESULTS = 3


class WikidataToolInput(BaseModel):
    query: str = Field(..., description="Entity or topic to look up on Wikidata, e.g. 'Albert Einstein' or 'Python (programming language)'.")


def _fetch_entity_summary(entity_id: str) -> Optional[str]:
    """Fetch a short label/description/claims summary for one Wikidata entity ID."""
    resp = requests.get(
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "ids": entity_id,
            "languages": "en",
            "props": "labels|descriptions|claims",
            "format": "json",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    entity = resp.json().get("entities", {}).get(entity_id)
    if not entity:
        return None

    label = entity.get("labels", {}).get("en", {}).get("value", entity_id)
    description = entity.get("descriptions", {}).get("en", {}).get("value", "")

    lines = [f"{label}: {description}" if description else label]
    lines.append(f"Wikidata ID: {entity_id}")
    lines.append(f"URL: https://www.wikidata.org/wiki/{entity_id}")
    return "\n".join(lines)


def _run_wikidata(query: str) -> str:
    try:
        search_resp = requests.get(
            WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": MAX_RESULTS,
                "format": "json",
            },
            timeout=TIMEOUT,
        )
        search_resp.raise_for_status()
        hits = search_resp.json().get("search", [])
        if not hits:
            return f"No Wikidata entities found for '{query}'."

        summaries = []
        for hit in hits:
            summary = _fetch_entity_summary(hit["id"])
            if summary:
                summaries.append(summary)

        if not summaries:
            return f"No Wikidata entities found for '{query}'."

        return "\n\n".join(summaries)

    except requests.RequestException as exc:
        return f"Error: could not reach Wikidata ({exc})."
    except Exception as exc:  # noqa: BLE001
        return f"Unexpected error while querying Wikidata: {exc}"


wikidata_tool = StructuredTool.from_function(
    func=_run_wikidata,
    name="wikidata_lookup",
    description=(
        "Looks up structured factual information about an entity (person, place, "
        "organization, concept, etc.) from Wikidata's knowledge graph. Returns "
        "labels, short descriptions, and links for the best-matching entities."
    ),
    args_schema=WikidataToolInput,
    return_direct=False,
    handle_tool_error=True,
)
