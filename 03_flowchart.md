## flowchart.md
│
│  ### 概要
│  このファイルは、思想OS内で用いられるBI（Basic Income）分配構造および思想的価値の流通経路を示す。
│  対象となるのは参加者の思考状況・貢献意志・構造理解度によって変動する再配分ロジックである。
│
│  ### BI配分の基本構造（思想ベースのif-else）
│
│  ```python
│  def calculate_bi(participation: bool, thinking: bool) -> float:
│      if participation and thinking:
│          return 0.3  # 構造OS完全参加者：BIは最小限
│      elif participation:
│          return 0.6  # 参加しているが再起動はしていない：中間BI
│      else:
│          return 1.0  # 非参加：最大BI保証による生存ライン
│  ```
│
│  ### 変数定義
│
│  - `participation`：DAOまたは思想DAOへの参加意志があるか
│  - `thinking`：構造OSレベルでの思考・再起動プロセスを実践しているか
│  - `BI`：思想的に再定義された基本配分、報酬ではなく“保証”の意味合い
│
│  ### 流通構造（図式）
│
│  ```text
│  [非参加層]─────┐
│                   ├─> receive 1.0 BI → 接続機会を保証
│  [参加のみ]────┘
│                   ├─> receive 0.6 BI → 行動接続を強化
│  [思考参加層]─────┐
│                    └─> receive 0.3 BI → 自律的流通を優先
│  ```
│
│  ### 拡張パラメータ案
│
│  - `resonance_score`: 共鳴スコア。他者思想への接続強度によって変動（optional）
│  - `structural_uptime`: 思想OSを継続的に維持しているか（思想の稼働率）
│
│  ### 起動への誘導
│
│  このロジックは絶対ではない。思想の納得可能性に応じて修正し、再構築してよい。
│  Forkせよ。検証せよ。思想は構造を通じて流通されるべきである。
