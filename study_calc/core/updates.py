"""The update-check core — the platform-agnostic half of #74 (epic #60).

This decides *whether* a newer study-calc release exists and how big the jump is;
it never downloads or installs anything (that is the per-format sibling, #75).
The only network call is a single GET to the GitHub Releases API, and even that
is injectable: every public function takes an optional ``fetcher`` so the bridge
and the tests exercise the policy **headlessly, with no network**.

The running version is single-sourced from ``pyproject.toml`` via
:func:`study_calc.resources.app_version`; the latest is the newest published
GitHub Release's semver tag. Comparison is plain semver (``vMAJOR.MINOR.PATCH``,
with optional pre-release/build suffixes), and any difference is classified as
**major / minor / patch** so the UI can word the notification accordingly.

Failures never raise out of :func:`check_updates` — they come back as a
``{"status": "error", "code": ...}`` model with a stable, localizable ``code``
(``update.error.*``), mirroring the ``SolveError`` / ``CasError`` discipline, so
an offline machine degrades gracefully instead of crashing.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

# The single repository this app updates from. Kept here (not in many call sites)
# so a fork only edits one line.
_REPO = "danilchernyshev/study-calc"
LATEST_RELEASE_API = f"https://api.github.com/repos/{_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{_REPO}/releases/latest"

# A short timeout keeps a background/startup check from hanging the app when the
# network is slow or unreachable.
_TIMEOUT_SECONDS = 6

# ``tag_name`` like ``v1.2.3``, ``1.2.3``, ``1.2.3-rc.1`` or ``1.2.3+build.5``.
_SEMVER = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)

# A GitHub API call without a User-Agent is rejected outright.
_USER_AGENT = "study-calc-update-check"

#: The result of a fetch: the parsed ``releases/latest`` JSON body.
Fetcher = Callable[[], dict]


class UpdateError(Exception):
    """A check failure carrying a stable, localizable ``code`` (``update.error.*``)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, order=True)
class Version:
    """A parsed semver. ``stable`` orders above an equal-core pre-release."""

    major: int
    minor: int
    patch: int
    # A pre-release (1.2.3-rc.1) sorts *below* the same stable core (1.2.3); the
    # flag is stored inverted so the dataclass's own ordering does the right thing.
    stable: bool = True


def parse_version(tag: str) -> Version:
    """Parse a semver ``tag`` (leading ``v`` optional) or raise :class:`UpdateError`."""
    match = _SEMVER.match((tag or "").strip())
    if match is None:
        raise UpdateError("update.error.bad_version")
    return Version(
        int(match["major"]),
        int(match["minor"]),
        int(match["patch"]),
        stable=match["pre"] is None,
    )


def bump_kind(current: Version, latest: Version) -> Optional[str]:
    """Classify ``latest`` relative to ``current``.

    Returns ``"major"`` / ``"minor"`` / ``"patch"`` when ``latest`` is newer, or
    ``None`` when it is the same or older (so the caller reports "up to date").
    """
    if latest <= current:
        return None
    if latest.major != current.major:
        return "major"
    if latest.minor != current.minor:
        return "minor"
    return "patch"


def _fetch_latest_release() -> dict:
    """GET the latest GitHub Release as parsed JSON, or raise :class:`UpdateError`.

    Network and HTTP failures map to stable codes: ``update.error.offline`` for an
    unreachable host/timeout and ``update.error.http`` for any other API error
    (including the 404 GitHub returns before the first release is published).
    """
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # reached the API, got a non-2xx
        raise UpdateError("update.error.http") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:  # never reached it
        raise UpdateError("update.error.offline") from exc
    except (ValueError, json.JSONDecodeError) as exc:  # malformed body
        raise UpdateError("update.error.http") from exc


def check_updates(current_version: str, fetcher: Fetcher | None = None) -> dict:
    """Compare the running version to the latest release; never raises.

    Returns a status model — ``status`` is one of:

    * ``"up_to_date"`` — no newer release (``current``, ``latest``).
    * ``"available"`` — a newer release: ``bump`` (major/minor/patch), the new
      ``version``, the release ``notes`` (English, as published), and the ``url``.
    * ``"error"`` — the check failed: a stable ``code`` (``update.error.*``).

    All strings here are raw data (versions, the release body, a URL); the bridge
    turns them into localized UI copy.
    """
    fetcher = fetcher or _fetch_latest_release
    try:
        payload = fetcher()
    except UpdateError as exc:
        return {"status": "error", "code": exc.code}

    tag = str(payload.get("tag_name") or "")
    try:
        current = parse_version(current_version)
        latest = parse_version(tag)
    except UpdateError as exc:
        return {"status": "error", "code": exc.code}

    bump = bump_kind(current, latest)
    latest_label = tag.lstrip("v")
    if bump is None:
        return {
            "status": "up_to_date",
            "current": current_version,
            "latest": latest_label,
        }
    return {
        "status": "available",
        "bump": bump,
        "current": current_version,
        "version": latest_label,
        "notes": str(payload.get("body") or "").strip(),
        "url": str(payload.get("html_url") or RELEASES_PAGE),
    }
