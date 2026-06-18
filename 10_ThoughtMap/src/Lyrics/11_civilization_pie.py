from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Meiryo"

BASE_DIR = Path(__file__).resolve().parent.parent

df = pd.read_csv(
    BASE_DIR / "output" / "lyrics_clusters.csv"
)

civilizations = {
    0:"社会文明",
    1:"技術文明",
    2:"試行文明",
    3:"認識文明",
    4:"社会文明",
    5:"哲学文明",
    6:"内省文明",
    7:"因果文明"
}

df["civilization"] = df["cluster"].map(civilizations)

summary = (
    df.groupby("civilization")
    .size()
)

plt.figure(figsize=(8,8))

plt.pie(
    summary.values,
    labels=summary.index,
    autopct="%1.0f%%"
)

plt.title("Jinn project 思想文明構成比")

plt.savefig(
    BASE_DIR / "output" / "civilization_pie.png",
    dpi=300
)

print("保存完了")