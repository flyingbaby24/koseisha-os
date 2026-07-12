# Source of Thought
## スキル生成 入出力仕様書

この文書は、`source_of_thought_skill_generation_design.md` を実装へ落とし込むための入出力仕様を定義する。

---

# 1. 目的

文章・作品ごとのEmbeddingとThoughtMapパラメータを入力として、Source of Thoughtの戦闘で使用するスキルデータを自動生成する。

アクティブスキルとパッシブスキルは別システムに分けず、発動条件 `trigger` で統一する。

```text
trigger = manual
```

の場合のみ、任意発動型のアクティブスキルとして扱う。

それ以外は、自動発動・条件発動・常時効果として扱う。

---

# 2. 生成処理の基本順序

以下の順序を固定する。

```text
1. 入力データ取得
2. Embedding取得
3. スキル概念判定
4. ThoughtMapパラメータ変換
5. 発動条件決定
6. 対象決定
7. 効果種別決定
8. 対象パラメータ決定
9. 条件決定
10. 効果量決定
11. 継続時間決定
12. 発動確率決定
13. コスト決定
14. クールダウン決定
15. 複合効果生成
16. バランス補正
17. 不正組み合わせ検査
18. スキル名生成
19. 説明文生成
20. DB保存
```

生成順序は原則変更しない。

---

# 3. 入力データ

## 3.1 必須入力

```json
{
  "doc_id": "string",
  "embedding": [0.0],
  "parameter_scores": {
    "philosophy": 0.0,
    "psychology": 0.0,
    "science": 0.0,
    "economy": 0.0,
    "karma": 0.0,
    "emotion": 0.0,
    "morality": 0.0,
    "ideology": 0.0,
    "individual": 0.0,
    "community": 0.0
  }
}
```

## 3.2 任意入力

```json
{
  "title": "string",
  "author": "string",
  "source_type": "official | personal",
  "text_excerpt": "string",
  "user_id": "string | null"
}
```

## 3.3 概念辞書

CSV形式。

```csv
Japanese,English,Category
共鳴,Resonance,Interaction
孤独,Solitude,Emotion
犠牲,Sacrifice,Ethics
```

推奨ファイル名：

```text
source_of_thought_concepts.csv
```

---

# 4. ThoughtMapと戦闘パラメータの対応

| ThoughtMap | Battle Parameter | 内部キー |
|---|---|---|
| 哲学 | 物理攻撃力 | `attack` |
| 心理 | スキル攻撃力 | `skill_attack` |
| 科学 | 物理防御力 | `defense` |
| 経済 | 素早さ | `speed` |
| カルマ | 運 | `luck` |
| 感情 | 攻撃回避率 | `evasion` |
| モラル | スキル防御力 | `skill_defense` |
| 理念 | 攻撃成功率 | `accuracy` |
| 個人 | HP | `hp` |
| 共同体 | SP | `sp` |

最大値を主パラメータ、2番目を副パラメータ、3番目を補助パラメータとして扱う。

---

# 5. 出力データ構造

## 5.1 Skill

```json
{
  "skill_id": "string",
  "doc_id": "string",
  "name_ja": "思想共鳴",
  "name_en": "Thought Resonance",
  "concepts": [
    {
      "label_ja": "共鳴",
      "label_en": "Resonance",
      "similarity": 0.782,
      "rank": 1
    }
  ],
  "trigger": "on_skill_use",
  "conditions": [],
  "effects": [],
  "cost": {
    "sp": 0,
    "hp_percent": 0.0,
    "consume_action": false
  },
  "cooldown": 0,
  "generation_version": 1,
  "description_ja": "味方がスキルを使用したとき、35%の確率で味方全体のSPを8回復する。",
  "description_en": "When an ally uses a skill, there is a 35% chance to restore 8 SP to all allies."
}
```

---

## 5.2 Effect

```json
{
  "effect_order": 1,
  "effect_type": "sp_recover",
  "target": "all_allies",
  "parameter": "sp",
  "operation": "recover",
  "value": 8,
  "value_type": "flat",
  "duration": 0,
  "probability": 0.35
}
```

---

# 6. Trigger定義

使用可能な内部値：

```text
manual
always
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
```

## 6.1 アクティブ判定

```text
trigger == manual
```

の場合のみアクティブスキル。

## 6.2 自動発動判定

```text
trigger != manual
```

の場合はパッシブ、リアクション、条件発動、常時効果のいずれかとして扱う。

---

# 7. Target定義

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

対象決定では、概念・発動条件・効果種別の整合性を優先する。

---

# 8. Effect Type定義

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

---

# 9. Operation定義

```text
add
subtract
multiply
recover
damage
set
disable
remove
copy
steal
revive
```

例：

```text
attack + increase → add または multiply
hp + heal → recover
hp + damage → damage
skill + seal → disable
status + cleanse → remove
```

