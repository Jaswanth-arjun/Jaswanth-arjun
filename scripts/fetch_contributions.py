#!/usr/bin/env python3
"""Fetch the public contribution calendar for a GitHub user.

No GraphQL, no personal access token: GitHub serves the same calendar
fragment the profile page uses at github.com/users/<user>/contributions.
We parse the day cells (<td data-date=... data-level=...>) and pair each
cell with its <tool-tip> ("N contributions on ...") via the cell id to
recover exact per-day counts, then write data/contributions.json with
raw days plus derived stats.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "Jaswanth-arjun"
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

HEADERS = {
    "User-Agent": "profile-art-bot/1.0 (+https://github.com/" + USERNAME + ")",
    "Accept": "text/html",
}

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def parse_count(text: str) -> int:
    m = re.search(r"(\d[\d,]*)", text or "")
    return int(m.group(1).replace(",", "")) if m else 0


def fetch() -> tuple[list[dict], str]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # tool-tip elements are keyed by the id of the day cell they describe
    counts_by_cell: dict[str, int] = {}
    for tip in soup.find_all("tool-tip"):
        cell_id = tip.get("for")
        if cell_id:
            counts_by_cell[cell_id] = parse_count(tip.get_text())

    days: list[dict] = []
    for td in soup.find_all("td", class_="ContributionCalendar-day"):
        d = td.get("data-date")
        if not d:
            continue
        cell_id = td.get("id", "")
        count = counts_by_cell.get(cell_id, 0)
        try:
            level = int(td.get("data-level", 0))
        except (TypeError, ValueError):
            level = 0
        days.append({"date": d, "count": count, "level": level})

    days.sort(key=lambda x: x["date"])
    return days, resp.text


def derive_stats(days: list[dict]) -> dict:
    counts = [d["count"] for d in days]
    dates = [date.fromisoformat(d["date"]) for d in days]

    total = sum(counts)

    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)

    # current streak: consecutive days with >0 ending at the last day
    current = 0
    for c in reversed(counts):
        if c > 0:
            current += 1
        else:
            break

    best_i = counts.index(max(counts)) if counts else 0
    best = {"count": counts[best_i] if counts else 0,
            "date": days[best_i]["date"] if counts else None}

    monthly: dict[str, int] = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]

    return {
        "total": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best,
        "first_day": days[0]["date"] if days else None,
        "last_day": days[-1]["date"] if days else None,
        "active_days": sum(1 for c in counts if c > 0),
        "monthly": dict(sorted(monthly.items())),
        "_dates_ok": bool(dates),
    }


def main() -> None:
    days, _html = fetch()
    if not days:
        print("error: no contribution cells found — GitHub markup may have changed", file=sys.stderr)
        sys.exit(1)

    payload = {
        "username": USERNAME,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": days,
        "stats": derive_stats(days),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    s = payload["stats"]
    print(f"saved {len(days)} days -> {OUT.relative_to(OUT.parent.parent)}")
    print(f"total={s['total']}  current_streak={s['current_streak']}  "
          f"longest={s['longest_streak']}  best_day={s['best_day']['count']} on {s['best_day']['date']}")


if __name__ == "__main__":
    main()
