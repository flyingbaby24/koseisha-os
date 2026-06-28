const stratagems = [
  {
    name: "瞞天過海",
    english: "Deceive the heavens to cross the sea",
    category: "Normality / Habit",
    bias: "正常性バイアス、慣れによる警戒低下",
    behavioral: "Status quo bias / habituation",
    example: "日常業務に紛れた情報漏洩、いつものUIに紛れた誘導"
  },
  {
    name: "囲魏救趙",
    english: "Besiege Wei to rescue Zhao",
    category: "Attention / Indirect Pressure",
    bias: "注意分散、間接圧力への反応",
    behavioral: "Limited attention / opportunity cost",
    example: "競合の本丸ではなく弱点市場を攻める、交渉で別論点を突く"
  },
  {
    name: "借刀殺人",
    english: "Kill with a borrowed knife",
    category: "Social / Responsibility",
    bias: "責任分散、代理行動、他者利用",
    behavioral: "Diffusion of responsibility / agency problem",
    example: "代理店・インフルエンサー・第三者レビューを使う"
  },
  {
    name: "以逸待労",
    english: "Wait at ease for the exhausted enemy",
    category: "Fatigue / Timing",
    bias: "疲労による判断力低下、焦り",
    behavioral: "Decision fatigue / ego depletion",
    example: "長期交渉、相手が疲れたタイミングで条件提示"
  },
  {
    name: "趁火打劫",
    english: "Loot a burning house",
    category: "Loss / Crisis",
    bias: "危機時の損失回避、焦燥判断",
    behavioral: "Loss aversion / scarcity under stress",
    example: "市場急落時の買収、炎上中の競合から顧客獲得"
  },
  {
    name: "声東撃西",
    english: "Make noise in the east, attack in the west",
    category: "Attention",
    bias: "注意誘導、一点集中による盲点化",
    behavioral: "Attentional bias / misdirection",
    example: "広告・政治・SNSで本命から視線を逸らす"
  },
  {
    name: "無中生有",
    english: "Create something from nothing",
    category: "Reality Construction",
    bias: "真実性錯覚、存在の錯覚、反復効果",
    behavioral: "Illusory truth effect / availability heuristic",
    example: "ステマ、噂、ブランド人気の演出"
  },
  {
    name: "暗渡陳倉",
    english: "Secretly cross at Chencang",
    category: "Expectation",
    bias: "予想固定、見えている経路への過信",
    behavioral: "Confirmation bias / inattentional blindness",
    example: "表向きのロードマップと裏の開発、競合の盲点攻略"
  },
  {
    name: "隔岸観火",
    english: "Watch the fire from across the river",
    category: "Social / Inaction",
    bias: "傍観者効果、介入コスト回避",
    behavioral: "Bystander effect / strategic delay",
    example: "競合同士の消耗を待つ、炎上を静観する"
  },
  {
    name: "笑裏蔵刀",
    english: "Hide a knife behind a smile",
    category: "Trust / Impression",
    bias: "ハロー効果、好意による警戒低下",
    behavioral: "Halo effect / affect heuristic",
    example: "営業トーク、政治的微笑、親切を装った誘導"
  },
  {
    name: "李代桃僵",
    english: "Sacrifice the plum tree to preserve the peach tree",
    category: "Trade-off",
    bias: "代替損失の受容、損切り判断",
    behavioral: "Sunk cost control / substitution",
    example: "小さな部門を切って本体を守る、炎上時の責任者交代"
  },
  {
    name: "順手牽羊",
    english: "Take the opportunity to steal a goat",
    category: "Opportunity",
    bias: "小さな損失の軽視、注意外の損失",
    behavioral: "Mental accounting / salience bias",
    example: "追加手数料、サブスクの小額課金、細かな権限取得"
  },
  {
    name: "打草驚蛇",
    english: "Beat the grass to startle the snake",
    category: "Detection",
    bias: "反応からの推定、警戒反応の観察",
    behavioral: "Signaling / information elicitation",
    example: "小さな質問で本音を見る、セキュリティ監査"
  },
  {
    name: "借屍還魂",
    english: "Borrow a corpse to revive the soul",
    category: "Authority / Legacy",
    bias: "権威バイアス、過去資産への信頼",
    behavioral: "Authority bias / nostalgia effect",
    example: "古いブランドの復活、権威ある名義を借りる"
  },
  {
    name: "調虎離山",
    english: "Lure the tiger away from the mountain",
    category: "Context",
    bias: "環境依存の強さ、ホーム優位",
    behavioral: "Context effect / home advantage",
    example: "相手の得意領域から引き離す、プラットフォーム変更"
  },
  {
    name: "欲擒故縦",
    english: "To capture, first let go",
    category: "Reactance",
    bias: "自由を与えられると警戒が下がる、心理的リアクタンス",
    behavioral: "Reactance theory / commitment",
    example: "営業で押さずに選ばせる、無料トライアル"
  },
  {
    name: "抛磚引玉",
    english: "Throw a brick to attract jade",
    category: "Reciprocity / Bait",
    bias: "返報性、アンカリング",
    behavioral: "Reciprocity / anchoring",
    example: "無料資料、安価な入口商品、釣り投稿"
  },
  {
    name: "擒賊擒王",
    english: "Capture the leader to capture the bandits",
    category: "Hierarchy",
    bias: "中心人物への依存、権威集中",
    behavioral: "Network centrality / authority bias",
    example: "キーマン攻略、インフルエンサー獲得"
  },
  {
    name: "釜底抽薪",
    english: "Remove the firewood from under the pot",
    category: "Root Cause",
    bias: "表面現象への注意偏り",
    behavioral: "Root cause intervention / systems thinking",
    example: "競合の資金源・供給網・流通を断つ"
  },
  {
    name: "渾水摸魚",
    english: "Fish in troubled waters",
    category: "Chaos",
    bias: "混乱時の注意低下、認知負荷",
    behavioral: "Cognitive load / ambiguity exploitation",
    example: "制度変更時の便乗、炎上中の情報操作"
  },
  {
    name: "金蝉脱殻",
    english: "Shed the shell like a golden cicada",
    category: "Appearance",
    bias: "外形維持による継続錯覚",
    behavioral: "Continuity bias / framing",
    example: "看板だけ残して中身を変える、ブランド移行"
  },
  {
    name: "関門捉賊",
    english: "Shut the door to catch the thief",
    category: "Constraint",
    bias: "逃げ道を失うと選択肢が狭まる",
    behavioral: "Choice architecture / constraint strategy",
    example: "契約条項、囲い込み、解約導線の制限"
  },
  {
    name: "遠交近攻",
    english: "Befriend distant states while attacking nearby ones",
    category: "Distance / Alliance",
    bias: "近接脅威の過大評価、遠方リスクの過小評価",
    behavioral: "Psychological distance / coalition strategy",
    example: "遠い業界と提携し、近い競合を攻める"
  },
  {
    name: "仮道伐虢",
    english: "Borrow a path to attack Guo",
    category: "Access",
    bias: "協力要請への油断、目的の誤認",
    behavioral: "Foot-in-the-door / trust exploitation",
    example: "API連携から市場侵入、提携を入口にする"
  },
  {
    name: "偸梁換柱",
    english: "Replace the beams and pillars",
    category: "Substitution",
    bias: "構造変化への気づきにくさ",
    behavioral: "Change blindness / substitution effect",
    example: "規約改定、UI変更で主導権を移す"
  },
  {
    name: "指桑罵槐",
    english: "Point at the mulberry, curse the locust",
    category: "Indirect Signaling",
    bias: "間接批判の読み取り、社会的圧力",
    behavioral: "Signaling / social norm enforcement",
    example: "名指しせず牽制、組織内メッセージ"
  },
  {
    name: "仮痴不癲",
    english: "Feign foolishness without going mad",
    category: "Impression",
    bias: "第一印象効果、ステレオタイプ、能力過小評価",
    behavioral: "Stereotyping / first impression effect",
    example: "弱そうに見せて油断させる、初心者を装う"
  },
  {
    name: "上屋抽梯",
    english: "Remove the ladder after the enemy climbs up",
    category: "Commitment",
    bias: "コミット後の撤退困難、損切り不能",
    behavioral: "Sunk cost fallacy / escalation of commitment",
    example: "導入後に条件変更、撤退コストを上げる"
  },
  {
    name: "樹上開花",
    english: "Make flowers bloom on a tree",
    category: "Signal Amplification",
    bias: "見せかけの規模、装飾による過大評価",
    behavioral: "Signaling / halo effect",
    example: "実態以上に大きく見せるPR、展示会演出"
  },
  {
    name: "反客為主",
    english: "Turn from guest into host",
    category: "Control",
    bias: "既成事実化、主導権移転への鈍感さ",
    behavioral: "Endowment effect / default effect",
    example: "外部委託先が主導権を握る、プラットフォーム依存"
  },
  {
    name: "美人計",
    english: "Use beauty as a trap",
    category: "Desire",
    bias: "魅力バイアス、感情による判断歪み",
    behavioral: "Affect heuristic / attractiveness bias",
    example: "広告モデル、恋愛詐欺、感情訴求"
  },
  {
    name: "空城計",
    english: "Empty fort strategy",
    category: "Uncertainty",
    bias: "情報不足時の物語補完、過剰推論",
    behavioral: "Ambiguity aversion / predictive inference",
    example: "沈黙による深読み、OSSの堂々公開、投資家の推測"
  },
  {
    name: "反間計",
    english: "Use enemy spies against them",
    category: "Trust / Doubt",
    bias: "疑心暗鬼、信頼ネットワークの破壊",
    behavioral: "Trust erosion / information asymmetry",
    example: "内部不信、リーク情報、競合撹乱"
  },
  {
    name: "苦肉計",
    english: "Inflict injury on oneself to win trust",
    category: "Credibility",
    bias: "犠牲を払う者は本気だと見なす",
    behavioral: "Costly signaling / credibility heuristic",
    example: "身銭を切るPR、謝罪演出、内部告発の信頼性"
  },
  {
    name: "連環計",
    english: "Chain stratagems together",
    category: "System",
    bias: "複数要因の連鎖を見落とす",
    behavioral: "Complexity neglect / systems trap",
    example: "複数施策の組み合わせ、依存関係で縛る"
  },
  {
    name: "走為上",
    english: "If all else fails, retreat",
    category: "Exit",
    bias: "撤退の恥、損切り回避",
    behavioral: "Sunk cost fallacy / loss aversion",
    example: "撤退判断、ピボット、プロジェクト停止"
  }
];

const rows = document.getElementById("rows");
const search = document.getElementById("search");
const category = document.getElementById("category");

const categories = [...new Set(stratagems.map(s => s.category))].sort();
for (const c of categories) {
  const opt = document.createElement("option");
  opt.value = c;
  opt.textContent = c;
  category.appendChild(opt);
}

function render() {
  const q = search.value.toLowerCase();
  const cat = category.value;

  rows.innerHTML = "";

  stratagems
    .filter(s => cat === "all" || s.category === cat)
    .filter(s => Object.values(s).join(" ").toLowerCase().includes(q))
    .forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${s.name}</strong></td>
        <td>${s.english}</td>
        <td><span class="badge">${s.category}</span></td>
        <td>${s.bias}</td>
        <td>${s.behavioral}</td>
        <td>${s.example}</td>
      `;
      rows.appendChild(tr);
    });
}

search.addEventListener("input", render);
category.addEventListener("change", render);
render();
