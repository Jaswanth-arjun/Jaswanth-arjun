#!/usr/bin/env python3
"""Prep a photo for ASCII conversion.

A flatly-lit face converts to a dark unreadable blob, so three steps fix it:

1. remove the background (rembg, if installed) so the subject is isolated
2. boost local contrast — CLAHE via OpenCV when available, otherwise a
   Pillow autocontrast + unsharp fallback
3. composite onto pure white so the background maps to the blank end of
   the ASCII ramp (white -> spaces)

Run once per photo:
    python scripts/prep_photo.py source-photo.jpg

Output: source-prepped.png (grayscale, same folder as the input)
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps, ImageFilter


def has_rembg() -> bool:
    try:
        import rembg  # noqa: F401
        return True
    except ImportError:
        return False


def has_cv2() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


def clahe_grayscale(img: Image.Image) -> Image.Image:
    import numpy as np
    import cv2

    arr = np.array(img)
    out = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(arr)
    return Image.fromarray(out, mode="L")


def pillow_fallback(img: Image.Image) -> Image.Image:
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python scripts/prep_photo.py <photo> [output.png]", file=sys.stderr)
        sys.exit(1)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name("source-prepped.png")

    img = Image.open(src).convert("RGB")

    if has_rembg():
        from rembg import remove

        print("rembg: removing background ...")
        cut = remove(img)
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(white, cut).convert("RGB")
    else:
        print("rembg not installed — assuming the background is already clean")

    gray = ImageOps.grayscale(img)

    if has_cv2():
        print("opencv: applying CLAHE ...")
        gray = clahe_grayscale(gray)
    else:
        print("opencv not installed — using Pillow contrast fallback")
        gray = pillow_fallback(gray)

    # composite safety: pin the histogram ends so bg -> pure white
    gray = ImageOps.autocontrast(gray, cutoff=(0, 1))

    gray.save(dst)
    print(f"saved {dst}")


if __name__ == "__main__":
    main()
