#!/usr/bin/env python3
"""
Сборка hero-фона: молочный #FBF1EA → градиент → размытый стол справа, поверх вырез.

Зависимости: Pillow.

Запуск из корня репозитория:
  python scripts/build_teacher_hero_background.py
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "img"

MILK = (251, 241, 234)
WIDTH = 2560
HEIGHT = 1920

# Градиент молочного в фото стола (доли ширины 0–1): слева полностью молочный → к концу плавно стол
GRADIENT_START_FRAC = 0.32
GRADIENT_END_FRAC = 0.78

BACKGROUND_SAMPLE_THRESHOLD = 40


def resize_cover_anchor_right(im: Image.Image, tw: int, th: int) -> Image.Image:
    iw, ih = im.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    im2 = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, nw - tw)
    top = max(0, (nh - th) // 2)
    return im2.crop((left, top, left + tw, top + th))


def horizontal_gradient_mask(width: int, height: int, x0: float, x1: float) -> Image.Image:
    """L-режим: 0 слева от перехода, 255 справа, плавный S-кривая между x0 и x1."""
    mask = Image.new("L", (width, height), 0)
    px = mask.load()
    for x in range(width):
        if x <= x0:
            alpha = 0
        elif x >= x1:
            alpha = 255
        else:
            t = (x - x0) / (x1 - x0)
            t = max(0.0, min(1.0, t))
            # smoothstep
            s = t * t * (3 - 2 * t)
            alpha = int(round(255 * s))
        for y in range(height):
            px[x, y] = alpha
    return mask


def edge_connected_dark_mask(rgb: Image.Image, threshold: int = BACKGROUND_SAMPLE_THRESHOLD) -> Image.Image:
    """
    Помечаем только тёмные пиксели, достижимые от края картинки (фон после вырезки),
    чтобы не тронуть чёрную одежду внутри силуета.
    """
    w, h = rgb.size
    px = rgb.load()
    reachable = Image.new("L", (w, h), 0)
    rpx = reachable.load()

    def dark(x: int, y: int) -> bool:
        r, g, b = px[x, y]
        return r < threshold and g < threshold and b < threshold

    dq: deque[tuple[int, int]] = deque()

    def try_seed(x: int, y: int) -> None:
        if dark(x, y):
            dq.append((x, y))

    for x in range(w):
        try_seed(x, 0)
        try_seed(x, h - 1)
    for y in range(h):
        try_seed(0, y)
        try_seed(w - 1, y)

    while dq:
        x, y = dq.popleft()
        if rpx[x, y]:
            continue
        if not dark(x, y):
            continue
        rpx[x, y] = 255
        if x > 0:
            dq.append((x - 1, y))
        if x + 1 < w:
            dq.append((x + 1, y))
        if y > 0:
            dq.append((x, y - 1))
        if y + 1 < h:
            dq.append((x, y + 1))

    return reachable


def cutout_black_bg_to_alpha(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    mask = edge_connected_dark_mask(rgb)
    out = rgb.convert("RGBA")
    alpha = Image.new("L", rgb.size, 255)
    # где фон — полная прозрачность (инвертируем: reachable = белый где фон)
    alpha_bytes = alpha.tobytes()
    mbytes = mask.tobytes()
    new_alpha = bytes(0 if mv else av for mv, av in zip(mbytes, alpha_bytes))
    out.putalpha(Image.frombytes("L", rgb.size, new_alpha))
    return out


def main() -> None:
    desk_path = IMG / "desk-blur-layer.png"
    cut_path = IMG / "source-teacher-cutout.png"
    out_path = IMG / "hero-bg-teacher-2560x1920.png"

    base = Image.new("RGB", (WIDTH, HEIGHT), MILK)

    desk = Image.open(desk_path).convert("RGB")
    desk = resize_cover_anchor_right(desk, WIDTH, HEIGHT)
    desk = desk.filter(ImageFilter.GaussianBlur(radius=11))

    x0 = int(WIDTH * GRADIENT_START_FRAC)
    x1 = int(WIDTH * GRADIENT_END_FRAC)
    grad = horizontal_gradient_mask(WIDTH, HEIGHT, x0, x1)
    desk_rgba = desk.convert("RGBA")
    desk_rgba.putalpha(grad)

    layered = Image.alpha_composite(base.convert("RGBA"), desk_rgba).convert("RGB")

    fg = cutout_black_bg_to_alpha(Image.open(cut_path))
    # высота человека относительно кадра
    target_h = int(HEIGHT * 0.82)
    scale = target_h / fg.height
    new_w = int(round(fg.width * scale))
    new_h = int(round(fg.height * scale))
    fg = fg.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # правее центра: центр модели немного правее середины канваса, низ к нижнему краю с небольшим отступом
    cx_canvas = WIDTH * 0.56
    bottom_margin = int(HEIGHT * 0.02)
    px = int(round(cx_canvas - fg.width / 2))
    py = HEIGHT - fg.height - bottom_margin

    layered_rgba = layered.convert("RGBA")
    layered_rgba.alpha_composite(fg, dest=(px, py))

    layered_rgba.convert("RGB").save(out_path, "PNG", optimize=True)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
