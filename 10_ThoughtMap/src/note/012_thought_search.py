from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent.parent

notes_dir = BASE_DIR / "notes"

files = list(notes_dir.glob("*.txt"))

titles = []
texts = []

for file in files:
    text = file.read_text(encoding="utf-8", errors="ignore").strip()
    if text:
        titles.append(file.stem)
        texts.append(text)

print(f"読み込みnote数: {len(texts)}")

if not texts:
    raise RuntimeError("notesフォルダにtxtファイルがありません。")

print("モデル読み込み中...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("note記事をベクトル化中...")
note_embeddings = model.encode(texts, show_progress_bar=True)

while True:
    query = input("\n検索したい思想・テーマを入力してください（終了は q）: ")

    if query.lower() == "q":
        print("終了します。")
        break

    print(f"\n検索語句: {query}")

    query_embedding = model.encode([query])

    scores = cosine_similarity(query_embedding, note_embeddings)[0]

    ranked = np.argsort(scores)[::-1]

    print("\n近いnote TOP10")
    print("=" * 60)

    for rank, idx in enumerate(ranked[:10], start=1):
        print(
            f"{rank}. {titles[idx]} "
            f"(similarity={scores[idx]:.4f})"
        )