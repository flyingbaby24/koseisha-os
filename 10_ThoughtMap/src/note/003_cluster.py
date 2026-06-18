from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans


BASE_DIR = Path(__file__).resolve().parent.parent

notes_dir = BASE_DIR / "notes"
output_dir = BASE_DIR / "output" / "notes"
output_dir.mkdir(parents=True, exist_ok=True)

files = list(notes_dir.glob("*.txt"))

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

print(f"読み込みnote数: {len(texts)}")

if not texts:
    raise RuntimeError("notesフォルダにtxtファイルがありません。")

print("モデル読み込み中...")
model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

print("ベクトル化中...")
embeddings = model.encode(
    texts,
    show_progress_bar=True
)

cluster_count = 8

print(
    f"クラスタリング中... "
    f"cluster_count={cluster_count}"
)

kmeans = KMeans(
    n_clusters=cluster_count,
    random_state=42,
    n_init="auto"
)

labels = kmeans.fit_predict(embeddings)

report_path = output_dir / "notes_cluster_report.txt"

with open(report_path, "w", encoding="utf-8") as f:

    for cluster_id in range(cluster_count):

        f.write("=" * 60 + "\n")
        f.write(f"Cluster {cluster_id}\n")
        f.write("=" * 60 + "\n")

        members = [
            (i, title)
            for i, title in enumerate(titles)
            if labels[i] == cluster_id
        ]

        f.write(f"記事数: {len(members)}\n\n")

        for i, title in members:
            f.write(f"{i + 1}: {title}\n")

        f.write("\n\n")

print(f"保存しました: {report_path}")