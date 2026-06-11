"""Tests for the persisted user settings (#74, #124) — fail-soft JSON store."""

import json

import pytest

from study_calc.core.learning import CURRICULUM_GRADES
from study_calc.core.settings import ALL, DEFAULTS, Settings, config_dir


def test_defaults_when_file_absent(tmp_path):
    s = Settings(path=tmp_path / "settings.json")
    assert s.auto_update_check is True  # the default
    assert not (tmp_path / "settings.json").exists()  # load must not create it


def test_set_persists_across_instances(tmp_path):
    path = tmp_path / "settings.json"
    Settings(path=path).set_auto_update_check(False)
    # A fresh instance reads the saved choice.
    assert Settings(path=path).auto_update_check is False
    # And it round-trips back on.
    Settings(path=path).set_auto_update_check(True)
    assert Settings(path=path).auto_update_check is True


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    s = Settings(path=path)
    assert s.auto_update_check == DEFAULTS["auto_update_check"]


def test_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"auto_update_check": False, "evil": 1}), encoding="utf-8")
    s = Settings(path=path)
    assert s.auto_update_check is False
    assert "evil" not in s._data  # only declared keys are honoured


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "settings.json"
    Settings(path=path).set_auto_update_check(False)
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["auto_update_check"] is False


def test_config_dir_is_under_study_calc():
    assert config_dir().name == "study-calc"


# --- curriculum filter (epic #102, issue #124) ---------------------------

# Pick a concrete grade-12 and grade-11 course straight from the live map so
# these tests track CURRICULUM_GRADES rather than hardcoding the catalogue.
_G12_COURSE = next(c for c, g in CURRICULUM_GRADES.items() if g == 12)
_G11_COURSE = next((c for c, g in CURRICULUM_GRADES.items() if g == 11), None)


def test_filter_defaults_to_all(tmp_path):
    s = Settings(path=tmp_path / "settings.json")
    assert s.active_grade == ALL
    assert s.active_course == ALL
    assert DEFAULTS["active_grade"] == ALL
    assert DEFAULTS["active_course"] == ALL


def test_set_grade_then_course_round_trips(tmp_path):
    path = tmp_path / "settings.json"
    Settings(path=path).set_active_grade("12")
    Settings(path=path).set_active_course(_G12_COURSE)
    reloaded = Settings(path=path)
    assert reloaded.active_grade == "12"
    assert reloaded.active_course == _G12_COURSE


def test_changing_grade_resets_course(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings(path=path)
    s.set_active_grade("12")
    s.set_active_course(_G12_COURSE)
    assert s.active_course == _G12_COURSE
    # Switching grade clears the now-incompatible course.
    s.set_active_grade("11")
    assert s.active_course == ALL
    assert Settings(path=path).active_course == ALL  # persisted


def test_unknown_grade_falls_back_to_all(tmp_path):
    s = Settings(path=tmp_path / "settings.json")
    s.set_active_grade("99")
    assert s.active_grade == ALL


def test_unknown_course_falls_back_to_all(tmp_path):
    s = Settings(path=tmp_path / "settings.json")
    s.set_active_grade("12")
    s.set_active_course("NOPE9Z")
    assert s.active_course == ALL


def test_specific_course_needs_a_grade(tmp_path):
    # With grade = All, no specific course is valid.
    s = Settings(path=tmp_path / "settings.json")
    s.set_active_course(_G12_COURSE)
    assert s.active_course == ALL


def test_course_from_other_grade_is_rejected(tmp_path):
    s = Settings(path=tmp_path / "settings.json")
    s.set_active_grade("12")
    s.set_active_course(_G11_COURSE if _G11_COURSE else "MCR3U")
    # A grade-11 code under grade 12 is not allowed → falls back to All.
    assert s.active_course == ALL


def test_stale_course_discarded_on_load(tmp_path):
    # A hand-written file with a grade/course mismatch is sanitised on read.
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"active_grade": "12", "active_course": "MCR3U"}),
        encoding="utf-8",
    )
    s = Settings(path=path)
    assert s.active_grade == "12"
    assert s.active_course == ALL


def test_dangling_course_without_grade_discarded_on_load(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"active_grade": ALL, "active_course": _G12_COURSE}),
        encoding="utf-8",
    )
    s = Settings(path=path)
    assert s.active_course == ALL


def test_integer_grade_value_is_coerced_on_load(tmp_path):
    # An int grade (e.g. from an older serialisation) reads as its string form.
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"active_grade": 12}), encoding="utf-8")
    assert Settings(path=path).active_grade == "12"


@pytest.mark.parametrize("bad", ["{not json", json.dumps({"active_grade": None})])
def test_corrupt_or_null_filter_falls_back(tmp_path, bad):
    path = tmp_path / "settings.json"
    path.write_text(bad, encoding="utf-8")
    s = Settings(path=path)
    assert s.active_grade == ALL
    assert s.active_course == ALL
