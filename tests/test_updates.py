"""Tests for the update-check core (#74) — semver logic + the check policy.

All headless: the network fetch is injected, so these exercise classification
and the status model with no real HTTP.
"""

import pytest

from study_calc.core.updates import (
    UpdateError,
    Version,
    bump_kind,
    check_updates,
    parse_version,
)


# --- semver parsing -------------------------------------------------------

@pytest.mark.parametrize(
    "tag, expected",
    [
        ("1.2.3", Version(1, 2, 3, stable=True)),
        ("v1.2.3", Version(1, 2, 3, stable=True)),
        ("v0.7.0", Version(0, 7, 0, stable=True)),
        ("1.2.3-rc.1", Version(1, 2, 3, stable=False)),
        ("v2.0.0-alpha", Version(2, 0, 0, stable=False)),
        ("1.2.3+build.5", Version(1, 2, 3, stable=True)),
    ],
)
def test_parse_version_valid(tag, expected):
    assert parse_version(tag) == expected


@pytest.mark.parametrize("tag", ["", "1.2", "v1", "1.2.x", "latest", "1.2.3.4", None])
def test_parse_version_malformed_raises(tag):
    with pytest.raises(UpdateError) as exc:
        parse_version(tag)
    assert exc.value.code == "update.error.bad_version"


# --- bump classification --------------------------------------------------

def test_bump_kind_major_minor_patch():
    cur = parse_version("1.2.3")
    assert bump_kind(cur, parse_version("2.0.0")) == "major"
    assert bump_kind(cur, parse_version("1.3.0")) == "minor"
    assert bump_kind(cur, parse_version("1.2.4")) == "patch"


def test_bump_kind_equal_or_older_is_none():
    cur = parse_version("1.2.3")
    assert bump_kind(cur, parse_version("1.2.3")) is None
    assert bump_kind(cur, parse_version("1.2.2")) is None
    assert bump_kind(cur, parse_version("1.0.0")) is None
    assert bump_kind(cur, parse_version("0.9.9")) is None


def test_prerelease_orders_below_its_stable_core():
    # 1.2.3 (current) vs 1.2.3-rc.1 (latest): the pre-release is *older*.
    assert bump_kind(parse_version("1.2.3"), parse_version("1.2.3-rc.1")) is None
    # A stable release supersedes the pre-release the user is running.
    assert bump_kind(parse_version("1.2.3-rc.1"), parse_version("1.2.3")) == "patch"


# --- the check policy (injected fetcher, no network) ----------------------

def _release(tag, *, body="", url="https://example/r"):
    return lambda: {"tag_name": tag, "body": body, "html_url": url}


def test_check_reports_available_with_notes_and_url():
    result = check_updates(
        "0.7.0", fetcher=_release("v0.8.0", body="- New thing", url="https://rel/0.8.0")
    )
    assert result["status"] == "available"
    assert result["bump"] == "minor"
    assert result["version"] == "0.8.0"
    assert result["notes"] == "- New thing"
    assert result["url"] == "https://rel/0.8.0"


def test_check_reports_up_to_date_when_equal_or_newer_running():
    assert check_updates("0.7.0", fetcher=_release("v0.7.0"))["status"] == "up_to_date"
    # Running ahead of the latest published release also reads as up to date.
    assert check_updates("0.9.0", fetcher=_release("v0.7.0"))["status"] == "up_to_date"


def test_check_classifies_major_update():
    result = check_updates("0.7.0", fetcher=_release("v1.0.0"))
    assert result["status"] == "available"
    assert result["bump"] == "major"


def test_check_offline_fetch_returns_error_model_not_raise():
    def offline():
        raise UpdateError("update.error.offline")

    result = check_updates("0.7.0", fetcher=offline)
    assert result == {"status": "error", "code": "update.error.offline"}


def test_check_malformed_remote_tag_is_error():
    result = check_updates("0.7.0", fetcher=_release("not-a-version"))
    assert result["status"] == "error"
    assert result["code"] == "update.error.bad_version"


def test_check_falls_back_to_releases_page_when_url_missing():
    result = check_updates("0.7.0", fetcher=lambda: {"tag_name": "v0.8.0"})
    assert result["status"] == "available"
    assert result["url"].startswith("https://github.com/")
