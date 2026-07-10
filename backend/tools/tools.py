
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


# ===================================================================================
# Registry data model
# ===================================================================================

@dataclass
class ToolEntry:
    """Metadata + lazy loader for one registerable tool."""
    name: str
    category: str
    description: str
    requires_key: Optional[str]  # env var name if an API key is needed, else None
    loader: Callable[[], BaseTool]
    _instance: Optional[BaseTool] = field(default=None, repr=False)
    _load_error: Optional[str] = field(default=None, repr=False)

    def get(self) -> BaseTool:
        """Load (once) and return the underlying tool instance. Raises if unavailable."""
        if self._instance is not None:
            return self._instance
        if self._load_error is not None:
            raise RuntimeError(self._load_error)
        try:
            self._instance = self.loader()
            return self._instance
        except Exception as exc:  # noqa: BLE001
            self._load_error = f"Tool '{self.name}' failed to load: {exc}"
            logger.warning(self._load_error)
            raise RuntimeError(self._load_error) from exc

    @property
    def available(self) -> bool:
        """Check loadability without raising — used for UI listing."""
        try:
            self.get()
            return True
        except RuntimeError:
            return False


# ===================================================================================
# Custom tool loaders
# ===================================================================================

def _load_math_tool() -> BaseTool:
    from backend.tools.math_tools import math_tool
    return math_tool


def _load_github_tool() -> BaseTool:
    from backend.tools.github_tools import github_tool
    return github_tool


def _load_chart_tool() -> BaseTool:
    from backend.tools.chart_tools import chart_tool
    return chart_tool


def _load_sports_tool() -> BaseTool:
    from backend.tools.sports_tools import sports_tool
    return sports_tool


def _load_stock_tool() -> BaseTool:
    from backend.tools.stocks_tools import stock_tool
    return stock_tool


# ===================================================================================
# Built-in LangChain tool loaders
# ===================================================================================

def _load_duckduckgo_search() -> BaseTool:
    """pip install duckduckgo-search"""
    from langchain_community.tools import DuckDuckGoSearchRun
    return DuckDuckGoSearchRun()


def _load_wikipedia() -> BaseTool:
    """pip install wikipedia"""
    from langchain_community.tools import WikipediaQueryRun
    from langchain_community.utilities import WikipediaAPIWrapper
    return WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=2000))


def _load_arxiv() -> BaseTool:
    """pip install arxiv"""
    from langchain_community.tools import ArxivQueryRun
    from langchain_community.utilities import ArxivAPIWrapper
    return ArxivQueryRun(api_wrapper=ArxivAPIWrapper(top_k_results=3, doc_content_chars_max=2000))


def _load_pubmed() -> BaseTool:
    from langchain_community.tools import PubmedQueryRun
    return PubmedQueryRun()


def _load_youtube_search() -> BaseTool:
    """pip install youtube_search"""
    from langchain_community.tools import YouTubeSearchTool
    return YouTubeSearchTool()


def _load_python_repl() -> BaseTool:
    """
    pip install langchain-experimental
    CAUTION: executes arbitrary Python. Only enable for trusted agent configurations.
    """
    from langchain_experimental.tools.python.tool import PythonAstREPLTool
    return PythonAstREPLTool()


def _load_wikidata() -> BaseTool:
    """Self-contained implementation — see backend/tools/wikidata_tools.py.
    (langchain_community's WikidataQueryRun/WikidataAPIWrapper integration was
    removed upstream, so we no longer depend on it.)"""
    from backend.tools.wikidata_tools import wikidata_tool
    return wikidata_tool


def _load_requests_get() -> BaseTool:
    """CAUTION: SSRF surface — arbitrary outbound HTTP GET."""
    from langchain_community.tools.requests.tool import RequestsGetTool
    from langchain_community.utilities.requests import TextRequestsWrapper
    return RequestsGetTool(requests_wrapper=TextRequestsWrapper(headers={}), allow_dangerous_requests=True)


# ===================================================================================
# Registry
# ===================================================================================

