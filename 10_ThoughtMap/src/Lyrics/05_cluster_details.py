from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = BASE_DIR / "output" / "lyrics_clusters.csv"

df = pd.read_csv(csv_path)

for cluster_id in sorted(df["cluster"].unique()):

    print("\n")
    print("=" * 60)
    print(f"CLUSTER {cluster_id}")
    print("=" * 60)

    works = df[df["cluster"] == cluster_id]

    for title in works["title"]:
        print(title)