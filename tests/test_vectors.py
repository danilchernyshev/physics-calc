"""Tests for the MCV4U0 vector-algebra engine and its i18n keys."""

import math

import pytest

from study_calc.core import vectors as V
from study_calc.i18n import I18n


def test_magnitude_pythagorean():
    assert V.run("magnitude", "3, 4").output_text == "|u| = 5"


def test_add_componentwise():
    assert V.run("add", "1,2,3", "4,5,6").output_text == "(5, 7, 9)"


def test_subtract_componentwise():
    assert V.run("subtract", "1,2,3", "4,5,6").output_text == "(-3, -3, -3)"


def test_scale_multiplies_each_component():
    assert V.run("scale", "1,2,3", scalar="2").output_text == "(2, 4, 6)"


def test_dot_product():
    assert V.run("dot", "1,2,3", "4,5,6").output_text == "u·v = 32"


def test_cross_product_3d_is_perpendicular():
    result = V.run("cross", "1,0,0", "0,1,0")
    assert result.output_text == "u×v = (0, 0, 1)"


def test_cross_product_2d_is_scalar():
    assert V.run("cross", "1,2", "3,4").output_text == "u×v = -2"


def test_angle_between_perpendicular_vectors_is_90():
    assert V.run("angle", "1,0", "0,1").output_text == "θ = 90°"


def test_projection_onto_axis():
    assert V.run("projection", "3,4", "1,0").output_text == "proj_v(u) = (3, 0)"


def test_unit_vector_has_length_one():
    result = V.run("unit", "3,4")
    assert result.output_text == "(0.6, 0.8)"


def test_dimension_mismatch_raises():
    with pytest.raises(V.VectorError) as info:
        V.run("add", "1,2", "1,2,3")
    assert info.value.code == "vec_dim_mismatch"


def test_angle_with_zero_vector_raises():
    with pytest.raises(V.VectorError) as info:
        V.run("angle", "0,0", "1,1")
    assert info.value.code == "vec_zero"


def test_bad_components_raise_parse_error():
    with pytest.raises(V.VectorError) as info:
        V.run("magnitude", "1, two")
    assert info.value.code == "vec_parse"


def test_pure_functions_directly():
    assert V.magnitude((3, 4)) == 5
    assert V.dot((1, 2), (3, 4)) == 11
    assert V.cross((1, 0, 0), (0, 1, 0)) == (0, 0, 1)


# --- i18n completeness for the vector keys, across every locale. ---

_VECTOR_KEYS = [
    "tab.vectors", "vector.operation", "vector.u", "vector.v", "vector.scalar",
    "vector.hint", "vector.steps_title", "vector.steps_placeholder",
    "vector.step.result", "vector.step.componentwise",
] + [f"vector.op.{oid}" for oid in V.OPERATIONS] + [
    f"vector.step.do.{oid}" for oid in V.OPERATIONS
]


@pytest.mark.parametrize("code", ["en", "es", "fr", "ru", "uk"])
def test_every_catalog_has_all_vector_keys(code):
    catalog = I18n()._catalogs[code]
    missing = set(_VECTOR_KEYS) - set(catalog)
    assert not missing, f"{code}.json is missing vector keys: {sorted(missing)}"


def test_every_vector_operation_has_a_learning_topic():
    from study_calc.core.learning import load_topic

    for op in V.OPERATIONS:
        assert load_topic(f"vec_{op}", "en") is not None, (
            f"vector operation '{op}' has no learning topic 'vec_{op}'"
        )
