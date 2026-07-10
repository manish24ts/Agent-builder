import json
from pprint import pprint

from backend.tools.stocks_tools import stock_tool, _run_stock_tool


def divider(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def show(result):
    print(json.dumps(result, indent=2, default=str))


# ==============================================================================
# DIRECT FUNCTION TESTS
# ==============================================================================

divider("TEST 1 - Single Quote")

result = _run_stock_tool(
    operation="quote",
    symbols=["RELIANCE"]
)
show(result)


divider("TEST 2 - Multiple Quotes")

result = _run_stock_tool(
    operation="quote",
    symbols=[
        "RELIANCE",
        "TCS",
        "INFY",
        "SBIN",
        "HDFCBANK"
    ]
)
show(result)


divider("TEST 3 - Mixed Valid + Invalid Symbols")

result = _run_stock_tool(
    operation="quote",
    symbols=[
        "RELIANCE",
        "INVALID123",
        "TCS",
        "NATCOPHARMA",
        "INFY"
    ]
)
show(result)


divider("TEST 4 - Invalid Symbol Only")

result = _run_stock_tool(
    operation="quote",
    symbols=["XYZINVALID"]
)
show(result)


divider("TEST 5 - History (1 Month)")

result = _run_stock_tool(
    operation="history",
    symbol="RELIANCE"
)
show(result)


divider("TEST 6 - History (6 Months Weekly)")

result = _run_stock_tool(
    operation="history",
    symbol="TCS",
    period="6mo",
    interval="1wk"
)
show(result)


divider("TEST 7 - History (1 Year Monthly)")

result = _run_stock_tool(
    operation="history",
    symbol="INFY",
    period="1y",
    interval="1mo"
)
show(result)


divider("TEST 8 - BSE Quote")

result = _run_stock_tool(
    operation="quote",
    exchange="BSE",
    symbols=["RELIANCE"]
)
show(result)


divider("TEST 9 - Invalid Operation")

result = _run_stock_tool(
    operation="price",
    symbols=["RELIANCE"]
)
show(result)


divider("TEST 10 - Invalid Exchange")

result = _run_stock_tool(
    operation="quote",
    exchange="NASDAQ",
    symbols=["RELIANCE"]
)
show(result)


divider("TEST 11 - Invalid Period")

result = _run_stock_tool(
    operation="history",
    symbol="RELIANCE",
    period="20years"
)
show(result)


divider("TEST 12 - Invalid Interval")

result = _run_stock_tool(
    operation="history",
    symbol="RELIANCE",
    interval="10sec"
)
show(result)


divider("TEST 13 - Missing Symbols")

result = _run_stock_tool(
    operation="quote"
)
show(result)


divider("TEST 14 - Missing History Symbol")

result = _run_stock_tool(
    operation="history"
)
show(result)


divider("TEST 15 - History with Intraday Data")

result = _run_stock_tool(
    operation="history",
    symbol="RELIANCE",
    period="5d",
    interval="15m"
)
show(result)


# ==============================================================================
# LANGCHAIN TOOL TESTS
# ==============================================================================

divider("TEST 16 - StructuredTool.invoke() Quote")

result = stock_tool.invoke({
    "operation": "quote",
    "symbols": ["RELIANCE", "TCS", "INFY"]
})
show(result)


divider("TEST 17 - StructuredTool.invoke() History")

result = stock_tool.invoke({
    "operation": "history",
    "symbol": "RELIANCE",
    "period": "3mo",
    "interval": "1d"
})
show(result)


divider("TEST 18 - StructuredTool Invalid Operation")

result = stock_tool.invoke({
    "operation": "hello",
    "symbols": ["RELIANCE"]
})
show(result)


# ==============================================================================
# STRESS TEST
# ==============================================================================

divider("TEST 19 - Large Batch Quote")

stocks = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "SBIN",
    "ICICIBANK",
    "ITC",
    "LT",
    "WIPRO",
    "MARUTI",
    "AXISBANK",
    "ULTRACEMCO",
    "SUNPHARMA",
    "NTPC",
    "POWERGRID"
]

result = _run_stock_tool(
    operation="quote",
    symbols=stocks
)

print("Success:", result["success"])
print("Quotes Returned:", result["quote_count"])

for q in result["quotes"]:
    print(
        f"{q['ticker']:15} "
        f"Success={q['success']} "
        f"Price={q.get('price')}"
    )


# ==============================================================================
# SUMMARY TEST
# ==============================================================================

divider("TEST 20 - Summary")

tests = [
    ("Quote", _run_stock_tool("quote", symbols=["RELIANCE"])),
    ("History", _run_stock_tool("history", symbol="RELIANCE")),
    ("Bad Exchange", _run_stock_tool("quote", exchange="ABC", symbols=["RELIANCE"])),
    ("Bad Symbol", _run_stock_tool("quote", symbols=["XYZINVALID"])),
]

for name, res in tests:
    print(f"{name:20} Success -> {res['success']}")


print("\n")
print("=" * 90)
print("ALL TESTS FINISHED")
print("=" * 90)