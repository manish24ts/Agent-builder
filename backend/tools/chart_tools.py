from __future__ import annotations

import base64
import io
from typing import Annotated, Any, Dict, List, Literal, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

ChartType = Literal[
    "line", "bar", "scatter", "pie",
    "histogram", "box", "violin",
    "heatmap", "correlation_matrix",
]

DEFAULT_FIGSIZE = (8.0, 5.5)
DEFAULT_DPI = 120
DEFAULT_COLOR = "#4C72B0"
DEFAULT_PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860", "#DA8BC3"]


# ===================================================================================
# Input schema — STRUCTURAL ONLY. No raising model_validators here.
# ===================================================================================

class ChartToolInput(BaseModel):
    """
    Type-level schema for chart_tool. Deliberately permissive: 'data' can be empty,
    optional fields can be None. All required-field-per-chart_type logic lives in
    _validate_semantics() inside the function body, not here — so bad input becomes
    a graceful {"success": False, "error": ...} instead of a crash before the tool runs.
    """

    chart_type: ChartType = Field(..., description="Type of chart to render.")
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Inline records, e.g. [{'month': 'Jan', 'sales': 100}, {'month': 'Feb', 'sales': 120}].",
    )
    x_field: Optional[str] = Field(None, description="Column for the x-axis. Required for line/bar/scatter.")
    y_field: Optional[str] = Field(None, description="Single y-axis column.")
    y_fields: Optional[List[str]] = Field(None, description="Multiple y columns for multi-series charts.")
    label_field: Optional[str] = Field(None, description="Category label column. Required for 'pie'.")
    value_field: Optional[str] = Field(None, description="Numeric value column. Required for 'pie'.")
    numeric_fields: Optional[List[str]] = Field(None, description="Numeric columns for heatmap/correlation_matrix.")
    title: Optional[str] = Field(None, description="Chart title.")
    x_label: Optional[str] = Field(None, description="X-axis label.")
    y_label: Optional[str] = Field(None, description="Y-axis label.")
    bins: Annotated[int, Field(ge=2, le=200)] = Field(20, description="Number of bins for 'histogram'.")
    horizontal: bool = Field(False, description="Render bar chart horizontally.")
    figsize: Annotated[tuple[float, float], Field(description="Figure size in inches (width, height).")] = DEFAULT_FIGSIZE


# ===================================================================================
# Semantic validation — runs INSIDE the try/except, so errors are always caught
# ===================================================================================

def _validate_semantics(cfg: ChartToolInput) -> None:
    """Raise RuntimeError (caught by the caller) for any chart_type-specific requirement that isn't met."""
    if not cfg.data:
        raise RuntimeError("'data' must contain at least one record.")

    needs_x_y = {"line", "bar", "scatter"}
    if cfg.chart_type in needs_x_y:
        if not cfg.x_field:
            raise RuntimeError(f"'x_field' is required for chart_type '{cfg.chart_type}'.")
        if not cfg.y_field and not cfg.y_fields:
            raise RuntimeError(f"'y_field' or 'y_fields' is required for chart_type '{cfg.chart_type}'.")

    if cfg.chart_type in {"histogram", "box", "violin"} and not cfg.y_field and not cfg.y_fields:
        raise RuntimeError(f"'y_field' (or 'y_fields') is required for chart_type '{cfg.chart_type}'.")

    if cfg.chart_type == "pie" and (not cfg.label_field or not cfg.value_field):
        raise RuntimeError("'label_field' and 'value_field' are required for chart_type 'pie'.")

    if cfg.chart_type == "correlation_matrix":
        if not cfg.numeric_fields or len(cfg.numeric_fields) < 2:
            raise RuntimeError("'numeric_fields' with at least 2 columns is required for 'correlation_matrix'.")


# ===================================================================================
# Data helpers
# ===================================================================================

def _column(data: List[Dict[str, Any]], field: str) -> List[Any]:
    missing = [i for i, row in enumerate(data) if field not in row]
    if missing:
        raise RuntimeError(f"Field '{field}' is missing in {len(missing)} record(s) (e.g. row {missing[0]}).")
    return [row[field] for row in data]


def _numeric_column(data: List[Dict[str, Any]], field: str) -> np.ndarray:
    values = _column(data, field)
    try:
        return np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Field '{field}' contains non-numeric values: {exc}") from exc


