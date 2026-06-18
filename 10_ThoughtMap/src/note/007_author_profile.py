from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# 日本語対応
plt.rcParams["font.family"] = "Yu Gothic"

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = (
    BASE_DIR
    / "output"
    / "notes"
    / "notes_clusters.csv"
)

output_dir = BASE_DIR / "output" / "notes"

df = pd.read_csv(csv_path)

cluster_counts = (
    df["cluster"]
    .value_counts()
    .sort_index()
)

print(cluster_counts)

plt.figure(figsize=(10, 6))

bars = plt.bar(
    [f"Cluster {i}" for i in cluster_counts.index],
    cluster_counts.values
)

for bar in bars:
    height = bar.get_height()

    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        str(int(height)),
        ha="center",
        va="bottom"
    )

plt.title("Author Thought Profile (Notes)")
plt.xlabel("Thought Cluster")
plt.ylabel("Number of Notes")

plt.tight_layout()

out_path = output_dir / "notes_author_profile.png"

plt.savefig(
    out_path,
    dpi=300
)

print(f"保存: {out_path}")