TOOL_REGISTRY: Dict[str, ToolEntry] = {
    # ---- Custom tools ----
    "math_tool": ToolEntry(
        name="math_tool", category="custom", requires_key=None,
        description="Solves basic to advanced math: arithmetic, algebra, calculus, linear algebra, and statistics.",
        loader=_load_math_tool,
    ),
    "github_tool": ToolEntry(
        name="github_tool", category="custom", requires_key=None,
        description="Analyzes public GitHub repositories: architecture, dependencies, API routes, security scan, and code statistics.",
        loader=_load_github_tool,
    ),
    "chart_tool": ToolEntry(
        name="chart_tool", category="custom", requires_key=None,
        description="Renders charts (line, bar, scatter, pie, histogram, box, violin, heatmap, correlation matrix) from inline data as a base64 PNG.",
        loader=_load_chart_tool,
    ),
    "sports_tool": ToolEntry(
        name="sports_tool", category="custom", requires_key="CRICAPI_KEY (cricket only)",
        description="Live scores, fixtures, and results for cricket, football, basketball, NFL, tennis, baseball, and ice hockey.",
        loader=_load_sports_tool,
    ),
    "stock_tool": ToolEntry(
        name="stock_tool", category="custom", requires_key=None,
        description="Indian stock market (NSE/BSE) price quotes and historical OHLC data.",
        loader=_load_stock_tool,
    ),

    # ---- Built-in LangChain tools ----
    "duckduckgo_search": ToolEntry(
        name="duckduckgo_search", category="builtin", requires_key=None,
        description="General-purpose web search.",
        loader=_load_duckduckgo_search,
    ),
    "wikipedia": ToolEntry(
        name="wikipedia", category="builtin", requires_key=None,
        description="Looks up summaries and facts from Wikipedia.",
        loader=_load_wikipedia,
    ),
    "arxiv": ToolEntry(
        name="arxiv", category="builtin", requires_key=None,
        description="Searches academic papers on arXiv.",
        loader=_load_arxiv,
    ),
    "pubmed": ToolEntry(
        name="pubmed", category="builtin", requires_key=None,
        description="Searches biomedical and life-sciences literature on PubMed.",
        loader=_load_pubmed,
    ),
    "youtube_search": ToolEntry(
        name="youtube_search", category="builtin", requires_key=None,
        description="Searches YouTube and returns matching video links.",
        loader=_load_youtube_search,
    ),
    "wikidata": ToolEntry(
        name="wikidata", category="builtin", requires_key=None,
        description="Structured factual lookups from Wikidata's knowledge graph.",
        loader=_load_wikidata,
    ),
    "python_repl": ToolEntry(
        name="python_repl", category="builtin", requires_key=None,
        description="Executes Python code for calculations and data manipulation. CAUTION: arbitrary code execution.",
        loader=_load_python_repl,
    ),
    "requests_get": ToolEntry(
        name="requests_get", category="builtin", requires_key=None,
        description="Performs raw HTTP GET requests to a given URL. CAUTION: SSRF surface, use with trusted agents only.",
        loader=_load_requests_get,
    ),
}


# ===================================================================================
# Public API for the agent builder
# ===================================================================================

def list_available_tools(category: Optional[str] = None) -> List[Dict[str, object]]:
    """
    Return metadata for every registered tool, for the agent builder's tool-picker UI.
    Does not raise for unloadable tools — flags them as unavailable instead.
    """
    entries = TOOL_REGISTRY.values() if category is None else [e for e in TOOL_REGISTRY.values() if e.category == category]
    return [
        {
            "name": e.name,
            "category": e.category,
            "description": e.description,
            "requires_key": e.requires_key,
            "available": e.available,
        }
        for e in entries
    ]


def get_tools_by_names(names: List[str]) -> List[BaseTool]:
    """
    Resolve a list of tool names (as selected by a user in the agent builder) into
    actual LangChain tool instances. Unknown names or tools that fail to load are
    skipped with a logged warning rather than raising — so one bad selection never
    prevents the rest of the agent's toolset from being built.
    """
    resolved: List[BaseTool] = []
    for name in names:
        entry = TOOL_REGISTRY.get(name)
        if entry is None:
            logger.warning("Requested tool '%s' is not registered — skipping.", name)
            continue
        try:
            resolved.append(entry.get())
        except RuntimeError as exc:
            logger.warning(str(exc))
    return resolved


def get_all_tools(category: Optional[str] = None) -> List[BaseTool]:
    """Load every available tool (optionally filtered by category), skipping failures."""
    names = [e.name for e in TOOL_REGISTRY.values() if category is None or e.category == category]
    return get_tools_by_names(names)