def _infer_numeric_fields(data: List[Dict[str, Any]]) -> List[str]:
    candidates = [k for k, v in data[0].items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    valid = []
    for field in candidates:
        try:
            _numeric_column(data, field)
            valid.append(field)
        except RuntimeError:
            continue
    if not valid:
        raise RuntimeError("No numeric columns found in 'data'. Specify 'numeric_fields' explicitly.")
    return valid


def _fig_to_base64(fig: plt.Figure) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DEFAULT_DPI, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


# ===================================================================================
# Chart renderers
# ===================================================================================

def _render_line(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    x = _column(cfg.data, cfg.x_field)
    series = cfg.y_fields or [cfg.y_field]
    for i, field in enumerate(series):
        y = _numeric_column(cfg.data, field)
        ax.plot(x, y, marker="o", label=field, color=DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)])
    if len(series) > 1:
        ax.legend()
    ax.set_xlabel(cfg.x_label or cfg.x_field)
    ax.set_ylabel(cfg.y_label or (series[0] if len(series) == 1 else "value"))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    return fig


def _render_bar(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    x = _column(cfg.data, cfg.x_field)
    series = cfg.y_fields or [cfg.y_field]
    n = len(series)
    positions = np.arange(len(x))
    width = 0.8 / n

    for i, field in enumerate(series):
        y = _numeric_column(cfg.data, field)
        offset = (i - (n - 1) / 2) * width
        color = DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
        if cfg.horizontal:
            ax.barh(positions + offset, y, height=width, label=field, color=color)
        else:
            ax.bar(positions + offset, y, width=width, label=field, color=color)

    if cfg.horizontal:
        ax.set_yticks(positions)
        ax.set_yticklabels(x)
        ax.set_xlabel(cfg.y_label or (series[0] if n == 1 else "value"))
        ax.set_ylabel(cfg.x_label or cfg.x_field)
    else:
        ax.set_xticks(positions)
        ax.set_xticklabels(x, rotation=30, ha="right")
        ax.set_ylabel(cfg.y_label or (series[0] if n == 1 else "value"))
        ax.set_xlabel(cfg.x_label or cfg.x_field)
    if n > 1:
        ax.legend()
    return fig


def _render_scatter(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    x = _numeric_column(cfg.data, cfg.x_field)
    series = cfg.y_fields or [cfg.y_field]
    for i, field in enumerate(series):
        y = _numeric_column(cfg.data, field)
        ax.scatter(x, y, label=field, color=DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)], alpha=0.75, edgecolors="white")
    if len(series) > 1:
        ax.legend()
    ax.set_xlabel(cfg.x_label or cfg.x_field)
    ax.set_ylabel(cfg.y_label or (series[0] if len(series) == 1 else "value"))
    return fig


def _render_pie(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    labels = _column(cfg.data, cfg.label_field)
    values = _numeric_column(cfg.data, cfg.value_field)
    if np.any(values < 0):
        raise RuntimeError("'value_field' must contain non-negative values for a pie chart.")
    ax.pie(values, labels=labels, autopct="%1.1f%%", colors=DEFAULT_PALETTE, startangle=90)
    ax.axis("equal")
    return fig


def _series_map(cfg: ChartToolInput) -> Dict[str, np.ndarray]:
    fields = cfg.y_fields or [cfg.y_field]
    return {field: _numeric_column(cfg.data, field) for field in fields}


def _render_histogram(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    for i, (field, values) in enumerate(_series_map(cfg).items()):
        ax.hist(values, bins=cfg.bins, alpha=0.65, label=field, color=DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)])
    if cfg.y_fields and len(cfg.y_fields) > 1:
        ax.legend()
    ax.set_xlabel(cfg.x_label or (cfg.y_field or "value"))
    ax.set_ylabel(cfg.y_label or "frequency")
    return fig


