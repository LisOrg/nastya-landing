#!/usr/bin/env python3
"""Склейка hero-фона и выреза: выравнивание left/center, плавный переход по краям."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "img"

FEATHER_FRAC = 0.03
EDGE_BLUR_RADIUS = 1.0


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def feather_alpha_horizontal(
    alpha: Image.Image,
    fade_frac: float,
    *,
    left: bool = False,
    right: bool = True,
) -> Image.Image:
    w, h = alpha.size
    fade_w = max(1, int(round(w * fade_frac)))
    out = alpha.copy()
    px = out.load()
    for x in range(w):
        keep = 1.0
        if left and x < fade_w:
            keep = min(keep, smoothstep(x / fade_w))
        if right and x >= w - fade_w:
            t = (x - (w - fade_w)) / fade_w
            keep = min(keep, 1.0 - smoothstep(t))
        if keep >= 1.0:
            continue
        for y in range(h):
            px[x, y] = int(px[x, y] * keep)
    return out


def trim_top_transparent(im: Image.Image, *, alpha_threshold: int = 10) -> Image.Image:
    """Убирает пустое пространство сверху, левый край холста сохраняется."""
    rgba = im.convert("RGBA")
    a = np.array(rgba.split()[-1])
    rows = np.where(a.max(axis=1) > alpha_threshold)[0]
    if rows.size == 0:
        return rgba
    top = int(rows[0])
    if top == 0:
        return rgba
    return rgba.crop((0, top, rgba.width, rgba.height))


def soften_edge_rgb(
    im: Image.Image,
    fade_frac: float,
    blur_radius: float,
    *,
    left: bool = False,
    right: bool = True,
) -> Image.Image:
    w, h = im.size
    fade_w = max(1, int(round(w * fade_frac)))
    out = im.copy()
    if left:
        edge = im.crop((0, 0, fade_w, h)).filter(ImageFilter.GaussianBlur(radius=blur_radius))
        out.paste(edge, (0, 0))
    if right:
        edge = im.crop((w - fade_w, 0, w, h)).filter(ImageFilter.GaussianBlur(radius=blur_radius))
        out.paste(edge, (w - fade_w, 0))
    return out


def merge(
    bg_path: Path,
    fg_path: Path,
    out_path: Path,
    *,
    align: str = "left",
    feather_frac: float = FEATHER_FRAC,
    edge_blur_radius: float = EDGE_BLUR_RADIUS,
) -> None:
    base = Image.open(bg_path).convert("RGBA")
    fg = trim_top_transparent(Image.open(fg_path))

    bw, bh = base.size
    scale = bh / fg.height
    nw = int(round(fg.width * scale))
    nh = bh
    fg = fg.resize((nw, nh), Image.Resampling.LANCZOS)

    if align == "center":
        px = max(0, (bw - nw) // 2)
        feather_left = feather_right = True
    elif align == "left":
        px = 0
        feather_left = False
        feather_right = True
    elif align == "right":
        px = max(0, bw - nw)
        feather_left = True
        feather_right = False
    else:
        raise ValueError(f"Unknown align: {align!r}")
    py = 0

    r, g, b, a = fg.split()
    a = feather_alpha_horizontal(
        a, feather_frac, left=feather_left, right=feather_right
    )
    rgb = soften_edge_rgb(
        Image.merge("RGB", (r, g, b)),
        feather_frac,
        edge_blur_radius,
        left=feather_left,
        right=feather_right,
    )
    fg = Image.merge("RGBA", (*rgb.split(), a))

    out = base.copy()
    out.alpha_composite(fg, dest=(px, py))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(out_path, "PNG", optimize=True)
    print(f"Saved: {out_path} ({out.size[0]}x{out.size[1]})")


def main() -> None:
    p = argparse.ArgumentParser(description="Склейка hero-фона и PNG-выреза")
    p.add_argument(
        "--bg",
        type=Path,
        default=IMG / "hero-chemistry-bg" / "chemistry-hero-bg-04-minimal-stack.png",
    )
    p.add_argument(
        "--fg",
        type=Path,
        default=IMG / "source-psyxo-cutout-upscaled.png",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=IMG / "hero-chemistry-bg-04-with-psyxo-feather3.png",
    )
    p.add_argument("--feather", type=float, default=FEATHER_FRAC)
    p.add_argument(
        "--align",
        choices=("left", "center", "right"),
        default="left",
        help="left / center / right — положение выреза по горизонтали",
    )
    args = p.parse_args()
    merge(args.bg, args.fg, args.out, align=args.align, feather_frac=args.feather)


if __name__ == "__main__":
    main()
