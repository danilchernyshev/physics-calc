"""Tests for the unit converter."""

import pytest

from physics_calc.core.units import convert, categories, units_of, ConversionError


def test_length_km_to_m():
    assert convert(1, "kilometer", "meter", "length") == pytest.approx(1000)


def test_length_inch_to_cm():
    assert convert(1, "inch", "centimeter", "length") == pytest.approx(2.54)


def test_mass_pound_to_kg():
    assert convert(1, "pound", "kilogram", "mass") == pytest.approx(0.45359237)


def test_speed_kmh_to_ms():
    assert convert(36, "km_per_hour", "meter_per_second", "speed") == pytest.approx(10)


def test_temperature_c_to_f():
    assert convert(100, "celsius", "fahrenheit", "temperature") == pytest.approx(212)


def test_temperature_f_to_c():
    assert convert(32, "fahrenheit", "celsius", "temperature") == pytest.approx(0)


def test_temperature_c_to_k():
    assert convert(0, "celsius", "kelvin", "temperature") == pytest.approx(273.15)


def test_roundtrip_identity():
    assert convert(123.4, "joule", "joule", "energy") == pytest.approx(123.4)


def test_unknown_category_raises_with_code():
    with pytest.raises(ConversionError) as info:
        convert(1, "meter", "meter", "luminosity")
    assert info.value.code == "unknown_category"


def test_unknown_unit_raises_with_code():
    with pytest.raises(ConversionError) as info:
        convert(1, "parsec", "meter", "length")
    assert info.value.code == "unknown_unit"


def test_categories_and_units_are_ids():
    assert "temperature" in categories()
    assert "celsius" in units_of("temperature")
    assert "meter" in units_of("length")
