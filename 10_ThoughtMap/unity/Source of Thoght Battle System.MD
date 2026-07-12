# ThoughtMap Battle System
## Resonance (Ally Synergy) & Hate (Target Selection) Specification

Version: Draft v0.1

---

# Overview

ThoughtMap Battleでは、カード性能だけでなく、

- 配置（Position）
- 思想共鳴（Resonance）
- ヘイト（Target Selection）
- スキル（Skill）

の4要素で戦況が変化する。

これにより、「どのカードを使うか」だけではなく、「どこへ配置するか」「誰の隣へ置くか」が重要な戦略となる。

---

# Resonance（共鳴）

## 概要

各カードは共鳴係数（Resonance Coefficient）を持つ。

例

```
1
1.1
1.2
1.3
1.4
1.5
```

味方同士が上下左右で隣接した場合、
共鳴係数の差によって能力補正を受ける。

---

# 共鳴判定

対象

```
↑
←  Card →
↓
```

上下左右のみ。

斜めは対象外。

---

# 共鳴差

```
Difference = abs(A - B)
```

例

```
A = 1.2
B = 1.4

Difference = 0.2
```

---

# 共鳴補正

|Difference|Resonance Bonus|
|----------|---------------|
|0.0|+20%|
|0.1|+15%|
|0.2|+10%|
|0.3|0%|
|0.4|-10%|
|0.5|-20%|

---

# 複数隣接時

上下左右すべて加算する。

例

```
上     +20%
下     +15%
左     -10%
右     +10%
----------------
合計   +35%
```

補正値には上限を設ける。

例

```
最大 +40%

最小 -40%
```

---

# Resonance対象能力

共鳴補正は最終能力値へ乗算される。

対象候補

- Physical Attack
- Skill Attack
- Physical Defense
- Skill Defense
- Speed
- Accuracy
- Dodge
- HP
- SP
- Luck

（将来的には全能力へ適用予定）

---

# Hate System（ヘイト）

## 概要

敵AIは単純な距離だけではなく、

「思想が遠い敵」

を狙いやすくなる。

つまり、

共鳴度が低い相手ほど敵視される。

---

# Hate係数

敵カードと対象カードの共鳴係数差を利用する。

```
Difference = abs(Self - Target)
```

例

敵

```
1.5
```

味方

```
1.5
1.4
1.2
1
```

差

```
0
0.1
0.3
0.5
```

---

# Hate倍率（案）

|Difference|Hate Multiplier|
|----------|---------------|
|0.0|0.7|
|0.1|0.9|
|0.2|1.0|
|0.3|1.1|
|0.4|1.3|
|0.5|1.5|

思想が遠いほど攻撃対象になりやすい。

---

# Target Selection

敵AIは各候補に対してTarget Scoreを計算する。

---

## 1. Column Weight（対面列）

真正面を最優先。

例

```
正面      ×1.5

隣列      ×1.0

さらに外側 ×0.6
```

---

## 2. Depth Weight（奥行）

距離が近いほど狙われやすい。

例

```
前列   ×1.2

中列   ×1.0

後列   ×0.8
```

---

## 3. Resonance Weight

共鳴差から算出。

```
0.7 ～ 1.5
```

---

## 4. Skill Modifier

スキルによる補正。

例

挑発

```
×2.0
```

潜伏

```
×0.5
```

守護

```
味方ヘイト20%吸収
```

など。

---

# 最終ヘイト計算

```
TargetScore
#ERROR!
ColumnWeight
×
DepthWeight
×
ResonanceWeight
×
SkillModifier
×
Random(0.95〜1.05)
```

TargetScoreが最も高いカードを攻撃対象とする。

---

# 配置ボーナス（予定）

盤面そのものにも役割を持たせる予定。

例

前列

```
Physical Attack +10%
Physical Defense -5%
```

中央

```
Accuracy +10%
Skill Success +10%
```

後列

```
Skill Attack +10%
Dodge +10%
```

左右方向にも個性を付与可能。

例

左

```
Speed
Dodge
```

中央

```
HP
SP
```

右

```
Attack
Critical
```

---

# 戦略性

プレイヤーは

- 強いカードを選ぶ
- 思想の近いカードを隣接させる
- 敵との思想差でヘイトを操作する
- 配置ボーナスを活用する
- スキルでヘイト・共鳴を制御する

これらを同時に考える必要がある。

ThoughtMap Battleでは、

「思想の相性」と「陣形」がゲーム性の中心となる。

---

# 今後追加予定

- 共鳴を利用するスキル
- 共鳴を遮断するスキル
- 共鳴をコピーするスキル
- ヘイト固定
- ヘイト分散
- 共鳴リンク
- 陣形ボーナス
- 属性別共鳴補正
- 共鳴チェイン
- 共鳴崩壊（思想が極端に離れた編成へのペナルティ）