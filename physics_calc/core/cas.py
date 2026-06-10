"""Symbolic math (CAS) engine backed by SymPy.

This is the algebraic counterpart of :mod:`physics_calc.core.formula`: where a
``Formula`` plugs *numbers* into a fixed equation, the CAS lets the user type an
arbitrary expression and ask for a symbolic transformation — simplify, expand,
factor, differentiate, integrate, solve an equation, or evaluate numerically.

Like the rest of :mod:`physics_calc.core`, this module is UI- and
language-agnostic. It speaks in stable operation ids (``"derivative"``) and
raises :class:`CasError` with a machine ``code`` plus parameters; the GUI and
:mod:`physics_calc.i18n` turn those into localized prose.

User input is never passed to :func:`eval`. Parsing goes through SymPy's
:func:`~sympy.parsing.sympy_parser.parse_expr`, whose namespace resolves bare
names to symbols rather than Python builtins, so ``"__import__"`` and friends
become inert symbols instead of executable code.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy
from sympy import Eq, Integral, diff, expand, factor, integrate, series, simplify
from sympy import solve as _sympy_solve
from sympy.core.basic import Basic
from sympy.core.symbol import Symbol
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

# Operation ids, in the order the GUI lists them. Each maps to a ``cas.op.<id>``
# i18n key. ``analyze`` (a SymPy-Gamma/Wolfram-Alpha-style overview) is first so
# it is the default. ``NEEDS_VARIABLE`` ops require a variable; ``USES_VARIABLE``
# ops merely accept one (``analyze`` works on constants too). When the variable
# is left blank it is auto-detected from the expression's single unknown.
OPERATIONS: tuple[str, ...] = (
    "analyze",
    "simplify",
    "expand",
    "factor",
    "derivative",
    "integral",
    "series",
    "solve",
    "evaluate",
)
NEEDS_VARIABLE: frozenset[str] = frozenset({"derivative", "integral", "series", "solve"})
USES_VARIABLE: frozenset[str] = NEEDS_VARIABLE | {"analyze"}

# ``2x`` -> ``2*x`` and ``x^2`` -> ``x**2`` so the input reads like ordinary
# math notation rather than Python. We deliberately use ``implicit_multiplication``
# (not the ``_application`` variant) so ``sin x`` stays a parse error instead of
# being silently reinterpreted as ``sin(x)``.
_TRANSFORMATIONS = standard_transformations + (implicit_multiplication, convert_xor)

# Sandbox for parsing. SymPy's default ``parse_expr`` namespace exposes Python
# builtins, so input like ``__import__("os").system(...)`` would *execute* — a
# real code-injection hole. We pass an explicit ``global_dict`` of only public
# SymPy names with ``__builtins__`` blanked out: any unknown name (including
# ``__import__``) then resolves to a harmless ``Symbol`` instead of a callable.
# ``eval`` re-injects real builtins into a namespace that omits ``__builtins__``,
# so setting it to ``{}`` explicitly is what actually closes the hole.
_GLOBAL_DICT: dict[str, object] = {"__builtins__": {}}
_GLOBAL_DICT.update({name: value for name, value in vars(sympy).items() if not name.startswith("_")})


class CasError(ValueError):
    """A symbolic operation could not be carried out.

    Carries a stable ``code`` (e.g. ``"cas_parse"``) and optional ``params`` so
    the presentation layer can build a localized message.
    """

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(code)


@dataclass(frozen=True)
class CasStep:
    """One line of a worked explanation.

    Language-neutral, like everything else in :mod:`physics_calc.core`: ``key``
    is an i18n message key (``"cas.step.do.factor"``) and ``params`` holds the
    already-rendered math strings to interpolate. The GUI turns it into prose.
    """

    key: str
    params: dict


@dataclass(frozen=True)
class CasResult:
    """The outcome of a CAS operation, ready to display.

    :param input_text: the parsed input re-rendered in canonical form, so the
        user can see how their typing was interpreted.
    :param output_text: the result rendered as a single-line string (for tests
        and compact use).
    :param steps: an ordered, localizable explanation of how the result was
        reached — rendered in the GUI's text area.
    """

    input_text: str
    output_text: str
    steps: tuple[CasStep, ...] = ()


def _parse(text: str) -> Basic:
    """Parse user text into a SymPy expression, or raise :class:`CasError`."""
    try:
        return parse_expr(
            text,
            transformations=_TRANSFORMATIONS,
            global_dict=_GLOBAL_DICT,
            evaluate=True,
        )
    except Exception as exc:  # SyntaxError, TokenError, SympifyError, ... — all map to one code
        # ``SyntaxError``/``TokenError`` stringify to their raw ``(msg, pos)`` args
        # tuple. Pull out the clean human sentence: ``.msg`` (SyntaxError) or the
        # first string arg (TokenError), falling back to the plain string form.
        detail = getattr(exc, "msg", None)
        if detail is None:
            detail = exc.args[0] if exc.args and isinstance(exc.args[0], str) else str(exc)
        raise CasError("cas_parse", detail=detail or type(exc).__name__) from exc


def _resolve_variable(expr: Basic, text: str) -> Symbol:
    """Decide which variable to act on.

    If the user typed one, parse it (must be a single symbol). If they left it
    blank, auto-detect it from ``expr`` — the way Wolfram Alpha and SymPy Gamma
    do — but only when there is exactly one unknown; zero or several is reported
    so the user can disambiguate.
    """
    text = text.strip()
    if text:
        symbol = _parse(text)
        if not isinstance(symbol, Symbol):
            raise CasError("cas_bad_variable", value=text)
        return symbol
    candidates = sorted(expr.free_symbols, key=str)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise CasError("cas_needs_variable")
    raise CasError("cas_ambiguous_variable", vars=", ".join(str(c) for c in candidates))


def _render(expr: object) -> str:
    """Render a result, appending a decimal value when it is an exact constant.

    A symbolic op often returns the input unchanged (``simplify(sin(30))`` is
    still ``sin(30)``) or an exact form (``sqrt(2)``, ``pi``, ``1/3``). When the
    result has no unknowns left it *is* a number, just not a decimal one — so we
    also show ``≈ <value>``. Plain integers/floats already read as numbers and
    are left alone, and anything still holding a free symbol (``2*x``) is too.
    """
    text = str(expr)
    try:
        if (
            getattr(expr, "is_number", False)
            and not getattr(expr, "is_Integer", False)
            and not getattr(expr, "is_Float", False)
        ):
            text += f"  ≈ {expr.evalf(6)}"
    except Exception:  # pragma: no cover — evalf failing is not worth surfacing
        pass
    return text


def _split_equation(text: str) -> Basic:
    """Build an equation from ``solve`` input.

    Accepts either ``lhs = rhs`` (an equation) or a bare expression, which is
    taken to equal zero. A doubled ``==`` or several ``=`` is rejected.
    """
    # ``evaluate=False`` keeps ``lhs``/``rhs`` accessible even for a degenerate
    # equation like ``1 = 0`` (an evaluating ``Eq`` would collapse to ``False``).
    parts = text.split("=")
    if len(parts) == 1:
        return Eq(_parse(parts[0]), 0, evaluate=False)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return Eq(_parse(parts[0]), _parse(parts[1]), evaluate=False)
    raise CasError("cas_parse", detail=text)


def run(operation: str, expression: str, variable: str = "") -> CasResult:
    """Run a symbolic ``operation`` on ``expression``.

    :param operation: one of :data:`OPERATIONS`.
    :param expression: the user's expression (or ``lhs = rhs`` for ``solve``).
    :param variable: the symbol to differentiate/integrate/solve for; required
        for operations in :data:`NEEDS_VARIABLE`, ignored otherwise.
    :raises CasError: with a stable ``code`` on any failure.
    """
    expression = expression.strip()
    if not expression:
        raise CasError("cas_empty")
    if operation not in OPERATIONS:
        raise CasError("cas_unknown_operation", operation=operation)

    try:
        if operation == "solve":
            return _run_solve(expression, variable)

        expr = _parse(expression)
        if operation == "analyze":
            return _run_analyze(expr, variable)

        # Variable-bearing ops resolve (or auto-detect) the symbol from the expr.
        symbol = _resolve_variable(expr, variable) if operation in NEEDS_VARIABLE else None
        steps: list[CasStep] = [CasStep("cas.step.input", {"expr": str(expr)})]
        if operation == "simplify":
            result = simplify(expr)
            steps.append(CasStep("cas.step.do.simplify", {}))
            if result == expr:
                steps.append(CasStep("cas.step.simplify_unchanged", {}))
        elif operation == "expand":
            result = expand(expr)
            steps.append(CasStep("cas.step.do.expand", {}))
        elif operation == "factor":
            result = factor(expr)
            steps.append(CasStep("cas.step.do.factor", {}))
        elif operation == "derivative":
            result = diff(expr, symbol)
            steps.append(CasStep("cas.step.do.derivative", {"var": str(symbol)}))
        elif operation == "integral":
            # Indefinite integral; SymPy omits the constant of integration.
            result = integrate(expr, symbol)
            steps.append(CasStep("cas.step.do.integral", {"var": str(symbol)}))
        elif operation == "series":
            # Truncated Taylor/Maclaurin expansion around the origin.
            result = series(expr, symbol, 0, _SERIES_ORDER).removeO()
            steps.append(CasStep("cas.step.do.series",
                                 {"var": str(symbol), "order": _SERIES_ORDER}))
        else:  # "evaluate"
            result = expr.evalf()
            steps.append(CasStep("cas.step.do.evaluate", {}))

        steps.append(CasStep("cas.step.result", {"result": _render(result)}))
        if operation == "integral" and not result.has(Integral):
            # Verify the antiderivative by differentiating it back to the integrand.
            back = simplify(diff(result, symbol))
            steps.append(CasStep("cas.step.integral_check", {"back": str(back)}))
        return CasResult(input_text=str(expr), output_text=_render(result), steps=tuple(steps))
    except CasError:
        raise  # already a domain error (e.g. cas_no_solution) — keep its code
    except Exception as exc:  # integrate/solve may raise NotImplementedError etc.
        raise CasError("cas_failed", detail=str(exc) or type(exc).__name__) from exc


# Number of terms kept in a Taylor expansion (``series``/``analyze``).
_SERIES_ORDER = 6


def _run_solve(expression: str, variable: str) -> CasResult:
    """Solve an equation and explain it: standard form, factoring, then roots."""
    equation = _split_equation(expression)
    standard = equation.lhs - equation.rhs
    symbol = _resolve_variable(standard, variable)
    solutions = _sympy_solve(equation, symbol)
    if not solutions:
        raise CasError("cas_no_solution")

    readable = f"{equation.lhs} = {equation.rhs}"  # "x**2 - 4 = 0", not "Eq(x**2 - 4, 0)"
    steps: list[CasStep] = [
        CasStep("cas.step.input", {"expr": readable}),
        CasStep("cas.step.do.solve", {"var": str(symbol)}),
    ]
    # Everything-on-one-side form, then a factored form when it differs.
    steps.append(CasStep("cas.step.solve_standard", {"expr": str(standard)}))
    factored = factor(standard)
    if factored != standard:
        steps.append(CasStep("cas.step.solve_factored", {"factored": str(factored)}))
    steps.append(CasStep("cas.step.solve_count", {"n": len(solutions)}))
    for sol in solutions:
        steps.append(CasStep("cas.step.solve_root", {"var": str(symbol), "root": _render(sol)}))

    output = ", ".join(f"{symbol} = {_render(sol)}" for sol in solutions)
    return CasResult(input_text=readable, output_text=output, steps=tuple(steps))


def _run_analyze(expr: Basic, variable: str) -> CasResult:
    """Produce a one-shot overview of an expression.

    Inspired by SymPy Gamma / Wolfram Alpha: rather than making the user choose
    a single operation, show every relevant view at once — algebraic forms, and
    (when there is a single variable) derivative, integral, real roots and a
    Taylor series, plus a decimal value for a constant. Each card is best-effort:
    a view that fails or adds nothing is simply skipped, never aborting the rest.
    """
    steps: list[CasStep] = [CasStep("cas.step.do.analyze", {})]
    steps.append(CasStep("cas.step.input", {"expr": str(expr)}))

    def card(key: str, value: object) -> None:
        steps.append(CasStep(key, {"value": _render(value)}))

    simplified = _try(lambda: simplify(expr))
    if simplified is not None:
        card("cas.step.card.simplified", simplified)
    factored = _try(lambda: factor(expr))
    if factored is not None and factored != expr and factored != simplified:
        card("cas.step.card.factored", factored)
    expanded = _try(lambda: expand(expr))
    if expanded is not None and expanded != expr and expanded != simplified:
        card("cas.step.card.expanded", expanded)

    # Pick the variable for the calculus cards: explicit, or the lone unknown.
    chosen = variable.strip()
    symbols = sorted(expr.free_symbols, key=str)
    symbol: Symbol | None = None
    if chosen:
        parsed = _try(lambda: _parse(chosen))
        symbol = parsed if isinstance(parsed, Symbol) else None
    elif len(symbols) == 1:
        symbol = symbols[0]

    if symbol is not None:
        var = {"var": str(symbol)}
        derivative = _try(lambda: diff(expr, symbol))
        if derivative is not None:
            steps.append(CasStep("cas.step.card.derivative", {**var, "value": _render(derivative)}))
        antiderivative = _try(lambda: integrate(expr, symbol))
        if antiderivative is not None and not antiderivative.has(Integral):
            steps.append(CasStep("cas.step.card.integral", {**var, "value": _render(antiderivative)}))
        roots = _try(lambda: _sympy_solve(Eq(expr, 0), symbol))
        if roots:
            value = ", ".join(_render(r) for r in roots)
            steps.append(CasStep("cas.step.card.roots", {**var, "value": value}))
        taylor = _try(lambda: series(expr, symbol, 0, _SERIES_ORDER).removeO())
        if taylor is not None and taylor != expr:
            steps.append(CasStep("cas.step.card.series", {**var, "value": _render(taylor)}))
    # A constant needs no separate numeric card: the simplified card, via
    # ``_render``, already appends its decimal value (e.g. ``pi  ≈ 3.14159``).

    output = _render(simplified if simplified is not None else expr)
    return CasResult(input_text=str(expr), output_text=output, steps=tuple(steps))


def _try(thunk):
    """Run a best-effort CAS view for ``analyze``; swallow failures, return None."""
    try:
        return thunk()
    except Exception:  # pragma: no cover — a single failing card must not abort analyze
        return None
