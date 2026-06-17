from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer
from umap import UMAP
from sklearn.cluster import KMeans

BASE_DIR = Path(__file__).resolve().parent.parent

lyrics_dir = BASE_DIR / "lyrics"
output_dir = BASE_DIR / "output"

files = list(lyrics_dir.glob("*.txt"))

titles = []
texts = []

for file in files:
    text = file.read_text(
        encoding="utf-8",
        errors="ignore"
    ).strip()

    if text:
        titles.append(file.stem)
        texts.append(text)

print("モデル読み込み")

model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

print("ベクトル化")

embeddings = model.encode(
    texts,
    show_progress_bar=True
)

print("UMAP")

reducer = UMAP(
    n_neighbors=10,
    min_dist=0.2,
    metric="cosine",
    random_state=42
)

points = reducer.fit_transform(embeddings)

print("クラスタリング")

kmeans = KMeans(
    n_clusters=8,
    random_state=42,
    n_init=10
)

clusters = kmeans.fit_predict(embeddings)

df = pd.DataFrame(
    {
        "title": titles,
        "cluster": clusters,
        "x": points[:, 0],
        "y": points[:, 1]
    }
)

csv_path = output_dir / "lyrics_clusters.csv"

df.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig"
)

print(csv_path)
print("保存完了")
