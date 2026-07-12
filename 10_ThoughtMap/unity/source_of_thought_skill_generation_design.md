# Source of Thought
## スキル効果付与生成プログラム設計一覧

## 全体構成

```text
文章・作品
↓
Embedding取得
↓
概念判定
↓
発動条件決定
↓
対象決定
↓
効果種類決定
↓
対象パラメータ決定
↓
効果量・確率・継続時間計算
↓
コスト・クールダウン計算
↓
バランス補正
↓
スキル名・説明文生成
↓
DB保存
```

---

## プログラム一覧

| No. | プログラム名 | 役割 |
|---:|---|---|
| 1 | `skill_concept_loader.py` | スキル概念辞書を読み込む |
| 2 | `skill_reference_embedding_generator.py` | 概念・対象・効果候補をEmbedding化する |
| 3 | `skill_concept_matcher.py` | 作品Embeddingと概念を比較する |
| 4 | `skill_parameter_mapper.py` | ThoughtMap値を戦闘能力へ変換する |
| 5 | `skill_trigger_generator.py` | 手動・被弾時・回避時などの発動条件を決める |
| 6 | `skill_target_generator.py` | 自身・単体・全体などの対象を決める |
| 7 | `skill_effect_type_generator.py` | 上昇・減少・回復・DOTなどを決める |
| 8 | `skill_stat_generator.py` | 攻撃・防御・HP・SPなどの対象能力を決める |
| 9 | `skill_condition_generator.py` | HP条件や属性条件などを生成する |
| 10 | `skill_value_calculator.py` | 威力・回復量・上昇量などを計算する |
| 11 | `skill_duration_calculator.py` | 継続ターンを計算する |
| 12 | `skill_probability_calculator.py` | 発動率・成功率を計算する |
| 13 | `skill_cost_calculator.py` | SP・HPコストを計算する |
| 14 | `skill_cooldown_calculator.py` | クールダウンを計算する |
| 15 | `skill_multi_effect_generator.py` | 複数効果を組み合わせる |
| 16 | `skill_balance_adjuster.py` | 全体攻撃や複合効果を補正する |
| 17 | `skill_name_generator.py` | 概念からスキル名を生成する |
| 18 | `skill_description_generator.py` | 効果説明文を生成する |
| 19 | `skill_validator.py` | 不正な組み合わせを除外する |
| 20 | `skill_repository.py` | SQLiteへ保存・読み込みする |
| 21 | `skill_generation_pipeline.py` | 全処理を順番に実行する |
| 22 | `generate_skills.py` | コマンドライン実行用 |

---

# 1. 概念辞書読み込み

## `skill_concept_loader.py`

和英併記の概念CSVを読み込む。

```csv
Japanese,English,Category
共鳴,Resonance,Interaction
孤独,Solitude,Emotion
犠牲,Sacrifice,Ethics
```

出力例：

```python
SkillConcept(
    japanese="共鳴",
    english="Resonance",
    category="Interaction"
)
```

# 2. 基準Embedding生成

## `skill_reference_embedding_generator.py`

以下の候補語を事前にEmbedding化する。

```text
概念
対象
発動条件
効果
状態異常
戦闘パラメータ
```

保存先例：

```text
reference_skill_embeddings
--------------------------
reference_id
reference_type
label_ja
label_en
embedding
```

# 3. 概念判定

## `skill_concept_matcher.py`

作品Embeddingと概念Embeddingを比較する。

```json
{
  "primary_concept": "共鳴",
  "primary_similarity": 0.782,
  "secondary_concept": "調和",
  "secondary_similarity": 0.744
}
```

上位候補は3〜5件保持する。

# 4. ThoughtMap値の戦闘能力変換

## `skill_parameter_mapper.py`

| ThoughtMap | Battle Parameter |
|---|---|
| 哲学 | 物理攻撃力 |
| 心理 | スキル攻撃力 |
| 科学 | 物理防御力 |
| 経済 | 素早さ |
| カルマ | 運 |
| 感情 | 攻撃回避率 |
| モラル | スキル防御力 |
| 理念 | 攻撃成功率 |
| 個人 | HP |
| 共同体 | SP |

# 5. 発動条件生成

## `skill_trigger_generator.py`

アクティブとパッシブを別構造にせず、発動条件で統一する。

```text
manual
battle_start
turn_start
turn_end
on_attack
on_skill_use
on_damage_taken
on_evade
on_critical
on_kill
on_ally_defeated
on_enemy_defeated
on_heal
on_status_applied
low_hp
low_sp
always
```

`manual`ならアクティブスキルとして扱う。

# 6. 対象決定

## `skill_target_generator.py`

```text
self
single_ally
all_allies
lowest_hp_ally
random_ally
single_enemy
all_enemies
random_enemy
highest_attack_enemy
lowest_defense_enemy
attacker
skill_user
```

概念との対応例：

```text
慈悲 → 味方
支配 → 敵
孤独 → 自身
共鳴 → 味方全体
混沌 → ランダム
復讐 → 攻撃してきた敵
```

# 7. 効果種類生成

## `skill_effect_type_generator.py`

```text
increase
decrease
damage
heal
dot
hot
seal
stun
silence
confuse
dispel
cleanse
shield
drain
reflect
copy
steal
revive
cooldown_reduce
sp_recover
sp_damage
```

# 8. 戦闘パラメータ決定

## `skill_stat_generator.py`

```text
attack
skill_attack
defense
skill_defense
evasion
accuracy
hp
sp
speed
luck
critical_rate
critical_damage
status_success
status_resistance
```

# 9. 条件生成

## `skill_condition_generator.py`

発動条件とは別に追加条件を付与する。

