#!/usr/bin/env python3
"""Convert source-prepped.png into a self-typing monochrome ASCII SVG.

The prepped image is downsampled to a character grid (~100x53) and each
pixel's brightness picks a glyph from a density ramp — sparse characters
for bright areas, dense ones for dark. Two design choices keep it clean:

- monochrome: one light-gray fill, no per-character rainbow
- high contrast: bright background washes out to the space glyph

Each row prints with a left-to-right wipe (a small block "cursor" rides
the wipe edge), staggered top to bottom, then freezes. The wipe is SMIL
inside the SVG, so GitHub plays it straight from <img>.

    RAMP = " .`:-=+*cs#%@"    # bright (sparse) -> dark (dense)

Output: jaswanth-ascii.svg
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "jaswanth-ascii.svg"

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense)
BRIGHT_CUT = 0.10       # darkness below this maps to a space (kills bg noise)
GAMMA = 0.80            # <1 pushes midtones darker -> subject pops

COLS, ROWS = 100, 53
CW, CH = 6.0, 7.2              # character cell size in svg units
PAD = 14                       # panel padding
INNER_W, INNER_H = COLS * CW, ROWS * CH

W = INNER_W + PAD * 2
H = INNER_H + PAD * 2

GLYPH_FILL = "#a8b3c2"         # one monochrome ink
CURSOR_FILL = "#39d353"        # terminal green block cursor
FONT = "ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace"

ROW_STAGGER = 0.04             # seconds between row starts
ROW_DUR = 0.22                 # wipe duration per row


def ascii_grid(img: Image.Image) -> list[str]:
    gray = img.convert("L").resize((COLS, ROWS), Image.LANCZOS)
    px = gray.load()
    lines = []
    last = len(RAMP) - 1
    for y in range(ROWS):
        row = []
        for x in range(COLS):
            t = (255 - px[x, y]) / 255.0        # darkness 0..1
            if t <= BRIGHT_CUT:                  # bg washes out to nothing
                row.append(" ")
            else:
                idx = round(((t - BRIGHT_CUT) / (1 - BRIGHT_CUT)) ** GAMMA * last)
                row.append(RAMP[idx])
        lines.append("".join(row).rstrip())
    return lines


def render(lines: list[str]) -> str:
    rows: list[str] = []
    for i, line in enumerate(lines):
        if not line:
            continue
        y = PAD + i * CH
        t = round(0.10 + i * ROW_STAGGER, 2)
        end_x = PAD + len(line) * CW

        # left-to-right wipe via animated clip rect
        clip = (
            f'<clipPath id="rc{i}"><rect x="{PAD}" y="{y}" width="0" height="{CH}">'
            f'<animate attributeName="width" from="0" to="{INNER_W}" '
            f'begin="{t}s" dur="{ROW_DUR}s" fill="freeze"/></rect></clipPath>'
        )
        # block cursor rides the wipe edge, then fades out
        cursor = (
            f'<rect x="0" y="{y}" width="{CW}" height="{CH}" fill="{CURSOR_FILL}">'
            f'<animate attributeName="x" from="{PAD}" to="{end_x}" '
            f'begin="{t}s" dur="{ROW_DUR}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="1" to="0" '
            f'begin="{t + ROW_DUR}s" dur="0.12s" fill="freeze"/></rect>'
        )
        text = (
            f'<text x="{PAD}" y="{y + CH - 1.4}" class="g" clip-path="url(#rc{i})" '
            f'textLength="{len(line) * CW}" lengthAdjust="spacing">{escape(line)}</text>'
        )
        rows.append(clip + cursor + text)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="ASCII portrait">
  <style>
    .bg{{fill:#0d1117;stroke:#21262d;stroke-width:1}}
    .g{{fill:{GLYPH_FILL};font:{CH - 0.4:.1f}px {FONT};white-space:pre}}
    @media (prefers-color-scheme: light){{
      .bg{{fill:#f6f8fa;stroke:#d0d7de}}
      .g{{fill:#57606a}}
    }}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="{W - 1:.0f}" height="{H - 1:.0f}" rx="12"/>
  {"".join(rows)}
</svg>
'''


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    if not src.exists():
        print(f"error: {src} not found — run scripts/prep_photo.py first", file=sys.stderr)
        sys.exit(1)

    lines = ascii_grid(Image.open(src))
    nonempty = sum(1 for l in lines if l)
    print(f"grid {COLS}x{ROWS}, {nonempty} printed rows")
    OUT.write_text(render(lines), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
