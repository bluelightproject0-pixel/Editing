"""Genera los recursos visuales del job ramses-popups (papel, congelado B/N, SVGs recortados).

Uso: python3 build/assets.py   (desde projects/ramses-popups)
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

OUT = "edit/assets/img"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
random.seed(7)

PAPER = (241, 238, 230)
INK = "#121212"
RED = "#E3261C"
COBALT = "#2B3FE0"


def crumple(w, h, strength=1.0, seed=3):
    """Mapa de sombreado de papel arrugado: planos irregulares con pliegues."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    shade = np.zeros((h, w), np.float32)
    for _ in range(46):
        cx, cy = r.uniform(0, w), r.uniform(0, h)
        ang = r.uniform(0, math.pi)
        nx, ny = math.cos(ang), math.sin(ang)
        d = (xx - cx) * nx + (yy - cy) * ny
        amp = r.uniform(2.0, 7.0) * strength
        shade += np.tanh(d / r.uniform(30, 140)) * amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r.uniform(250, 700) ** 2))
    noise = r.normal(0, 1.6, (h, w)).astype(np.float32)
    return shade + noise


def facets(w, h, n=420, seed=5):
    """Papel arrugado: facetas (Voronoi) con su propio plano de luz y pliegues finos en los bordes."""
    r = np.random.default_rng(seed)
    pts = np.stack([r.uniform(-60, w + 60, n), r.uniform(-60, h + 60, n)], 1).astype(np.float32)
    light = r.normal(0, 4.0, n).astype(np.float32)
    gx = r.normal(0, 0.045, n).astype(np.float32)
    gy = r.normal(0, 0.045, n).astype(np.float32)
    shade = np.zeros((h, w), np.float32)
    edge = np.zeros((h, w), np.float32)
    xs = np.arange(w, dtype=np.float32)
    for y0 in range(0, h, 64):
        ys = np.arange(y0, min(h, y0 + 64), dtype=np.float32)
        X, Y = np.meshgrid(xs, ys)
        d = (X[..., None] - pts[:, 0]) ** 2 + (Y[..., None] - pts[:, 1]) ** 2
        idx = np.argsort(d, axis=-1)[..., :2]
        d1 = np.take_along_axis(d, idx[..., :1], -1)[..., 0]
        d2 = np.take_along_axis(d, idx[..., 1:2], -1)[..., 0]
        k = idx[..., 0]
        shade[y0:y0 + len(ys)] = light[k] + gx[k] * (X - pts[k, 0]) + gy[k] * (Y - pts[k, 1])
        gap = np.sqrt(d2) - np.sqrt(d1)
        edge[y0:y0 + len(ys)] = np.exp(-gap / 1.4)
    s8 = Image.fromarray(np.clip(shade * 4 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    shade = (np.asarray(s8, np.float32) - 128) / 4
    return shade - edge * 7 + r.normal(0, 1.6, (h, w)).astype(np.float32)


def folds(w, h, n=520, seed=9):
    """Papel arrugado de verdad: mapa de alturas con dobleces locales (líneas de pliegue con ventana
    gaussiana) iluminado de lado. Devuelve un sombreado aditivo en niveles de gris."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    hgt = np.zeros((h, w), np.float32)
    for _ in range(n):
        cx, cy = r.uniform(-100, w + 100), r.uniform(-100, h + 100)
        ang = r.uniform(0, math.pi)
        nx, ny = math.cos(ang), math.sin(ang)
        d = (xx - cx) * nx + (yy - cy) * ny
        along = -(xx - cx) * ny + (yy - cy) * nx
        L = r.uniform(25, 110)           # largo del pliegue
        Wd = r.uniform(40, 140)          # alcance a los lados
        win = np.exp(-(along / L) ** 2 - (d / Wd) ** 2)
        amp = r.uniform(4, 13) * (1 if r.random() < 0.5 else -1)
        hgt += amp * np.abs(np.tanh(d / r.uniform(6, 18))) * win
    gy, gx = np.gradient(hgt)
    lx, ly, lz = -0.55, -0.65, 0.52      # luz desde arriba a la izquierda
    nz = 1.0 / np.sqrt(gx ** 2 + gy ** 2 + 1)
    shade = (-gx * lx - gy * ly + lz) * nz
    shade = (shade - shade.mean()) * 46
    return shade + r.normal(0, 1.4, (h, w)).astype(np.float32)


def paper_grid(path, w=1080, h=1920):
    base = np.ones((h, w, 3), np.float32) * np.array(PAPER, np.float32)
    s = folds(w, h) + crumple(w, h, 0.25)
    base += s[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    step = 54
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(120, 140, 170, 70), width=2)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(120, 140, 170, 70), width=2)
    # el sombreado también oscurece las líneas en los pliegues
    img = Image.fromarray(np.clip(np.asarray(img, np.float32) + s[..., None] * 0.6, 0, 255).astype(np.uint8))
    img.save(path, quality=90)


def paper_tile(path, n=256):
    a = np.ones((n, n, 3), np.float32) * np.array((246, 243, 236), np.float32)
    a += rng.normal(0, 3.0, (n, n, 1)).astype(np.float32)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path)


def cheese_bw(src, path):
    im = Image.open(src).convert("L")
    im = ImageOps.autocontrast(im, cutoff=1)
    a = np.asarray(im, np.float32)
    a = (a - 128) * 1.18 + 128 + rng.normal(0, 6, a.shape)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB").save(path, quality=90)


def last_frame_note():
    pass


STRAWBERRY = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 330" width="300" height="330">
  <defs>
    <pattern id="dots" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(20)">
      <rect width="12" height="12" fill="{RED}"/>
      <circle cx="6" cy="6" r="2.6" fill="#b3120c"/>
    </pattern>
  </defs>
  <g stroke-linejoin="round" stroke-linecap="round">
    <!-- borde de sticker blanco -->
    <path d="M150 312 C78 286 26 214 34 142 C40 98 82 78 150 86 C218 78 260 98 266 142 C274 214 222 286 150 312 Z" fill="#fff" stroke="#fff" stroke-width="34"/>
    <path d="M92 70 L120 38 L150 66 L180 34 L210 70 L184 92 L150 84 L116 92 Z" fill="#fff" stroke="#fff" stroke-width="34"/>
    <!-- cuerpo -->
    <path d="M150 312 C78 286 26 214 34 142 C40 98 82 78 150 86 C218 78 260 98 266 142 C274 214 222 286 150 312 Z" fill="url(#dots)" stroke="{INK}" stroke-width="7"/>
    <!-- semillas -->
    <g fill="#F5C400" stroke="{INK}" stroke-width="3">
      <ellipse cx="98" cy="140" rx="6" ry="10" transform="rotate(-20 98 140)"/>
      <ellipse cx="150" cy="128" rx="6" ry="10"/>
      <ellipse cx="202" cy="140" rx="6" ry="10" transform="rotate(20 202 140)"/>
      <ellipse cx="80" cy="196" rx="6" ry="10" transform="rotate(-25 80 196)"/>
      <ellipse cx="126" cy="184" rx="6" ry="10" transform="rotate(-8 126 184)"/>
      <ellipse cx="176" cy="184" rx="6" ry="10" transform="rotate(8 176 184)"/>
      <ellipse cx="222" cy="196" rx="6" ry="10" transform="rotate(25 222 196)"/>
      <ellipse cx="112" cy="240" rx="6" ry="10" transform="rotate(-18 112 240)"/>
      <ellipse cx="152" cy="236" rx="6" ry="10"/>
      <ellipse cx="192" cy="240" rx="6" ry="10" transform="rotate(18 192 240)"/>
      <ellipse cx="150" cy="282" rx="5" ry="9"/>
    </g>
    <!-- hojas -->
    <path d="M92 70 L120 38 L150 66 L180 34 L210 70 L184 92 L150 84 L116 92 Z" fill="#1f9d55" stroke="{INK}" stroke-width="7"/>
    <path d="M150 66 L152 18" stroke="{INK}" stroke-width="8" fill="none"/>
    <!-- brillo -->
    <path d="M78 130 C80 112 92 102 108 98" stroke="#fff" stroke-width="9" fill="none" opacity=".85"/>
  </g>
</svg>
"""

BOOKS = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 260" width="340" height="260">
  <defs>
    <pattern id="ht" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
      <rect width="9" height="9" fill="#fff"/>
      <circle cx="4.5" cy="4.5" r="3" fill="{COBALT}"/>
    </pattern>
    <pattern id="ht2" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
      <rect width="9" height="9" fill="{COBALT}"/>
      <circle cx="4.5" cy="4.5" r="2" fill="#fff"/>
    </pattern>
  </defs>
  <g stroke="{COBALT}" stroke-width="6" stroke-linejoin="round">
    <g stroke="#fff" stroke-width="30" fill="#fff">
      <rect x="40" y="168" width="270" height="62" rx="6"/>
      <rect x="58" y="106" width="236" height="62" rx="6" transform="rotate(-4 176 137)"/>
      <rect x="30" y="46" width="250" height="60" rx="6" transform="rotate(3 155 76)"/>
    </g>
    <rect x="40" y="168" width="270" height="62" rx="6" fill="url(#ht)"/>
    <rect x="40" y="168" width="38" height="62" fill="{COBALT}"/>
    <rect x="58" y="106" width="236" height="62" rx="6" fill="url(#ht2)" transform="rotate(-4 176 137)"/>
    <rect x="30" y="46" width="250" height="60" rx="6" fill="url(#ht)" transform="rotate(3 155 76)"/>
    <rect x="232" y="46" width="30" height="60" fill="{COBALT}" transform="rotate(3 155 76)"/>
  </g>
</svg>
"""

HAT = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 120" width="220" height="120">
  <g fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">
    <path class="draw" d="M14 88 C40 104 180 104 206 84"/>
    <path class="draw" d="M30 84 C34 60 44 30 70 34 C88 36 96 50 110 50 C124 50 132 36 150 34 C176 30 186 60 190 84"/>
    <path class="draw" d="M62 64 C90 72 130 72 158 64"/>
  </g>
</svg>
"""


def main():
    paper_grid(f"{OUT}/paper_grid.jpg")
    paper_tile(f"{OUT}/paper_tile.png")
    cheese_bw(f"{OUT}/cheese_36.jpg", f"{OUT}/cheese_36_bw.jpg")
    open(f"{OUT}/fresa.svg", "w").write(STRAWBERRY)
    open(f"{OUT}/libros.svg", "w").write(BOOKS)
    open(f"{OUT}/sombrero.svg", "w").write(HAT)
    print("ok", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
