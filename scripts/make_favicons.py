#!/usr/bin/env python3
"""Generate placeholder favicon assets (pure stdlib, no Pillow).

Draws a rounded dark square with a light "T", rendered at several sizes, and
writes favicon.ico (PNG-in-ICO container), the PNG variants PaperMod expects,
and a monochrome safari-pinned-tab SVG.

Usage: python3 make_favicons.py <output_dir>
"""
import struct
import sys
import zlib
from pathlib import Path

BG = (46, 46, 51)          # theme colour from hugo.toml
FG = (236, 236, 236)
SS = 4                     # supersampling factor for anti-aliasing


def rounded_alpha(x, y, size, radius):
    """1.0 inside the rounded square, 0.0 outside, using a distance test."""
    cx = min(max(x, radius), size - radius)
    cy = min(max(y, radius), size - radius)
    d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
    if x < radius or x > size - radius:
        if y < radius or y > size - radius:
            return 1.0 if d <= radius else 0.0
    return 1.0


def in_letter_t(x, y, size):
    """The 'T' glyph in normalised 0..1 coordinates."""
    u, v = x / size, y / size
    if 0.20 <= v <= 0.36 and 0.20 <= u <= 0.80:      # top bar
        return True
    if 0.36 <= v <= 0.80 and 0.43 <= u <= 0.57:      # stem
        return True
    return False


def render(size):
    radius = size * 0.22
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = a = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    x = px + (sx + 0.5) / SS
                    y = py + (sy + 0.5) / SS
                    if not rounded_alpha(x, y, size, radius):
                        continue
                    cr, cg, cb = FG if in_letter_t(x, y, size) else BG
                    r += cr
                    g += cg
                    b += cb
                    a += 255
            n = SS * SS
            row += bytes((round(r / n), round(g / n), round(b / n), round(a / n)))
        rows.append(bytes(row))
    return rows


def encode_png(size, rows):
    raw = b"".join(b"\x00" + row for row in rows)
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def encode_ico(pngs):
    """ICO container embedding PNG data (supported by every modern browser)."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blobs = b"", b""
    for size, data in pngs:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32,
                               len(data), offset)
        blobs += data
        offset += len(data)
    return header + entries + blobs


SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
       '<path d="M2.5 2.5h11v3h-4v8h-3v-8h-4z"/></svg>\n')

out = Path(sys.argv[1] if len(sys.argv) > 1 else "static")
out.mkdir(parents=True, exist_ok=True)

made = {}
for size in (16, 32, 180):
    png = encode_png(size, render(size))
    made[size] = png
    if size == 180:
        (out / "apple-touch-icon.png").write_bytes(png)
    else:
        (out / f"favicon-{size}x{size}.png").write_bytes(png)

(out / "favicon.ico").write_bytes(encode_ico([(16, made[16]), (32, made[32]), (48, encode_png(48, render(48)))]))
(out / "safari-pinned-tab.svg").write_text(SVG)

for p in sorted(out.iterdir()):
    print(f"  {p.name:<26} {p.stat().st_size:>7}B")
