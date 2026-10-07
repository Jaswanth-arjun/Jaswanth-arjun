#!/usr/bin/env python3
"""Hand-author a neofetch-style info card as an animated SVG.

The card is the story the contribution graph can't tell: role, stack,
and highlights, printed line by line like a real neofetch run. Each row
fades and slides in on a short stagger; a block cursor keeps blinking
at the prompt below. Pure CSS keyframes inside the SVG, so GitHub plays
it straight from <img>.

Set STATIC=1 to emit a frozen frame for local Quick Look previews.

Output: info-card.svg
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "info-card.svg"

STATIC = os.environ.get("STATIC") == "1"

USER = "jaswanth"
HOST = "github"

# the story numbers can't tell — keep it short enough to fit one line
ROWS = [
    ("Now",        "Full-Stack & AI Developer · building in public"),
    ("Prev",       "Campus-Connection · MailMind-AI · recoveriq-pro"),
    ("Stack",      "TypeScript · JavaScript · Java · Python · Dart · PHP"),
    ("Focus",      "AI agents · RAG · resume & job automation"),
    ("Highlights", "54 public repos across web, AI & mobile"),
    ("GitHub",     "7 followers · shipping daily"),
]

W, H = 620, 300
TITLE_H = 38
ROW_Y0, ROW_PITCH, VALUE_X = 70, 30, 122
KEY_X = 28

FONT = "ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace"

# neofetch-ish label colors, dark then light variants
KEY_DARK = ["#7ee787", "#79c0ff", "#ffa657", "#d2a8ff", "#ff7b72", "#56d4dd"]
KEY_LIGHT = ["#1a7f37", "#0550ae", "#bc4c00", "#8250df", "#cf222e", "#0969da"]


def keyframes() -> str:
    if STATIC:
        return ".row{animation:none}.cursor{animation:none}"
    return (
        ".row{animation:print .5s cubic-bezier(.22,.61,.36,1) both}"
        "@keyframes print{from{opacity:0;transform:translateX(-10px)}"
        "to{opacity:1;transform:translateX(0)}}"
        ".cursor{animation:blink 1.1s steps(1) infinite}"
        "@keyframes blink{50%{opacity:0}}"
    )


def render() -> str:
    parts: list[str] = []
    for i, (key, value) in enumerate(ROWS):
        y = ROW_Y0 + i * ROW_PITCH
        delay = 0.15 + i * 0.13
        parts.append(
            f'<g class="row" style="animation-delay:{delay:.2f}s">'
            f'<text class="k{i}" x="{KEY_X}" y="{y}" font-weight="700">{escape(key)}</text>'
            f'<text class="v" x="{VALUE_X}" y="{y}">{escape(value)}</text>'
            f'</g>'
        )

    prompt_y = ROW_Y0 + len(ROWS) * ROW_PITCH + 16

    key_rules_dark = " ".join(f".k{i}{{fill:{c}}}" for i, c in enumerate(KEY_DARK))
    key_rules_light = " ".join(f".k{i}{{fill:{c}}}" for i, c in enumerate(KEY_LIGHT))

    dots = "".join(
        f'<circle cx="{20 + i * 16}" cy="19" r="5" fill="{c}"/>'
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f"))
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="neofetch-style profile info card">
  <style>
    .bg{{fill:#0d1117;stroke:#21262d;stroke-width:1}}
    .title{{fill:#8b949e;font:11.5px {FONT}}}
    .v{{fill:#e6edf3;font:13px {FONT}}}
    .prompt{{fill:#8b949e;font:12.5px {FONT}}}
    .cursor{{fill:#39d353}}
    .divider{{stroke:#21262d;stroke-width:1}}
    {key_rules_dark}
    {keyframes()}
    @media (prefers-color-scheme: light){{
      .bg{{fill:#f6f8fa;stroke:#d0d7de}}
      .title{{fill:#59636e}}
      .v{{fill:#1f2328}}
      .prompt{{fill:#59636e}}
      .divider{{stroke:#d0d7de}}
      {key_rules_light}
    }}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12"/>
  {dots}
  <text class="title" x="{W / 2}" y="23" text-anchor="middle">{USER}@{HOST}: ~/whoami</text>
  <line class="divider" x1="1" y1="{TITLE_H}" x2="{W - 1}" y2="{TITLE_H}"/>
  {"".join(parts)}
  <text class="prompt" x="{KEY_X}" y="{prompt_y}">{USER}@{HOST} ~ $</text>
  <rect class="cursor" x="{KEY_X + 118}" y="{prompt_y - 11}" width="8" height="14"/>
</svg>
'''


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size / 1024:.1f} KB){'  [static]' if STATIC else ''}")


if __name__ == "__main__":
    main()
