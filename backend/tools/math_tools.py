"""
Handles: arithmetic evaluation, algebraic simplification/solving, calculus
(derivatives, integrals, limits, series), linear algebra, and statistics.

Backends: sympy (symbolic), numpy (linear algebra), scipy.stats (statistics)
"""

from typing import List, Literal, Optional, Annotated
from pydantic import BaseModel, Field, model_validator
from langchain_core.tools import StructuredTool

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
)
from scipy import stats as sstats

# Safe parsing transformations: allows "2x" -> "2*x", "sin x" -> "sin(x)"
_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------
class MathToolInput(BaseModel):
    operation: Literal[
        "evaluate", "simplify", "solve", "differentiate", "integrate",
        "limit", "series", "matrix", "stats", "roots", "factor",
    ] = Field(..., description="The math operation to perform.")

    expression: Optional[str] = Field(
        None,
        description=(
            "Expression or equation as a string, e.g. 'x**2 + 3*x - 4', "
            "'Eq(x**2, 4)' for solve, or 'sin(x)*exp(x)' for calculus."
        ),
    )
    variable: str = Field("x", description="Symbolic variable for algebra/calculus ops.")
    variables: Optional[List[str]] = Field(
        None, description="Extra variables, for multi-variable solve/systems (comma-separated equations in 'expression')."
    )
    point: Optional[float] = Field(None, description="Point to evaluate a limit at (required for 'limit').")
    order: Annotated[int, Field(ge=1, le=10)] = Field(
        1, description="Derivative order, or number of series terms."
    )
    lower_bound: Optional[float] = Field(None, description="Lower bound for a definite integral.")
    upper_bound: Optional[float] = Field(None, description="Upper bound for a definite integral.")

    # -- linear algebra --
    matrix_a: Optional[List[List[float]]] = Field(None, description="Primary matrix, as list of rows.")
    matrix_b: Optional[List[List[float]]] = Field(None, description="Second matrix/vector, if the op needs one.")
    matrix_operation: Optional[Literal[
        "add", "subtract", "multiply", "inverse", "determinant",
        "transpose", "eigen", "solve_linear", "rank",
    ]] = Field(None, description="Which matrix operation to run.")

    # -- statistics --
    data: Optional[List[float]] = Field(None, description="Numeric sample for statistics ops.")
    data_b: Optional[List[float]] = Field(None, description="Second sample, for ttest_ind / correlation.")
    stat_operation: Optional[Literal[
        "mean", "median", "std", "var", "mode", "describe",
        "ttest_1samp", "ttest_ind", "correlation", "normal_pdf", "normal_cdf", "zscore",
    ]] = Field(None, description="Which statistics operation to run.")
    popmean: Optional[float] = Field(None, description="Population mean, for ttest_1samp.")

    @model_validator(mode="after")
    def _validate_required_fields(self) -> "MathToolInput":
        op = self.operation
        symbolic_ops = {"evaluate", "simplify", "solve", "differentiate",
                        "integrate", "limit", "series", "roots", "factor"}
        if op in symbolic_ops and not self.expression:
            raise ValueError(f"'expression' is required for operation '{op}'.")
        if op == "limit" and self.point is None:
            raise ValueError("'point' is required for operation 'limit'.")
        if op == "integrate" and (self.lower_bound is None) != (self.upper_bound is None):
            raise ValueError("Provide both bounds for a definite integral, or neither for indefinite.")
        if op == "matrix" and (self.matrix_a is None or self.matrix_operation is None):
            raise ValueError("'matrix_a' and 'matrix_operation' are required for operation 'matrix'.")
        if op == "stats" and (self.data is None or self.stat_operation is None):
            raise ValueError("'data' and 'stat_operation' are required for operation 'stats'.")
        return self



def _sym(name: str) -> sp.Symbol:
    return sp.Symbol(name)


def _parse(expr_str: str, local_syms: Optional[dict] = None) -> sp.Expr:
    try:
        return parse_expr(expr_str, transformations=_TRANSFORMS, local_dict=local_syms)
    except Exception as e:
        raise ValueError(f"Could not parse expression '{expr_str}': {e}")