---

# 10. Value Type定義

```text
flat
percent
multiplier
turns
count
```

例：

```json
{
  "value": 20,
  "value_type": "percent"
}
```

---

# 11. Condition定義

```json
{
  "condition_type": "hp_below",
  "operator": "less_than",
  "value": 0.5,
  "target": "self"
}
```

使用可能な条件例：

```text
hp_below
hp_above
sp_below
sp_above
ally_count_at_least
ally_count_at_most
enemy_has_status
self_has_status
was_damaged_last_turn
same_attribute_count
concept_present_in_party
```

---

# 12. Cost定義

```json
{
  "sp": 20,
  "hp_percent": 0.0,
  "consume_action": true,
  "self_debuff": null,
  "usage_limit": null
}
```

使用可能なコスト：

```text
SP消費
HP割合消費
行動消費
自己デバフ
次ターン行動不能
使用回数制限
クールダウン
```

---

# 13. 効果量計算仕様

基本式の初期案：

```python
base_value = minimum_value + normalized_similarity * value_range
```

補正例：

```text
単体対象       × 1.00
敵全体         × 0.65
味方全体       × 0.70
ランダム対象   × 0.85
自動発動       × 0.65
低HP限定       × 1.30
SP消費あり     × 1.20
HP消費あり     × 1.30
複合効果2個    × 0.75
複合効果3個    × 0.60
```

数値はハードコードせず、設定ファイルから変更可能にする。

推奨ファイル：

```text
skill_balance_config.json
```

---

# 14. 継続時間仕様

使用可能な値：

```text
0 = 即時
1 = 1ターン
2 = 2ターン
3 = 3ターン
-1 = 戦闘終了まで
-2 = 次の攻撃まで
-3 = 次の被弾まで
```

DOT、HOT、能力上昇、能力低下には原則として継続時間を設定する。

即時回復、即時ダメージ、SP回復には原則として `0` を設定する。

---

# 15. 発動確率仕様

内部表現は `0.0〜1.0` とする。

```json
{
  "probability": 0.35
}
```

初期制限例：

```text
自身への能力上昇       最大100%
単体DOT                最大75%
単体スキル封じ         最大50%
全体スキル封じ         最大20%
蘇生                    最大100%
```

---

# 16. クールダウン仕様

```text
0〜5ターン
```

以下の要素が強いほど長くする。

```text
全体対象
高威力
複数効果
確定状態異常
蘇生
コピー
反射
```

---

# 17. 複合効果仕様

1スキルに含める効果数：

```text
最小1
推奨最大2
絶対最大3
```

主概念を第1効果、副概念を第2効果に使用する。

3つ目は原則として、コスト・条件・弱い補助効果に限定する。

---

# 18. バリデーション仕様

以下は初期状態では禁止する。

```text
敵への通常回復
味方への通常ダメージ
自身を対象とする蘇生
即時効果への継続時間付与
DOTへの能力上昇operation
手動発動スキルへの低確率発動
対象が存在しないtriggerとtargetの組み合わせ
```

設定で許可できるようにする。

```json
{
  "allow_friendly_fire": false,
  "allow_enemy_heal": false,
  "allow_self_dot": true,
  "allow_self_revive": false
}
```

---

# 19. DB構造

## 19.1 generated_skills

```sql
CREATE TABLE generated_skills (
    skill_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    user_id TEXT,
    name_ja TEXT NOT NULL,
    name_en TEXT,
    trigger TEXT NOT NULL,
    cost_sp INTEGER NOT NULL DEFAULT 0,
    cost_hp_percent REAL NOT NULL DEFAULT 0,
    consume_action INTEGER NOT NULL DEFAULT 0,
    cooldown INTEGER NOT NULL DEFAULT 0,
    description_ja TEXT,
    description_en TEXT,
    generation_version INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
```

## 19.2 generated_skill_concepts

```sql
CREATE TABLE generated_skill_concepts (
    skill_id TEXT NOT NULL,
    concept_rank INTEGER NOT NULL,
    concept_ja TEXT NOT NULL,
    concept_en TEXT,
    similarity REAL NOT NULL,
    PRIMARY KEY (skill_id, concept_rank)
);
```

## 19.3 generated_skill_effects

```sql
CREATE TABLE generated_skill_effects (
    effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    effect_order INTEGER NOT NULL,
    effect_type TEXT NOT NULL,
    target TEXT NOT NULL,
    parameter TEXT,
    operation TEXT NOT NULL,
    value REAL NOT NULL,
    value_type TEXT NOT NULL,
    duration INTEGER NOT NULL DEFAULT 0,
    probability REAL NOT NULL DEFAULT 1.0
);
```

## 19.4 generated_skill_conditions

```sql
CREATE TABLE generated_skill_conditions (
    condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    condition_order INTEGER NOT NULL,
    condition_type TEXT NOT NULL,
    operator TEXT,
    value REAL,
    target TEXT
);
```

