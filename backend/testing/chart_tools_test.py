import base64
import os

from backend.tools.chart_tools import chart_tool


OUTPUT_DIR = "chart_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_chart(result: dict, filename: str):
    assert result["success"] is True

    with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
        f.write(base64.b64decode(result["image_base64"]))

    print(f"✓ {filename}")


# -------------------------------------------------------------------
# Sample Dataset
# -------------------------------------------------------------------

sales_data = [
    {"month": "Jan", "sales": 100, "profit": 20, "cost": 80},
    {"month": "Feb", "sales": 130, "profit": 25, "cost": 105},
    {"month": "Mar", "sales": 90, "profit": 18, "cost": 72},
    {"month": "Apr", "sales": 160, "profit": 35, "cost": 125},
    {"month": "May", "sales": 180, "profit": 45, "cost": 135},
]

scatter_data = [
    {"height": 160, "weight": 55},
    {"height": 165, "weight": 60},
    {"height": 170, "weight": 67},
    {"height": 175, "weight": 73},
    {"height": 180, "weight": 80},
]

pie_data = [
    {"department": "Engineering", "employees": 45},
    {"department": "Marketing", "employees": 15},
    {"department": "Sales", "employees": 25},
    {"department": "HR", "employees": 10},
]

distribution_data = [
    {"score": 82},
    {"score": 91},
    {"score": 74},
    {"score": 88},
    {"score": 95},
    {"score": 67},
    {"score": 79},
    {"score": 84},
    {"score": 90},
    {"score": 76},
]


# -------------------------------------------------------------------
# Individual Tests
# -------------------------------------------------------------------


def test_line_chart():
    result = chart_tool.invoke({
        "chart_type": "line",
        "data": sales_data,
        "x_field": "month",
        "y_field": "sales",
        "title": "Monthly Sales"
    })

    save_chart(result, "line.png")


def test_multi_line_chart():
    result = chart_tool.invoke({
        "chart_type": "line",
        "data": sales_data,
        "x_field": "month",
        "y_fields": ["sales", "profit", "cost"],
        "title": "Sales vs Profit vs Cost"
    })

    save_chart(result, "multi_line.png")


def test_bar_chart():
    result = chart_tool.invoke({
        "chart_type": "bar",
        "data": sales_data,
        "x_field": "month",
        "y_field": "sales"
    })

    save_chart(result, "bar.png")


def test_grouped_bar_chart():
    result = chart_tool.invoke({
        "chart_type": "bar",
        "data": sales_data,
        "x_field": "month",
        "y_fields": ["sales", "profit"]
    })

    save_chart(result, "grouped_bar.png")


def test_horizontal_bar():
    result = chart_tool.invoke({
        "chart_type": "bar",
        "data": sales_data,
        "x_field": "month",
        "y_field": "sales",
        "horizontal": True
    })

    save_chart(result, "horizontal_bar.png")


def test_scatter():
    result = chart_tool.invoke({
        "chart_type": "scatter",
        "data": scatter_data,
        "x_field": "height",
        "y_field": "weight"
    })

    save_chart(result, "scatter.png")


def test_pie():
    result = chart_tool.invoke({
        "chart_type": "pie",
        "data": pie_data,
        "label_field": "department",
        "value_field": "employees"
    })

    save_chart(result, "pie.png")


def test_histogram():
    result = chart_tool.invoke({
        "chart_type": "histogram",
        "data": distribution_data,
        "y_field": "score"
    })

    save_chart(result, "histogram.png")


def test_box():
    result = chart_tool.invoke({
        "chart_type": "box",
        "data": sales_data,
        "y_fields": ["sales", "profit", "cost"]
    })

    save_chart(result, "box.png")


def test_violin():
    result = chart_tool.invoke({
        "chart_type": "violin",
        "data": sales_data,
        "y_fields": ["sales", "profit", "cost"]
    })

    save_chart(result, "violin.png")


def test_heatmap():
    result = chart_tool.invoke({
        "chart_type": "heatmap",
        "data": sales_data,
        "numeric_fields": ["sales", "profit", "cost"]
    })

    save_chart(result, "heatmap.png")


def test_correlation():
    result = chart_tool.invoke({
        "chart_type": "correlation_matrix",
        "data": sales_data,
        "numeric_fields": ["sales", "profit", "cost"]
    })

    save_chart(result, "correlation.png")


# -------------------------------------------------------------------
# Error Handling Tests
# -------------------------------------------------------------------


def test_invalid_field():
    result = chart_tool.invoke({
        "chart_type": "line",
        "data": sales_data,
        "x_field": "month",
        "y_field": "INVALID"
    })

    assert result["success"] is False
    print("✓ Invalid field handled")


def test_empty_data():
    result = chart_tool.invoke({
        "chart_type": "line",
        "data": [],
        "x_field": "month",
        "y_field": "sales"
    })

    assert result["success"] is False
    print("✓ Empty data handled")


def test_non_numeric():
    bad_data = [
        {"x": 1, "y": "hello"},
        {"x": 2, "y": "world"},
    ]

    result = chart_tool.invoke({
        "chart_type": "scatter",
        "data": bad_data,
        "x_field": "x",
        "y_field": "y"
    })

    assert result["success"] is False
    print("✓ Non-numeric values handled")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":

    print("\n========== GENERATING CHARTS ==========\n")

    test_line_chart()
    test_multi_line_chart()
    test_bar_chart()
    test_grouped_bar_chart()
    test_horizontal_bar()
    test_scatter()
    test_pie()
    test_histogram()
    test_box()
    test_violin()
    test_heatmap()
    test_correlation()

    print("\n========== TESTING ERRORS ==========\n")

    test_invalid_field()
    test_empty_data()
    test_non_numeric()

    print("\n===================================")
    print("✓ ALL TESTS PASSED")
    print(f"Charts saved in '{OUTPUT_DIR}/'")