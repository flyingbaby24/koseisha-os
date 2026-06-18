from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

csv_file = BASE_DIR / "gutendex_books" / "gutendex_results.csv"

df = pd.read_csv(csv_file)

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
    df.groupby("author")[score_cols]
      .mean()
      .round(4)
)

author_avg["books"] = df.groupby("author").size()

author_avg = author_avg.sort_values(
    "philosophy",
    ascending=False
)

print("\n=== AUTHOR AVERAGES ===\n")
print(author_avg)

out_csv = BASE_DIR / "gutendex_books" / "author_average.csv"
author_avg.to_csv(out_csv)

print(f"\nSaved: {out_csv}")