from pathlib import Path

import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
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

print("2Dマップ化中...")
reducer = UMAP(
    n_neighbors=10,
    min_dist=0.2,
    metric="cosine",
    random_state=42
)

points = reducer.fit_transform(embeddings)

plt.figure(figsize=(12, 9))
plt.scatter(points[:, 0], points[:, 1])

for i, title in enumerate(titles):
    plt.text(points[i, 0], points[i, 1], str(i + 1), fontsize=8)

plt.title("ThoughtMap Lyrics Map")
plt.xlabel("Axis 1")
plt.ylabel("Axis 2")
plt.tight_layout()

map_path = output_dir / "lyrics_map.png"
plt.savefig(map_path, dpi=200)

print(f"マップを保存しました: {map_path}")

# 番号と曲名の対応表を保存
index_path = output_dir / "lyrics_index.txt"

with open(index_path, "w", encoding="utf-8") as f:
    for i, title in enumerate(titles):
        f.write(f"{i + 1}: {title}\n")

print(f"対応表を保存しました: {index_path}")