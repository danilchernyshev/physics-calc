"""Tests for the persisted user settings (#74) — fail-soft JSON store."""

import json

from study_calc.core.settings import DEFAULTS, Settings, config_dir


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
