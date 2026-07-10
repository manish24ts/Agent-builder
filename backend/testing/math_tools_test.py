from backend.tools.math_tools import math_tool


def run_test(title: str, payload: dict):
    print("=" * 80)
    print(f"TEST: {title}")
    print("-" * 80)

    try:
        result = math_tool.invoke(payload)
        print(result)
    except Exception as e:
        print("Exception:", e)

    print()


# ------------------------------------------------------------------------------
# Arithmetic
# ------------------------------------------------------------------------------

run_test(
    "Basic Evaluation",
    {
        "operation": "evaluate",
        "expression": "2 + 3 * 4"
    }
)

run_test(
    "Scientific Evaluation",
    {
        "operation": "evaluate",
        "expression": "sqrt(144)+sin(pi/2)"
    }
)

# ------------------------------------------------------------------------------
# Algebra
# ------------------------------------------------------------------------------

run_test(
    "Simplify",
    {
        "operation": "simplify",
        "expression": "(x**2-1)/(x-1)"
    }
)

run_test(
    "Factor",
    {
        "operation": "factor",
        "expression": "x**2+5*x+6"
    }
)

run_test(
    "Roots",
    {
        "operation": "roots",
        "expression": "x**2-9"
    }
)

run_test(
    "Solve Equation",
    {
        "operation": "solve",
        "expression": "x**2 - 4 = 0"
    }
)

# ------------------------------------------------------------------------------
# Calculus
# ------------------------------------------------------------------------------

run_test(
    "Derivative",
    {
        "operation": "differentiate",
        "expression": "sin(x)*exp(x)"
    }
)

run_test(
    "Second Derivative",
    {
        "operation": "differentiate",
        "expression": "x**5",
        "order": 2
    }
)

run_test(
    "Indefinite Integral",
    {
        "operation": "integrate",
        "expression": "x**2"
    }
)

run_test(
    "Definite Integral",
    {
        "operation": "integrate",
        "expression": "x",
        "lower_bound": 0,
        "upper_bound": 5
    }
)

run_test(
    "Limit",
    {
        "operation": "limit",
        "expression": "sin(x)/x",
        "point": 0
    }
)

run_test(
    "Taylor Series",
    {
        "operation": "series",
        "expression": "exp(x)",
        "order": 5
    }
)

# ------------------------------------------------------------------------------
# Matrix
# ------------------------------------------------------------------------------

matrix = [
    [1, 2],
    [3, 4]
]

run_test(
    "Determinant",
    {
        "operation": "matrix",
        "matrix_operation": "determinant",
        "matrix_a": matrix
    }
)

run_test(
    "Inverse",
    {
        "operation": "matrix",
        "matrix_operation": "inverse",
        "matrix_a": matrix
    }
)

run_test(
    "Transpose",
    {
        "operation": "matrix",
        "matrix_operation": "transpose",
        "matrix_a": matrix
    }
)

run_test(
    "Rank",
    {
        "operation": "matrix",
        "matrix_operation": "rank",
        "matrix_a": matrix
    }
)

run_test(
    "Matrix Multiplication",
    {
        "operation": "matrix",
        "matrix_operation": "multiply",
        "matrix_a": matrix,
        "matrix_b": matrix
    }
)

# ------------------------------------------------------------------------------
# Statistics
# ------------------------------------------------------------------------------

sample = [1, 2, 3, 4, 5]

run_test(
    "Mean",
    {
        "operation": "stats",
        "stat_operation": "mean",
        "data": sample
    }
)

run_test(
    "Median",
    {
        "operation": "stats",
        "stat_operation": "median",
        "data": sample
    }
)

run_test(
    "Standard Deviation",
    {
        "operation": "stats",
        "stat_operation": "std",
        "data": sample
    }
)

run_test(
    "Variance",
    {
        "operation": "stats",
        "stat_operation": "var",
        "data": sample
    }
)

run_test(
    "Describe",
    {
        "operation": "stats",
        "stat_operation": "describe",
        "data": sample
    }
)

run_test(
    "Correlation",
    {
        "operation": "stats",
        "stat_operation": "correlation",
        "data": [1,2,3,4,5],
        "data_b": [2,4,6,8,10]
    }
)

# ------------------------------------------------------------------------------
# Validation Tests
# ------------------------------------------------------------------------------

run_test(
    "Missing Expression",
    {
        "operation": "simplify"
    }
)

run_test(
    "Limit Without Point",
    {
        "operation": "limit",
        "expression": "sin(x)/x"
    }
)

run_test(
    "Matrix Without Matrix",
    {
        "operation": "matrix",
        "matrix_operation": "inverse"
    }
)

run_test(
    "Statistics Without Data",
    {
        "operation": "stats",
        "stat_operation": "mean"
    }
)

run_test(
    "Unsupported Operation",
    {
        "operation": "banana",
        "expression": "2+2"
    }
)