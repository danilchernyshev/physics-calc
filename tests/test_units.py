"""Тесты конвертера единиц измерения."""

import pytest

from physics_calc.core.units import convert, categories, units_of, ConversionError


def test_length_km_to_m():
    assert convert(1, "км", "м", "Длина") == pytest.approx(1000)


def test_length_inch_to_cm():
    assert convert(1, "дюйм", "см", "Длина") == pytest.approx(2.54)


def test_mass_pound_to_kg():
    assert convert(1, "фунт", "кг", "Масса") == pytest.approx(0.45359237)


def test_speed_kmh_to_ms():
    assert convert(36, "км/ч", "м/с", "Скорость") == pytest.approx(10)


def test_temperature_c_to_f():
    assert convert(100, "°C", "°F", "Температура") == pytest.approx(212)


def test_temperature_f_to_c():
    assert convert(32, "°F", "°C", "Температура") == pytest.approx(0)


def test_temperature_c_to_k():
    assert convert(0, "°C", "K", "Температура") == pytest.approx(273.15)


def test_roundtrip_identity():
    assert convert(123.4, "Дж", "Дж", "Энергия") == pytest.approx(123.4)


def test_unknown_category_raises():
    with pytest.raises(ConversionError):
        convert(1, "м", "м", "Светимость")


def test_unknown_unit_raises():
    with pytest.raises(ConversionError):
        convert(1, "парсек", "м", "Длина")


def test_categories_and_units_consistent():
    assert "Температура" in categories()
    assert "°C" in units_of("Температура")
    assert "м" in units_of("Длина")
