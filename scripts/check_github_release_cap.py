#!/usr/bin/env python3
"""Check GitHub Release publication capacity for the Shanghai calendar day."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Shanghai")
REPO = "pearjelly/cliany.site"


def _published_tags_today(releases: Any, today: date) -> list[str]:
    if not isinstance(releases, list):
        raise ValueError("GitHub Releases response is not a list")
    tags: list[str] = []
    for release in releases:
        if not isinstance(release, dict):
            raise ValueError("GitHub Releases response contains a non-object")
        if release.get("isDraft"):
            continue
        published_at = release.get("publishedAt")
        tag = release.get("tagName")
        if not isinstance(published_at, str) or not isinstance(tag, str):
            raise ValueError("Published GitHub Release is missing a timestamp or tag")
        timestamp = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("GitHub Release timestamp has no timezone")
        if timestamp.astimezone(TIMEZONE).date() == today:
            tags.append(tag)
    return sorted(set(tags))


def _fetch_releases() -> Any:
    result = subprocess.run(
        ["gh", "release", "list", "--repo", REPO, "--json", "tagName,publishedAt,isDraft", "--limit", "1000"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", help="Shanghai calendar day (YYYY-MM-DD); defaults to today.")
    parser.add_argument("--max-daily-releases", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail when publication capacity is exhausted or unknown.")
    args = parser.parse_args(argv)
    if args.max_daily_releases < 1:
        parser.error("--max-daily-releases must be positive")
    today = date.fromisoformat(args.today) if args.today else datetime.now(TIMEZONE).date()
    tags: list[str] = []
    error: str | None = None
    try:
        tags = _published_tags_today(_fetch_releases(), today)
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
        error = str(exc)
    capacity = max(args.max_daily_releases - len(tags), 0) if error is None else None
    report = {
        "ok": capacity is not None and capacity > 0,
        "today": today.isoformat(),
        "timezone": "Asia/Shanghai",
        "published_tags_today": tags,
        "release_count_today": len(tags) if error is None else None,
        "max_daily_releases": args.max_daily_releases,
        "daily_release_capacity_remaining": capacity,
        "error": error,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"GitHub Releases {today}: {len(tags) if error is None else 'unknown'}/{args.max_daily_releases}")
        if tags:
            print(", ".join(tags))
        if error:
            print(f"remote check failed: {error}")
    return 1 if args.strict and not report["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
