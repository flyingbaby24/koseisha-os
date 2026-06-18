from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_CSV = BASE_DIR / "gutendex_books" / "gutendex_results.csv"
OUTPUT_CSV = BASE_DIR / "gutendex_books" / "author_average_clean.csv"

df = pd.read_csv(INPUT_CSV)

# -----------------------------
# 統合
# -----------------------------
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

# -----------------------------
# 除外
# -----------------------------
REMOVE_AUTHORS = {
    "Forster, John",
    "Shorter, Clement King",
    "Cruttwell, Charles Thomas",
    "Dill, Samuel",
    "Malham-Dembleby, John",
    "Joy, John C. (John Chrisentia)",
    "Renan, Ernest",
}

df = df[~df["author"].isin(REMOVE_AUTHORS)].copy()

# -----------------------------
# 正規化
# -----------------------------
def canonical_author(author):
    if author in AUTHOR_MAP:
        return AUTHOR_MAP[author]

    if "," in author:
        return author.split(",")[0].strip()

    return author


df["canonical_author"] = df["author"].fillna("").apply(canonical_author)

score_cols = [
    "philosophy",
    "society",
    "religion",
    "love",
    "death",
    "nature",
    "war",
    "identity",
]

author_avg = (
    df.groupby("canonical_author")[score_cols]
      .mean()
      .round(4)
)

author_avg["books"] = (
    df.groupby("canonical_author")
      .size()
)

author_avg = author_avg.sort_values(
    ["books", "philosophy"],
    ascending=[False, False]
)

print("\n=== CLEAN AUTHOR AVERAGES ===\n")
print(author_avg)

author_avg.to_csv(OUTPUT_CSV)

print(f"\nSaved: {OUTPUT_CSV}")