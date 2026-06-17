from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


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

print("類似度計算中...")
sim_matrix = cosine_similarity(embeddings)

report_path = output_dir / "similarity_report.txt"

top_n = 5

with open(report_path, "w", encoding="utf-8") as f:
    for i, title in enumerate(titles):
        scores = sim_matrix[i]

        # 自分自身を除外
        ranked = np.argsort(scores)[::-1]
        ranked = [idx for idx in ranked if idx != i]

        f.write("=" * 60 + "\n")
        f.write(f"{i + 1}: {title}\n")
        f.write("近い作品 TOP5\n")

        for rank, idx in enumerate(ranked[:top_n], start=1):
            f.write(
                f"{rank}. {idx + 1}: {titles[idx]} "
                f"(similarity={scores[idx]:.4f})\n"
            )

        f.write("\n")

print(f"保存しました: {report_path}")
