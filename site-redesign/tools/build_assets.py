"""Derive the optimised top-page assets from the originals already in docs/.

Run from the repository root:  python3 site-redesign/tools/build_assets.py
Requires Pillow with WebP support. Originals are never modified.
"""
from pathlib import Path
from PIL import Image, ImageOps

DOCS = Path(__file__).resolve().parents[2] / "docs"
OUT = DOCS / "assets" / "img"
OUT.mkdir(parents=True, exist_ok=True)
PAPER = (236, 232, 223)
INK = (8, 10, 13)


def cover(im, ratio):
    """Centre-crop to the given width/height ratio."""
    w, h = im.size
    if w / h > ratio:
        nw = round(h * ratio)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = round(w / ratio)
    return im.crop((0, 0, w, nh))  # keep the top: UI captures read from the top


def variants(src, name, widths, ratio=16 / 9, quality=78):
    im = Image.open(DOCS / src).convert("RGB")
    im = cover(im, ratio)
    for w in widths:
        out = im.resize((w, round(w / ratio)), Image.LANCZOS)
        out.save(OUT / f"{name}-{w}.webp", "WEBP", quality=quality, method=6)


# Project media (16:9)
variants("research/source-of-thought/screenshots/web-v1/battle.jpg", "sot-battle", [640, 960, 1280])
variants("kunizukuri/images/world.webp", "kunizukuri-world", [480, 960])
variants("images/mandalizm-hero.webp", "mandalizm", [480, 960])
variants("images/jinnsp-library.png", "jinnsp", [480, 960])

# Brand mark: the ink cherub, recoloured to paper for dark surfaces.
logo = Image.open(DOCS / "images/logo.png").convert("RGBA")
alpha = logo.getchannel("A")
light = Image.new("RGBA", logo.size, PAPER + (255,))
light.putalpha(alpha)
for size in (96, 192):
    light.resize((size, size), Image.LANCZOS).save(OUT / f"jinn-mark-{size}.webp", "WEBP", quality=82, method=6)
    light.resize((size, size), Image.LANCZOS).save(OUT / f"jinn-mark-{size}.png", optimize=True)

# Icons: ink mark on a paper disc so it reads on light and dark browser chrome.
def icon(size):
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    disc = Image.new("L", (size * 4, size * 4), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(disc).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    disc = disc.resize((size, size), Image.LANCZOS)
    paper = Image.new("RGBA", (size, size), PAPER + (255,))
    canvas.paste(paper, (0, 0), disc)
    inner = round(size * 0.92)
    mark = Image.new("RGBA", logo.size, INK + (255,))
    mark.putalpha(alpha)
    mark = mark.resize((inner, inner), Image.LANCZOS)
    off = (size - inner) // 2
    canvas.alpha_composite(mark, (off, off))
    return canvas

icon(180).save(OUT / "apple-touch-icon.png", optimize=True)
icon(32).save(OUT / "icon-32.png", optimize=True)
icon(48).save(DOCS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("assets written to", OUT)

# Square logo for structured data (Organization.logo).
icon(512).save(OUT / "icon-512.png", optimize=True)
