"""Builds docs/research/stratagems/fonts/atlas-han-600.woff2.

A subset of Noto Serif JP SemiBold (SIL OFL 1.1) holding only the glyphs the
Stratagems Atlas sets in its display face: the 36 stratagem names, the six
chapter names and numerals, and 三十六計. Everything else on the page uses the
reader's own fonts, so this file stays near 30 KB.

    pip install fonttools brotli
    python3 site-redesign/tools/build_stratagems_font.py path/to/NotoSerifJP-SemiBold.ttf

The source font is not committed. It is available from Google Fonts
(https://fonts.google.com/noto/specimen/Noto+Serif+JP) or the npm package
@expo-google-fonts/noto-serif-jp (600SemiBold/NotoSerifJP_600SemiBold.ttf).
It also writes fonts/atlas-han-600.txt, the list of glyphs in the subset. Re-run
this script whenever a stratagem name or chapter label changes;
tests/stratagems-atlas.test.mjs fails if a display glyph is missing.
"""
import re
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs/research/stratagems"
OUT = PAGE / "fonts/atlas-han-600.woff2"
FAMILY = "Jinn Atlas Han"


def display_text():
    data = (PAGE / "stratagems.js").read_text(encoding="utf-8")
    i18n = (PAGE / "i18n.js").read_text(encoding="utf-8")
    names = re.findall(r'^\s*"?name"?:\s*"([^"]+)"', data, re.M)
    if len(names) != 36:
        sys.exit(f"expected 36 stratagem names, found {len(names)}")
    block = i18n[i18n.index("const chapterLabels"):i18n.index("function chapterIndexOf")]
    chapters = re.findall(r'(?:num|name|short):\s*"([^"]+)"', block)
    numerals = re.search(r"chapterNumerals = \[([^\]]+)\]", i18n).group(1)
    text = "".join(names + chapters) + numerals + "三十六計"
    return "".join(sorted({c for c in text if ord(c) > 0x2E7F}))


def main(source):
    glyphs = display_text()
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["kern", "palt", "vert", "vrt2"]
    options.hinting = False
    options.desubroutinize = True
    options.name_IDs = [0, 1, 2, 4, 6, 13, 14]
    font = TTFont(source)
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=glyphs)
    subsetter.subset(font)
    for record in font["name"].names:
        if record.nameID in (1, 4):
            record.string = FAMILY
        elif record.nameID == 6:
            record.string = FAMILY.replace(" ", "")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(OUT), options)
    # The glyph list lets tests/stratagems-atlas.test.mjs check coverage without parsing WOFF2.
    OUT.with_suffix(".txt").write_text(glyphs + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(glyphs)} glyphs, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
