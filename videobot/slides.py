"""Renders clean slide images and a thumbnail with Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import config

FONT_CANDIDATES = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"],
    "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono.ttf"],
}

BG_TOP = (14, 18, 28)
BG_BOTTOM = (24, 32, 52)
INK = (236, 240, 247)
MUTE = (150, 162, 184)
CODE_BG = (8, 11, 18)


def font(kind, size):
    for p in FONT_CANDIDATES[kind]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def background(w, h):
    img = Image.new("RGB", (w, h), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)))
    return img


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=f) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_slide(slide, index, total, path):
    W, H = config.size
    vertical = H > W
    s = W / 1920 if not vertical else W / 1080
    img = background(W, H)
    d = ImageDraw.Draw(img)
    accent = hex_rgb(config.accent)
    pad = int((110 if not vertical else 80) * s)
    max_w = W - 2 * pad

    # accent bar + slide counter
    d.rectangle([0, 0, W, int(10 * s)], fill=accent)
    d.text((pad, int(50 * s)), config.channel_name.upper(), font=font("bold", int(26 * s)), fill=accent)
    counter = f"{index + 1}/{total}"
    cf = font("regular", int(26 * s))
    d.text((W - pad - d.textlength(counter, font=cf), int(50 * s)), counter, font=cf, fill=MUTE)

    y = int((150 if not vertical else 260) * s)
    hf = font("bold", int((78 if not vertical else 84) * s))
    for line in wrap(d, slide["heading"], hf, max_w)[:3]:
        d.text((pad, y), line, font=hf, fill=INK)
        y += int(hf.size * 1.18)
    y += int(30 * s)

    bf = font("regular", int((44 if not vertical else 50) * s))
    for b in slide.get("bullets", []):
        lines = wrap(d, b, bf, max_w - int(60 * s))
        r = int(9 * s)
        cy = y + bf.size // 2 + int(4 * s)
        d.ellipse([pad, cy - r, pad + 2 * r, cy + r], fill=accent)
        for line in lines[:2]:
            d.text((pad + int(50 * s), y), line, font=bf, fill=INK)
            y += int(bf.size * 1.3)
        y += int(14 * s)

    code = (slide.get("code") or "").strip("\n")
    if code:
        mf = font("mono", int((32 if not vertical else 34) * s))
        lines = code.splitlines()[:10]
        line_h = int(mf.size * 1.4)
        box_h = line_h * len(lines) + int(50 * s)
        top = y + int(30 * s)
        d.rounded_rectangle([pad, top, W - pad, top + box_h], radius=int(18 * s), fill=CODE_BG, outline=(45, 55, 80), width=2)
        cy = top + int(25 * s)
        for line in lines:
            while line and d.textlength(line, font=mf) > max_w - int(60 * s):
                line = line[:-2] + "…"
            d.text((pad + int(30 * s), cy), line, font=mf, fill=(160, 230, 170))
            cy += line_h

    img.save(path, "PNG")
    return path


def render_thumbnail(text, path):
    W, H = 1280, 720
    img = background(W, H)
    d = ImageDraw.Draw(img)
    accent = hex_rgb(config.accent)
    d.rectangle([0, H - 28, W, H], fill=accent)
    d.rectangle([60, 70, 80, H - 110], fill=accent)
    size = 120
    while size > 50:
        f = font("bold", size)
        lines = wrap(d, text.upper(), f, W - 200)
        if len(lines) <= 3:
            break
        size -= 8
    y = (H - len(lines) * int(size * 1.15)) // 2 - 20
    for line in lines:
        d.text((120, y), line, font=f, fill=INK, stroke_width=3, stroke_fill=(0, 0, 0))
        y += int(size * 1.15)
    d.text((120, H - 95), config.channel_name, font=font("bold", 34), fill=MUTE)
    img.save(path, "JPEG", quality=90)
    return path