```text
HP50%以下
HP30%以下
SP50%以上
味方が3人以上
味方が1人だけ
敵が状態異常中
自身が状態異常中
前ターンに被弾
同属性カードが2枚以上
特定概念を持つ味方が存在
```

# 10. 効果量計算

## `skill_value_calculator.py`

参照要素：

```text
Embedding類似度
ThoughtMap値
対象数
発動条件
継続時間
発動確率
コスト
複合効果数
```

基本式例：

```python
base_value = 10 + similarity * 30
```

補正例：

```text
単体       × 1.00
敵全体     × 0.65
味方全体   × 0.70
自動発動   × 0.65
低HP限定   × 1.30
SP消費あり × 1.20
```

# 11. 継続時間計算

## `skill_duration_calculator.py`

```text
即時
1ターン
2ターン
3ターン
戦闘終了まで
次の攻撃まで
次の被弾まで
永続
```

# 12. 発動確率計算

## `skill_probability_calculator.py`

```text
100%
75%
50%
35%
25%
10%
```

強い自動効果や状態異常には上限を付ける。

# 13. コスト計算

## `skill_cost_calculator.py`

```text
SP消費
HP消費
カード消費
行動回数消費
次ターン行動不能
自身へのデバフ
クールダウン
```

概念別の傾向：

```text
犠牲 → HP消費
知識 → SP消費
暴走 → 防御低下
時間 → クールダウン増加
契約 → 使用回数制限
```

# 14. クールダウン計算

## `skill_cooldown_calculator.py`

候補は0〜5ターン程度。

```text
単体攻撃+20% → CT1
味方全体攻撃+30% → CT3
敵全体スキル封じ → CT5
```

# 15. 複数効果生成

## `skill_multi_effect_generator.py`

```text
共鳴 + 慈悲
→ 味方全体SP回復 + HOT

犠牲 + 勇気
→ 自身HP消費 + 味方全体攻撃上昇

記憶 + 観測
→ 敵スキルコピー + 命中上昇
```

最大2〜3効果程度に制限する。

# 16. バランス補正

## `skill_balance_adjuster.py`

| 要素 | コストポイント |
|---|---:|
| 単体攻撃 | 10 |
| 全体攻撃 | 18 |
| 回復 | 12 |
| 全体回復 | 22 |
| スキル封じ | 25 |
| 1ターン延長 | 5 |
| 発動率100% | 10 |
| 自動発動 | 15 |
| 複合効果追加 | 12 |

上限を超えた場合：

```text
効果量を下げる
発動率を下げる
SP消費を上げる
クールダウンを伸ばす
```

# 17. スキル名生成

## `skill_name_generator.py`

```text
共鳴 + SP回復
→ 思想共鳴
→ 共鳴の波
→ 精神同期

孤独 + 回避上昇
→ 孤高の歩み
→ 独影
→ 静寂の残響
```

# 18. 説明文生成

## `skill_description_generator.py`

内部データから説明文を組み立てる。

> 味方がスキルを使用したとき、35%の確率で味方全体のSPを8回復する。

# 19. 不正組み合わせ検査

## `skill_validator.py`

```text
敵HP回復
味方にDOT
自身を蘇生
即時効果なのに3ターン継続
DOTなのに攻撃上昇
手動発動なのに発動率30%
```

# 20. DB保存

## `skill_repository.py`

```text
generated_skills
----------------
skill_id
doc_id
name_ja
name_en
concept_ja
concept_en
trigger
target
cost_sp
cost_hp
cooldown
probability
generation_version
created_at
```

```text
generated_skill_effects
-----------------------
effect_id
skill_id
effect_order
effect_type
parameter
value
duration
target
probability
```

# 21. 全体パイプライン

## `skill_generation_pipeline.py`

```python
def generate_skill(document):
    embedding = load_document_embedding(document.doc_id)
    concepts = concept_matcher.match(embedding)
    battle_stats = parameter_mapper.map(document.parameter_scores)
    trigger = trigger_generator.generate(embedding, concepts, battle_stats)
    target = target_generator.generate(embedding, concepts, trigger)
    effect_type = effect_type_generator.generate(embedding, concepts, target)
    stat = stat_generator.generate(battle_stats, effect_type)
    value = value_calculator.calculate(concepts, target, effect_type, stat)
    duration = duration_calculator.calculate(effect_type, value)
    probability = probability_calculator.calculate(trigger, effect_type, value)
    cost = cost_calculator.calculate(
        trigger, target, effect_type, value, duration
    )

    skill = build_skill(
        concepts=concepts,
        trigger=trigger,
        target=target,
        effect_type=effect_type,
        stat=stat,
        value=value,
        duration=duration,
        probability=probability,
        cost=cost,
    )

    skill = balance_adjuster.adjust(skill)
    skill_validator.validate(skill)
    skill.name = name_generator.generate(skill)
    skill.description = description_generator.generate(skill)
    skill_repository.save(skill)
    return skill
```

# 22. 実行用プログラム

## `generate_skills.py`

単体生成：

```bash
python -m skills.generate_skills --doc-id 12345
```

一括生成：

```bash
python -m skills.generate_skills --all
```

再生成：

```bash
python -m skills.generate_skills \
  --all \
  --generation-version 2 \
  --overwrite
```

---

# 最初に作る最低限の構成

```text
skill_concept_matcher.py
skill_parameter_mapper.py
skill_trigger_generator.py
skill_target_generator.py
skill_effect_generator.py
skill_value_calculator.py
skill_balance_adjuster.py
skill_generation_pipeline.py
```

まずは以下の9要素で統一する。

```text
Concept
Trigger
Target
Effect
Parameter
Value
Duration
Probability
Cost
```

アクティブとパッシブは別システムにせず、`trigger = manual`だけをアクティブ扱いにする。それ以外は、自動発動・条件発動・常時効果として同じ生成器で処理する。
