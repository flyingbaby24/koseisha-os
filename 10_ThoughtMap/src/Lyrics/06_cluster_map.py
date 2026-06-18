from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from umap import UMAP


BASE_DIR = Path(__file__).resolve().parent.parent

lyrics_dir = BASE_DIR / "lyrics"
output_dir = BASE_DIR / "output"
output_dir.mkdir(parents=True, exist_ok=True)

files = list(lyrics_dir.glob("*.txt"))

titles = []
texts = []

for file in files:
    text = file.read_text(encoding="utf-8", errors="ignore").strip()
    if text:
        titles.append(file.stem)
        texts.append(text)

print(f"読み込み曲数: {len(texts)}")

if not texts:
    raise RuntimeError("lyricsフォルダにtxtファイルがありません。")

print("モデル読み込み中...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("ベクトル化中...")
embeddings = model.encode(texts, show_progress_bar=True)

cluster_count = 8

print(f"クラスタリング中... cluster_count={cluster_count}")
kmeans = KMeans(
    n_clusters=cluster_count,
    random_state=42,
    n_init="auto"
)

labels = kmeans.fit_predict(embeddings)

print("クラスタ中心を計算中...")
cluster_centers = []

for cluster_id in range(cluster_count):
    members = embeddings[labels == cluster_id]
    center = np.mean(members, axis=0)
    cluster_centers.append(center)

cluster_centers = np.array(cluster_centers)

print("クラスタマップ化中...")
reducer = UMAP(
    n_neighbors=3,
    min_dist=0.3,
    metric="cosine",
    random_state=42
)

cluster_points = reducer.fit_transform(cluster_centers)

plt.figure(figsize=(10, 8))
plt.scatter(cluster_points[:, 0], cluster_points[:, 1], s=500)

for cluster_id in range(cluster_count):
    x = cluster_points[cluster_id, 0]
    y = cluster_points[cluster_id, 1]

    count = int(np.sum(labels == cluster_id))

    plt.text(
        x,
        y,
        f"Cluster {cluster_id}\n{count} works",
        fontsize=10,
        ha="center",
        va="center"
    )

plt.title("ThoughtMap Cluster Map")
plt.xlabel("Axis 1")
plt.ylabel("Axis 2")
plt.tight_layout()

map_path = output_dir / "cluster_map.png"
plt.savefig(map_path, dpi=200)

print(f"クラスタマップを保存しました: {map_path}")

report_path = output_dir / "cluster_distance_report.txt"

print("クラスタ距離レポート作成中...")

with open(report_path, "w", encoding="utf-8") as f:
    for i in range(cluster_count):
        f.write("=" * 60 + "\n")
        f.write(f"Cluster {i} に近いCluster\n")

        distances = []

        for j in range(cluster_count):
            if i == j:
                continue

            a = cluster_centers[i]
            b = cluster_centers[j]

            cosine = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            distance = 1 - cosine

            distances.append((j, distance))

        distances.sort(key=lambda x: x[1])

        for j, distance in distances:
            f.write(f"Cluster {j}: distance={distance:.4f}\n")

        f.write("\n")

print(f"クラスタ距離レポートを保存しました: {report_path}")