def _fmt(x) -> str:
    """Prefer clean floats over long sympy Rationals when the result is numeric."""
    if isinstance(x, sp.Basic) and x.is_number and not x.free_symbols:
        try:
            f = float(x)
            return str(x) if x.is_Integer or x.is_Rational else f"{x} ≈ {f:.10g}"
        except (TypeError, ValueError):
            return str(x)
    return str(x)



def _run_math(
    operation: str,
    expression: Optional[str] = None,
    variable: str = "x",
    variables: Optional[List[str]] = None,
    point: Optional[float] = None,
    order: int = 1,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
    matrix_a: Optional[List[List[float]]] = None,
    matrix_b: Optional[List[List[float]]] = None,
    matrix_operation: Optional[str] = None,
    data: Optional[List[float]] = None,
    data_b: Optional[List[float]] = None,
    stat_operation: Optional[str] = None,
    popmean: Optional[float] = None,
) -> str:
    try:
        x = _sym(variable)

        # ---------- symbolic / calculus ----------
        if operation == "evaluate":
            result = _parse(expression).evalf()
            return f"Result: {_fmt(result)}"

        if operation == "simplify":
            result = sp.simplify(_parse(expression))
            return f"Simplified: {result}"

        if operation == "factor":
            result = sp.factor(_parse(expression))
            return f"Factored: {result}"

        if operation == "solve":
            if "=" in expression and "==" not in expression:
                lhs, rhs = expression.split("=", 1)
                eq = sp.Eq(_parse(lhs), _parse(rhs))
            else:
                eq = _parse(expression)
            syms = [_sym(v) for v in variables] if variables else [x]
            solutions = sp.solve(eq, *syms)
            return f"Solution(s): {solutions}"

        if operation == "differentiate":
            result = sp.diff(_parse(expression), x, order)
            return f"d^{order}/d{variable}^{order} = {result}"

        if operation == "integrate":
            expr = _parse(expression)
            if lower_bound is not None:
                result = sp.integrate(expr, (x, lower_bound, upper_bound))
                return f"Definite integral [{lower_bound}, {upper_bound}]: {_fmt(result)}"
            result = sp.integrate(expr, x)
            return f"Indefinite integral: {result} + C"

        if operation == "limit":
            result = sp.limit(_parse(expression), x, point)
            return f"Limit as {variable} -> {point}: {_fmt(result)}"

        if operation == "series":
            result = sp.series(_parse(expression), x, 0, order + 1)
            return f"Series expansion (order {order}): {result}"

        if operation == "roots":
            expr = _parse(expression)
            result = sp.solve(sp.Eq(expr, 0), x)
            return f"Roots: {result}"

        # ---------- linear algebra ----------
        if operation == "matrix":
            A = np.array(matrix_a, dtype=float)
            B = np.array(matrix_b, dtype=float) if matrix_b is not None else None

            if matrix_operation == "add":
                return f"Result:\n{(A + B).tolist()}"
            if matrix_operation == "subtract":
                return f"Result:\n{(A - B).tolist()}"
            if matrix_operation == "multiply":
                return f"Result:\n{(A @ B).tolist()}"
            if matrix_operation == "inverse":
                return f"Inverse:\n{np.linalg.inv(A).tolist()}"
            if matrix_operation == "determinant":
                return f"Determinant: {np.linalg.det(A):.10g}"
            if matrix_operation == "transpose":
                return f"Transpose:\n{A.T.tolist()}"
            if matrix_operation == "eigen":
                vals, vecs = np.linalg.eig(A)
                return f"Eigenvalues: {vals.tolist()}\nEigenvectors:\n{vecs.tolist()}"
            if matrix_operation == "rank":
                return f"Rank: {np.linalg.matrix_rank(A)}"
            if matrix_operation == "solve_linear":
                b = np.array(matrix_b, dtype=float).flatten()
                return f"Solution vector: {np.linalg.solve(A, b).tolist()}"

        # ---------- statistics ----------
        if operation == "stats":
            arr = np.array(data, dtype=float)

            if stat_operation == "mean":
                return f"Mean: {np.mean(arr):.10g}"
            if stat_operation == "median":
                return f"Median: {np.median(arr):.10g}"
            if stat_operation == "std":
                return f"Std dev: {np.std(arr, ddof=1):.10g}"
            if stat_operation == "var":
                return f"Variance: {np.var(arr, ddof=1):.10g}"
            if stat_operation == "mode":
                m = sstats.mode(arr, keepdims=False)
                return f"Mode: {m.mode} (count: {m.count})"
            if stat_operation == "describe":
                d = sstats.describe(arr)
                return (f"n={d.nobs}, mean={d.mean:.6g}, variance={d.variance:.6g}, "
                        f"min={d.minmax[0]:.6g}, max={d.minmax[1]:.6g}, "
                        f"skewness={d.skewness:.6g}, kurtosis={d.kurtosis:.6g}")
            if stat_operation == "zscore":
                return f"Z-scores: {sstats.zscore(arr).tolist()}"
            if stat_operation == "ttest_1samp":
                if popmean is None:
                    return "Error: 'popmean' is required for ttest_1samp."
                t, p = sstats.ttest_1samp(arr, popmean)
                return f"t-statistic: {t:.6g}, p-value: {p:.6g}"
            if stat_operation == "ttest_ind":
                if data_b is None:
                    return "Error: 'data_b' is required for ttest_ind."
                t, p = sstats.ttest_ind(arr, np.array(data_b, dtype=float))
                return f"t-statistic: {t:.6g}, p-value: {p:.6g}"
            if stat_operation == "correlation":
                if data_b is None:
                    return "Error: 'data_b' is required for correlation."
                r, p = sstats.pearsonr(arr, np.array(data_b, dtype=float))
                return f"Pearson r: {r:.6g}, p-value: {p:.6g}"
            if stat_operation == "normal_pdf":
                if point is None:
                    return "Error: 'point' is required for normal_pdf."
                return f"PDF at {point}: {sstats.norm.pdf(point, loc=np.mean(arr), scale=np.std(arr)):.10g}"
            if stat_operation == "normal_cdf":
                if point is None:
                    return "Error: 'point' is required for normal_cdf."
                return f"CDF at {point}: {sstats.norm.cdf(point, loc=np.mean(arr), scale=np.std(arr)):.10g}"

        return f"Error: unsupported operation '{operation}'."

    except ZeroDivisionError:
        return "Error: division by zero."
    except np.linalg.LinAlgError as e:
        return f"Linear algebra error: {e}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error while computing '{operation}': {e}"


# ---------------------------------------------------------------------------
# StructuredTool registration
# ---------------------------------------------------------------------------
math_tool = StructuredTool.from_function(
    func=_run_math,
    name="advanced_math_solver",
    description=(
        "Solves math problems from basic arithmetic to advanced algebra, calculus, "
        "linear algebra, and statistics. Use `operation` to pick the mode: "
        "'evaluate' (compute a numeric expression), 'simplify', 'factor', "
        "'solve' (equations, use 'x=4' or 'Eq(x,4)' style, supports systems via 'variables'), "
        "'differentiate' / 'integrate' (calculus, supports definite integrals via bounds), "
        "'limit' (needs 'point'), 'series' (Taylor expansion), 'roots' (zeros of a polynomial/expr), "
        "'matrix' (add/subtract/multiply/inverse/determinant/transpose/eigen/rank/solve_linear via "
        "'matrix_a', 'matrix_b', 'matrix_operation'), and 'stats' (mean/median/std/var/mode/describe/"
        "ttest/correlation/normal_pdf/normal_cdf via 'data', 'stat_operation'). "
        "Always returns a clean, human-readable string result."
    ),
    args_schema=MathToolInput,
    return_direct=False,
    handle_tool_error=True,
)