---

# 20. 推奨ディレクトリ構成

```text
skills/
├── config/
│   ├── skill_balance_config.json
│   └── skill_validation_config.json
├── data/
│   └── source_of_thought_concepts.csv
├── models/
│   ├── skill.py
│   ├── skill_effect.py
│   ├── skill_condition.py
│   └── skill_concept.py
├── generators/
│   ├── skill_concept_matcher.py
│   ├── skill_parameter_mapper.py
│   ├── skill_trigger_generator.py
│   ├── skill_target_generator.py
│   ├── skill_effect_type_generator.py
│   ├── skill_stat_generator.py
│   ├── skill_condition_generator.py
│   ├── skill_value_calculator.py
│   ├── skill_duration_calculator.py
│   ├── skill_probability_calculator.py
│   ├── skill_cost_calculator.py
│   ├── skill_cooldown_calculator.py
│   ├── skill_multi_effect_generator.py
│   ├── skill_balance_adjuster.py
│   ├── skill_name_generator.py
│   └── skill_description_generator.py
├── repositories/
│   └── skill_repository.py
├── validators/
│   └── skill_validator.py
├── skill_generation_pipeline.py
└── generate_skills.py
```

---

# 21. 最小実装範囲

初回実装では以下のみ対応する。

## Trigger

```text
manual
battle_start
turn_start
on_attack
on_skill_use
on_damage_taken
on_evade
low_hp
always
```

## Target

```text
self
single_ally
all_allies
single_enemy
all_enemies
random_enemy
attacker
```

## Effect Type

```text
increase
decrease
damage
heal
dot
hot
seal
shield
sp_recover
sp_damage
```

## Effect数

```text
1〜2
```

---

# 22. 初回実装時に行わないこと

以下は初回実装対象外とする。

```text
AIによる自由文スキル名生成
複雑な自然言語解釈
3効果以上の複合スキル
敵味方を反転する特殊効果
コピー・反射・蘇生の完全実装
Unity戦闘ロジックへの直接組み込み
既存ThoughtMap検索処理の大規模変更
```

まずPython側で生成結果をJSONまたはSQLiteへ保存し、内容を確認できる状態を作る。

---

# 23. 実行インターフェース

単体生成：

```bash
python -m skills.generate_skills --doc-id 12345
```

全件生成：

```bash
python -m skills.generate_skills --all
```

上書き生成：

```bash
python -m skills.generate_skills --all --overwrite
```

生成バージョン指定：

```bash
python -m skills.generate_skills --all --generation-version 1
```

JSONプレビュー：

```bash
python -m skills.generate_skills --doc-id 12345 --dry-run
```

---

# 24. dry-run出力例

```json
{
  "skill_id": "skill_12345_v1",
  "doc_id": "12345",
  "name_ja": "思想共鳴",
  "name_en": "Thought Resonance",
  "trigger": "on_skill_use",
  "effects": [
    {
      "effect_order": 1,
      "effect_type": "sp_recover",
      "target": "all_allies",
      "parameter": "sp",
      "operation": "recover",
      "value": 8,
      "value_type": "flat",
      "duration": 0,
      "probability": 0.35
    }
  ],
  "cost": {
    "sp": 0,
    "hp_percent": 0.0,
    "consume_action": false
  },
  "cooldown": 0,
  "generation_version": 1
}
```

---

# 25. 実装ルール

- Embeddingの各次元へ固定意味を割り当てない。
- 候補語Embeddingとの類似度比較によって要素を選択する。
- 乱数だけでスキル構造を決めない。
- 同じ入力と同じ生成バージョンからは、原則として同じ結果を返す。
- バランス値は設定ファイルへ分離する。
- 既存DBを破壊しない。
- 既存テーブルへ直接列追加せず、まず新規テーブルで実装する。
- UIやUnity側を先に変更しない。
- `dry-run` で生成結果を確認できるようにする。
- 生成根拠として、概念類似度と主要パラメータを保存する。

---

# 26. CodeXへの実装指示例

```text
source_of_thought_skill_generation_design.md と
skill_generation_spec.md を仕様書として読み、
まず最小実装範囲だけをPython側へ実装してください。

既存のThoughtMap検索、FastAPI、Streamlit、Unity側は変更しないでください。

最初に以下を実装してください。

1. models
2. concept CSV loader
3. concept matcher
4. parameter mapper
5. trigger generator
6. target generator
7. effect generator
8. value calculator
9. validator
10. dry-run対応のgenerate_skills.py

DB保存は新規テーブルのみを使用し、
既存テーブルを破壊・変更しないでください。

実装前に、変更予定ファイル一覧と処理フローを提示してください。
実装後に、変更ファイル一覧、実行コマンド、dry-run出力例を提示してください。
```