def _render_box(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    series = _series_map(cfg)
    ax.boxplot(list(series.values()), tick_labels=list(series.keys()), patch_artist=True,
               boxprops=dict(facecolor=DEFAULT_COLOR, alpha=0.6))
    ax.set_ylabel(cfg.y_label or "value")
    return fig


def _render_violin(cfg: ChartToolInput) -> plt.Figure:
    fig, ax = plt.subplots(figsize=cfg.figsize)
    series = _series_map(cfg)
    parts = ax.violinplot(list(series.values()), showmeans=True, showmedians=False)
    for body in parts["bodies"]:
        body.set_facecolor(DEFAULT_COLOR)
        body.set_alpha(0.6)
    ax.set_xticks(range(1, len(series) + 1))
    ax.set_xticklabels(list(series.keys()))
    ax.set_ylabel(cfg.y_label or "value")
    return fig


def _render_heatmap(cfg: ChartToolInput) -> plt.Figure:
    fields = cfg.numeric_fields or _infer_numeric_fields(cfg.data)
    matrix = np.array([_numeric_column(cfg.data, f) for f in fields])
    fig, ax = plt.subplots(figsize=cfg.figsize)
    im = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_yticks(range(len(fields)))
    ax.set_yticklabels(fields)
    ax.set_xticks(range(matrix.shape[1]))
    ax.set_xticklabels(range(1, matrix.shape[1] + 1))
    ax.set_xlabel(cfg.x_label or "record index")
    fig.colorbar(im, ax=ax)
    return fig


def _render_correlation_matrix(cfg: ChartToolInput) -> plt.Figure:
    fields = cfg.numeric_fields
    matrix = np.array([_numeric_column(cfg.data, f) for f in fields])
    corr = np.corrcoef(matrix)

    fig, ax = plt.subplots(figsize=cfg.figsize)
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(fields)))
    ax.set_xticklabels(fields, rotation=30, ha="right")
    ax.set_yticks(range(len(fields)))
    ax.set_yticklabels(fields)
    for i in range(len(fields)):
        for j in range(len(fields)):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center",
                     color="white" if abs(corr[i, j]) > 0.5 else "black", fontsize=9)
    fig.colorbar(im, ax=ax)
    return fig


_RENDERERS = {
    "line": _render_line, "bar": _render_bar, "scatter": _render_scatter, "pie": _render_pie,
    "histogram": _render_histogram, "box": _render_box, "violin": _render_violin,
    "heatmap": _render_heatmap, "correlation_matrix": _render_correlation_matrix,
}


# ===================================================================================
# Dispatcher + StructuredTool
# ===================================================================================

def _run_chart_tool(
    chart_type: str,
    data: List[Dict[str, Any]],
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    y_fields: Optional[List[str]] = None,
    label_field: Optional[str] = None,
    value_field: Optional[str] = None,
    numeric_fields: Optional[List[str]] = None,
    title: Optional[str] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    bins: int = 20,
    horizontal: bool = False,
    figsize: tuple[float, float] = DEFAULT_FIGSIZE,
) -> Dict[str, Any]:
    """
    Render a chart from inline data and return it as a base64-encoded PNG.
    Never raises — every failure mode returns {"success": False, "error": "..."} so
    the calling LLM can see what went wrong and retry with corrected arguments.
    """
    try:
        cfg = ChartToolInput(
            chart_type=chart_type, data=data, x_field=x_field, y_field=y_field, y_fields=y_fields,
            label_field=label_field, value_field=value_field, numeric_fields=numeric_fields,
            title=title, x_label=x_label, y_label=y_label, bins=bins, horizontal=horizontal, figsize=figsize,
        )
        _validate_semantics(cfg)

        fig = _RENDERERS[cfg.chart_type](cfg)
        if cfg.title:
            fig.suptitle(cfg.title)
        fig.tight_layout()
        image_b64 = _fig_to_base64(fig)

        return {
            "success": True,
            "chart_type": cfg.chart_type,
            "image_base64": image_b64,
            "image_data_uri": f"data:image/png;base64,{image_b64}",
            "record_count": len(cfg.data),
        }
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 — tool boundary must never raise
        return {"success": False, "error": f"Unexpected error rendering '{chart_type}': {exc}"}


chart_tool = StructuredTool.from_function(
    func=_run_chart_tool,
    name="chart_tool",
    description=(
        "Renders charts from inline data (a list of dict records) and returns a base64-encoded PNG "
        "— no files, no external services. chart_type options: 'line', 'bar' (horizontal=True for "
        "horizontal bars), 'scatter', 'pie' (needs label_field + value_field), 'histogram' (needs "
        "y_field, optional bins), 'box', 'violin' (y_field or y_fields for multiple groups), "
        "'heatmap' (numeric_fields optional), 'correlation_matrix' (needs 2+ numeric_fields). "
        "Line/bar/scatter need x_field + y_field (or y_fields for multi-series). Always check the "
        "'success' field in the response — on failure it returns a descriptive 'error' instead of crashing."
    ),
    args_schema=ChartToolInput,
    return_direct=False,
    handle_tool_error=True,
)