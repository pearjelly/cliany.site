from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_blocks_invalid_website_javascript() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    required = [
        "website-javascript:",
        "Website JavaScript Syntax",
        "actions/setup-node@v4",
        'node-version: "24"',
        "Validate website JavaScript",
        "node --check site/script.js",
    ]
    for snippet in required:
        assert snippet in text


def test_release_preflight_rechecks_website_javascript() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    required = [
        "release-preflight:",
        "Release Preflight",
        "actions/setup-node@v4",
        'node-version: "24"',
        "Validate website JavaScript",
        "node --check site/script.js",
    ]
    for snippet in required:
        assert snippet in text
