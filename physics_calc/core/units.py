"""Конвертер единиц измерения.

Большинство величин переводятся через общий базовый блок СИ с помощью линейного
коэффициента. Температура — особый случай (смещение нуля), поэтому для неё
заданы явные функции прямого и обратного перевода в кельвины.
"""

from __future__ import annotations

from typing import Callable, Dict


class ConversionError(ValueError):
    """Неизвестная категория или единица измерения."""


# Линейные категории: единица → множитель перевода в базовую единицу СИ.
_LINEAR: Dict[str, Dict[str, float]] = {
    "Длина": {
        "м": 1.0,
        "км": 1000.0,
        "см": 0.01,
        "мм": 0.001,
        "миля": 1609.344,
        "фут": 0.3048,
        "дюйм": 0.0254,
    },
    "Масса": {
        "кг": 1.0,
        "г": 0.001,
        "мг": 1e-6,
        "т": 1000.0,
        "фунт": 0.45359237,
        "унция": 0.028349523125,
    },
    "Время": {
        "с": 1.0,
        "мс": 0.001,
        "мин": 60.0,
        "ч": 3600.0,
        "сутки": 86400.0,
    },
    "Скорость": {
        "м/с": 1.0,
        "км/ч": 1000.0 / 3600.0,
        "миль/ч": 1609.344 / 3600.0,
        "узел": 1852.0 / 3600.0,
    },
    "Энергия": {
        "Дж": 1.0,
        "кДж": 1000.0,
        "кал": 4.184,
        "ккал": 4184.0,
        "кВт·ч": 3.6e6,
        "эВ": 1.602176634e-19,
    },
    "Давление": {
        "Па": 1.0,
        "кПа": 1000.0,
        "бар": 1e5,
        "атм": 101325.0,
        "мм рт. ст.": 133.322387415,
    },
    "Сила": {
        "Н": 1.0,
        "кН": 1000.0,
        "дин": 1e-5,
        "кгс": 9.80665,
    },
}

# Температура: единица → (в кельвины, из кельвинов).
_TEMPERATURE: Dict[str, tuple[Callable[[float], float], Callable[[float], float]]] = {
    "°C": (lambda c: c + 273.15, lambda k: k - 273.15),
    "K": (lambda k: k, lambda k: k),
    "°F": (lambda f: (f - 32.0) * 5.0 / 9.0 + 273.15,
           lambda k: (k - 273.15) * 9.0 / 5.0 + 32.0),
}


def categories() -> list[str]:
    """Список доступных категорий величин."""
    return list(_LINEAR.keys()) + ["Температура"]


def units_of(category: str) -> list[str]:
    """Единицы измерения внутри категории."""
    if category == "Температура":
        return list(_TEMPERATURE.keys())
    if category not in _LINEAR:
        raise ConversionError(f"Неизвестная категория: {category}")
    return list(_LINEAR[category].keys())


def convert(value: float, from_unit: str, to_unit: str, category: str) -> float:
    """Перевести ``value`` из ``from_unit`` в ``to_unit`` внутри ``category``."""
    if category == "Температура":
        return _convert_temperature(value, from_unit, to_unit)

    table = _LINEAR.get(category)
    if table is None:
        raise ConversionError(f"Неизвестная категория: {category}")
    if from_unit not in table or to_unit not in table:
        raise ConversionError(
            f"Единица «{from_unit}» или «{to_unit}» не относится к категории «{category}»."
        )
    base = value * table[from_unit]      # в базовую единицу СИ
    return base / table[to_unit]         # из базовой единицы в целевую


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in _TEMPERATURE or to_unit not in _TEMPERATURE:
        raise ConversionError(
            f"Единица «{from_unit}» или «{to_unit}» не относится к температуре."
        )
    to_kelvin, _ = _TEMPERATURE[from_unit]
    _, from_kelvin = _TEMPERATURE[to_unit]
    return from_kelvin(to_kelvin(value))
