const stratagems = [
  {
    id: 1,
    name: "瞞天過海",
    reading: "まんてんかかい",
    english: "Deceive the heavens to cross the sea",
    category: "Normality / Habit",
    bias: "正常性バイアス、慣れによる警戒低下",
    behavioral: "Status quo bias / habituation",
    summary: "あまりにも日常的なものは疑われにくい。反復と慣れを利用する計略。",
    example: "日常業務に紛れた情報漏洩、いつものUIに紛れた誘導",
interpretation: `
瞞天過海は日常に紛れる策ではない。

本質は相手にとっての「正常」を設計することにある。

人は反復されたものを正常だと認識し、
正常性バイアスによって警戒を解く。
`,
principle: `
「正常」は自然発生するものではない。
物語と反復によって構築される。
`,
breakdown: [
  "物語を構築する",
  "反復する",
  "共有される",
  "正常が形成される",
  "正常性バイアスが働く",
  "警戒心が低下する"
],
    noteTitle: "「瞞天過海」は日常に紛れる策ではない。「正常」を設計する策である。",
    noteUrl: "https://note.com/flying_baby/n/nc73a19124331",
    relatedStratagems: [],
    relatedIdioms: [],
    relatedBiases: [],
    relatedConcepts: [],
    relatedNotes: [],
    references: []
  },
  {
  id: 2,

  name: "囲魏救趙",

  reading: "いぎきゅうちょう",

  english: "Besiege Wei to rescue Zhao",

  category: "Attention / Indirect Pressure",

  bias: "注意分散、間接圧力への反応",

  behavioral: "Resource allocation / Opportunity cost",

  summary: "正面から助けるのではなく、相手の別の重要地点を突いて行動を変えさせる。",

  example: "競合の本丸ではなく弱点市場を攻める、交渉で別論点を突く",

  interpretation: `
囲魏救趙は「注意を逸らす計略」ではない。

本質は、相手の限られたリソースをどこへ配分させるかにある。

人は戦力・人材・資金・時間など有限の資源を常に配分している。

その配分先を変えさせることで、本来の戦略そのものを変更させる計略である。
`,

  principle: `
人は有限なリソースを優先順位に従って配分する。

新たな重要課題が生じると、
既存のリソース配分を変更せざるを得ない。
`,

  breakdown: [
    "相手の現在のリソース配分を把握する",
    "別の重要課題を発生させる",
    "優先順位を変更させる",
    "リソース配分を再構成させる",
    "本命への圧力を弱める"
  ],

  noteTitle: "囲魏救趙は「注意を逸らす計略」ではない　「リソース配分を操作する計略」である",

  noteUrl: "https://note.com/flying_baby/n/naad914606937",

  relatedStratagems: [4,19],

  relatedIdioms: [],

  relatedBiases: [
    "限定合理性",
    "機会費用"
  ],

  relatedConcepts: [
    "リソース配分",
    "優先順位",
    "意思決定"
  ],

  relatedNotes: [],

  references: []
  },
  {
    id: 3,
    name: "借刀殺人",
    reading: "しゃくとうさつじん",
    english: "Kill with a borrowed knife",
    category: "Social / Responsibility",
    bias: "責任分散、代理行動、他者利用",
    behavioral: "Diffusion of responsibility / agency problem",
    summary: "自分の手を汚さず、他者の力・権威・怒りを利用する。",
    example: "代理店・インフルエンサー・第三者レビューを使う",
    interpretation: `
借刀殺人は「他人を利用する計略」ではない。

本質は、人は利害・立場・感情に基づいて意思決定するという人間理解にある。

相手の利害と自分の目的が一致する構造を設計すれば、人は命令されなくても自発的に行動する。

借りているのは刀ではない。
本当に借りているのは、人間の意思決定そのものである。
`,

principle: `
人は命令によって動くよりも、
「自分の利益でもある」と認識した時に最も強く動く。

利害の一致は、強制よりも持続的な協力を生み出す。
`,

breakdown: [
  "相手の利害・立場・感情を理解する",
  "自分の目的との共通利益を見つける",
  "利害が一致する状況を設計する",
  "相手は自らの意思で行動する",
  "結果として目的が達成される"
],

noteTitle: "借刀殺人は「他人を利用する計略」ではない　「人は利害に従って動く」という人間理解である",

noteUrl: "https://note.com/flying_baby/n/n22f89c8558ea",
    relatedStratagems: [],
    relatedIdioms: [],
    relatedBiases: [],
    relatedConcepts: [],
    relatedNotes: [],
    references: []
  },
  {
    id: 4,
    name: "以逸待労",
    reading: "いいつたいろう",
    english: "Wait at ease for the exhausted enemy",
    category: "Fatigue / Timing",
    bias: "疲労による判断力低下、焦り",
    behavioral: "Decision fatigue / ego depletion",
    summary: "余裕を保ち、相手の疲労や焦りが判断を鈍らせるのを待つ。",
    example: "長期交渉、相手が疲れたタイミングで条件提示",
    interpretation: `
以逸待労は「疲れるまで待つ計略」ではない。

本質は、相手の認知資源を消耗させる環境を設計することにある。

人は常に情報を処理し、判断を繰り返している。
情報不足、情報過多、時間制限、不確実性、疲労などは、すべて認知資源を消耗させる。

認知資源が枯渇すると判断能力は低下し、最適な意思決定が難しくなる。

以逸待労とは、その状態を意図的に生み出し、最も判断力が低下した瞬間を利用する戦略なのである。
`,

principle: `
疲労とは原因ではなく結果である。

本質は認知資源の消耗にあり、
認知資源が不足すると、人は優先順位や判断精度を維持できなくなる。
`,

breakdown: [
  "認知資源を消耗させる環境を設計する",
  "情報過多・情報不足・時間制限・不確実性を与える",
  "判断力を徐々に低下させる",
  "認知資源が再配分される",
  "最適な意思決定ができなくなった瞬間を狙う"
],

noteTitle: "以逸待労は「疲れるまで待つ計略」ではない　「認知資源を枯渇させる計略」である",

noteUrl: "https://note.com/flying_baby/n/n550b83e1cf00",

relatedStratagems: [2,19,35],

relatedBiases: [
  "Decision fatigue",
  "Cognitive load",
  "Ego depletion"
],

relatedConcepts: [
  "認知資源",
  "意思決定",
  "注意資源",
  "情報処理",
  "リソース配分"
],
    relatedNotes: [],
    references: []
  },
  {
  id: 5,
  name: "趁火打劫",
  reading: "ちんかだこう",
  english: "Loot a burning house",
  category: "Loss / Crisis",
  bias: "危機時の優先順位変化、損失回避、注意資源の再配分",
  behavioral: "Loss aversion / priority reallocation",
  summary: "危機によって優先順位が変化し、守れなくなった場所を突く。",
  example: "競合企業の炎上中に顧客を獲得する、市場暴落時に優良資産を買う、障害対応中の隙を突くサイバー攻撃",

  interpretation: `
趁火打劫は「火事場泥棒」ではない。

本質は、危機によって優先順位が変化した瞬間を利用することにある。

人は危機に直面すると、
命・財産・信用・安全など、
守るべき対象の優先順位を急激に組み替える。

その結果、
すべてを同時には守れなくなり、
注意もリソースも届かない空白が生まれる。

趁火打劫とは、
その空白へ最も早く到達する計略なのである。
`,

  principle: `
危機そのものが本質ではない。

危機によって優先順位が再編成され、
限られた認知資源・時間・戦力が別の場所へ集中することで、
守れなくなった場所が必ず生まれる。
`,

  breakdown: [
    "危機によって優先順位が変化する",
    "重要対象へ認知資源とリソースが集中する",
    "守備の薄い領域が生まれる",
    "その空白を素早く発見する",
    "最も価値の高い機会を獲得する"
  ],

  noteTitle: "趁火打劫は「火事場泥棒」ではない──優先順位が変わった瞬間を突く計略である",

  noteUrl: "https://note.com/flying_baby/n/n03c2bb2b2e40",

  relatedStratagems: [2,4,19],

  relatedIdioms: [],

  relatedBiases: [
    "Loss aversion",
    "Attentional prioritization",
    "Priority reallocation"
  ],

  relatedConcepts: [
    "優先順位",
    "認知資源",
    "リソース配分",
    "危機管理",
    "機会費用"
  ],

  relatedNotes: [],

  references: []
},
  {
  id: 6,
  name: "声東撃西",
  reading: "せいとうげきせい",
  english: "Make noise in the east, attack in the west",
  category: "Attention / Priority",
  bias: "優先順位の誤認、注意誘導、認知資源の集中",
  behavioral: "Attentional bias / priority manipulation",
  summary: "重要ではないものを重要だと思わせ、本命の優先順位を下げさせる。",
  example: "派手なニュース・炎上・スキャンダルで注目を集め、本命の政策変更・侵入・交渉を通す",

  interpretation: `
声東撃西は「注意を逸らす計略」ではない。

本質は、相手の優先順位を誤認させることにある。

人は重要だと思ったものへ注意を向ける。
つまり、注意は原因ではなく結果である。

東へ注意が向くのは、
東の方が重要だと思わされているからである。

声東撃西とは、
重要ではないものを重要だと思わせ、
本当に重要な場所の優先順位を下げさせる情報戦なのである。
`,

  principle: `
人はすべてを同時には見られない。

限られた認知資源は、
「今もっとも重要だ」と認識された対象へ集中する。

そのため、優先順位を誤認させれば、
相手の注意配分そのものを操作できる。
`,

  breakdown: [
    "目立つ情報を提示する",
    "相手にそれを重要だと認識させる",
    "認知資源をそちらへ集中させる",
    "本命の優先順位を下げさせる",
    "誰も見ていない場所へ本命を通す"
  ],

  noteTitle: "声東撃西は「注意を逸らす計略」ではない──優先順位を騙す計略である",

  noteUrl: "https://note.com/flying_baby/n/n747686dc1bfd",

  relatedStratagems: [2,5,8,32],

  relatedIdioms: [],

  relatedBiases: [
    "Attentional bias",
    "Salience bias",
    "Inattentional blindness"
  ],

  relatedConcepts: [
    "優先順位",
    "注意資源",
    "認知資源",
    "情報戦",
    "ミスディレクション"
  ],

  relatedNotes: [],

  references: []
},
  {
  id: 7,
  name: "無中生有",
  reading: "むちゅうしょうゆう",
  english: "Create something from nothing",
  category: "Reality Construction / Social Attention",
  bias: "集団注目による重要度錯覚、真実性錯覚、社会的証明",
  behavioral: "Social proof / illusory truth effect / availability heuristic",
  summary: "集団の注目を利用し、実体が薄いものに重要度を構築する。",
  example: "行列、ランキング、フォロワー数、口コミ、売上No.1、話題化された商品",

  interpretation: `
無中生有は「嘘を信じ込ませる計略」ではない。

本質は、人間が集団の注目を重要度として認識する本能を利用することにある。

人は多くの人が注目しているものを見ると、
「何か重要なことがあるはずだ」と判断する。

これは欠陥ではなく、
群れで生きる生物が獲得した合理的な情報収集能力である。

無中生有とは、
何もない場所に実体を作るのではなく、
集団の注目を起点に重要度そのものを構築する計略なのである。
`,

  principle: `
人間は集団の行動を情報として利用する。

多くの人が見ているもの、
集まっている場所、
話題になっている対象は、
実体の有無とは別に「重要そうだ」と認識される。

そのため、注目の集中を作れば、
重要度そのものを後から発生させることができる。
`,

  breakdown: [
    "注目の起点を作る",
    "集団が反応する",
    "周囲がその反応を重要度として認識する",
    "さらに注目が集まる",
    "実体以上の存在感が形成される",
    "重要度が後から構築される"
  ],

  noteTitle: "無中生有は「嘘を信じ込ませる計略」ではない──集団本能を利用する計略である",

  noteUrl: "https://note.com/flying_baby/n/n1e27db01aab8",

  relatedStratagems: [1,6,17,29],

  relatedIdioms: [],

  relatedBiases: [
    "Social proof",
    "Illusory truth effect",
    "Availability heuristic",
    "Bandwagon effect"
  ],

  relatedConcepts: [
    "集団心理",
    "社会的証明",
    "重要度の構築",
    "群れの本能",
    "注目経済",
    "アルゴリズム"
  ],

  relatedNotes: [],

  references: []
},
  {
  id: 8,
  name: "暗渡陳倉",
  reading: "あんとちんそう",
  english: "Secretly cross at Chencang",
  category: "Search Space / Exploration",
  bias: "探索空間の限定、選択肢の固定、探索停止",
  behavioral: "Choice architecture / search space reduction / bounded rationality",
  summary: "相手の探索範囲を限定し、見えない経路を検討させなくする。",
  example: "UIで機能を埋もれさせる、検索結果に出ない情報、二択だけを提示する議論",

  interpretation: `
暗渡陳倉は「裏道を通る計略」ではない。

本質は、相手の探索空間を制限することにある。

人は無限の可能性を探索しているわけではない。
提示された選択肢の中で問題を解こうとする。

そのため、
相手に「ここだけ見れば十分だ」と思わせれば、
本命の経路は探索対象から外れる。

裏道が成功するのではない。
相手が探さなくなることが成功なのである。
`,

  principle: `
思考は探索空間の中で行われる。

見えている選択肢だけが比較対象となり、
見えていない選択肢は存在していても検討されにくい。

探索空間を設計することは、
認知そのものを設計することでもある。
`,

  breakdown: [
    "相手に見える選択肢を提示する",
    "その範囲だけで十分だと思わせる",
    "探索を終了させる",
    "本命の経路を探索対象外にする",
    "見えない経路から目的を達成する"
  ],

  noteTitle: "暗渡陳倉は「裏道を通る計略」ではない──探索空間を制限する計略である",

  noteUrl: "https://note.com/flying_baby/n/n9b053aec8f19",

  relatedStratagems: [6,19,32],

  relatedIdioms: [],

  relatedBiases: [
    "Bounded rationality",
    "Choice architecture",
    "Confirmation bias",
    "Inattentional blindness"
  ],

  relatedConcepts: [
    "探索空間",
    "探索停止",
    "選択肢設計",
    "情報設計",
    "Choice architecture",
    "アルゴリズム"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 9,
  name: "隔岸観火",
  reading: "かくがんか",
  english: "Watch the fire from across the river",
  category: "Value / Commitment",
  bias: "撤退不能、価値観への執着、コミットメントの固定",
  behavioral: "Escalation of commitment / sunk cost fallacy / identity protection",
  summary: "相手が撤退できなくなる認知を利用し、時間による消耗を待つ。",
  example: "価格競争、SNS炎上、政治対立、企業間の消耗戦",

  interpretation: `
隔岸観火は「傍観する計略」ではない。

本質は、人が撤退できなくなる認知を利用することにある。

人は非合理だから戦い続けるのではない。

自分にとって最も重要な価値を守ろうとする結果、
撤退できなくなるのである。

時間が相手を倒すのではない。

相手自身の価値観が、
消耗戦を継続させるのである。
`,

  principle: `
合理性は利益から生まれるのではない。

人は自分が最も重要だと考える価値を守るように意思決定する。

名誉・信頼・信念・地位・国家・宗教など、
守る対象が強いほど、
撤退は心理的に困難になる。

その結果、
双方が資源を投入し続け、
消耗戦が生まれる。
`,

  breakdown: [
    "相手が何を最優先で守っているかを見抜く",
    "その価値ゆえに撤退できない状態を確認する",
    "双方が資源を投入し続ける",
    "時間が双方の認知資源とリソースを消耗させる",
    "十分に弱った段階で行動する"
  ],

  noteTitle: "隔岸観火は「傍観する計略」ではない──人が撤退できなくなる認知を利用する計略である",

  noteUrl: "https://note.com/flying_baby/n/n51d39f292ec2",

  relatedStratagems: [4,5,11,28],

  relatedIdioms: [],

  relatedBiases: [
    "Escalation of commitment",
    "Sunk cost fallacy",
    "Identity-protective cognition",
    "Loss aversion"
  ],

  relatedConcepts: [
    "価値観",
    "合理性",
    "撤退不能",
    "コミットメント",
    "消耗戦",
    "優先順位"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 10,
  name: "笑裏蔵刀",
  reading: "しょうりぞうとう",
  english: "Hide a knife behind a smile",
  category: "Friend-Foe Recognition",
  bias: "敵味方認識、ハロー効果、警戒解除",
  behavioral: "Coalitional psychology / halo effect / costly signaling",

  summary: "味方シグナルを利用し、敵味方認識を操作して警戒を解除させる。",

  example: "営業、政治、詐欺、恋愛、フレンドリーなUIやブランド設計",

  interpretation: `
笑裏蔵刀は「笑顔で騙す計略」ではない。

本質は、相手の敵味方認識を利用することにある。

人は常に全員を警戒して生きることはできない。

そのため、
笑顔・共感・親切・同じ服装・同じ言葉など、
味方らしいシグナルを見ると、
一時的に警戒を下げるよう進化してきた。

利用しているのは笑顔ではない。

敵味方を判定する認知システムそのものである。
`,

  principle: `
共感は信用そのものではない。

本来は、
認知資源を節約するための
「味方かもしれない」という高速判定である。

味方シグナルを認識すると、
警戒に使う認知資源は一時的に解放される。

その認知を利用することで、
本来なら警戒される行動も受け入れられやすくなる。
`,

  breakdown: [
    "相手が味方と認識するシグナルを把握する",
    "味方シグナルを提示する",
    "敵味方認識を味方側へ傾ける",
    "警戒に使う認知資源を解除させる",
    "本来の目的を実行する"
  ],

  noteTitle: "笑裏蔵刀は「笑顔で騙す計略」ではない──敵味方認識を利用する計略である",

  noteUrl: "https://note.com/flying_baby/n/n44d85cb0464b",

  relatedStratagems: [1,3,7,34],

  relatedIdioms: [],

  relatedBiases: [
    "Halo effect",
    "Coalitional psychology",
    "In-group bias",
    "Affect heuristic"
  ],

  relatedConcepts: [
    "敵味方認識",
    "味方シグナル",
    "認知資源",
    "集団生活",
    "偽装伝達",
    "社会的シグナル"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 11,

  name: "李代桃僵",

  reading: "りだいとうきょう",

  english: "Sacrifice the plum tree to preserve the peach tree",

  category: "Management / Capacity",

  bias: "保持コストの不可視化、損失回避、管理限界",

  behavioral: "Bounded rationality / cognitive load / loss aversion",

  summary: "管理能力には限界があることを理解し、全体を守るために管理対象を整理する。",

  example: "不要事業の整理、メール・ファイル整理、組織再編、人間関係の整理、在庫圧縮",

  interpretation: `
李代桃僵は「犠牲を払う計略」ではない。

本質は、人間の管理能力には限界があるという認知を利用することにある。

人は情報・人間関係・財産・組織・感情など、
あらゆるものを保持しようとする。

しかし、
保持対象が増えるほど管理コストは増え、
やがて認知資源の限界を超えてしまう。

李代桃僵とは、
一部を失うことを目的とする兵法ではない。

全体を維持するため、
限られた管理能力を最適配分する計略なのである。
`,

  principle: `
生物は変化を検知するために進化した。

そのため、
「保持し続けること」は背景となって認識されにくく、
保持コストも意識されにくい。

一方で、
失うことだけは強く認知される。

その結果、
不要なものまで抱え込み、
管理能力の限界を超えてしまう。

管理対象を整理することは損失ではなく、
全体最適化なのである。
`,

  breakdown: [
    "管理対象を把握する",
    "認知資源・管理能力の限界を理解する",
    "価値順位を決める",
    "重要度の低い対象を整理する",
    "管理対象を適正規模へ戻す",
    "全体の維持と最適化を図る"
  ],

  noteTitle: "李代桃僵は「犠牲を払う計略」ではない──管理限界を利用する計略である",

  noteUrl: "https://note.com/flying_baby/n/n2abf16217ae5",

  relatedStratagems: [4,5,9,19,36],

  relatedIdioms: [],

  relatedBiases: [
    "Loss aversion",
    "Bounded rationality",
    "Cognitive load",
    "Decision fatigue"
  ],

  relatedConcepts: [
    "認知資源",
    "管理能力",
    "保持コスト",
    "全体最適",
    "優先順位",
    "リソース配分"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 12,

  name: "順手牽羊",

  reading: "じゅんしゅけんよう",

  english: "Take the opportunity to steal a goat",

  category: "Background / Gradual Change",

  bias: "変化閾値、背景化、漸進的変化への鈍感さ",

  behavioral: "Change blindness / habituation / just noticeable difference",

  summary: "認知閾値を下回る小さな変化を積み重ね、背景となった変化によって認識を書き換える。",

  example: "少しずつ値上げするサブスク、UI変更を段階的に行う、毎日の広告接触、価値観の漸進的な誘導",

  interpretation: `
順手牽羊は「小さな機会を拾う計略」ではない。

本質は、人間が背景化した変化を認識しにくいことを利用することにある。

生物は危険を察知するため、
変化を検知するよう進化してきた。

しかし、
認知閾値を下回る小さな変化は、
背景となり認識されにくい。

順手牽羊とは、
目立つ変化で相手を動かす兵法ではない。

背景化した小さな変化を積み重ね、
気付かれないまま認知そのものを書き換える計略なのである。
`,

  principle: `
人は変化を検知するために進化した。

しかし、
変化量が認知閾値を超えない場合、
その変化は背景として処理される。

背景となったものは、
意識されないまま世界を理解する基準となる。

フックは注意を奪う。

背景は認識を作る。
`,

  breakdown: [
    "認知閾値を超えない小さな変化を設計する",
    "変化を継続的に積み重ねる",
    "背景として認識させる",
    "当たり前という基準を形成する",
    "認知そのものを書き換える"
  ],

  noteTitle: "順手牽羊は「小さな機会を拾う計略」ではない──背景化した変化を利用する計略である",

  noteUrl: "https://note.com/flying_baby/n/n1d83888847ae",

  relatedStratagems: [1,6,10,11,25],

  relatedIdioms: [],

  relatedBiases: [
    "Change blindness",
    "Habituation",
    "Just noticeable difference",
    "Mere exposure effect"
  ],

  relatedConcepts: [
    "背景化",
    "認知閾値",
    "変化検知",
    "慣れ",
    "反復",
    "世界モデル"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 13,

  name: "打草驚蛇",

  reading: "だそうきょうだ",

  english: "Beat the grass to startle the snake",

  category: "Threshold / Detection",

  bias: "認知閾値、反応閾値、重要度判定",

  behavioral: "Signal detection theory / threshold testing / information elicitation",

  summary: "小さな刺激を与え、相手がどの変化を無視できず反応するのかを測定する。",

  example: "小さな質問で本音を見る、価格変更テスト、セキュリティ監査、相手の許容範囲を探る交渉",

  interpretation: `
打草驚蛇は「反応を見る計略」ではない。

本質は、相手の認知閾値を測定することにある。

生物はすべての刺激に反応していては生きていけない。

そのため、
自分にとって重要だと判断した変化だけに反応する。

つまり反応とは、
その対象にとって
無視できない変化が発生したという情報である。

打草驚蛇とは、
相手を驚かせる兵法ではない。

刺激と反応を観察し、
相手が何を重要視し、
どの程度の変化で動くのかを測定する計略なのである。
`,

  principle: `
相手の内部状態は直接見ることができない。

だから、
外部から小さな刺激を与え、
返ってくる反応を観察する。

攻撃するのか。
逃げるのか。
警戒するのか。
無視するのか。

その違いによって、
相手の価値観、恐れ、守る対象、認知閾値が見えてくる。

認知閾値を知れば、
閾値を超えて反応を引き出すことも、
閾値を下回る変化で気付かれず消耗させることもできる。
`,

  breakdown: [
    "小さな刺激を与える",
    "相手の反応を観察する",
    "反応した刺激と無視した刺激を比較する",
    "相手の重要対象と認知閾値を推定する",
    "閾値を超える攻撃か、閾値以下の消耗かを選択する",
    "その後の戦略を最適化する"
  ],

  noteTitle: "打草驚蛇は「反応を見る計略」ではない──認知閾値を測定する計略である",

  noteUrl: "https://note.com/flying_baby/n/nad135c902aa0",

  relatedStratagems: [8,12,20,32],

  relatedIdioms: [],

  relatedBiases: [
    "Signal detection theory",
    "Change detection",
    "Salience bias",
    "Threat perception"
  ],

  relatedConcepts: [
    "認知閾値",
    "反応閾値",
    "刺激と反応",
    "情報抽出",
    "重要度判定",
    "探索"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 14,

  name: "借屍還魂",

  reading: "しゃくしかんこん",

  english: "Borrow a corpse to revive the soul",

  category: "Success Memory / Legacy",

  bias: "成功体験、権威バイアス、過去実績への信頼",

  behavioral: "Authority bias / availability heuristic / transfer of trust",

  summary: "過去に成功した記憶を再利用し、新しい対象へ信頼や期待を転移させる。",

  example: "復刻ブランド、老舗企業、名門校、元○○、ベストセラー、過去IPの再利用",

  interpretation: `
借屍還魂は「権威を借りる計略」ではない。

本質は、人が成功体験を再利用する認知の性質を利用することにある。

人は権威そのものを信じているのではない。

一度成功したものは、
もう一度成功する可能性が高いと認識しているのである。

借りているのは権威ではない。

過去に成功したという記憶であり、
その記憶が新しい対象へ信頼を転移させるのである。
`,

  principle: `
成功体験は思考のショートカットである。

生物は限られた認知資源で生きているため、
毎回ゼロから判断していては間に合わない。

だから、
一度成功した行動や対象を記憶し、
似た状況で再利用する。

過去の成功、伝統、ブランド、肩書きは、
現在の価値そのものではなく、
成功の記憶を呼び出す装置として働く。
`,

  breakdown: [
    "過去に成功した対象を見つける",
    "その成功記憶を呼び出せる名前・形式・物語を使う",
    "相手に過去の成功を想起させる",
    "現在の対象への検証コストを下げる",
    "信頼や期待を新しい対象へ転移させる"
  ],

  noteTitle: "借屍還魂は「権威を借りる計略」ではない──成功体験を再利用する計略である",

  noteUrl: "https://editor.note.com/notes/n7f9edbb0ab75/edit/",

  relatedStratagems: [1,7,10,29,30],

  relatedIdioms: [],

  relatedBiases: [
    "Authority bias",
    "Availability heuristic",
    "Halo effect",
    "Status quo bias"
  ],

  relatedConcepts: [
    "成功体験",
    "思考のショートカット",
    "信頼の転移",
    "ブランド",
    "伝統",
    "過去実績"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 15,

  name: "調虎離山",

  reading: "ちょうこりざん",

  english: "Lure the tiger away from the mountain",

  category: "Context / Environment",

  bias: "環境依存、ホームアドバンテージ、文脈依存記憶",

  behavioral: "Context-dependent cognition / home advantage / predictive processing",

  summary: "能力ではなく、その能力を成立させる認知環境を崩す。",

  example: "アウェー戦、異動・転職、プラットフォーム変更、市場環境の変化、兵糧攻め",

  interpretation: `
調虎離山は「得意な場所から誘い出す計略」ではない。

本質は、相手が能力を発揮するための認知の前提条件を崩すことにある。

人は環境そのものを覚えているのではない。

「この環境ならこう行動すればよい」という予測モデルを学習している。

そのため、
環境が変わると、
これまで使えていた予測モデルは機能しなくなる。

能力が落ちたのではない。

能力を支えていた認知環境が失われたのである。
`,

  principle: `
認知は環境を前提として成立する。

人は限られた認知資源を節約するため、
環境ごとの予測モデルを学習する。

予測可能な環境では認知コストは低く、
本来の能力へ資源を集中できる。

一方、
環境が変化すると、
認知資源は環境適応へ再配分される。

その結果、
能力そのものではなく、
能力を発揮する効率が低下する。

調虎離山とは、
人を弱くする兵法ではなく、
能力を支える認知環境を崩す兵法なのである。
`,

  breakdown: [
    "相手が能力を発揮している環境を把握する",
    "その環境から相手を切り離す",
    "予測モデルを機能しなくする",
    "認知資源を環境適応へ再配分させる",
    "能力発揮効率を低下させる",
    "その隙に目的を達成する"
  ],

  noteTitle: "調虎離山は「得意な場所から誘い出す計略」ではない──認知の前提条件を崩す計略である",

  noteUrl: "https://note.com/flying_baby/n/n680ea4736142",

  relatedStratagems: [4,11,19,20],

  relatedIdioms: [],

  relatedBiases: [
    "Context-dependent cognition",
    "Home advantage",
    "Predictive processing",
    "Cognitive load"
  ],

  relatedConcepts: [
    "認知環境",
    "予測モデル",
    "認知資源",
    "ホームアドバンテージ",
    "環境依存",
    "文脈依存記憶"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 16,

  name: "欲擒故縦",

  reading: "よくきんこしょう",

  english: "To capture, first let go",

  category: "Choice / Cognitive Task",

  bias: "主体性、一貫性、自己決定感、認知課題",

  behavioral: "Self-perception theory / commitment & consistency / cognitive closure",

  summary: "答えを与えるのではなく、相手自身に認知課題を解決させる。",

  example: "営業でプランを選ばせる、UIの選択ボタン、教育で課題を考えさせる、マジシャンズ・チョイス",

  interpretation: `
欲擒故縦は「わざと逃がす計略」ではない。

本質は、相手自身に認知課題を解決させることにある。

人は自由だから動くのではない。

提示された問題を自分で解決したと認識した時、
その結果を自分の意思決定として受け入れる。

主体性とは、
自由から生まれるものではない。

「自分で答えを出した」という認知から生まれるのである。
`,

  principle: `
人は選択することが好きなのではない。

未解決の状態を終わらせたいのである。

認知は、
提示された課題を解決しようとする。

そのため、
答えを押し付けられるよりも、
自分で導き出した答えの方が、
責任感・主体性・一貫性・愛着を持ちやすい。

欲擒故縦とは、
相手へ自由を与える兵法ではない。

認知課題を相手へ委ね、
自ら答えを導いたという認識を形成する兵法なのである。
`,

  breakdown: [
    "認知課題を提示する",
    "相手自身に解決を委ねる",
    "自分で答えを導いたと認識させる",
    "主体性と責任感を形成する",
    "結果を自分の意思決定として受け入れる",
    "自発的な行動を引き出す"
  ],

  noteTitle: "欲擒故縦は「わざと逃がす計略」ではない──認知課題を相手に解決させる計略である",

  noteUrl: "https://note.com/flying_baby/n/n949e121f4ccf",

  relatedStratagems: [8,10,13,17,22,32],

  relatedIdioms: [],

  relatedBiases: [
    "Commitment and consistency",
    "Self-perception theory",
    "Need for cognitive closure",
    "Choice architecture"
  ],

  relatedConcepts: [
    "認知課題",
    "主体性",
    "自己決定",
    "認知的完結欲求",
    "意思決定",
    "マジシャンズ・チョイス"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 17,

  name: "抛磚引玉",

  reading: "ほうせんいんぎょく",

  english: "Throw a brick to attract jade",

  category: "Evaluation / Entry Cost",

  bias: "認知コスト、試行コスト、未知回避",

  behavioral: "Processing fluency / uncertainty reduction / mere exposure",

  summary: "価値を渡るのではなく、認知コストの低い入口を設計する。",

  example: "試食、無料体験、ゲーム体験版、無料相談、要約記事、ショート動画、AIレコメンド",

  interpretation: `
抛磚引玉は「小さなものを差し出す計略」ではない。

本質は、認知コストの低い入口を提示することにある。

人は未知の価値を評価することが苦手である。

そのため、
価値そのものを提示しても、
判断できず行動できないことが多い。

まずは、
負担なく触れられる入口を設計する。

未知だったものが既知になることで、
初めて価値を評価できるようになる。

利用しているのは無料ではない。

価値を判断できる認知状態そのものである。
`,

  principle: `
人は価値があるから受け入れるのではない。

判断しやすいから受け入れるのである。

未知の対象を評価するには、
時間・労力・お金など、
様々な認知資源を消費する。

入口の認知コストを下げれば、
人はまず体験し、
その後で価値を判断する。

抛磚引玉とは、
価値を提供する兵法ではない。

価値へ到達するための認知的入口を設計する兵法なのである。
`,

  breakdown: [
    "相手にとって未知の価値を把握する",
    "認知コストの低い入口を設計する",
    "まず体験できる状態を作る",
    "未知を既知へ変える",
    "価値を評価できる認知状態を形成する",
    "本来の価値へ自然に到達させる"
  ],

  noteTitle: "抛磚引玉は「小さなものを差し出す計略」ではない──認知コストを下げる入口を提示する計略である",

  noteUrl: "https://note.com/flying_baby/n/n4f413f72b970",

  relatedStratagems: [1,8,12,16,24],

  relatedIdioms: [],

  relatedBiases: [
    "Processing fluency",
    "Uncertainty reduction",
    "Mere exposure effect",
    "Choice architecture"
  ],

  relatedConcepts: [
    "認知コスト",
    "入口設計",
    "試行コスト",
    "Processing Fluency",
    "フリーミアム",
    "時間資源"
  ],

  relatedNotes: [],

  references: []
  },
  {
  id: 18,

  name: "擒賊擒王",

  reading: "きんぞくきんおう",

  english: "Capture the leader to capture the bandits",

  category: "Decision Network / Centrality",

  bias: "意思決定の委譲、中心性、認知コスト",

  behavioral: "Network centrality / authority heuristic / cognitive offloading",

  summary: "肩書きではなく、意思決定が集約される中心を支配する。",

  example: "決裁者への営業、実質的な経営者への交渉、SNSアルゴリズムの攻略、検索エンジン最適化",

  interpretation: `
擒賊擒王は「リーダーを倒す計略」ではない。

本質は、意思決定が集約されている中心を支配することにある。

人はすべてを自分で判断して生きているわけではない。

専門家、上司、経験者などへ
意思決定を委ねることで、
認知コストを節約している。

そのため、
判断が集約されている場所を押さえれば、
集団全体の行動も変化する。

攻撃しているのは人物ではない。

認知と意思決定のネットワークそのものである。
`,

  principle: `
認知資源には限界がある。

そのため人は、
すべてを自分で判断せず、
信頼できる対象へ意思決定を委譲する。

意思決定が一箇所へ集約されるほど、
集団は効率化される一方、
その中心への依存も強くなる。

擒賊擒王とは、
肩書きを狙う兵法ではない。

認知と意思決定が最も集中する場所を見抜き、
そこへ働きかける兵法なのである。
`,

  breakdown: [
    "集団の意思決定構造を観察する",
    "判断が最も集約される中心を特定する",
    "その中心へ働きかける、または排除する",
    "集団全体の意思決定構造を変化させる",
    "行動全体へ影響を及ぼす"
  ],

  noteTitle: "擒賊擒王は「リーダーを倒す計略」ではない──意思決定の中心を支配する計略である",

  noteUrl: "https://note.com/flying_baby/n/ne78d8d9fe5f4",

  relatedStratagems: [3,6,10,14,19,30],

  relatedIdioms: [],

  relatedBiases: [
    "Authority heuristic",
    "Network centrality",
    "Cognitive offloading",
    "Delegated decision-making"
  ],

  relatedConcepts: [
    "意思決定",
    "認知コスト",
    "ネットワーク中心性",
    "ボトルネック",
    "意思決定の委譲",
    "アルゴリズム"
  ],

  relatedNotes: [],

  references: []
  },
  {
  "id": 19,
  "name": "釜底抽薪",
  "reading": "ふていちゅうしん",
  "english": "Remove the firewood from under the pot",
  "category": "Background / Infrastructure",
  "bias": "背景化、変化盲、土台の不可視化",
  "behavioral": "Change blindness / background processing / systems thinking",
  "summary": "背景化された基盤へ介入し、表面現象そのものを成立させなくする。",
  "example": "資金源を断つ、半導体供給を止める、サーバー停止、通信網遮断、物流停止、エネルギー供給を絶つ",

  "interpretation": `
釜底抽薪は「土台を狙う計略」ではない。

本質は、人間が変化しないものを背景として処理する認知の性質を利用することにある。

人は危険を素早く察知するため、
変化したものへ注意を向ける。

その一方で、
変化しないものは認知資源を節約するため、
背景として処理される。

土台とは下にあるものではない。

変化しにくいため、
誰も意識しなくなった構造そのものなのである。

釜底抽薪とは、
目立つ現象を攻撃する兵法ではない。

背景化された基盤へ介入し、
その現象自体を成立させなくする計略なのである。
`,

  "principle": `
背景とは重要ではないものではない。

認知資源を節約するため、
脳が意識的な処理を省略している対象である。

電気、水道、通信、物流、法律、言語など、
変化しないものほど背景となる。

しかし、
それらが失われた瞬間、
初めて人は世界を支えていた基盤だったことに気付く。

釜底抽薪とは、
背景として見落とされた構造そのものへ介入する兵法なのである。
`,

  "breakdown": [
    "相手を支える背景構造を把握する",
    "背景化されている基盤を特定する",
    "その基盤へ介入する",
    "表面現象を成立できなくする",
    "相手は原因を理解する前に機能を失う"
  ],

  "noteTitle": "釜底抽薪は「土台を狙う計略」ではない──人は変化しないものを背景化する",

  "noteUrl": "https://note.com/flying_baby/n/n8fdaac4a18b8",

  "relatedStratagems": [11,12,15,25],

  "relatedIdioms": [],

  "relatedBiases": [
    "Change blindness",
    "Habituation",
    "Background processing",
    "Systems thinking"
  ],

  "relatedConcepts": [
    "背景化",
    "変化検知",
    "認知資源",
    "インフラ",
    "システム思考",
    "土台構造"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 20,
  "name": "渾水摸魚",
  "reading": "こんすいぼぎょ",
  "english": "Fish in troubled waters",
  "category": "Decision / Cognitive Load",
  "bias": "判断軸の喪失、認知負荷、比較対象の増加",
  "behavioral": "Cognitive load / choice overload / bounded rationality",
  "summary": "判断軸を曖昧にし、認知負荷を高めることで正常な意思決定を困難にする。",
  "example": "専門家が異なる基準で議論する、SNSで相反する情報を大量に流す、制度変更で判断基準を複雑化する",

  "interpretation": `
渾水摸魚は「混乱に乗じる計略」ではない。

本質は、人間が判断軸を失うと認知負荷が急激に増加することを利用することにある。

混乱とは情報量が多いことではない。

何を基準に判断すればよいか分からなくなった状態である。

人は比較する基準が明確なら、
大量の情報でも整理できる。

しかし、
判断軸そのものが曖昧になると、
認知資源は急速に消耗し、
正常な意思決定が難しくなる。

渾水摸魚とは、
混乱を起こす兵法ではない。

相手の判断軸そのものを曖昧にし、
認知負荷を高める計略なのである。
`,

  "principle": `
認知負荷は情報量だけでは決まらない。

人は比較対象や判断軸が増えるほど、
どの基準で評価すべきかを考え続ける必要がある。

その結果、
認知資源が限界へ近づくと、
思考を省略し、
権威、感情、第一印象などの認知のショートカットへ依存しやすくなる。

判断軸を失わせることは、
判断能力そのものを低下させるのである。
`,

  "breakdown": [
    "相手が依存している判断軸を把握する",
    "異なる評価軸や比較基準を提示する",
    "判断軸を曖昧にする",
    "認知負荷を急激に高める",
    "思考を省略させ認知のショートカットへ誘導する"
  ],

  "noteTitle": "渾水摸魚は「混乱に乗じる計略」ではない──人は判断軸を失うと認知負荷が爆発する",

  "noteUrl": "https://note.com/flying_baby/",

  "relatedStratagems": [4,6,13,16,32],

  "relatedIdioms": [],

  "relatedBiases": [
    "Cognitive load",
    "Choice overload",
    "Bounded rationality",
    "Decision fatigue"
  ],

  "relatedConcepts": [
    "判断軸",
    "比較基準",
    "認知負荷",
    "認知資源",
    "意思決定",
    "判断コスト"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 21,
  "name": "金蝉脱殻",
  "reading": "きんせんだっかく",
  "english": "Shed the shell like a golden cicada",
  "category": "Continuity / Cognitive Model",
  "bias": "継続性錯覚、認知モデルの再利用、更新コスト",
  "behavioral": "Continuity bias / schema persistence / cognitive economy",
  "summary": "相手の認知モデルを更新させず、継続性を維持させる。",
  "example": "ブランド名は同じまま経営交代、ロゴは同じだが中身が変わるサービス、企業買収後も同じブランドを維持する",

  "interpretation": `
金蝉脱殻は「外見を残す計略」ではない。

本質は、人間が一度形成した認知モデルを簡単には更新しないことを利用することにある。

人は毎回世界を理解し直しているわけではない。

一度学習した人物、会社、ブランド、制度などを
認知のショートカットとして再利用している。

そのため、
外見や名前が維持されている限り、
中身まで同じだと認識しやすい。

金蝉脱殻とは、
外見を偽装する兵法ではない。

相手が既に持っている認知モデルそのものを利用し、
更新させない計略なのである。
`,

  "principle": `
認知モデルは認知資源を節約するために存在する。

人は毎回ゼロから対象を理解するのではなく、
過去の経験・記憶・評価をまとめた認知モデルを再利用する。

一度形成したモデルを書き換えるには、
記憶・経験・評価・行動まで再構築しなければならない。

そのため脳は、
理解よりも維持を優先する。

外見が変わらなければ、
認知モデルも更新されにくいのである。
`,

  "breakdown": [
    "相手が持つ認知モデルを把握する",
    "外見や名称など継続性の手掛かりを維持する",
    "内部だけを変化させる",
    "相手に認知モデルを更新させない",
    "従来と同じ対象だと思わせたまま目的を達成する"
  ],

  "noteTitle": "金蝉脱殻は「外見を残す計略」ではない──人は認知モデルを簡単には更新しない",

  "noteUrl": "https://note.com/flying_baby/n/n317720c624cd",

  "relatedStratagems": [1,10,14,25,30],

  "relatedIdioms": [],

  "relatedBiases": [
    "Continuity bias",
    "Schema persistence",
    "Status quo bias",
    "Cognitive economy"
  ],

  "relatedConcepts": [
    "認知モデル",
    "認知のショートカット",
    "継続性",
    "更新コスト",
    "スキーマ",
    "ブランド認知"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 22,
  "name": "関門捉賊",
  "reading": "かんもんそくぞく",
  "english": "Shut the door to catch the thief",
  "category": "Action Cost / Choice Architecture",
  "bias": "実行コスト、選択アーキテクチャ、現状維持バイアス",
  "behavioral": "Choice architecture / friction cost / status quo bias",
  "summary": "実行コストを操作し、実質的な選択肢を制御する。",
  "example": "解約導線を複雑化する、違約金を設定する、レコメンドで候補を限定する、UIで望む行動を押しやすくする",

  "interpretation": `
関門捉賊は「逃げ道を塞ぐ計略」ではない。

本質は、人間が実行コストの低い行動を選ぶことを利用することにある。

人は存在する選択肢の中から行動を選んでいるわけではない。

時間、労力、危険、金銭、手間など、
実行に必要なコストを無意識に比較し、
最も実行しやすい選択肢を選んでいる。

そのため、
逃げ道を消さなくても、
逃げるためのコストを十分に高くすれば、
人は別の選択肢を選ぶようになる。

関門捉賊とは、
出口を物理的に塞ぐ兵法ではない。

実行コストそのものを設計し、
相手の行動を制御する計略なのである。
`,

  "principle": `
人は可能な行動ではなく、
実行しやすい行動を選ぶ。

選択肢が存在していても、
実行コストが高ければ、
実質的には選択肢として機能しない。

逆に、
望む行動の実行コストを下げれば、
人は自由意思だと感じたまま、
その方向へ自然に行動する。

実行コストを設計することは、
選択そのものを設計することなのである。
`,

  "breakdown": [
    "相手が取り得る選択肢を把握する",
    "望まない行動の実行コストを高める",
    "望む行動の実行コストを下げる",
    "実質的な選択肢を限定する",
    "相手は自発的に望む行動を選択する"
  ],

  "noteTitle": "関門捉賊は「逃げ道を塞ぐ計略」ではない──実行コストを操作し、行動を制御する",

  "noteUrl": "https://note.com/flying_baby/n/n89e0e2d28def",

  "relatedStratagems": [8,16,17,28,30],

  "relatedIdioms": [],

  "relatedBiases": [
    "Choice architecture",
    "Status quo bias",
    "Friction cost",
    "Default effect"
  ],

  "relatedConcepts": [
    "実行コスト",
    "選択アーキテクチャ",
    "認知コスト",
    "UI/UX",
    "レコメンド",
    "行動設計"
  ],

  "relatedNotes": [],

  "references": []
},
  {
  "id": 23,
  "name": "遠交近攻",
  "reading": "えんこうきんこう",
  "english": "Befriend distant states while attacking nearby ones",
  "category": "Community / Relationship Cost",
  "bias": "近接競争、利害調整コスト、共同体維持コスト",
  "behavioral": "Coalition formation / transaction cost / resource allocation",
  "summary": "共同体に発生する関係維持コストを最適化し、競争と協力の境界を設計する。",
  "example": "遠い業界との提携、APIエコシステム、異業種連携、家族や組織の役割分担、プラットフォーム戦略",

  "interpretation": `
遠交近攻は「遠くと組む計略」ではない。

本質は、共同体に発生する関係維持コストを最適化することにある。

近い者ほど生活圏・市場・資源・役割が重なり、
利害調整が必要になる。

共同体を維持するには、
説明・相談・配慮・合意形成など、
継続的な認知コストを支払い続けなければならない。

一方で、
利害が重なりにくい遠い相手とは、
競争よりも補完関係を築きやすい。

遠交近攻とは、
距離そのものではなく、
関係維持コストを設計し、
競争と協力の境界を最適化する計略なのである。
`,

  "principle": `
共同体は価値観だけでは成立しない。

役割・利益・責任・ルールを継続的に調整できることが、
共同体を維持する条件である。

人は距離そのものではなく、
利害調整に必要な認知コストによって、
協力相手と競争相手を選択する。

API連携やプラットフォーム戦略も、
共同体を形成し、
関係維持コストを共有することで、
競争を協力へ変換しているのである。
`,

  "breakdown": [
    "利害が重なる相手を把握する",
    "共同体形成に必要な調整コストを理解する",
    "競争の大きい相手との利害を整理する",
    "補完関係を築ける相手と共同体を形成する",
    "関係維持コストを最適化する",
    "競争と協力の境界を設計する"
  ],

  "noteTitle": "遠交近攻は「遠くと組む計略」ではない──共同体の関係維持コストを最適化する計略である",

  "noteUrl": "https://note.com/flying_baby/n/n646f410976f7",

  "relatedStratagems": [3,11,18,22,24,30],

  "relatedIdioms": [],

  "relatedBiases": [
    "Coalition formation",
    "Transaction cost",
    "Resource allocation",
    "Social exchange theory"
  ],

  "relatedConcepts": [
    "共同体",
    "関係税",
    "関係維持コスト",
    "利害調整",
    "APIエコシステム",
    "プラットフォーム",
    "競争",
    "協力"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 24,
  "name": "仮道伐虢",
  "reading": "かどうばっかく",
  "english": "Borrow a path to attack Guo",
  "category": "Generalization / Cognitive Model",
  "bias": "普遍化、認知モデルの再利用、信頼の一般化",
  "behavioral": "Generalization / schema learning / trust transfer",
  "summary": "一度形成された認知モデルを普遍化させ、小さな許可を前提へ変える。",
  "example": "API連携、OAuth認証、無料トライアル、SaaS導入、社内ツール導入、プラットフォーム連携",

  "interpretation": `
仮道伐虢は「協力を装う計略」ではない。

本質は、人間が一度形成した認知モデルを普遍化することにある。

人は毎回ゼロから相手を評価しているわけではない。

一度安全だと判断すると、
その判断を次の場面にも適用する。

小さな許可は、
単なる一回の承認ではない。

その後の判断全体を書き換える認知モデルの入口となる。

仮道伐虢とは、
道を借りる兵法ではない。

入口で形成された認知を普遍化し、
やがて前提そのものへ変える計略なのである。
`,

  "principle": `
信頼とは道徳ではない。

認知資源を節約するため、
過去の成功体験を未来へ一般化する認知の働きである。

一度安全だと判断した対象は、
以後も安全だという認知モデルが形成される。

APIやプラットフォームも、
最初は便利な機能として導入されるが、
やがて存在そのものが前提となる。

入口を作ることより、
入口を当たり前へ変えることが本質なのである。
`,

  "breakdown": [
    "小さな許可や協力関係を獲得する",
    "安全な存在という認知モデルを形成する",
    "その認知を別の場面へ普遍化させる",
    "存在そのものを前提へ変える",
    "本来の目的へ自然に到達する"
  ],

  "noteTitle": "仮道伐虢は「協力を装う計略」ではない──認知の普遍化を利用して前提になる計略である",

  "noteUrl": "https://note.com/flying_baby/n/n0c425763e918",

  "relatedStratagems": [10,14,17,21,22,30],

  "relatedIdioms": [],

  "relatedBiases": [
    "Generalization",
    "Schema learning",
    "Trust transfer",
    "Cognitive economy"
  ],

  "relatedConcepts": [
    "普遍化",
    "一般化",
    "認知モデル",
    "信頼",
    "API",
    "プラットフォーム",
    "ロックイン",
    "前提条件"
  ],

  "relatedNotes": [],

  "references": []
},
  {
  "id": 25,
  "name": "偸梁換柱",
  "reading": "とうりょうかんちゅう",
  "english": "Replace the beams and pillars",
  "category": "Background / Stable Infrastructure",

  "bias": "変化盲、背景化、安定性への依存",

  "behavioral": "Change blindness / background processing / predictive processing",

  "summary": "変わらないと思われている基盤を背景化させ、その構造を書き換える。",

  "example": "利用規約変更、サブスク料金改定、UIデザイン変更、API仕様変更、SNSアルゴリズム更新、法制度改正、社内ルール変更",

  "interpretation": `
偸梁換柱は「すり替える計略」ではない。

本質は、人間が変わらない基盤を監視しないことを利用することにある。

人は毎日、
建物、
電気、
水道、
通信、
OS、
APIなどを確認して生きてはいない。

それらが安定しているという前提があるからこそ、
認知資源を本来の目的へ集中できる。

その結果、
変わらないと思われている構造は背景となり、
監視対象から外れる。

偸梁換柱とは、
柱を交換する兵法ではない。

背景となった基盤そのものを書き換える計略なのである。
`,

  "principle": `
安定とは安全ではない。

認知資源を節約するため、
人は変化しない対象を背景として処理する。

注意は変化したものへ向き、
背景となった基盤は監視されなくなる。

だからこそ、
最も重要な土台ほど、
静かに置き換えることが可能になる。

偸梁換柱とは、
背景となった安定構造を利用する兵法なのである。
`,

  "breakdown": [
    "相手が前提として信頼している基盤を把握する",
    "その基盤が背景化していることを確認する",
    "監視されない構造を書き換える",
    "相手は従来の認知モデルを維持する",
    "変更後の構造が新しい前提として定着する"
  ],

  "noteTitle": "偸梁換柱は「すり替える計略」ではない──人は変わらない基盤を監視しない",

  "noteUrl": "https://note.com/flying_baby/n/n8503e3f9ef6c",

  "relatedStratagems": [12,19,21,24],

  "relatedIdioms": [],

  "relatedBiases": [
    "Change blindness",
    "Background processing",
    "Predictive processing",
    "Habituation"
  ],

  "relatedConcepts": [
    "背景化",
    "変化盲",
    "認知資源",
    "安定性",
    "インフラ",
    "認知モデル",
    "前提条件"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 26,
  "name": "指桑罵槐",
  "reading": "しそうばかい",
  "english": "Point at the mulberry, curse the locust",
  "category": "Social Norm / Group Pressure",

  "bias": "集団規範、社会的排除、同調圧力",

  "behavioral": "Norm enforcement / social conformity / ostracism avoidance",

  "summary": "集団規範を想起させ、排除リスクを認知させることで行動を修正させる。",

  "example": "SNSで『普通はこうする』という投稿、名指ししない批判、組織内の全体向け注意、『みんな守っている』というルールの強調、炎上による社会的制裁、暗黙のマナーによる牽制",

  "interpretation": `
指桑罵槐は「遠回しに批判する計略」ではない。

本質は、人間が集団規範から外れることを強く恐れる認知の性質を利用することにある。

人は一対一で批判されるよりも、
「普通ならそうする」
「みんなそうしている」
という表現に強く反応する。

その言葉の背後に、
社会全体の評価を読み取るからである。

指桑罵槐とは、
遠回しに批判する兵法ではない。

集団規範を想起させ、
排除される可能性を認知させることで、
相手が自発的に行動を修正する計略なのである。
`,

  "principle": `
人間は共同体の中で生きることで生存してきた。

そのため、
集団から排除される可能性は、
生存リスクとして強く認知される。

個人の意見であっても、
「社会では普通」
「みんなそうしている」
という形で提示されると、
脳はそれを社会規範として処理し始める。

重要なのは、
実際に全員がそう考えている必要はないことである。

集団規範を想起させるだけで、
排除リスクは十分に機能する。
`,

  "breakdown": [
    "集団規範を想起させる表現を提示する",
    "個人の意見を社会全体の評価として認識させる",
    "集団から外れる可能性を想起させる",
    "排除リスクを認知させる",
    "相手が自発的に行動を修正する"
  ],

  "noteTitle": "指桑罵槐は「遠回しに批判する計略」ではない──集団規範を利用し、排除の圧力を生み出す計略である",

  "noteUrl": "https://note.com/flying_baby/n/nb69b2930c03b",

  "relatedStratagems": [3,10,18,23],

  "relatedIdioms": [],

  "relatedBiases": [
    "Social conformity",
    "Norm enforcement",
    "Ostracism avoidance",
    "Social proof"
  ],

  "relatedConcepts": [
    "集団規範",
    "同調圧力",
    "社会的排除",
    "共同体",
    "社会規範",
    "常識",
    "空気"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 27,
  "name": "仮痴不癲",
  "reading": "かちふてん",
  "english": "Feign foolishness without going mad",
  "category": "Ability Estimation / Cognitive Shortcut",

  "bias": "第一印象効果、ステレオタイプ、能力推定、集団評価",

  "behavioral": "Thin-slice judgment / stereotyping / halo effect / social proof",

  "summary": "能力そのものではなく、能力推定に使われる認知のショートカットを操作する。",

  "example": "初心者を装う営業、弱気に振る舞う交渉、SNSでの肩書き演出、フォロワー数による信頼形成、有名企業出身というブランド、学歴や資格による能力推定、推薦コメント",

  "interpretation": `
仮痴不癲は「愚かなふりをする計略」ではない。

本質は、人間が能力推定を認知のショートカットへ委ねることを利用することにある。

人は他人の能力を直接測ることはできない。

本来なら、
長期間観察し、
多くの状況を比較し、
実績を確認しなければ能力は分からない。

しかし、
それには膨大な認知資源が必要になる。

そのため人は、
第一印象、
肩書き、
服装、
話し方、
周囲の評価などを能力の代理指標として利用する。

仮痴不癲とは、
愚かなふりをする兵法ではない。

能力推定そのものを認知のショートカットへ委ねさせる計略なのである。
`,

  "principle": `
能力は直接観察しなければ分からない。

しかし、
認知資源には限界があるため、
人は能力そのものではなく、
能力らしく見える情報を利用して判断する。

さらに、
集団評価は能力推定を代行する認知システムとして働く。

そのため、
能力ではなく、
能力をどう認知させるかを操作することで、
相手の評価そのものを変えることができる。
`,

  "breakdown": [
    "能力を直接評価しにくい状況を作る",
    "第一印象や肩書きなど代理指標を提示する",
    "集団評価や外部評価を利用する",
    "能力推定を認知のショートカットへ委ねさせる",
    "相手が能力を過小評価または過大評価する"
  ],

  "noteTitle": "仮痴不癲は「愚かなふりをする計略」ではない──能力推定を認知のショートカットへ委ねさせる計略である",

  "noteUrl": "https://note.com/flying_baby/",

  "relatedStratagems": [3,10,14,18,26],

  "relatedIdioms": [],

  "relatedBiases": [
    "Halo effect",
    "Thin-slice judgment",
    "Stereotyping",
    "Social proof",
    "Authority bias"
  ],

  "relatedConcepts": [
    "能力推定",
    "第一印象",
    "認知のショートカット",
    "代理指標",
    "集団評価",
    "ステレオタイプ",
    "肩書き"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 28,
  "name": "上屋抽梯",
  "reading": "じょうおくちゅうてい",
  "english": "Remove the ladder after ascending the roof",
  "category": "Commitment / Exit Cost",

  "bias": "サンクコスト、コミットメント・エスカレーション、損失回避",

  "behavioral": "Sunk cost fallacy / escalation of commitment / loss aversion",

  "summary": "コミット後の認知を利用し、撤退コストを認知させることで継続を選ばせる。",

  "example": "無料トライアル後の有料移行、データ移行コストの高いSaaS、チーム導入済みシステム、サブスクリプション、オンラインゲームの育成データ、資格学習、ポイント制度や会員ランク",

  "interpretation": `
上屋抽梯は「逃げ道を断つ計略」ではない。

本質は、人間が一度コミットすると、
撤退による損失を強く意識する認知の性質を利用することにある。

人は行動する前と、
行動した後では意思決定の基準が変わる。

始める前は、
「やるか、やらないか」
を比較している。

しかし、
時間、お金、労力、人間関係などを投資すると、
判断基準は
「ここまでの投資を失うか、続けるか」
へ変化する。

上屋抽梯とは、
逃げ道を断つ兵法ではない。

コミット後の認知を利用し、
撤退を困難にする計略なのである。
`,

  "principle": `
撤退コストは物理的な障害ではない。

人が失うものを大きく認知することで生まれる。

実際に退出できるかどうかではなく、
「ここでやめるともったいない」
という認知が選択を固定する。

関門捉賊が入口を設計する兵法なら、
上屋抽梯は出口を設計する兵法なのである。
`,

  "breakdown": [
    "相手に最初のコミットを行わせる",
    "時間・労力・資金などの投資を積み重ねさせる",
    "撤退による損失を強く認知させる",
    "継続する方が合理的だと認識させる",
    "選択を固定し撤退を困難にする"
  ],

  "noteTitle": "上屋抽梯は「逃げ道を断つ計略」ではない──コミット後の認知を利用し、撤退を困難にする計略である",

  "noteUrl": "https://note.com/flying_baby/n/nf4bb20b3981b",

  "relatedStratagems": [22,24,30],

  "relatedIdioms": [],

  "relatedBiases": [
    "Sunk cost fallacy",
    "Escalation of commitment",
    "Loss aversion",
    "Status quo bias"
  ],

  "relatedConcepts": [
    "コミットメント",
    "撤退コスト",
    "サンクコスト",
    "ロックイン",
    "継続バイアス",
    "意思決定"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 29,
  "name": "樹上開花",
  "reading": "じゅじょうかいか",
  "english": "Decorate the tree with blossoms",
  "category": "Evaluation / Signaling",

  "bias": "シグナリング、ハロー効果、代理指標への依存",

  "behavioral": "Signaling theory / Halo effect / Proxy evaluation",

  "summary": "評価システムが採用する代理シグナルを操作し、実体以上の評価を獲得する。",

  "example": "ブランドデザイン、高級ホテルの内装、Apple製品のパッケージ、展示会ブース、SNSのフォロワー数、WebサイトやUIデザイン、学歴や肩書き",

  "interpretation": "樹上開花は「実体を飾る計略」ではない。\n\n本質は、人間が実体そのものではなく、評価システムが採用するシグナルによって対象を評価することにある。\n\n人は対象を完全に理解してから判断しているわけではない。\n\n身なり、ブランド、肩書き、フォロワー数、デザインなど、能力そのものではない情報を利用し、実体を推測している。\n\nつまり評価は、\n実体 → 評価\nではなく、\nシグナル → 実体の推測 → 評価\nという流れで形成される。\n\n樹上開花とは、評価システムが採用している代理指標を操作し、実体以上の評価を獲得する計略なのである。",

  "principle": "人間はすべてを直接評価することはできない。\n\n限られた認知資源の中で、評価しやすい特徴を代理指標として利用する。\n\nブランド、デザイン、肩書き、フォロワー数、話し方、服装などは実体ではない。\n\nしかし、それらは実体を推測するシグナルとして機能し、評価の入り口となる。\n\n評価システムが採用するシグナルを設計することで、実体そのものより先に評価を変えることができる。",

  "breakdown": [
    "評価システムが採用する代理指標を把握する",
    "評価に利用されるシグナルを設計する",
    "相手に実体を推測させる",
    "実体以上の評価を形成する",
    "評価の変化が実体への期待を強化する"
  ],

  "noteTitle": "樹上開花は「実体を飾る計略」ではない──評価システムが採用するシグナルを操作する計略である",

  "noteUrl": "https://note.com/flying_baby/n/n19639fa94482",

  "relatedStratagems": [7,10,14,21,30],

  "relatedIdioms": [],

  "relatedBiases": [
    "Signaling theory",
    "Halo effect",
    "Proxy evaluation",
    "Attribute substitution"
  ],

  "relatedConcepts": [
    "シグナリング",
    "代理指標",
    "評価システム",
    "ブランド",
    "第一印象",
    "ルッキズム",
    "UIデザイン",
    "社会的シグナル"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 30,
  "name": "反客為主",
  "reading": "はんかくいしゅ",
  "english": "Turn from guest into host",

  "category": "Dependency / Negotiation Power",

  "bias": "依存関係、交渉力、ロックイン",

  "behavioral": "Dependency theory / Lock-in effect / Power asymmetry",

  "summary": "依存関係を形成し、その依存から生まれる交渉力によって潜在的な主導権を顕在化させる。",

  "example": "巨大顧客への売上依存、App Store・Google Playへの依存、クラウドサービスへの依存、APIへの依存、外部委託先への依存、SNSプラットフォームへの依存",

  "interpretation": "反客為主は「客が主人になる計略」ではない。\n\n本質は、依存関係から生まれる交渉力を利用することにある。\n\n主導権は突然移動するものではない。\n\n人は相手へ依存した瞬間から、その相手の要求を無視しにくくなる。\n\n売上、技術、情報、集客など、依存対象が大きいほど、その相手は立場に関係なく意思決定へ影響を及ぼす。\n\nつまり、反客為主とは客が主人へ変化する兵法ではない。\n\n依存関係を形成し、その依存によって潜在的に存在していた主導権を顕在化させる計略なのである。",

  "principle": "力は肩書きや立場から生まれるのではない。\n\n人は重要な資源を相手へ依存すると、その資源を失うコストを避けるため、相手の要望を受け入れやすくなる。\n\n依存される側は、命令しなくても意思決定へ影響を与えられる。\n\n主導権とは権限ではなく、依存関係が生み出す交渉力なのである。",

  "breakdown": [
    "相手が依存する価値を提供する",
    "依存関係を継続的に形成する",
    "相手の代替コストを高める",
    "依存による交渉力を獲得する",
    "潜在的な主導権を顕在化させる"
  ],

  "noteTitle": "反客為主は「客が主人になる計略」ではない──依存関係を利用して主導権を顕在化させる計略である",

  "noteUrl": "https://note.com/flying_baby/n/nba46c6578022",

  "relatedStratagems": [3,18,23,24],

  "relatedIdioms": [],

  "relatedBiases": [
    "Dependency theory",
    "Lock-in effect",
    "Power asymmetry",
    "Switching cost"
  ],

  "relatedConcepts": [
    "依存関係",
    "交渉力",
    "主導権",
    "ロックイン",
    "プラットフォーム",
    "API",
    "スイッチングコスト",
    "ベンダーロックイン"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 31,
  "name": "美人計",
  "reading": "びじんけい",
  "english": "The Beauty Trap",

  "category": "Reward / Motivation",

  "bias": "報酬予測、欲望、インセンティブ、価値判断",

  "behavioral": "Reward prediction / Incentive salience / Temporal discounting",

  "summary": "人間の報酬系を刺激し、欲望によって判断の重み付けを変える。",

  "example": "恋愛詐欺、高額投資の甘い勧誘、インフルエンサー広告、「限定」「今だけ」の販売手法、ガチャ演出、ブランド戦略、SNSの承認獲得",

  "interpretation": "美人計は「美女を使う計略」ではない。\n\n本質は、人間の報酬系を刺激し、判断の重み付けを変えることにある。\n\n人は常に合理的な判断をしているわけではない。\n\n魅力や期待、利益などの報酬を感じると、その報酬に対する期待が他の判断材料よりも強く評価される。\n\nつまり、判断能力が失われるのではない。\n\n報酬への期待によって、意思決定の優先順位そのものが変化するのである。\n\n美人計とは、美女を利用する兵法ではない。\n\n相手が最も価値を感じる報酬を提示し、欲望によって判断の重みを変える計略なのである。",

  "principle": "欲望とは理性の反対ではない。\n\n人間は複数の価値を同時に評価し、それぞれへ重みを付けながら意思決定している。\n\n恋愛、金銭、承認、権力、名誉、所属、好奇心など、人によって重要視する報酬は異なる。\n\nさらに状況によっても、その重みは変化する。\n\n報酬系を刺激することは、判断を消すことではなく、意思決定の評価関数そのものを書き換えることなのである。",

  "breakdown": [
    "相手が最も価値を感じる報酬を把握する",
    "報酬への期待を形成する",
    "報酬の重みを他の判断材料より高める",
    "判断基準の優先順位を変化させる",
    "望む意思決定を自然に選択させる"
  ],

  "noteTitle": "美人計は「美女を使う計略」ではない──人間の報酬系を刺激し、判断の重みを変える計略である",

  "noteUrl": "https://note.com/flying_baby/n/n58e5a0431144",

  "relatedStratagems": [3,10,16,17,29],

  "relatedIdioms": [],

  "relatedBiases": [
    "Reward prediction",
    "Incentive salience",
    "Temporal discounting",
    "Motivated reasoning"
  ],

  "relatedConcepts": [
    "報酬系",
    "欲望",
    "価値判断",
    "意思決定",
    "ドーパミン",
    "インセンティブ",
    "承認欲求",
    "限定効果"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 32,
  "name": "空城計",
  "reading": "くうじょうけい",
  "english": "The Empty Fort Strategy",

  "category": "Inference / Uncertainty",

  "bias": "不確実性、推論、曖昧性回避、損失回避",

  "behavioral": "Predictive processing / uncertainty reduction / ambiguity aversion",

  "summary": "情報の空白を利用し、相手自身に推論させることで判断を迷わせる。",

  "example": "交渉で即答しない、企業が次の戦略を伏せる、ゲームで意図的に動かない、AIが一部情報を伏せる、沈黙による駆け引き",

  "interpretation": `
空城計は「ハッタリの計略」ではない。

本質は、人間が情報の空白を放置できず、
自ら推論を始めることにある。

人は未知をそのまま維持することが苦手である。

情報が不足すると、
経験・知識・恐怖・期待を利用し、
空白を埋める物語を自ら構築する。

空城計とは、
敵を騙す兵法ではない。

情報の空白そのものを利用し、
相手自身に推論させる計略なのである。
`,

  "principle": `
脳は未来を予測するために存在する。

そのため、
情報が欠けると、
何が起きているのかを推論し、
最も妥当だと思われる物語を補完する。

可能性が複数存在すると、
認知資源はその比較へ使われ、
判断は遅れやすくなる。

不確実性は、
相手の認知活動そのものを増加させるのである。
`,

  "breakdown": [
    "情報を意図的に欠落させる",
    "相手に情報不足を認識させる",
    "相手自身が複数の可能性を推論する",
    "不確実性によって判断が遅れる",
    "その間に時間・行動・選択の自由を確保する"
  ],

  "noteTitle": "空城計は「ハッタリの計略」ではない──人は情報が欠けると、自ら物語を作り始める",

  "noteUrl": "https://note.com/flying_baby/n/n7c0c92d99d35",

  "relatedStratagems": [
    8,
    13,
    16,
    20,
    33
  ],

  "relatedIdioms": [],

  "relatedBiases": [
    "Predictive processing",
    "Ambiguity aversion",
    "Need for cognitive closure",
    "Loss aversion"
  ],

  "relatedConcepts": [
    "推論",
    "予測",
    "情報の空白",
    "不確実性",
    "認知資源",
    "物語生成",
    "意思決定"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
  "id": 33,
  "name": "反間計",
  "reading": "はんかんけい",
  "english": "Counter-Espionage / Reverse Use of Trusted Channels",

  "category": "Trust / Information Channel",

  "bias": "信頼ヒューリスティック、情報源バイアス、権威への依存",

  "behavioral": "Trust heuristic / Source credibility / Cognitive offloading",

  "summary": "信頼された情報経路を逆利用し、誤った認知を形成させる。",

  "example": "偽ニュース、なりすましメール、SNSのデマ、内部リーク、AIによる偽画像・偽音声、乗っ取られた公式アカウント",

  "interpretation": `
反間計は「間者を使う計略」ではない。

本質は、人間が信頼を認知のショートカットとして利用することにある。

人は毎回すべての情報を検証して判断しているわけではない。

認知コストを節約するため、
「この人が言うなら正しい」
「この媒体なら信用できる」
という信頼された情報経路を利用して判断している。

反間計とは、
敵の間者を利用する兵法ではない。

相手が信頼している情報経路そのものを逆利用し、
誤った認知を形成させる計略なのである。
`,

  "principle": `
信頼とは道徳ではない。

認知資源を節約するため、
人は情報そのものよりも、
誰が伝えたかを判断材料として利用する。

信頼された情報源ほど検証コストは低下し、
内容も受け入れられやすくなる。

そのため、
情報経路が汚染されると、
人は誤った認知を形成しやすくなる。
`,

  "breakdown": [
    "相手が信頼している情報経路を把握する",
    "その情報経路へ介入する",
    "信頼を維持したまま誤情報を流す",
    "相手は検証せず認知を形成する",
    "判断・意思決定が歪む",
    "組織や人間関係の信頼が崩壊する"
  ],

  "noteTitle": "反間計は「間者を使う計略」ではない──人は信頼を認知のショートカットとして利用する",

  "noteUrl": "https://note.com/flying_baby/n/n8601783986cb",

  "relatedStratagems": [
    10,
    14,
    18,
    21,
    24,
    31
  ],

  "relatedIdioms": [],

  "relatedBiases": [
    "Trust heuristic",
    "Source credibility",
    "Authority bias",
    "Cognitive offloading",
    "Truth-default theory"
  ],

  "relatedConcepts": [
    "信頼",
    "認知のショートカット",
    "情報源",
    "情報経路",
    "認知資源",
    "情報操作",
    "偽情報",
    "離間"
  ],

  "relatedNotes": [],

  "references": []
  },
  {
    id: 34,
    name: "苦肉計",
    reading: "くにくけい",
    english: "Inflict injury on oneself to win trust",
    category: "Credibility",
    bias: "犠牲を払う者は本気だと見なす",
    behavioral: "Costly signaling / credibility heuristic",
    summary: "自分に痛みを与えることで、本気度や信用を演出する。",
    example: "身銭を切るPR、謝罪演出、内部告発の信頼性",
    interpretation: `
`,
    principle: `
`,
    breakdown: [],
    noteTitle: "",
    noteUrl: "",
    relatedStratagems: [],
    relatedIdioms: [],
    relatedBiases: [],
    relatedConcepts: [],
    relatedNotes: [],
    references: []
  },
  {
    id: 35,
    name: "連環計",
    reading: "れんかんけい",
    english: "Chain stratagems together",
    category: "System",
    bias: "複数要因の連鎖を見落とす",
    behavioral: "Complexity neglect / systems trap",
    summary: "単独ではなく、複数の仕掛けを連鎖させて逃げにくくする。",
    example: "複数施策の組み合わせ、依存関係で縛る",
    interpretation: `
`,
    principle: `
`,
    breakdown: [],
    noteTitle: "",
    noteUrl: "",
    relatedStratagems: [],
    relatedIdioms: [],
    relatedBiases: [],
    relatedConcepts: [],
    relatedNotes: [],
    references: []
  },
  {
    id: 36,
    name: "走為上",
    reading: "そういじょう",
    english: "If all else fails, retreat",
    category: "Exit",
    bias: "撤退の恥、損切り回避",
    behavioral: "Sunk cost fallacy / loss aversion",
    summary: "逃げることを敗北ではなく、合理的な選択肢として扱う。",
    example: "撤退判断、ピボット、プロジェクト停止",
    interpretation: `
`,
    principle: `
`,
    breakdown: [],
    noteTitle: "",
    noteUrl: "",
    relatedStratagems: [],
    relatedIdioms: [],
    relatedBiases: [],
    relatedConcepts: [],
    relatedNotes: [],
    references: []
  }
];

const cards = document.getElementById('cards');
const search = document.getElementById('search');
const category = document.getElementById('category');
const categoryCards = document.getElementById('categoryCards');
const categoryCount = document.getElementById('categoryCount');
const detailPane = document.getElementById('detailPane');
const mobileDetailDrawer = document.getElementById('mobileDetailDrawer');
const mobileDetailContent = document.getElementById('mobileDetailContent');
const mobileDetailNumber = document.getElementById('mobileDetailNumber');
const closeDetailButton = document.getElementById('closeDetailButton');
const treeViewButton = document.getElementById('treeViewButton');
const listViewButton = document.getElementById('listViewButton');

const categories = [...new Set(stratagems.map((stratagem) => stratagem.category))].sort();
const mobileQuery = window.matchMedia('(max-width: 899px)');
let selectedStratagemId = stratagems[0]?.id ?? null;
let atlasView = 'tree';

categoryCount.textContent = categories.length;

for (const categoryName of categories) {
  const option = document.createElement('option');
  option.value = categoryName;
  option.textContent = categoryName;
  category.appendChild(option);
}

function hasContent(value) {
  return typeof value === 'string' && value.trim() !== '';
}

function hasItems(value) {
  return Array.isArray(value) && value.length > 0;
}

function toSearchText(value) {
  if (Array.isArray(value)) return value.map(toSearchText).join(' ');
  if (value && typeof value === 'object') return Object.values(value).map(toSearchText).join(' ');
  return String(value ?? '');
}

function renderOptionalSection(title, content) {
  if (!hasContent(content)) return '';

  return '<div class="optional-section"><p><b>' + title + ':</b> ' + content + '</p></div>';
}

function renderBreakdown(items) {
  if (!hasItems(items)) return '';

  return '<div class="optional-section"><p><b>Breakdown:</b></p><ul class="breakdown-list">'
    + items.map((item) => '<li>' + item + '</li>').join('')
    + '</ul></div>';
}

function renderNoteLink(stratagem) {
  if (!hasContent(stratagem.noteUrl)) return '';

  return '<a class="note-link" href="' + stratagem.noteUrl + '" target="_blank" rel="noopener noreferrer">Read Note &rarr;</a>';
}

function getFilteredStratagems() {
  const query = search.value.toLowerCase().trim();
  const selectedCategory = category.value;
  return stratagems
    .filter((stratagem) => selectedCategory === 'all' || stratagem.category === selectedCategory)
    .filter((stratagem) => toSearchText(stratagem).toLowerCase().includes(query));
}

function getStratagemById(id) {
  return stratagems.find((stratagem) => stratagem.id === id) ?? stratagems[0] ?? null;
}

function setActiveView(nextView) {
  atlasView = nextView;
  treeViewButton.classList.toggle('active', atlasView === 'tree');
  listViewButton.classList.toggle('active', atlasView === 'list');
  render();
}

function renderCategoryCards() {
  categoryCards.innerHTML = '';

  categories.forEach((categoryName) => {
    const count = stratagems.filter((stratagem) => stratagem.category === categoryName).length;
    const div = document.createElement('div');
    div.className = 'category-card';
    div.innerHTML = '<strong>' + categoryName + '</strong><span>' + count + ' stratagem' + (count > 1 ? 's' : '') + ' mapped</span>';
    div.addEventListener('click', () => {
      category.value = categoryName;
      render();
      document.getElementById('atlas').scrollIntoView({ behavior: 'smooth' });
    });
    categoryCards.appendChild(div);
  });
}

function renderStratagemDetail(stratagem) {
  if (!stratagem) {
    return '<article class="stratagem-card empty-state"><h3>No stratagem selected</h3><p class="summary">一覧から計略を選択してください。</p></article>';
  }

  return [
    '<article class="stratagem-card">',
    '<div class="card-top">',
    '<span class="number">#' + String(stratagem.id).padStart(2, '0') + '</span>',
    '<span class="badge">' + stratagem.category + '</span>',
    '</div>',
    '<h3 id="mobileDetailTitle">' + stratagem.name + '</h3>',
    '<p class="reading">' + stratagem.reading + '</p>',
    '<p class="english">' + stratagem.english + '</p>',
    '<p class="summary">' + stratagem.summary + '</p>',
    '<div class="meta">',
    '<p><b>Bias:</b> ' + stratagem.bias + '</p>',
    '<p><b>Behavioral reading:</b> ' + stratagem.behavioral + '</p>',
    '<p><b>Modern example:</b> ' + stratagem.example + '</p>',
    renderOptionalSection('Jinn Interpretation', stratagem.interpretation),
    renderOptionalSection('Cognitive Principle', stratagem.principle),
    renderBreakdown(stratagem.breakdown),
    renderNoteLink(stratagem),
    '</div>',
    '</article>'
  ].join('');
}

function renderNoResults() {
  cards.innerHTML = '<article class="stratagem-nav-card empty-state"><h3>No results</h3><p class="summary">別のキーワードで検索してください。</p></article>';
  detailPane.innerHTML = renderStratagemDetail(null);
}

function renderNavCard(stratagem) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'stratagem-nav-card';
  button.dataset.id = String(stratagem.id);
  button.classList.toggle('active', stratagem.id === selectedStratagemId);
  button.innerHTML = [
    '<div class="nav-card-top">',
    '<span class="number">#' + String(stratagem.id).padStart(2, '0') + '</span>',
    '<span class="badge">' + stratagem.category + '</span>',
    '</div>',
    '<h3>' + stratagem.name + '</h3>',
    '<p class="reading">' + stratagem.reading + '</p>',
    '<p class="english">' + stratagem.english + '</p>'
  ].join('');
  button.addEventListener('click', () => selectStratagem(stratagem.id));
  return button;
}

function renderList(filtered) {
  cards.className = 'stratagem-list list-view';
  filtered.forEach((stratagem) => {
    cards.appendChild(renderNavCard(stratagem));
  });
}

function renderTree(filtered) {
  cards.className = 'stratagem-list tree-view';
  categories.forEach((categoryName) => {
    const items = filtered.filter((stratagem) => stratagem.category === categoryName);
    if (!items.length) return;

    const group = document.createElement('section');
    group.className = 'category-group';
    const heading = document.createElement('h3');
    heading.className = 'category-heading';
    heading.textContent = categoryName;
    group.appendChild(heading);

    items.forEach((stratagem) => {
      group.appendChild(renderNavCard(stratagem));
    });

    cards.appendChild(group);
  });
}

function selectStratagem(id) {
  selectedStratagemId = id;
  const selected = getStratagemById(selectedStratagemId);
  detailPane.innerHTML = renderStratagemDetail(selected);
  mobileDetailContent.innerHTML = renderStratagemDetail(selected);
  mobileDetailNumber.textContent = '#' + String(selected.id).padStart(2, '0');

  [...cards.querySelectorAll('.stratagem-nav-card')].forEach((card) => {
    card.classList.toggle('active', Number(card.dataset.id) === selectedStratagemId);
  });

  if (mobileQuery.matches) {
    openMobileDetail();
  }
}

function openMobileDetail() {
  mobileDetailDrawer.classList.add('open');
  mobileDetailDrawer.setAttribute('aria-hidden', 'false');
  document.body.classList.add('detail-drawer-open');
  mobileDetailContent.scrollTop = 0;
  closeDetailButton.focus({ preventScroll: true });
}

function closeMobileDetail() {
  mobileDetailDrawer.classList.remove('open');
  mobileDetailDrawer.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('detail-drawer-open');
}

function render() {
  const previousScrollTop = cards.parentElement?.scrollTop ?? 0;
  const filtered = getFilteredStratagems();

  cards.innerHTML = '';

  if (!filtered.length) {
    renderNoResults();
    return;
  }

  if (!filtered.some((stratagem) => stratagem.id === selectedStratagemId)) {
    selectedStratagemId = filtered[0].id;
  }

  if (atlasView === 'tree') {
    renderTree(filtered);
  } else {
    renderList(filtered);
  }

  const selected = getStratagemById(selectedStratagemId);
  detailPane.innerHTML = renderStratagemDetail(selected);
  mobileDetailContent.innerHTML = renderStratagemDetail(selected);
  mobileDetailNumber.textContent = '#' + String(selected.id).padStart(2, '0');

  requestAnimationFrame(() => {
    if (cards.parentElement) {
      cards.parentElement.scrollTop = previousScrollTop;
    }
  });
}

search.addEventListener('input', render);
category.addEventListener('change', render);
treeViewButton.addEventListener('click', () => setActiveView('tree'));
listViewButton.addEventListener('click', () => setActiveView('list'));
closeDetailButton.addEventListener('click', closeMobileDetail);
mobileDetailDrawer.addEventListener('click', (event) => {
  if (event.target.matches('[data-close-detail]')) {
    closeMobileDetail();
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && mobileDetailDrawer.classList.contains('open')) {
    closeMobileDetail();
  }
});

renderCategoryCards();
render();
