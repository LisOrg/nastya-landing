#!/usr/bin/env python3
"""Апскейл PNG-вырезов (RGBA) через RealESRGAN x4. Результат — отдельные *-upscaled.png."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

# basicsr 1.4.x + torchvision 0.26+
import torchvision.transforms.functional as F

_mock = types.ModuleType("torchvision.transforms.functional_tensor")
_mock.rgb_to_grayscale = F.rgb_to_grayscale
sys.modules["torchvision.transforms.functional_tensor"] = _mock

from basicsr.archs.rrdbnet_arch import RRDBNet  # noqa: E402
from realesrgan import RealESRGANer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "img"
WEIGHTS = ROOT / "weights" / "RealESRGAN_x4plus.pth"
SCALE = 4
TILE = 400

SOURCES = [
    IMG / "source-teacher-2-cutout.png",
    IMG / "source-psyxo-cutout.png",
    IMG / "шапка-вырез.png",
]


def out_path(src: Path) -> Path:
    return src.with_name(f"{src.stem}-upscaled{src.suffix}")


def build_upsampler() -> RealESRGANer:
    model = RRDBNet(
        num_in_ch=3,
        num_out_ch=3,
        num_feat=64,
        num_block=23,
        num_grow_ch=32,
        scale=SCALE,
    )
    return RealESRGANer(
        scale=SCALE,
        model_path=str(WEIGHTS),
        model=model,
        tile=TILE,
        tile_pad=12,
        pre_pad=0,
        half=False,
    )


def upscale_rgba(im: Image.Image, upsampler: RealESRGANer) -> Image.Image:
    im = im.convert("RGBA")
    r, g, b, a = im.split()
    rgb = Image.merge("RGB", (r, g, b))

    # Нейтральный фон — меньше артефактов на волосах и краях
    bg = Image.new("RGB", im.size, (128, 128, 128))
    bg.paste(rgb, mask=a)
    bgr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)

    enhanced, _ = upsampler.enhance(bgr, outscale=SCALE)
    out_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    ow, oh = out_rgb.shape[1], out_rgb.shape[0]

    out_a = a.resize((ow, oh), Image.Resampling.LANCZOS)
    out_a = out_a.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))

    result = Image.fromarray(out_rgb).convert("RGBA")
    result.putalpha(out_a)
    return result


def main() -> None:
    upsampler = build_upsampler()
    for src in SOURCES:
        if not src.is_file():
            raise FileNotFoundError(src)
        dst = out_path(src)
        print(f"Upscaling {src.name} …")
        result = upscale_rgba(Image.open(src), upsampler)
        result.save(dst, "PNG", optimize=True)
        print(f"  -> {dst.name}  {im_size_str(src)} -> {result.size[0]}x{result.size[1]}")


def im_size_str(path: Path) -> str:
    with Image.open(path) as im:
        w, h = im.size
    return f"{w}x{h}"


if __name__ == "__main__":
    main()
