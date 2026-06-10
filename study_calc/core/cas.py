"""Symbolic math (CAS) engine backed by SymPy.

This is the algebraic counterpart of :mod:`study_calc.core.formula`: where a
``Formula`` plugs *numbers* into a fixed equation, the CAS lets the user type an
arbitrary expression and ask for a symbolic transformation — simplify, expand,
factor, differentiate, integrate, solve an equation, or evaluate numerically.

Like the rest of :mod:`study_calc.core`, this module is UI- and
language-agnostic. It speaks in stable operation ids (``"derivative"``) and
raises :class:`CasError` with a machine ``code`` plus parameters; the GUI and
:mod:`study_calc.i18n` turn those into localized prose.

User input is never passed to :func:`eval`. Parsing goes through SymPy's
:func:`~sympy.parsing.sympy_parser.parse_expr`, whose namespace resolves bare
names to symbols rather than Python builtins, so ``"__import__"`` and friends
become inert symbols instead of executable code.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy
from sympy import (
    Eq,
    Integral,
    Interval,
    diff,
    expand,
    expand_log,
    factor,
    integrate,
    limit,
    nan,
    oo,
    series,
    simplify,
    trigsimp,
    zoo,
)
from sympy import solve as _sympy_solve
from sympy.calculus.util import continuous_domain
from sympy.core.basic import Basic
from sympy.core.relational import Relational
from sympy.core.symbol import Symbol
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)
from sympy.sets import FiniteSet, Union
from sympy.solvers.inequalities import solve_univariate_inequality

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
    "limit",
    "solve",
    "inequality",
    "logarithm",
    "trig_simplify",
    "identity",
    "function",
    "rate",
    "combine",
    "evaluate",
)
# Ops whose symbol the *generic* ``run`` path must resolve before working. The
# MHF4U additions (``inequality``/``function``/``rate``/``combine``) resolve
# their own symbol inside a dedicated handler, so they are not listed here.
NEEDS_VARIABLE: frozenset[str] = frozenset({"derivative", "integral", "series", "solve"})
# Ops for which the GUI should enable the (optional) variable field.
USES_VARIABLE: frozenset[str] = NEEDS_VARIABLE | {
    "analyze", "inequality", "function", "rate", "combine", "limit",
}
# Extra free-text input fields an operation needs beyond the expression and the
# variable. Each id maps to a ``cas.field.<id>`` i18n label; the GUI renders one
# entry per id and passes the typed values to :func:`run` as keyword arguments.
OP_FIELDS: dict[str, tuple[str, ...]] = {
    "rate": ("a", "b"),
    "combine": ("g",),
    "limit": ("at",),
}

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

    Language-neutral, like everything else in :mod:`study_calc.core`: ``key``
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


def run(operation: str, expression: str, variable: str = "", **fields: str) -> CasResult:
    """Run a symbolic ``operation`` on ``expression``.

    :param operation: one of :data:`OPERATIONS`.
    :param expression: the user's expression (or ``lhs = rhs`` for ``solve``/
        ``identity``, or a relation like ``x^2 - 4 > 0`` for ``inequality``).
    :param variable: the symbol to differentiate/integrate/solve for; required
        for operations in :data:`NEEDS_VARIABLE`, ignored otherwise.
    :param fields: extra inputs an operation declares in :data:`OP_FIELDS`
        (e.g. ``a``/``b`` for ``rate``, ``g`` for ``combine``, ``at`` for
        ``limit``).
    :raises CasError: with a stable ``code`` on any failure.
    """
    expression = expression.strip()
    if not expression:
        raise CasError("cas_empty")
    if operation not in OPERATIONS:
        raise CasError("cas_unknown_operation", operation=operation)

    try:
        # Ops with their own input grammar (an equation, a relation, a second
        # function, a point) are dispatched to dedicated handlers.
        if operation == "solve":
            return _run_solve(expression, variable)
        if operation == "inequality":
            return _run_inequality(expression, variable)
        if operation == "identity":
            return _run_identity(expression)
        if operation == "rate":
            return _run_rate(expression, variable, fields)
        if operation == "combine":
            return _run_combine(expression, variable, fields)
        if operation == "limit":
            return _run_limit(expression, variable, fields)

        expr = _parse(expression)
        if operation == "analyze":
            return _run_analyze(expr, variable)
        if operation == "function":
            return _run_function(expr, variable)

        # Variable-bearing ops resolve (or auto-detect) the symbol from the expr.
        symbol = _resolve_variable(expr, variable) if operation in NEEDS_VARIABLE else None
        steps: list[CasStep] = [CasStep("cas.step.input", {"expr": str(expr)})]
        if operation == "simplify":
            result = simplify(expr)
            steps.append(CasStep("cas.step.do.simplify", {}))
            if result == expr:
                steps.append(CasStep("cas.step.simplify_unchanged", {}))
        elif operation == "logarithm":
            # Apply the laws of logarithms: split products/powers into a sum.
            result = expand_log(expr, force=True)
            steps.append(CasStep("cas.step.do.logarithm", {}))
            if result == expr:
                steps.append(CasStep("cas.step.simplify_unchanged", {}))
        elif operation == "trig_simplify":
            result = trigsimp(expr)
            steps.append(CasStep("cas.step.do.trig_simplify", {}))
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


def _render_value(value: object) -> str:
    """Render a scalar result, naming the infinities and the undefined case.

    Limits and end behaviour can land on ``±∞`` or an undefined value; ``_render``
    would turn those into noise (``oo ≈ oo``), so handle them explicitly first.
    """
    if value == oo:
        return "∞"
    if value == -oo:
        return "-∞"
    if value == zoo or value == nan:
        return "undefined"
    return _render(value)


def _render_set(s: object) -> str:
    """Format a SymPy solution set (interval/union/finite) for a student.

    Produces ``(-∞, -2) ∪ (2, ∞)`` rather than SymPy's ``Union(Interval.open…)``.
    Unrecognised set shapes fall back to ``str`` so nothing ever crashes.
    """
    if s == sympy.S.EmptySet or getattr(s, "is_empty", False):
        return "∅"
    if isinstance(s, FiniteSet):
        return "{" + ", ".join(_render(x) for x in s.args) + "}"
    if isinstance(s, Interval):
        left = "-∞" if s.start == -oo else _render(s.start)
        right = "∞" if s.end == oo else _render(s.end)
        lb = "(" if bool(s.left_open) or s.start == -oo else "["
        rb = ")" if bool(s.right_open) or s.end == oo else "]"
        return f"{lb}{left}, {right}{rb}"
    if isinstance(s, Union):
        return " ∪ ".join(_render_set(a) for a in s.args)
    return str(s)


def _run_inequality(expression: str, variable: str) -> CasResult:
    """Solve a polynomial/rational inequality, rendering the interval solution."""
    rel = _parse(expression)
    if not isinstance(rel, Relational):
        raise CasError("cas_not_inequality")
    symbol = _resolve_variable(rel, variable)
    solution = solve_univariate_inequality(rel, symbol, relational=False)
    rendered = _render_set(solution)

    readable = f"{rel.lhs} {rel.rel_op} {rel.rhs}"
    steps = [
        CasStep("cas.step.input", {"expr": readable}),
        CasStep("cas.step.do.inequality", {"var": str(symbol)}),
        CasStep("cas.step.inequality_solution", {"var": str(symbol), "set": rendered}),
    ]
    return CasResult(input_text=readable, output_text=rendered, steps=tuple(steps))


def _run_identity(expression: str) -> CasResult:
    """Prove (or disprove) an identity ``lhs = rhs`` by simplifying ``lhs - rhs``."""
    equation = _split_equation(expression)
    difference = simplify(trigsimp(equation.lhs - equation.rhs))
    holds = difference == 0

    readable = f"{equation.lhs} = {equation.rhs}"
    steps = [
        CasStep("cas.step.input", {"expr": readable}),
        CasStep("cas.step.do.identity", {}),
    ]
    if holds:
        steps.append(CasStep("cas.step.identity_true", {}))
    else:
        steps.append(CasStep("cas.step.identity_false", {"diff": str(difference)}))
    return CasResult(
        input_text=readable, output_text=str(holds), steps=tuple(steps)
    )


def _run_rate(expression: str, variable: str, fields: dict) -> CasResult:
    """Average rate of change on ``[a, b]``; or the instantaneous rate at ``a``.

    With both endpoints filled, compute ``(f(b) - f(a)) / (b - a)``. With ``b``
    left blank, fall back to the instantaneous rate ``f'(a)``.
    """
    expr = _parse(expression)
    symbol = _resolve_variable(expr, variable)
    a_text = (fields.get("a") or "").strip()
    if not a_text:
        raise CasError("cas_needs_point")
    a = _parse(a_text)
    b_text = (fields.get("b") or "").strip()

    steps = [CasStep("cas.step.input", {"expr": str(expr)})]
    if b_text:
        b = _parse(b_text)
        fb, fa = expr.subs(symbol, b), expr.subs(symbol, a)
        result = simplify((fb - fa) / (b - a))
        steps.append(CasStep("cas.step.do.rate_average",
                             {"var": str(symbol), "a": str(a), "b": str(b)}))
        steps.append(CasStep("cas.step.rate_formula",
                             {"fb": _render(fb), "fa": _render(fa), "b": str(b), "a": str(a)}))
    else:
        derivative = diff(expr, symbol)
        result = simplify(derivative.subs(symbol, a))
        steps.append(CasStep("cas.step.do.rate_instant", {"var": str(symbol), "a": str(a)}))
        steps.append(CasStep("cas.step.rate_derivative",
                             {"deriv": str(derivative), "var": str(symbol), "a": str(a)}))
    steps.append(CasStep("cas.step.result", {"result": _render_value(result)}))
    return CasResult(input_text=str(expr), output_text=_render_value(result), steps=tuple(steps))


def _run_combine(expression: str, variable: str, fields: dict) -> CasResult:
    """Combine two functions: f±g, f·g, f/g, and both compositions f∘g, g∘f."""
    f = _parse(expression)
    g_text = (fields.get("g") or "").strip()
    if not g_text:
        raise CasError("cas_needs_second_function")
    g = _parse(g_text)

    symbols = sorted(f.free_symbols | g.free_symbols, key=str)
    if variable.strip():
        symbol = _parse(variable.strip())
        if not isinstance(symbol, Symbol):
            raise CasError("cas_bad_variable", value=variable)
    elif len(symbols) == 1:
        symbol = symbols[0]
    elif not symbols:
        symbol = Symbol("x")  # both constants: composition is trivial but well-defined
    else:
        raise CasError("cas_ambiguous_variable", vars=", ".join(str(c) for c in symbols))

    steps = [
        CasStep("cas.step.do.combine", {}),
        CasStep("cas.step.combine_inputs", {"f": str(f), "g": str(g)}),
    ]
    for key, value in (
        ("cas.step.card.sum", f + g),
        ("cas.step.card.difference", f - g),
        ("cas.step.card.product", f * g),
        ("cas.step.card.quotient", f / g),
    ):
        steps.append(CasStep(key, {"value": _render(simplify(value))}))
    fg = simplify(f.subs(symbol, g))
    gf = simplify(g.subs(symbol, f))
    steps.append(CasStep("cas.step.card.compose_fg", {"var": str(symbol), "value": _render(fg)}))
    steps.append(CasStep("cas.step.card.compose_gf", {"var": str(symbol), "value": _render(gf)}))
    return CasResult(
        input_text=f"f = {f}, g = {g}", output_text=f"f∘g = {_render(fg)}", steps=tuple(steps)
    )


def _run_limit(expression: str, variable: str, fields: dict) -> CasResult:
    """Evaluate a limit of ``expression`` as the variable approaches a point.

    The point may be a number or ``oo`` / ``-oo`` (typed literally), which the
    SymPy parser already resolves to infinity.
    """
    expr = _parse(expression)
    symbol = _resolve_variable(expr, variable)
    at_text = (fields.get("at") or "").strip()
    if not at_text:
        raise CasError("cas_needs_point")
    point = _parse(at_text)
    result = limit(expr, symbol, point)
    steps = [
        CasStep("cas.step.input", {"expr": str(expr)}),
        CasStep("cas.step.do.limit", {"var": str(symbol), "at": _render_value(point)}),
        CasStep("cas.step.result", {"result": _render_value(result)}),
    ]
    return CasResult(input_text=str(expr), output_text=_render_value(result), steps=tuple(steps))


def _oblique_asymptote(expr: Basic, symbol: Symbol):
    """Return the linear oblique asymptote of a rational expression, or ``None``."""
    num, den = expr.as_numer_denom()
    if not den.has(symbol):
        return None
    quotient, _remainder = sympy.div(num, den, symbol)
    if quotient == 0 or sympy.degree(quotient, symbol) != 1:
        return None
    return quotient


def _end_behaviour(expr: Basic, symbol: Symbol) -> str:
    """Describe the limits of ``expr`` as the variable goes to ``±∞``."""
    lp = limit(expr, symbol, oo)
    ln = limit(expr, symbol, -oo)
    return f"{symbol}→∞: {_render_value(lp)};  {symbol}→-∞: {_render_value(ln)}"


def _run_function(expr: Basic, variable: str) -> CasResult:
    """Sketch a function's key features: domain, intercepts, asymptotes, holes,
    end behaviour and turning points — the MHF4U/MCV4U curve-sketching toolkit.

    Every card is best-effort (via :func:`_try`): a feature that cannot be
    computed is simply skipped, never aborting the rest.
    """
    symbol = _resolve_variable(expr, variable)
    var = {"var": str(symbol)}
    steps = [
        CasStep("cas.step.do.function", {"var": str(symbol)}),
        CasStep("cas.step.input", {"expr": str(expr)}),
    ]

    domain = _try(lambda: continuous_domain(expr, symbol, sympy.S.Reals))
    if domain is not None:
        steps.append(CasStep("cas.step.card.domain", {"value": _render_set(domain)}))

    y_int = _try(lambda: expr.subs(symbol, 0))
    if y_int is not None and getattr(y_int, "is_finite", False) and not y_int.has(symbol):
        steps.append(CasStep("cas.step.card.y_intercept", {"value": _render(y_int)}))

    roots = _try(lambda: _sympy_solve(Eq(expr, 0), symbol)) or []
    real_roots = [r for r in roots if getattr(r, "is_real", False)]
    if real_roots:
        steps.append(CasStep("cas.step.card.x_intercepts",
                             {**var, "value": ", ".join(_render(r) for r in real_roots)}))

    # Vertical asymptotes vs. holes: a denominator zero is a hole when the
    # numerator also vanishes there (a common factor cancels), else an asymptote.
    num, den = expr.as_numer_denom()
    if den.has(symbol):
        den_zeros = _try(lambda: _sympy_solve(Eq(den, 0), symbol)) or []
        holes = [z for z in den_zeros if _try(lambda z=z: num.subs(symbol, z)) == 0]
        asymptotes = [z for z in den_zeros if z not in holes]
        if asymptotes:
            steps.append(CasStep("cas.step.card.vertical_asymptote",
                                 {**var, "value": ", ".join(f"{symbol} = {_render(z)}" for z in asymptotes)}))
        if holes:
            steps.append(CasStep("cas.step.card.hole",
                                 {**var, "value": ", ".join(f"{symbol} = {_render(z)}" for z in holes)}))

    horizontal = _try(lambda: limit(expr, symbol, oo))
    if horizontal is not None and getattr(horizontal, "is_finite", False) and not horizontal.has(symbol):
        steps.append(CasStep("cas.step.card.horizontal_asymptote", {"value": f"y = {_render(horizontal)}"}))
    else:
        oblique = _try(lambda: _oblique_asymptote(expr, symbol))
        if oblique is not None:
            steps.append(CasStep("cas.step.card.oblique_asymptote", {"value": f"y = {_render(oblique)}"}))

    behaviour = _try(lambda: _end_behaviour(expr, symbol))
    if behaviour is not None:
        steps.append(CasStep("cas.step.card.end_behaviour", {**var, "value": behaviour}))

    critical = _try(lambda: _sympy_solve(Eq(diff(expr, symbol), 0), symbol)) or []
    real_critical = [c for c in critical if getattr(c, "is_real", False)]
    if real_critical:
        steps.append(CasStep("cas.step.card.turning_points",
                             {**var, "value": ", ".join(f"{symbol} = {_render(c)}" for c in real_critical)}))

    return CasResult(input_text=str(expr), output_text=str(expr), steps=tuple(steps))


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


def sample(
    expression: str,
    variable: str = "",
    x_min: float = -10.0,
    x_max: float = 10.0,
    num: int = 500,
):
    """Sample ``expression`` over ``[x_min, x_max]`` for plotting.

    Returns ``(xs, ys, asymptotes)``: parallel arrays of x/y values (with ``NaN``
    inserted at infinities and near vertical asymptotes, so the plotted curve
    breaks instead of drawing spurious vertical lines), and the list of real
    vertical-asymptote x-positions inside the window. Kept here, next to the
    parser, so the GUI never touches SymPy. ``numpy`` is imported lazily.

    :raises CasError: if the expression cannot be parsed or has no single
        plotting variable.
    """
    import numpy as np

    expr = _parse(expression)
    symbol = _resolve_variable(expr, variable)
    try:
        func = sympy.lambdify(symbol, expr, "numpy")
        xs = np.linspace(x_min, x_max, num)
        with np.errstate(all="ignore"):
            raw = func(xs)
        ys = np.asarray(raw, dtype=complex)
        if ys.ndim == 0:  # a constant expression evaluates to a scalar
            ys = np.full(xs.shape, complex(ys))
        # Keep the real part; drop non-real and runaway values so asymptotes
        # show as breaks rather than near-vertical strokes.
        ys = np.where(np.abs(ys.imag) < 1e-9, ys.real, np.nan)
        ys = np.where(np.isfinite(ys) & (np.abs(ys) < 1e6), ys, np.nan)
    except Exception as exc:
        raise CasError("cas_failed", detail=str(exc) or type(exc).__name__) from exc

    asymptotes: list[float] = []
    numer, den = expr.as_numer_denom()
    if den.has(symbol):
        for z in _try(lambda: _sympy_solve(Eq(den, 0), symbol)) or []:
            if getattr(z, "is_real", False) and numer.subs(symbol, z) != 0:
                zf = float(z)
                if x_min < zf < x_max:
                    asymptotes.append(zf)
    return xs, ys, asymptotes
