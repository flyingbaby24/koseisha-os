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
    id: 5,
    name: "趁火打劫",
    reading: "ちんかだこう",
    english: "Loot a burning house",
    category: "Loss / Crisis",
    bias: "危機時の損失回避、焦燥判断",
    behavioral: "Loss aversion / scarcity under stress",
    summary: "相手が混乱や損失に直面している時に、その判断の歪みを利用する。",
    example: "市場急落時の買収、炎上中の競合から顧客獲得",
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
    id: 6,
    name: "声東撃西",
    reading: "せいとうげきせい",
    english: "Make noise in the east, attack in the west",
    category: "Attention",
    bias: "注意誘導、一点集中による盲点化",
    behavioral: "Attentional bias / misdirection",
    summary: "目立つ情報で注意を誘導し、本命を見えにくくする。",
    example: "広告・政治・SNSで本命から視線を逸らす",
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
    id: 7,
    name: "無中生有",
    reading: "むちゅうしょうゆう",
    english: "Create something from nothing",
    category: "Reality Construction",
    bias: "真実性錯覚、存在の錯覚、反復効果",
    behavioral: "Illusory truth effect / availability heuristic",
    summary: "実体が薄いものでも、反復・演出・噂によって存在感が生まれる。",
    example: "ステマ、噂、ブランド人気の演出",
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
    id: 8,
    name: "暗渡陳倉",
    reading: "あんとちんそう",
    english: "Secretly cross at Chencang",
    category: "Expectation",
    bias: "予想固定、見えている経路への過信",
    behavioral: "Confirmation bias / inattentional blindness",
    summary: "見えている動きで相手の予測を固定し、別経路で本命を進める。",
    example: "表向きのロードマップと裏の開発、競合の盲点攻略",
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
    id: 9,
    name: "隔岸観火",
    reading: "かくがんかんか",
    english: "Watch the fire from across the river",
    category: "Social / Inaction",
    bias: "傍観者効果、介入コスト回避",
    behavioral: "Bystander effect / strategic delay",
    summary: "他者の混乱に介入せず、消耗や変化を待つ。",
    example: "競合同士の消耗を待つ、炎上を静観する",
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
    id: 10,
    name: "笑裏蔵刀",
    reading: "しょうりぞうとう",
    english: "Hide a knife behind a smile",
    category: "Trust / Impression",
    bias: "ハロー効果、好意による警戒低下",
    behavioral: "Halo effect / affect heuristic",
    summary: "好意的な外見や態度で警戒を下げ、裏の意図を隠す。",
    example: "営業トーク、政治的微笑、親切を装った誘導",
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
    id: 11,
    name: "李代桃僵",
    reading: "りだいとうきょう",
    english: "Sacrifice the plum tree to preserve the peach tree",
    category: "Trade-off",
    bias: "代替損失の受容、損切り判断",
    behavioral: "Sunk cost control / substitution",
    summary: "重要なものを守るために、別のものを犠牲にする。",
    example: "小さな部門を切って本体を守る、炎上時の責任者交代",
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
    id: 12,
    name: "順手牽羊",
    reading: "じゅんしゅけんよう",
    english: "Take the opportunity to steal a goat",
    category: "Opportunity",
    bias: "小さな損失の軽視、注意外の損失",
    behavioral: "Mental accounting / salience bias",
    summary: "目立たない小さな機会を拾い、相手が軽視する損失を利用する。",
    example: "追加手数料、サブスクの小額課金、細かな権限取得",
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
    id: 13,
    name: "打草驚蛇",
    reading: "だそうきょうだ",
    english: "Beat the grass to startle the snake",
    category: "Detection",
    bias: "反応からの推定、警戒反応の観察",
    behavioral: "Signaling / information elicitation",
    summary: "小さな刺激を与え、隠れた相手や本音の反応を見る。",
    example: "小さな質問で本音を見る、セキュリティ監査",
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
    id: 14,
    name: "借屍還魂",
    reading: "しゃくしかんこん",
    english: "Borrow a corpse to revive the soul",
    category: "Authority / Legacy",
    bias: "権威バイアス、過去資産への信頼",
    behavioral: "Authority bias / nostalgia effect",
    summary: "既にある名義・権威・過去資産を利用して新しい意味を宿す。",
    example: "古いブランドの復活、権威ある名義を借りる",
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
    id: 15,
    name: "調虎離山",
    reading: "ちょうこりざん",
    english: "Lure the tiger away from the mountain",
    category: "Context",
    bias: "環境依存の強さ、ホーム優位",
    behavioral: "Context effect / home advantage",
    summary: "相手を得意な場所・条件から引き離し、能力を弱める。",
    example: "相手の得意領域から引き離す、プラットフォーム変更",
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
    id: 16,
    name: "欲擒故縦",
    reading: "よくきんこしょう",
    english: "To capture, first let go",
    category: "Reactance",
    bias: "自由を与えられると警戒が下がる、心理的リアクタンス",
    behavioral: "Reactance theory / commitment",
    summary: "追い詰めず、あえて自由を与えることで相手の自発的接近を誘う。",
    example: "営業で押さずに選ばせる、無料トライアル",
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
    id: 17,
    name: "抛磚引玉",
    reading: "ほうせんいんぎょく",
    english: "Throw a brick to attract jade",
    category: "Reciprocity / Bait",
    bias: "返報性、アンカリング",
    behavioral: "Reciprocity / anchoring",
    summary: "小さなものを差し出し、より大きな反応や価値を引き出す。",
    example: "無料資料、安価な入口商品、釣り投稿",
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
    id: 18,
    name: "擒賊擒王",
    reading: "きんぞくきんおう",
    english: "Capture the leader to capture the bandits",
    category: "Hierarchy",
    bias: "中心人物への依存、権威集中",
    behavioral: "Network centrality / authority bias",
    summary: "集団全体ではなく、中心人物・権威・キーノードを狙う。",
    example: "キーマン攻略、インフルエンサー獲得",
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
    id: 19,
    name: "釜底抽薪",
    reading: "ふていちゅうしん",
    english: "Remove the firewood from under the pot",
    category: "Root Cause",
    bias: "表面現象への注意偏り",
    behavioral: "Root cause intervention / systems thinking",
    summary: "表面の火ではなく、火を支える燃料を取り除く。",
    example: "競合の資金源・供給網・流通を断つ",
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
    id: 20,
    name: "渾水摸魚",
    reading: "こんすいぼぎょ",
    english: "Fish in troubled waters",
    category: "Chaos",
    bias: "混乱時の注意低下、認知負荷",
    behavioral: "Cognitive load / ambiguity exploitation",
    summary: "混乱している環境では判断精度が落ちる。その隙を利用する。",
    example: "制度変更時の便乗、炎上中の情報操作",
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
    id: 21,
    name: "金蝉脱殻",
    reading: "きんせんだっかく",
    english: "Shed the shell like a golden cicada",
    category: "Appearance",
    bias: "外形維持による継続錯覚",
    behavioral: "Continuity bias / framing",
    summary: "外見や看板を残しながら、中身だけを入れ替える。",
    example: "看板だけ残して中身を変える、ブランド移行",
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
    id: 22,
    name: "関門捉賊",
    reading: "かんもんそくぞく",
    english: "Shut the door to catch the thief",
    category: "Constraint",
    bias: "逃げ道を失うと選択肢が狭まる",
    behavioral: "Choice architecture / constraint strategy",
    summary: "出口を塞ぎ、相手の選択肢を限定する。",
    example: "契約条項、囲い込み、解約導線の制限",
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
    id: 23,
    name: "遠交近攻",
    reading: "えんこうきんこう",
    english: "Befriend distant states while attacking nearby ones",
    category: "Distance / Alliance",
    bias: "近接脅威の過大評価、遠方リスクの過小評価",
    behavioral: "Psychological distance / coalition strategy",
    summary: "遠方と組み、近くの脅威を処理する。心理的距離を利用する計略。",
    example: "遠い業界と提携し、近い競合を攻める",
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
    id: 24,
    name: "仮道伐虢",
    reading: "かどうばっかく",
    english: "Borrow a path to attack Guo",
    category: "Access",
    bias: "協力要請への油断、目的の誤認",
    behavioral: "Foot-in-the-door / trust exploitation",
    summary: "通行や協力を名目にアクセス権を得て、本来の目的を達成する。",
    example: "API連携から市場侵入、提携を入口にする",
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
    id: 25,
    name: "偸梁換柱",
    reading: "とうりょうかんちゅう",
    english: "Replace the beams and pillars",
    category: "Substitution",
    bias: "構造変化への気づきにくさ",
    behavioral: "Change blindness / substitution effect",
    summary: "柱や梁のような重要構造を、気づかれないうちに入れ替える。",
    example: "規約改定、UI変更で主導権を移す",
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
    id: 26,
    name: "指桑罵槐",
    reading: "しそうばかい",
    english: "Point at the mulberry, curse the locust",
    category: "Indirect Signaling",
    bias: "間接批判の読み取り、社会的圧力",
    behavioral: "Signaling / social norm enforcement",
    summary: "直接言わず、別対象を叱ることで本命に圧力をかける。",
    example: "名指しせず牽制、組織内メッセージ",
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
    id: 27,
    name: "仮痴不癲",
    reading: "かちふてん",
    english: "Feign foolishness without going mad",
    category: "Impression",
    bias: "第一印象効果、ステレオタイプ、能力過小評価",
    behavioral: "Stereotyping / first impression effect",
    summary: "愚者のふりをして、相手の見下しや油断を引き出す。",
    example: "弱そうに見せて油断させる、初心者を装う",
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
    id: 28,
    name: "上屋抽梯",
    reading: "じょうおくちゅうてい",
    english: "Remove the ladder after the enemy climbs up",
    category: "Commitment",
    bias: "コミット後の撤退困難、損切り不能",
    behavioral: "Sunk cost fallacy / escalation of commitment",
    summary: "相手を一度乗せた後、退路を断って選択を固定する。",
    example: "導入後に条件変更、撤退コストを上げる",
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
    id: 29,
    name: "樹上開花",
    reading: "じゅじょうかいか",
    english: "Make flowers bloom on a tree",
    category: "Signal Amplification",
    bias: "見せかけの規模、装飾による過大評価",
    behavioral: "Signaling / halo effect",
    summary: "実体以上に華やかに見せ、相手の評価を増幅させる。",
    example: "実態以上に大きく見せるPR、展示会演出",
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
    id: 30,
    name: "反客為主",
    reading: "はんかくいしゅ",
    english: "Turn from guest into host",
    category: "Control",
    bias: "既成事実化、主導権移転への鈍感さ",
    behavioral: "Endowment effect / default effect",
    summary: "客の立場から入り込み、いつの間にか主導権を握る。",
    example: "外部委託先が主導権を握る、プラットフォーム依存",
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
    id: 31,
    name: "美人計",
    reading: "びじんけい",
    english: "Use beauty as a trap",
    category: "Desire",
    bias: "魅力バイアス、感情による判断歪み",
    behavioral: "Affect heuristic / attractiveness bias",
    summary: "魅力や欲望によって判断力を鈍らせる。",
    example: "広告モデル、恋愛詐欺、感情訴求",
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
    id: 32,
    name: "空城計",
    reading: "くうじょうけい",
    english: "Empty fort strategy",
    category: "Uncertainty",
    bias: "情報不足時の物語補完、過剰推論",
    behavioral: "Ambiguity aversion / predictive inference",
    summary: "情報の空白を作り、相手自身に物語を補完させる。",
    example: "沈黙による深読み、OSSの堂々公開、投資家の推測",
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
    id: 33,
    name: "反間計",
    reading: "はんかんけい",
    english: "Use enemy spies against them",
    category: "Trust / Doubt",
    bias: "疑心暗鬼、信頼ネットワークの破壊",
    behavioral: "Trust erosion / information asymmetry",
    summary: "情報と疑念を使い、相手組織の信頼構造を壊す。",
    example: "内部不信、リーク情報、競合撹乱",
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

