from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yfinance as yf
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

VALID_OPERATIONS = {"quote", "history"}
VALID_EXCHANGES = {"NSE", "BSE"}
EXCHANGE_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1d", "1wk", "1mo"}
MAX_HISTORY_ROWS = 200  

class StockToolInput(BaseModel):
    """Type-level schema for stock_tool. Business rules validated in _run_stock_tool."""

    operation: str = Field(..., description="'quote' (current price for one or more symbols) or 'history' (OHLC time series for one symbol).")
    symbols: Optional[List[str]] = Field(
        None,
        description="List of stock symbols for 'quote', e.g. ['RELIANCE', 'TCS', 'INFY']. Suffix (.NS/.BO) optional — added automatically based on 'exchange'.",
    )
    symbol: Optional[str] = Field(None, description="Single stock symbol for 'history', e.g. 'RELIANCE'.")
    exchange: str = Field("NSE", description="'NSE' or 'BSE'. Determines which suffix is appended if the symbol has none.")
    period: str = Field("1mo", description="History range for 'history': 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max.")
    interval: str = Field("1d", description="History granularity for 'history': 1m, 5m, 15m, 30m, 60m, 1d, 1wk, 1mo. Intraday intervals only work with short periods.")


# ===================================================================================
# Helpers
# ===================================================================================

def _normalize_symbol(raw: str, exchange: str) -> str:
    """Append the correct Yahoo Finance suffix if the symbol doesn't already have one."""
    symbol = raw.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol
    return symbol + EXCHANGE_SUFFIX[exchange]


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _fetch_single_quote(raw_symbol: str, exchange: str) -> Dict[str, Any]:
    """
    Fetch one symbol's quote. Never raises — returns an error field on failure.

    Uses ticker.history() as the primary source rather than fast_info: fast_info hits
    a lighter Yahoo endpoint that intermittently returns empty/malformed responses
    (a known yfinance/Yahoo issue, not specific to any one symbol). history() is the
    same reliable endpoint the 'history' operation already depends on.
    """
    ticker_symbol = _normalize_symbol(raw_symbol, exchange)
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="5d", interval="1d")

        if df is None or df.empty:
            return {
                "symbol": raw_symbol, "ticker": ticker_symbol, "success": False,
                "error": "No price data returned — check the symbol is correct and currently listed.",
            }

        last_row = df.iloc[-1]
        last_price = _safe_float(last_row.get("Close"))
        prev_close = _safe_float(df.iloc[-2].get("Close")) if len(df) >= 2 else None

        if last_price is None:
            return {"symbol": raw_symbol, "ticker": ticker_symbol, "success": False, "error": "Price data was returned but is unusable (null close)."}

        change = round(last_price - prev_close, 2) if prev_close is not None else None
        change_pct = round((change / prev_close) * 100, 2) if change is not None and prev_close else None

        return {
            "symbol": raw_symbol,
            "ticker": ticker_symbol,
            "success": True,
            "price": round(last_price, 2),
            "previous_close": round(prev_close, 2) if prev_close is not None else None,
            "change": change,
            "change_percent": change_pct,
            "day_high": _safe_float(last_row.get("High")),
            "day_low": _safe_float(last_row.get("Low")),
            "volume": int(last_row["Volume"]) if not _isnan(last_row.get("Volume")) else None,
            "currency": "INR",
            "as_of": last_row.name.isoformat() if hasattr(last_row.name, "isoformat") else datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:  # noqa: BLE001 — isolate this symbol's failure from the batch
        return {"symbol": raw_symbol, "ticker": ticker_symbol, "success": False, "error": f"Failed to fetch quote: {exc}"}



def _fetch_history(raw_symbol: str, exchange: str, period: str, interval: str) -> Dict[str, Any]:
    ticker_symbol = _normalize_symbol(raw_symbol, exchange)
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period, interval=interval)

    if df is None or df.empty:
        raise RuntimeError(f"No historical data returned for '{ticker_symbol}' (period={period}, interval={interval}). Check the symbol and that the market has traded in this range.")

    if len(df) > MAX_HISTORY_ROWS:
        df = df.tail(MAX_HISTORY_ROWS)

    rows = [
        {
            "date": idx.isoformat(),
            "open": _safe_float(row.get("Open")),
            "high": _safe_float(row.get("High")),
            "low": _safe_float(row.get("Low")),
            "close": _safe_float(row.get("Close")),
            "volume": int(row["Volume"]) if not _isnan(row.get("Volume")) else None,
        }
        for idx, row in df.iterrows()
    ]

    return {
        "symbol": raw_symbol,
        "ticker": ticker_symbol,
        "period": period,
        "interval": interval,
        "row_count": len(rows),
        "data": rows,
    }


