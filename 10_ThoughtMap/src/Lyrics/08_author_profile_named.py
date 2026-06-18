from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Yu Gothic"

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = BASE_DIR / "output" / "lyrics_clusters.csv"
labels_path = BASE_DIR / "output" / "cluster_labels.json"
output_dir = BASE_DIR / "output"

df = pd.read_csv(csv_path)

with open(labels_path, "r", encoding="utf-8") as f:
    labels = json.load(f)

cluster_counts = df["cluster"].value_counts().sort_index()

names = []
values = []

for cluster_id, count in cluster_counts.items():
    label = labels.get(str(cluster_id), f"Cluster {cluster_id}")
    names.append(label)
    values.append(count)

plt.figure(figsize=(12, 7))

bars = plt.bar(names, values)

for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        str(int(height)),
        ha="center",
        va="bottom"
    )

plt.title("Jinn Project 思想プロフィール")
plt.xlabel("思想属性")
plt.ylabel("作品数")
plt.xticks(rotation=30, ha="right")

plt.tight_layout()

out_path = output_dir / "author_profile_named.png"
plt.savefig(out_path, dpi=300)

print(f"保存: {out_path}")