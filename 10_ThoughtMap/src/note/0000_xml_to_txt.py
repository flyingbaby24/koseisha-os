from pathlib import Path
import re
import xml.etree.ElementTree as ET
from html import unescape

from bs4 import BeautifulSoup


BASE_DIR = Path(r"D:\ThoughtMap")

INPUT_XML = BASE_DIR / "input" / "note-flying_baby-1.xml"
OUTPUT_DIR = BASE_DIR / "notes"

MIN_TEXT_LENGTH = 50


def safe_filename(name):
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name)

    if not name:
        name = "untitled"

    return name[:80]


def clean_text_from_html(html):

    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "img", "figure", "figcaption"]):
        tag.decompose()

    text = soup.get_text("\n")

    text = unescape(text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    text = "\n".join(
        line.strip()
        for line in text.splitlines()
    )

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def main():

    if not INPUT_XML.exists():
        print(f"XML file not found: {INPUT_XML}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "wp": "http://wordpress.org/export/1.2/",
    }

    tree = ET.parse(INPUT_XML)
    root = tree.getroot()

    items = root.findall(".//item")

    exported = 0
    skipped = 0

    for item in items:

        title = item.findtext("title", default="untitled")

        content = item.find("content:encoded", ns)

        if content is None:
            skipped += 1
            continue

        html = content.text or ""

        body = clean_text_from_html(html)

        if len(body) < MIN_TEXT_LENGTH:
            skipped += 1
            continue

        title_safe = safe_filename(title)

        link = item.findtext("link", default="")

        filename = f"{exported + 1:04d}_{title_safe}.txt"

        output_path = OUTPUT_DIR / filename

        output_text = (
            f"TITLE: {title}\n"
            f"URL: {link}\n\n"
            f"{body}\n"
        )

        output_path.write_text(
            output_text,
            encoding="utf-8"
        )

        exported += 1

    print()
    print("=== DONE ===")
    print("Items    :", len(items))
    print("Exported :", exported)
    print("Skipped  :", skipped)
    print("Output   :", OUTPUT_DIR)


if __name__ == "__main__":
    main()