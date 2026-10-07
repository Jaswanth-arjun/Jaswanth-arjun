#!/usr/bin/env python3
"""Render the contribution calendar as a self-revealing animated SVG.

Reads data/contributions.json (written by fetch_contributions.py) and
draws the classic 53-week calendar of rounded boxes that slide in
diagonally, column by column, then freeze. The animation is pure CSS
keyframes inside the SVG, so GitHub plays it straight from <img>.

Output: contrib-heatmap.svg
"""

from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

# github-ish green ramp: none -> brightest (level 5 is a neon top end)
PALETTE_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
PALETTE_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39", "#0b7a2e"]

CELL, GAP = 11, 3
PITCH = CELL + GAP
X0, Y0 = 46, 30              # left labels + month labels breathing room
FONT = "ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace"

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def sun_index(d: date) -> int:
    """Sunday-based weekday: Sun=0 .. Sat=6."""
    return (d.weekday() + 1) % 7


def build_columns(days: list[dict]) -> tuple[list[list[dict | None]], date]:
    """Bucket days into Sunday-aligned week columns."""
    start = date.fromisoformat(days[0]["date"])
    swd = sun_index(start)

    def col_of(d: date) -> int:
        return ((d - start).days + swd) // 7

    ncols = max((col_of(date.fromisoformat(d["date"])) for d in days), default=1) + 1
    cols: list[list[dict | None]] = [[None] * 7 for _ in range(ncols)]
    for day in days:
        d = date.fromisoformat(day["date"])
        cols[col_of(d)][sun_index(d)] = day
    return cols, start


def neon_cutoff(counts: list[int]) -> float:
    nonzero = sorted(c for c in counts if c > 0)
    if not nonzero:
        return float("inf")
    return nonzero[max(0, math.ceil(len(nonzero) * 0.97) - 1)]


def color_for(day: dict, cut: float) -> int:
    lvl = day["level"]
    if day["count"] >= cut and day["count"] > 0:
        return 5
    return max(0, min(4, lvl))


def month_labels(cols: list[list[dict | None]], x0: float) -> list[tuple[float, str]]:
    labels: list[tuple[float, str]] = []
    last_month = None
    for ci, col in enumerate(cols):
        first = next((d for d in col if d), None)
        if not first:
            continue
        m = date.fromisoformat(first["date"]).month
        if last_month is not None and m != last_month and ci > 0:
            labels.append((x0 + ci * PITCH, MONTH_ABBR[m - 1]))
        last_month = m
    return labels


def render() -> str:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    days = payload["days"]
    stats = payload["stats"]
    cols, _start = build_columns(days)
    cut = neon_cutoff([d["count"] for d in days])

    ncols = len(cols)
    grid_w = ncols * PITCH - GAP
    grid_h = 7 * PITCH - GAP
    foot_y = Y0 + grid_h + 30
    height = foot_y + 12

    # per-column groups, staggered diagonal reveal
    col_groups: list[str] = []
    for ci, col in enumerate(cols):
        rects = []
        for ri, day in enumerate(col):
            if not day:
                continue
            x = X0 + ci * PITCH
            y = Y0 + ri * PITCH
            rects.append(
                f'<rect class="c{color_for(day, cut)}" x="{x}" y="{y}" '
                f'width="{CELL}" height="{CELL}" rx="2.5"/>'
            )
        delay = 0.15 + ci * 0.018
        col_groups.append(
            f'<g class="col" style="animation-delay:{delay:.3f}s">{"".join(rects)}</g>'
        )

    # month labels above the grid
    month_text = "".join(
        f'<text class="muted" x="{x}" y="{Y0 - 10}">{escape(t)}</text>'
        for x, t in month_labels(cols, X0)
    )

    # weekday labels on the left
    day_text = "".join(
        f'<text class="muted" x="{X0 - 8}" y="{Y0 + r * PITCH + CELL - 1}" text-anchor="end">{lbl}</text>'
        for r, lbl in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )

    best = stats.get("best_day") or {}
    best_date = best.get("date") or ""
    footer = (
        f'{stats["total"]:,} contributions in the last year'
        f'   ·   current streak {stats["current_streak"]}d'
        f'   ·   longest {stats["longest_streak"]}d'
        f'   ·   best day {best.get("count", 0)} on {best_date}'
    )

    # never clip the stats line: size the panel to fit grid and footer
    width = max(X0 + grid_w, X0 + len(footer) * 6.9) + 14

    palette_dark = " ".join(f".c{i}{{fill:{c}}}" for i, c in enumerate(PALETTE_DARK))
    palette_light = " ".join(f".c{i}{{fill:{c}}}" for i, c in enumerate(PALETTE_LIGHT))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Contribution heatmap: {stats["total"]} contributions in the last year">
  <style>
    .bg{{fill:#0d1117;stroke:#21262d;stroke-width:1}}
    .muted{{fill:#8b949e;font:10px {FONT}}}
    .stats{{fill:#c9d1d9;font:11.5px {FONT}}}
    .col{{animation:drop .5s cubic-bezier(.22,.61,.36,1) both}}
    @keyframes drop{{from{{opacity:0;transform:translate(14px,14px)}}to{{opacity:1;transform:translate(0,0)}}}}
    {palette_dark}
    @media (prefers-color-scheme: light){{
      .bg{{fill:#f6f8fa;stroke:#d0d7de}}
      .muted{{fill:#59636e}}
      .stats{{fill:#1f2328}}
      {palette_light}
    }}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12"/>
  {month_text}
  {day_text}
  {"".join(col_groups)}
  <text class="stats" x="{X0}" y="{foot_y}">{escape(footer)}</text>
</svg>
'''


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
