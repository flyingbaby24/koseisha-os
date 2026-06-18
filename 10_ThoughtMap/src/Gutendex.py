from pathlib import Path
import re
import csv
import requests
import matplotlib.pyplot as plt

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "gutendex_books"
OUT.mkdir(exist_ok=True)

RESULT_CSV = OUT / "gutendex_results.csv"


CATEGORIES = {
    "philosophy": "truth, meaning, ethics, existence, consciousness, wisdom",
    "society": "class, family, reputation, marriage, manners, wealth, status, community, social order",
    "religion": "god, faith, sin, salvation, prayer, sacred, soul",
    "love": "romance, affection, marriage, desire, longing, heartbreak",
    "death": "death, grief, mortality, loss, afterlife, decay",
    "nature": "forest, sea, sky, animals, seasons, earth, wilderness",
    "war": "battle, army, soldiers, weapons, invasion, military, battlefield, war",
    "identity": "self, name, memory, personality, inner life, transformation",
}


def safe_name(name):
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name.strip("_")[:100]


def search_books(query, limit=10):
    url = "https://gutendex.com/books"
    r = requests.get(
        url,
        params={"search": query, "languages": "en"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["results"][:limit]


def get_author_name(book):
    if book.get("authors"):
        return book["authors"][0]["name"]
    return "Unknown_Author"


def get_text_url(book):
    formats = book.get("formats", {})

    for k, v in formats.items():
        if k.startswith("text/plain") and v.endswith(".txt"):
            return v

    for k, v in formats.items():
        if k.startswith("text/plain"):
            return v

    return None


def make_book_folder(book):
    author = safe_name(get_author_name(book))
    folder = OUT / author
    graph_folder = folder / "graphs"

    folder.mkdir(parents=True, exist_ok=True)
    graph_folder.mkdir(parents=True, exist_ok=True)

    return folder, graph_folder


def download_text(book):
    text_url = get_text_url(book)
    if not text_url:
        return None, None

    r = requests.get(text_url, timeout=30)
    r.raise_for_status()

    folder, graph_folder = make_book_folder(book)

    title = safe_name(book["title"])
    path = folder / f"{book['id']}_{title}.txt"
    path.write_text(r.text, encoding="utf-8", errors="ignore")

    return path, graph_folder


def clean_text(text, max_chars=120_000):
    start = text.find("*** START")
    end = text.find("*** END")

    if start != -1:
        text = text[start:]

    if end != -1:
        text = text[:end]

    return text[:max_chars]


def score_text(text, model, category_embeddings):
    emb = model.encode([text])
    sims = cosine_similarity(emb, category_embeddings)[0]

    scores = sims.clip(min=0)
    total = scores.sum()

    if total:
        scores = scores / total

    return scores


def save_csv_row(row):
    exists = RESULT_CSV.exists()

    with RESULT_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "book_id",
                "author",
                "title",
                "text_path",
                "graph_path",
                *CATEGORIES.keys(),
            ],
        )

        if not exists:
            writer.writeheader()

        writer.writerow(row)


def main():
    query = input("Search author/title: ").strip()
    books = search_books(query, limit=10)

    print("\nFound:")
    for i, b in enumerate(books):
        author = get_author_name(b)
        print(f"{i}: {b['title']} / {author}")

    selected = input("\nAnalyze which indexes? e.g. 0,1,2 : ").strip()
    indexes = [int(x) for x in selected.split(",") if x.strip().isdigit()]

    if not indexes:
        print("No indexes selected.")
        return

    print("\nLoading model...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    category_names = list(CATEGORIES.keys())
    category_texts = list(CATEGORIES.values())
    category_embeddings = model.encode(category_texts)

    for i in indexes:
        book = books[i]

        path, graph_folder = download_text(book)
        if not path:
            print(f"Skipped: {book['title']} no plain text found.")
            continue

        print(f"\nDownloaded: {book['title']}")

        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = clean_text(raw)

        scores = score_text(text, model, category_embeddings)

        print(f"\n=== {book['title']} ===")
        for name, score in sorted(zip(category_names, scores), key=lambda x: x[1], reverse=True):
            print(f"{name:12s}: {score:.3f}")

        plt.figure(figsize=(8, 5))
        plt.bar(category_names, scores)
        plt.title(f"ThoughtMap: {book['title'][:40]}")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        img_path = graph_folder / f"{path.stem}_thoughtmap.png"
        plt.savefig(img_path, dpi=160)
        plt.close()

        row = {
            "book_id": book["id"],
            "author": get_author_name(book),
            "title": book["title"],
            "text_path": str(path),
            "graph_path": str(img_path),
        }

        for name, score in zip(category_names, scores):
            row[name] = round(float(score), 6)

        save_csv_row(row)

        print(f"Saved graph: {img_path}")
        print(f"Saved CSV row: {RESULT_CSV}")


if __name__ == "__main__":
    main()