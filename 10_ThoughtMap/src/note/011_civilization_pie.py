from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Meiryo"

BASE_DIR = Path(__file__).resolve().parent.parent

df = pd.read_csv(
    BASE_DIR
    / "output"
    / "notes"
    / "notes_clusters.csv"
)

# 仮ラベル
# notes_cluster_details.py を見て後で修正
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
)

plt.figure(figsize=(8, 8))

plt.pie(
    summary.values,
    labels=summary.index,
    autopct="%1.0f%%"
)

plt.title("Jinn project Note 思想文明構成比")

plt.savefig(
    BASE_DIR
    / "output"
    / "notes"
    / "notes_civilization_pie.png",
    dpi=300
)

print("保存完了")