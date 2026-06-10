"""Vector algebra for MCV4U0 (Calculus and Vectors).

The geometric/algebraic vector strand of Ontario's Grade 12 Calculus and Vectors
course: magnitude, the four arithmetic operations, the dot and cross products,
the angle between vectors, projections, and unit vectors — in two or three
dimensions.

Like the rest of :mod:`study_calc.core`, this module is UI- and language-neutral.
Operations are named by stable ids (``"dot"``); each returns a
:class:`VectorResult` whose :class:`VectorStep` s carry an i18n *key* plus the
already-rendered numbers, and failures raise :class:`VectorError` with a machine
``code``. Only the Python standard library is used — no SymPy, no NumPy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Operation ids, in the order the GUI lists them.
OPERATIONS: tuple[str, ...] = (
    "magnitude",
    "add",
    "subtract",
    "scale",
    "dot",
    "cross",
    "angle",
    "projection",
    "unit",
)
# Ops that need a second vector ``v`` / a scalar ``k`` in addition to ``u``.
NEEDS_SECOND: frozenset[str] = frozenset({"add", "subtract", "dot", "cross", "angle", "projection"})
NEEDS_SCALAR: frozenset[str] = frozenset({"scale"})

Vector = tuple[float, ...]


class VectorError(ValueError):
    """A vector operation could not be carried out.

    Carries a stable ``code`` (e.g. ``"vec_dim_mismatch"``) and optional
    ``params`` so the presentation layer can build a localized message.
    """

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(code)


@dataclass(frozen=True)
class VectorStep:
    """One line of a worked explanation (i18n ``key`` + already-rendered params)."""

    key: str
    params: dict


@dataclass(frozen=True)
class VectorResult:
    """The outcome of a vector operation, ready to display."""

    output_text: str
    steps: tuple[VectorStep, ...] = ()


def _fmt(value: float) -> str:
    """Format a scalar: whole numbers without a tail, else 6 significant digits."""
    if math.isfinite(value) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.6g}"


def _vec(components: Vector) -> str:
    """Render a vector as ``(a, b, c)``."""
    return "(" + ", ".join(_fmt(c) for c in components) + ")"


def parse_vector(text: str) -> Vector:
    """Parse ``"1, 2, 3"`` into a 1-, 2- or 3-component float tuple.

    A lone number (``"30"``) is a valid 1-D vector — magnitude, scaling and the
    arithmetic operations all make sense in one dimension; only the cross product
    insists on 2-D/3-D, and it guards that itself.

    :raises VectorError: ``vec_empty`` if blank, ``vec_parse`` on a non-number or
        a dimension other than 1, 2 or 3.
    """
    text = text.strip()
    if not text:
        raise VectorError("vec_empty")
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip() != ""]
    if len(parts) not in (1, 2, 3):
        raise VectorError("vec_parse", value=text)
    try:
        return tuple(float(p) for p in parts)
    except ValueError as exc:
        raise VectorError("vec_parse", value=text) from exc


def _same_dim(u: Vector, v: Vector) -> None:
    if len(u) != len(v):
        raise VectorError("vec_dim_mismatch", a=len(u), b=len(v))


def magnitude(u: Vector) -> float:
    """Euclidean length ``|u| = √(Σ uᵢ²)``."""
    return math.sqrt(sum(c * c for c in u))


def dot(u: Vector, v: Vector) -> float:
    """Dot product ``u·v = Σ uᵢ·vᵢ``."""
    _same_dim(u, v)
    return sum(a * b for a, b in zip(u, v))


def cross(u: Vector, v: Vector) -> Vector | float:
    """Cross product. In 3D returns a vector; in 2D returns the scalar z-component."""
    _same_dim(u, v)
    if len(u) == 2:
        return u[0] * v[1] - u[1] * v[0]
    if len(u) == 3:
        return (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
    raise VectorError("vec_cross_dim")


def run(operation: str, u_text: str, v_text: str = "", scalar: str = "") -> VectorResult:
    """Run a vector ``operation`` on the typed inputs.

    :param operation: one of :data:`OPERATIONS`.
    :param u_text: the first vector, as ``"1, 2, 3"``.
    :param v_text: the second vector (for ops in :data:`NEEDS_SECOND`).
    :param scalar: the scalar multiplier (for ops in :data:`NEEDS_SCALAR`).
    :raises VectorError: with a stable ``code`` on any failure.
    """
    if operation not in OPERATIONS:
        raise VectorError("vec_unknown_operation", operation=operation)

    u = parse_vector(u_text)
    v: Vector | None = None
    if operation in NEEDS_SECOND:
        v = parse_vector(v_text)
        _same_dim(u, v)

    if operation == "magnitude":
        return _run_magnitude(u)
    if operation == "add":
        return _run_sum(u, v, sign=1, op="add")
    if operation == "subtract":
        return _run_sum(u, v, sign=-1, op="subtract")
    if operation == "scale":
        return _run_scale(u, scalar)
    if operation == "dot":
        return _run_dot(u, v)
    if operation == "cross":
        return _run_cross(u, v)
    if operation == "angle":
        return _run_angle(u, v)
    if operation == "projection":
        return _run_projection(u, v)
    return _run_unit(u)  # "unit"


def _run_magnitude(u: Vector) -> VectorResult:
    mag = magnitude(u)
    squares = " + ".join(f"{_fmt(c)}²" for c in u)
    steps = (
        VectorStep("vector.step.do.magnitude", {"u": _vec(u)}),
        VectorStep("vector.step.magnitude_formula", {"squares": squares}),
        VectorStep("vector.step.result", {"result": _fmt(mag)}),
    )
    return VectorResult(output_text=f"|u| = {_fmt(mag)}", steps=steps)


def _run_sum(u: Vector, v: Vector, sign: int, op: str) -> VectorResult:
    result = tuple(a + sign * b for a, b in zip(u, v))
    steps = (
        VectorStep(f"vector.step.do.{op}", {"u": _vec(u), "v": _vec(v)}),
        VectorStep("vector.step.componentwise", {}),
        VectorStep("vector.step.result", {"result": _vec(result)}),
    )
    return VectorResult(output_text=_vec(result), steps=steps)


def _run_scale(u: Vector, scalar: str) -> VectorResult:
    scalar = scalar.strip().replace(",", ".")
    try:
        k = float(scalar)
    except ValueError as exc:
        raise VectorError("vec_bad_scalar", value=scalar or "") from exc
    result = tuple(k * c for c in u)
    steps = (
        VectorStep("vector.step.do.scale", {"k": _fmt(k), "u": _vec(u)}),
        VectorStep("vector.step.componentwise", {}),
        VectorStep("vector.step.result", {"result": _vec(result)}),
    )
    return VectorResult(output_text=_vec(result), steps=steps)


def _run_dot(u: Vector, v: Vector) -> VectorResult:
    products = " + ".join(f"{_fmt(a)}·{_fmt(b)}" for a, b in zip(u, v))
    value = dot(u, v)
    steps = (
        VectorStep("vector.step.do.dot", {"u": _vec(u), "v": _vec(v)}),
        VectorStep("vector.step.dot_formula", {"products": products}),
        VectorStep("vector.step.result", {"result": _fmt(value)}),
    )
    return VectorResult(output_text=f"u·v = {_fmt(value)}", steps=steps)


def _run_cross(u: Vector, v: Vector) -> VectorResult:
    result = cross(u, v)
    rendered = _vec(result) if isinstance(result, tuple) else _fmt(result)
    note_key = "vector.step.cross_3d" if isinstance(result, tuple) else "vector.step.cross_2d"
    steps = (
        VectorStep("vector.step.do.cross", {"u": _vec(u), "v": _vec(v)}),
        VectorStep(note_key, {}),
        VectorStep("vector.step.result", {"result": rendered}),
    )
    return VectorResult(output_text=f"u×v = {rendered}", steps=steps)


def _run_angle(u: Vector, v: Vector) -> VectorResult:
    mu, mv = magnitude(u), magnitude(v)
    if mu == 0 or mv == 0:
        raise VectorError("vec_zero")
    cosine = dot(u, v) / (mu * mv)
    cosine = max(-1.0, min(1.0, cosine))  # guard tiny floating-point overshoot
    radians = math.acos(cosine)
    degrees = math.degrees(radians)
    steps = (
        VectorStep("vector.step.do.angle", {"u": _vec(u), "v": _vec(v)}),
        VectorStep("vector.step.angle_formula",
                   {"dot": _fmt(dot(u, v)), "mu": _fmt(mu), "mv": _fmt(mv), "cos": _fmt(cosine)}),
        VectorStep("vector.step.angle_result", {"deg": _fmt(degrees), "rad": _fmt(radians)}),
    )
    return VectorResult(output_text=f"θ = {_fmt(degrees)}°", steps=steps)


def _run_projection(u: Vector, v: Vector) -> VectorResult:
    mv = magnitude(v)
    if mv == 0:
        raise VectorError("vec_zero")
    d = dot(u, v)
    scalar_proj = d / mv
    factor = d / (mv * mv)
    vector_proj = tuple(factor * c for c in v)
    steps = (
        VectorStep("vector.step.do.projection", {"u": _vec(u), "v": _vec(v)}),
        VectorStep("vector.step.proj_scalar", {"dot": _fmt(d), "mv": _fmt(mv), "value": _fmt(scalar_proj)}),
        VectorStep("vector.step.proj_vector", {"value": _vec(vector_proj)}),
    )
    return VectorResult(output_text=f"proj_v(u) = {_vec(vector_proj)}", steps=steps)


def _run_unit(u: Vector) -> VectorResult:
    mag = magnitude(u)
    if mag == 0:
        raise VectorError("vec_zero")
    result = tuple(c / mag for c in u)
    steps = (
        VectorStep("vector.step.do.unit", {"u": _vec(u)}),
        VectorStep("vector.step.unit_formula", {"mag": _fmt(mag)}),
        VectorStep("vector.step.result", {"result": _vec(result)}),
    )
    return VectorResult(output_text=_vec(result), steps=steps)
