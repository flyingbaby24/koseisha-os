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

plt.figure(figsize=(14, 10))

# 作品点
plt.scatter(
    df["x"],
    df["y"],
    s=30,
    alpha=0.35
)

# クラスタ重心とラベル
for cluster_id in sorted(df["cluster"].unique()):
    cluster_df = df[df["cluster"] == cluster_id]

    center_x = cluster_df["x"].mean()
    center_y = cluster_df["y"].mean()

    label = labels.get(str(cluster_id), f"Cluster {cluster_id}")
    count = len(cluster_df)

    plt.scatter(
        center_x,
        center_y,
        s=700,
        alpha=0.85
    )

    plt.text(
        center_x,
        center_y,
        f"{label}\n{count}作品",
        fontsize=10,
        ha="center",
        va="center"
    )

plt.title("Jinn Project 思想大陸図")
plt.xlabel("Axis 1")
plt.ylabel("Axis 2")

plt.tight_layout()

out_path = output_dir / "thought_continent.png"
plt.savefig(out_path, dpi=300)

print(f"保存: {out_path}")