const categories = [...new Set(stratagems.map((stratagem) => stratagem.category))].sort();

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

function renderStratagemCard(stratagem) {
  const card = document.createElement('article');
  card.className = 'stratagem-card';
  card.innerHTML = [
    '<div class="card-top">',
    '<span class="number">#' + String(stratagem.id).padStart(2, '0') + '</span>',
    '<span class="badge">' + stratagem.category + '</span>',
    '</div>',
    '<h3>' + stratagem.name + '</h3>',
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
    '</div>'
  ].join('');
  return card;
}

function renderNoResults() {
  cards.innerHTML = '<article class="stratagem-card"><h3>No results</h3><p class="summary">別のキーワードで検索してください。</p></article>';
}

function render() {
  const query = search.value.toLowerCase().trim();
  const selectedCategory = category.value;
  const filtered = stratagems
    .filter((stratagem) => selectedCategory === 'all' || stratagem.category === selectedCategory)
    .filter((stratagem) => toSearchText(stratagem).toLowerCase().includes(query));

  cards.innerHTML = '';

  filtered.forEach((stratagem) => {
    cards.appendChild(renderStratagemCard(stratagem));
  });

  if (!filtered.length) renderNoResults();
}

search.addEventListener('input', render);
category.addEventListener('change', render);

renderCategoryCards();
render();
