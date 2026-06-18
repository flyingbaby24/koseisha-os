from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Meiryo"

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = (
    BASE_DIR
    / "output"
    / "notes"
    / "notes_clusters.csv"
)

output_dir = BASE_DIR / "output" / "notes"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(csv_path)

# note版：クラスタ → 文明
# まずは仮設定。notes_cluster_details.py の結果を見て後で調整推奨。
civilizations = {
    0: "認識文明",
    1: "教育文明",
    2: "構造文明",
    3: "社会文明",
    4: "AI対話文明",
    5: "内省文明",
    6: "哲学文明",
    7: "問い文明"
}

df["civilization"] = df["cluster"].map(civilizations)

summary = (
    df.groupby("civilization")
    .size()
    .sort_values(ascending=False)
)

print(summary)

plt.figure(figsize=(12, 7))

bars = plt.bar(
    summary.index,
    summary.values
)

for bar in bars:
    y = bar.get_height()

    plt.text(
        bar.get_x() + bar.get_width() / 2,
        y,
        str(int(y)),
        ha="center",
        va="bottom"
    )

plt.title("Jinn project Note 思想文明マップ")
plt.ylabel("記事数")
plt.xticks(rotation=20)

plt.tight_layout()

out_path = output_dir / "notes_civilization_map.png"

plt.savefig(out_path, dpi=300)

print(f"保存完了: {out_path}")