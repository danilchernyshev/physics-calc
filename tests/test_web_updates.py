"""Bridge + screen-model tests for the update feature (#74).

Headless: the Bridge takes an injected ``update_fetcher`` and a ``Settings`` on a
tmp path, so nothing touches the network or the real config dir.
"""

import json

import pytest

from study_calc.core.settings import Settings
from study_calc.core.updates import UpdateError
from study_calc.i18n import _LOCALES_DIR, i18n
from study_calc.web.bridge import Bridge


@pytest.fixture(autouse=True)
def _english():
    """Keep the shared i18n singleton on English around each test."""
    i18n.set_language("en")
    yield
    i18n.set_language("en")


def _bridge(tmp_path, *, tag="v9.9.9", version="0.7.0", auto=True):
    settings = Settings(path=tmp_path / "settings.json")
    settings.set_auto_update_check(auto)
    return Bridge(
        version=version,
        settings=settings,
        update_fetcher=lambda: {"tag_name": tag, "body": "Notes", "html_url": "https://rel"},
    )


# --- get_state surfaces version + auto-check + the chrome label -----------

def test_get_state_exposes_version_and_update_chrome(tmp_path):
    state = _bridge(tmp_path, version="0.7.0", auto=True).get_state()
    assert state["version"] == "0.7.0"
    assert state["autoUpdateCheck"] is True
    assert state["labels"]["updates"]  # localized, non-empty


# --- check_updates returns a localized model -----------------------------

def test_check_updates_available_is_localized(tmp_path):
    model = _bridge(tmp_path, tag="v9.9.9", version="0.7.0").check_updates()
    assert model["status"] == "available"
    assert model["newVersion"] == "9.9.9"
    assert "9.9.9" in model["message"]
    assert model["bumpNote"]  # major/minor/patch sentence
    assert model["notes"] == "Notes"
    assert model["url"] == "https://rel"
    assert model["viewRelease"]


def test_check_updates_up_to_date(tmp_path):
    model = _bridge(tmp_path, tag="v0.7.0", version="0.7.0").check_updates()
    assert model["status"] == "up_to_date"
    assert model["message"]


def test_check_updates_offline_is_graceful(tmp_path):
    # A fetcher signals failure with UpdateError (the real one wraps OSError /
    # timeouts into update.error.offline before raising).
    def offline():
        raise UpdateError("update.error.offline")

    bridge = Bridge(
        version="0.7.0",
        settings=Settings(path=tmp_path / "s.json"),
        update_fetcher=offline,
    )
    model = bridge.check_updates()
    assert model["status"] == "error"
    assert model["message"]  # localized offline message, not a raw code


def test_check_updates_localizes_in_russian(tmp_path):
    bridge = _bridge(tmp_path, tag="v0.7.0", version="0.7.0")
    en = bridge.check_updates()["message"]
    i18n.set_language("ru")
    ru = bridge.check_updates()["message"]
    assert en != ru


# --- the auto-check toggle persists --------------------------------------

def test_set_auto_update_check_persists(tmp_path):
    path = tmp_path / "settings.json"
    bridge = Bridge(version="0.7.0", settings=Settings(path=path))
    model = bridge.set_auto_update_check(False)
    assert model["autoCheck"] is False
    # Persisted to disk for the next launch.
    assert Settings(path=path).auto_update_check is False


def test_update_screen_idle_before_any_check(tmp_path):
    model = _bridge(tmp_path).update_screen()
    assert model["status"] == "idle"
    assert model["checkButton"]
    assert "0.7.0" in model["currentLine"]


# --- i18n parity: every new key in all five locales ----------------------

_UPDATE_KEYS = [
    "menu.updates",
    "updates.title",
    "updates.intro",
    "updates.current_version",
    "updates.check_button",
    "updates.checking",
    "updates.auto_check",
    "updates.up_to_date",
    "updates.available",
    "updates.bump.major",
    "updates.bump.minor",
    "updates.bump.patch",
    "updates.whats_new",
    "updates.view_release",
    "updates.error.offline",
    "updates.error.http",
    "updates.error.bad_version",
]


@pytest.mark.parametrize("lang", ["en", "es", "fr", "ru", "uk"])
def test_update_keys_present_in_every_locale(lang):
    catalog = json.loads((_LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    missing = [key for key in _UPDATE_KEYS if key not in catalog]
    assert not missing, f"{lang}.json missing update keys: {missing}"
