from pathlib import Path
import csv
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path("D:/ThoughtMap")

LYRICS_DIR = BASE_DIR / "notes"
GUTENDEX_DIR = BASE_DIR / "gutendex_books"
OUTPUT_DIR = BASE_DIR / "output" / "notes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

REMOVE_AUTHORS = {
    "Forster, John",
    "Shorter, Clement King",
    "Cruttwell, Charles Thomas",
    "Dill, Samuel",
    "Malham-Dembleby, John",
    "Joy, John C. (John Chrisentia)",
    "Renan, Ernest",
}

AUTHOR_MAP = {
    "Nietzsche, Friedrich Wilhelm": "Nietzsche",
    "Austen, Jane": "Austen",
    "Tolstoy, Leo, graf": "Tolstoy",
    "Dickens, Charles": "Dickens",
    "Darwin, Charles": "Darwin",
    "Plato": "Plato",
    "Thoreau, Henry David": "Thoreau",
    "Brontë, Charlotte": "Bronte",
    "Marcus Aurelius, Emperor of Rome": "Marcus Aurelius",
}

def canonical_author(author: str) -> str:
    author = str(author)
    if author in AUTHOR_MAP:
        return AUTHOR_MAP[author]
    if "," in author:
        return author.split(",")[0].strip()
    return author.strip()

def clean_gutenberg_text(text: str, max_chars: int = 120_000) -> str:
    start = text.find("*** START")
    end = text.find("*** END")
    if start != -1:
        text = text[start:]
    if end != -1:
        text = text[:end]
    return text[:max_chars].strip()

def load_lyrics():
    titles, texts = [], []
    for file in sorted(LYRICS_DIR.glob("*.txt")):
        text = file.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            titles.append(file.stem)
            texts.append(text)
    if not texts:
        raise RuntimeError("lyricsフォルダにtxtファイルがありません。")
    return titles, texts

def load_gutendex_books():
    csv_path = GUTENDEX_DIR / "gutendex_results.csv"
    if not csv_path.exists():
        raise RuntimeError(f"見つかりません: {csv_path}")

    df = pd.read_csv(csv_path)
    df = df[~df["author"].isin(REMOVE_AUTHORS)].copy()
    df["canonical_author"] = df["author"].apply(canonical_author)

    rows = []
    for _, row in df.iterrows():
        path = Path(row["text_path"])
        if not path.exists():
            # 相対パスだった場合の保険
            path = BASE_DIR / row["text_path"]

        if not path.exists():
            print(f"skip missing text: {row['text_path']}")
            continue

        text = clean_gutenberg_text(
            path.read_text(encoding="utf-8", errors="ignore")
        )

        if text:
            rows.append({
                "book_id": row["book_id"],
                "author": row["author"],
                "canonical_author": row["canonical_author"],
                "title": row["title"],
                "text": text,
            })

    if not rows:
        raise RuntimeError("Gutendex本文が読み込めませんでした。")

    return pd.DataFrame(rows)

def main():
    print("lyrics読み込み中...")
    lyric_titles, lyric_texts = load_lyrics()
    print(f"lyrics: {len(lyric_texts)}")

    print("Gutendex本文読み込み中...")
    books_df = load_gutendex_books()
    print(f"gutendex books: {len(books_df)}")

    print("モデル読み込み中...")
    model = SentenceTransformer(MODEL_NAME)

    print("lyrics embedding作成中...")
    lyric_embeddings = model.encode(lyric_texts, show_progress_bar=True)
    my_vector = np.mean(lyric_embeddings, axis=0, keepdims=True)

    print("Gutendex book embedding作成中...")
    book_embeddings = model.encode(
        books_df["text"].tolist(),
        show_progress_bar=True
    )

    # -----------------------------
    # Book similarity
    # -----------------------------
    print("作品単位の近似度計算中...")
    book_scores = cosine_similarity(my_vector, book_embeddings)[0]

    book_out = books_df[["book_id", "canonical_author", "author", "title"]].copy()
    book_out["similarity"] = book_scores
    book_out = book_out.sort_values("similarity", ascending=False)

    book_csv = OUTPUT_DIR / "gutendex_book_similarity_to_lyrics.csv"
    book_out.to_csv(book_csv, index=False, encoding="utf-8-sig")

    print("\n=== Closest Books ===")
    print(book_out[["canonical_author", "title", "similarity"]].head(20).to_string(index=False))

    # -----------------------------
    # Author similarity
    # -----------------------------
    print("\n作者平均embedding作成中...")
    author_rows = []

    for author, group in books_df.groupby("canonical_author"):
        idxs = group.index.tolist()
        # books_dfのindexが飛んでいる可能性があるので位置に変換
        positions = [books_df.index.get_loc(i) for i in idxs]
        author_vector = np.mean(book_embeddings[positions], axis=0, keepdims=True)
        sim = cosine_similarity(my_vector, author_vector)[0][0]

        author_rows.append({
            "author": author,
            "books": len(group),
            "similarity": sim,
        })

    author_out = pd.DataFrame(author_rows)
    author_out = author_out.sort_values("similarity", ascending=False)

    author_csv = OUTPUT_DIR / "gutendex_author_similarity_to_lyrics.csv"
    author_out.to_csv(author_csv, index=False, encoding="utf-8-sig")

    print("\n=== Closest Authors ===")
    print(author_out.head(20).to_string(index=False))

    print(f"\n保存しました:")
    print(book_csv)
    print(author_csv)

if __name__ == "__main__":
    main()
