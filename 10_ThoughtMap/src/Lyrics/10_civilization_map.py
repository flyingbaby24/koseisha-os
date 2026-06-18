from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Meiryo"

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = BASE_DIR / "output" / "lyrics_clusters.csv"

df = pd.read_csv(csv_path)

# クラスタ → 文明

civilizations = {
    0: "社会文明",
    1: "技術文明",
    2: "試行文明",
    3: "認識文明",
    4: "社会文明",
    5: "哲学文明",
    6: "内省文明",
    7: "因果文明"
}

df["civilization"] = df["cluster"].map(civilizations)

summary = (
    df.groupby("civilization")
    .size()
    .sort_values(ascending=False)
)

print(summary)

plt.figure(figsize=(12,7))

bars = plt.bar(
    summary.index,
    summary.values
)

for bar in bars:
    y = bar.get_height()

    plt.text(
        bar.get_x() + bar.get_width()/2,
        y,
        str(int(y)),
        ha="center"
    )

plt.title("Jinn project 思想文明マップ")
plt.ylabel("作品数")
plt.xticks(rotation=20)

plt.tight_layout()

out_path = BASE_DIR / "output" / "civilization_map.png"

plt.savefig(out_path, dpi=300)

print(f"保存完了: {out_path}")