def _isnan(value: Any) -> bool:
    try:
        return value != value  # NaN != NaN is True; works without importing math/pandas here
    except Exception:
        return True


# ===================================================================================
# Semantic validation — runs INSIDE the try/except in _run_stock_tool
# ===================================================================================

def _validate_inputs(operation: str, exchange: str, symbols: Optional[List[str]], symbol: Optional[str], period: str, interval: str) -> None:
    if operation not in VALID_OPERATIONS:
        raise RuntimeError(f"Unsupported operation '{operation}'. Valid options: {sorted(VALID_OPERATIONS)}.")
    if exchange not in VALID_EXCHANGES:
        raise RuntimeError(f"Unsupported exchange '{exchange}'. Valid options: {sorted(VALID_EXCHANGES)}.")

    if operation == "quote" and not symbols:
        raise RuntimeError("'symbols' (a non-empty list) is required for operation 'quote'.")
    if operation == "history":
        if not symbol:
            raise RuntimeError("'symbol' is required for operation 'history'.")
        if period not in VALID_PERIODS:
            raise RuntimeError(f"Unsupported period '{period}'. Valid options: {sorted(VALID_PERIODS)}.")
        if interval not in VALID_INTERVALS:
            raise RuntimeError(f"Unsupported interval '{interval}'. Valid options: {sorted(VALID_INTERVALS)}.")


# ===================================================================================
# Dispatcher + StructuredTool
# ===================================================================================

def _run_stock_tool(
    operation: str,
    symbols: Optional[List[str]] = None,
    symbol: Optional[str] = None,
    exchange: str = "NSE",
    period: str = "1mo",
    interval: str = "1d",
) -> Dict[str, Any]:
    """
    Fetch current quotes or historical OHLC data for Indian stocks (NSE/BSE) via Yahoo Finance.

    Guaranteed never to raise: invalid operation/exchange/period/interval, missing required
    fields, network errors, and per-symbol failures are all caught and returned as
    {"success": False, "error": "..."}. Batch quote requests isolate failures per symbol,
    so one bad ticker never aborts the others.
    """
    try:
        operation_norm = (operation or "").strip().lower()
        exchange_norm = (exchange or "NSE").strip().upper()
        period_norm = (period or "1mo").strip().lower()
        interval_norm = (interval or "1d").strip().lower()

        _validate_inputs(operation_norm, exchange_norm, symbols, symbol, period_norm, interval_norm)

        if operation_norm == "quote":
            results = [_fetch_single_quote(s, exchange_norm) for s in symbols]
            return {
                "success": True,
                "operation": "quote",
                "exchange": exchange_norm,
                "quote_count": len(results),
                "quotes": results,
                "note": "Prices reflect Yahoo Finance's standard feed (near real-time, may lag by seconds to a few minutes). Not a tick-level NSE real-time feed.",
            }

        data = _fetch_history(symbol, exchange_norm, period_norm, interval_norm)
        return {"success": True, "operation": "history", "exchange": exchange_norm, **data}

    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 — absolute last line of defense
        return {"success": False, "error": f"Unexpected error during '{operation}': {exc}"}


stock_tool = StructuredTool.from_function(
    func=_run_stock_tool,
    name="stock_tool",
    description=(
        "Gets Indian stock prices (NSE/BSE) via Yahoo Finance"
        "operation: 'quote' (current price for one or more symbols — needs 'symbols' list, e.g. "
        "['RELIANCE', 'TCS', 'INFY']) or 'history' (OHLC time series for one symbol — needs 'symbol', "
        "plus optional 'period' [1d/5d/1mo/3mo/6mo/1y/2y/5y/ytd/max] and 'interval' "
        "[1m/5m/15m/30m/60m/1d/1wk/1mo]). 'exchange' is 'NSE' (default) or 'BSE' — determines the "
        "suffix auto-appended to bare symbols. Always check 'success' before using the data; for "
        "'quote', also check each individual result's 'success' field since batch requests isolate "
        "per-symbol failures."
    ),
    args_schema=StockToolInput,
    return_direct=False,
    handle_tool_error=True,
)