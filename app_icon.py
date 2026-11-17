"""Generate iOS/Android PNG app icons from the same fixed 512-unit artwork as icon.svg.

No heavyweight imaging packages or network calls are needed on GitHub Actions.
SVG is used by the website; PNG sizes below support Apple and other launchers.
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

SIZES = (180, 192, 512)
NAVY = (23, 42, 67)
GOLD = (255, 211, 140)
INK = (36, 65, 91)
PAPER = (255, 247, 232)


def _rounded_rect(x, y, left, top, right, bottom, radius):
    cx = (left + right) * 0.5
    cy = (top + bottom) * 0.5
    dx = max(abs(x - cx) - (right - left) * 0.5 + radius, 0)
    dy = max(abs(y - cy) - (bottom - top) * 0.5 + radius, 0)
    return math.hypot(dx, dy) - radius if dx or dy else -radius


def _circle(x, y, cx, cy, radius):
    return math.hypot(x - cx, y - cy) - radius


def _segment(x, y, ax, ay, bx, by, width):
    length_sq = (bx - ax)**2 + (by - ay)**2
    t = max(0, min(1, ((x - ax)*(bx - ax) + (y - ay)*(by - ay)) / length_sq))
    return math.hypot(x - ax - t*(bx - ax), y - ay - t*(by - ay)) - width / 2


def _blend(base, paint, edge, antialias=1.6):
    # Premultiplied-like single-pixel coverage; all layer colors are opaque.
    coverage = max(0., min(1., 0.5 - edge / antialias))
    return tuple(round(base[k] * (1 - coverage) + paint[k] * coverage) for k in range(3))


def _pixel(x, y):
    # Soft midnight gradient. Artwork coordinates are the SVG viewBox units.
    v = min(1, max(0, (x + y) / 1024))
    rgb = tuple(round((29, 56, 86)[k] * (1 - v) + (16, 28, 50)[k] * v) for k in range(3))
    alpha = round(255 * max(0, min(1, 0.5 - _rounded_rect(x, y, 0, 0, 512, 512, 110) / 1.5)))
    # The moon and its navy occlusion form an instantly recognizable crescent.
    rgb = _blend(rgb, GOLD, _circle(x, y, 226, 194, 126))
    rgb = _blend(rgb, NAVY, _circle(x, y, 286, 134, 118))
    rgb = _blend(rgb, (255, 240, 208), _circle(x, y, 362, 112, 7))
    rgb = _blend(rgb, (245, 215, 165), _circle(x, y, 406, 198, 4))
    # A small flight path ties the moon to the incoming letter.
    rgb = _blend(rgb, (214, 168, 105), _segment(x, y, 116, 223, 228, 209, 5))
    # Letter with cream paper, deep-blue folded flap, and gold border.
    rgb = _blend(rgb, (225, 185, 118), _rounded_rect(x, y, 115, 258, 397, 423, 26))
    paper = (round(255 - (y - 262) / 170 * 16),
             round(247 - (y - 262) / 170 * 23),
             round(232 - (y - 262) / 170 * 36))
    rgb = _blend(rgb, paper, _rounded_rect(x, y, 123, 266, 389, 415, 20))
    for a, b, color, width in [
        ((129, 405), (220, 328), (156, 171, 192), 9),
        ((383, 405), (292, 328), (156, 171, 192), 9),
        ((126, 279), (256, 363), INK, 13),
        ((256, 363), (386, 279), INK, 13),
    ]:
        rgb = _blend(rgb, color, _segment(x, y, *a, *b, width))
    # The wax-seal numeral 9 stays legible at 60px and home-screen scale.
    rgb = _blend(rgb, INK, _circle(x, y, 358, 369, 41))
    rgb = _blend(rgb, GOLD, _circle(x, y, 358, 369, 33))
    digit_outer = _circle(x, y, 357, 363, 17)
    digit_inner = _circle(x, y, 357, 363, 9)
    if digit_outer <= 1 and digit_inner >= -1:
        rgb = _blend(rgb, NAVY, max(digit_outer, -digit_inner))
    rgb = _blend(rgb, NAVY, _segment(x, y, 368, 366, 365, 391, 9))
    return (*rgb, alpha)


def _chunk(name, data):
    payload = name + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xffffffff)


def icon_png(size):
    if size not in SIZES:
        raise ValueError("unsupported icon size")
    # Stored RGBA rows compress very efficiently; all input is local artwork.
    rows = bytearray()
    for y in range(size):
        rows.append(0)  # PNG filter: none
        for x in range(size):
            rows.extend(_pixel((x+0.5)*512/size, (y+0.5)*512/size))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(rows), 9)) +
            _chunk(b"IEND", b""))


def render_icons(destination):
    directory = Path(destination)
    directory.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        name = "apple-touch-icon.png" if size == 180 else "icon-" + str(size) + ".png"
        (directory / name).write_bytes(icon_png(size))


if __name__ == "__main__":
    render_icons(Path(__file__).resolve().parent / "_site/assets")
