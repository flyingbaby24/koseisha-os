// Builds the two Source of Thought Tactics pages from one template.
//
//   node docs/tools/build-sott.mjs
//
// docs/sott/index.html (English) and docs/sott/index-ja.html (Japanese) are both written from the
// structure in page() and the two string tables below, so the languages cannot drift apart and a
// regeneration never drops a section. CI runs this script and fails if the committed pages differ.
// Japanese is written for the page, not translated line by line.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const docs = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const base = "https://www.jinn-project.com/";
// Public alpha (Cloudflare Pages, project "sott"). Change together with tests/jinn-sott-site.test.mjs.
const PLAY_URL = "https://sott-8kg.pages.dev/formation.html";
const esc = (s) => String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

const KEYS = ["PHILOSOPHY", "PSYCHOLOGY", "SCIENCE", "MORAL", "ECONOMY", "IDEOLOGY", "EMOTION", "INDIVIDUAL", "COMMUNITY", "KARMA"];
const ROLES = ["VANGUARD", "INTERFERER", "DEFENDER", "GUARDIAN", "BUILDER", "SNIPER", "SUPPORTER", "INDEPENDENT", "COOPERATOR", "RAIDER"];
// Works offered in section 02 (order must match docs/sott/sott-data.js).
const WORKS = ["The Wishing Carpet", "Anglo-Saxon Literature", "A Vision of the Future", "Selected Papers on Hysteria", "The Master of St. Benedict's", "Sea Curse"];

const L = {
  en: {
    lang: "en", file: "index.html", url: base + "sott/", alt: base + "sott/index-ja.html", locale: "en_US", altLocale: "ja_JP",
    home: "../", homeTop: "../#projects", tm: "../research/thoughtmap/", sot: "../research/source-of-thought/", atlas: "../research/stratagems/?lang=en", legal: "../legal/", support: "../support/",
    title: "Source of Thought Tactics — Thought becomes territory | Jinn Project",
    desc: "Source of Thought Tactics (SoTT) is a network tactics game in development at Jinn Project: works of literature, philosophy and science become units and fight for a 50-node board.",
    ogAlt: "Source of Thought Tactics — a 5 vs 5 battle on the 50-node network board.",
    skip: "Skip to content", brandLabel: "Jinn Project — home", crumb: "Source of Thought Tactics", langLabel: "Language", index: "Index", indexLabel: "Sections", railLabel: "Page sections",
    nav: ["Top", "Thought becomes territory", "The battlefield", "Tactical decisions", "Gameplay gallery", "AI plays tactics", "From ThoughtMap to SoTT", "Development"],
    heroBrand: "A Jinn Project work", chip: "Playable alpha",
    heroSub: "A network tactics game in which works of literature, philosophy and science become units, and the ideas they carry decide how they fight.",
    heroCatch: "Thought becomes territory.",
    heroPosterAlt: "Source of Thought Tactics: ten units fight across the octagonal nodes of the network board.",
    facts: [["Nodes", "50"], ["Links", "78"], ["Battle", "5 vs 5"], ["Roster", "40 works"]],
    scroll: "Scroll", pause: "Pause film", play: "Play film", heroFilm: "Background: real gameplay, development build",
    s2k: "Thought becomes territory", s2h: "A book becomes a unit. <em>A unit becomes ground.</em>",
    s2l: "Every unit in SoTT is a real work. Its ten-part thought composition is the only thing the game reads: the strongest part chooses the role, each part sets one combat stat, and where the unit walks becomes territory.",
    pick: "Choose a work",
    steps: [
      ["Work", "It starts with a text.", "The roster holds 40 works, most of them public-domain books catalogued by Project Gutenberg. Nothing about a unit is invented for balance; it is read from the work."],
      ["Parameters", "Ten parts of thought.", "Each work carries a thought composition in the ThoughtMap parameter format: philosophy, psychology, science, morality, economy, ideology, emotion, individual, community and karma."],
      ["Unit", "The strongest part chooses the role.", "The dominant parameter maps to one of ten roles, and each parameter drives exactly one stat: philosophy becomes attack, individual becomes HP, karma becomes mobility. Emotion makes a healer."],
      ["Network", "Placed on a graph, not a grid.", "Five units are deployed on the nodes of a 50-node board. Allies joined by links or by shared territory resonate: stronger basic attacks and faster SP recovery, in up to three stages."],
      ["Tactics", "Where it walks, it owns.", "Every node a unit moves through becomes its side’s territory and stays that way after it leaves. Holding enough of the board, for long enough, wins the battle."],
    ],
    stepNames: ["Work", "Parameters", "Unit", "Network", "Tactics"],
    noteLabel: "Status", s2note: "Implemented today: a fixed roster of 40 works whose parameters were computed ahead of time and shipped with the build. The game does not yet connect to ThoughtMap at runtime, so works added to ThoughtMap do not appear in SoTT automatically.",
    workTag: "Roster work", radarAlt: "Radar chart of the work’s ten thought parameters", basic: "basic action", schematic: "schematic spread", boardReal: "the real board graph",
    k: ["Philosophy", "Psychology", "Science", "Morality", "Economy", "Ideology", "Emotion", "Individual", "Community", "Karma"],
    r: ["Vanguard", "Interferer", "Defender", "Guardian", "Builder", "Sniper", "Supporter", "Independent", "Cooperator", "Raider"],
    s3k: "The battlefield", s3h: "Fifty nodes. <em>No front line.</em>",
    s3l: "TACTICAL is a 5 vs 5 battle on a graph of 50 nodes and 78 links. There are no rows to hold: range, support and victory are all read from how the network is connected at that moment.",
    boardTag: "Explanatory diagram — not the game", modes: [["read", "Read the network"], ["march", "March for territory"], ["cut", "Cut a link"]],
    boardLabel: "Interactive diagram of the 50-node board. Use the arrow keys to move between nodes and Enter to select.",
    boardCap: "Built from the real board graph of the recorded battle (board seed 73) and its starting positions. Movement here is simplified to one link per move, with no combat; the real rules are below, and the real game is in the film.",
    boardFallback: "The interactive board needs JavaScript. The rules it illustrates are listed below.",
    reset: "Reset the board", tallyA: "Cyan", tallyB: "Rose",
    readT: "Read the network", readHint: "Select any node. Its links light up: one move away in solid gold, two links away dashed.",
    readNode: "{links} links. One hop reaches {links} nodes; two hops reach {two}. In the game a unit’s mobility decides how many hops it gets.",
    marchT: "March for territory", marchHint: "Select a cyan unit, then a linked node beside it. The node it enters becomes cyan territory. Rose answers every move.",
    marchPicked: "Now choose a gold-ringed node linked to that unit.", marchBad: "That node is not linked to the selected unit, or it is occupied.",
    marchClaim: "{n} claimed. It stays cyan after the unit leaves.", marchFlip: "{n} flipped from rose to cyan.",
    cutT: "Cut a link", cutHint: "Select a link to sever it, as a Raider’s CUT does. Select it again to restore it, as a Builder’s CONNECT does.",
    cutState: "{cuts} links cut. Units with no ally left in their part of the network: cyan {a}, rose {b}. In the game an isolated unit defends at ×0.75 and acts more slowly.",
    tallyRule: "Territory victory: 23 of 50 nodes (46%) with a lead of 4, held for 3 Battle Time.", tallyMet: "Territory condition met. In the game it must now be held for 3 Battle Time.",
    rules: [
      ["Board", "A graph, generated from a seed.", "Fifty octagonal nodes joined by 78 links. Normal movement follows links; every node starts neutral."],
      ["Territory", "Moving is claiming.", "A move claims every node on its path and can flip the enemy’s. Territory also tilts skill potency toward the side that holds more."],
      ["Connection", "Linked units resonate.", "Allies joined by a link or by shared territory gain up to three stages: basic attacks up to ×1.15 and SP recovery up to ×1.3."],
      ["Division", "Links can be cut.", "Raiders cut links and Builders create them. A unit left with no ally in its part of the network takes more damage and waits longer."],
      ["Initiative", "Time, not rounds.", "Every action costs Battle Time according to the action and the unit’s speed. Whoever is ready next acts next."],
      ["Victory", "Three ways to end it.", "Eliminate the other side; or hold 23 of 50 nodes with a 4-node lead for 3 BT; or be ahead when the battle reaches 180 BT or 1,000 commands."],
    ],
    filmH: "The same board, in play.", real: "Real gameplay footage", filmPlay: "Play the highlight · 0:59",
    filmCap: "One complete TACTICAL battle on the development build, cut down to 59 seconds: opening, skills, healing, decisive blows and the territory victory. Trimmed only; no sound. In this recording both sides were played by the game’s built-in AI through the normal interface.",
    filmAlt: "Highlight film of a Source of Thought Tactics battle",
    s4k: "Tactical decisions", s4h: "Every command shows its <em>consequence first.</em>",
    s4l: "Choose a unit, choose a command, read the forecast, then execute. These clips are the real interface at the game’s own timing.",
    decs: [
      ["Move", "Take ground on the way.", "Reachable nodes light up along the links. Inside your own territory a unit travels freely, so ground taken early becomes speed later.", ["MOVE", "Territory", "Friendly network"], "d-move"],
      ["Skill", "Spend SP where it counts.", "A skill’s target window shows range, cost, cooldown and the computed result before you commit. Here a Sniper’s LONGSHOT reaches across the board.", ["SKILL", "SP", "Forecast"], "d-skill"],
      ["Impact", "Feel which blow mattered.", "Attackers lunge, the clock holds for an instant, the target recoils. Three weights of impact: normal, strong, and the blow that defeats. There are no random criticals.", ["Lunge", "Hit-stop", "Three tiers"], "d-impact"],
      ["Buff / Debuff", "Status with a clock on it.", "Effects are measured in Battle Time and show when they will end. An Interferer’s DISRUPT pushes an enemy’s next turn back; the panel shows by how much.", ["BUFF", "DEBUFF", "DISRUPT"], "d-status"],
      ["Healer", "Mend beside you, heal at range.", "In the current build a Supporter’s basic action is MEND: free, but only for a wounded ally on an adjacent cell. Its Ranged Heal reaches two links away for SP, and overflow becomes a barrier.", ["MEND · 0 SP", "Ranged Heal", "Barrier"], "d-heal"],
      ["Territory", "Hold the board, win the battle.", "The HUD tracks both sides’ nodes against the 23-node mark. Hold the lead for 3 Battle Time and the battle ends on territory, whoever is still standing.", ["23 / 50", "Lead of 4", "3 BT"], "d-territory"],
    ],
    decNow: "Now showing", decToggle: "Pause / play", decAlt: "Gameplay clip",
    s5k: "Gameplay gallery", s5h: "Straight from <em>the build.</em>",
    s5l: "Unretouched screenshots of the development build at 1920×1080. Select one to see it at full size.",
    shots: [
      ["battle", "Battle", "Mid-battle, turn 97: cyan and rose territory, status effects and the initiative order.", "A TACTICAL battle in progress with both territories spread across the board"],
      ["formation", "Formation", "The formation screen with five units placed and the whole 50-node board in view.", "Formation screen showing the full board and the deployed squad"],
      ["unit", "Unit", "A unit’s detail: role, stats ranked within the roster, basic action and skill.", "Unit detail panel for a Supporter with stats and skill"],
      ["board", "Board", "Battle start. Ten units on the 50-node board, every node still neutral.", "The 50-node board at the start of a 5 vs 5 battle"],
      ["skill", "Skill", "LONGSHOT selected: target window, SP cost and the forecast before EXECUTE.", "Skill target preview with forecast panel"],
      ["heal", "Healer", "Ranged Heal preview: target, range, SP cost and the HP it will restore.", "Ranged Heal preview with the heal forecast"],
      ["move", "Move", "MOVE selected: the eleven nodes this unit can reach along the links.", "Reachable nodes highlighted for a move"],
      ["result", "Result", "Territory victory: 25 of 50 nodes with a 14-node lead, held for 3 Battle Time.", "Battle result panel announcing a territory victory"],
      ["attack", "Attack", "AIM selected: the Sniper’s target and the expected damage.", "Attack target preview for a ranged basic attack"],
      ["title", "Title", "The title screen of the development build.", "SoTT title screen"],
    ],
    lbClose: "Close", lbPrev: "Previous", lbNext: "Next", lbLabel: "Screenshot viewer", open: "View full size",
    s6k: "AI plays tactics", s6h: "A local language model, <em>playing by the rules.</em>",
    s6l: "As an experiment, an AI VTuber system was connected to SoTT as an external player. A local Qwen3 4B model builds a squad, places it, and then commands it for a whole battle while the characters commentate.",
    figs: [["76", "legal actions chosen by the model in the accepted battle, start to finish"], ["10", "formation and placement decisions made before the battle"], ["150", "commands in that battle, re-simulated from the replay with an identical result"], ["0", "invalid commands, substituted moves or automatic time-outs on the model’s side"]],
    roles: [
      ["Human", "Starts and stops.", "A person launches the session and can halt it. During the recorded battle no game command was entered by hand.", "var(--amber)"],
      ["Enemy AI", "The game’s own opponent.", "Team B is played by the AI built into SoTT. It scores every legal command and searches routes toward territory. It is not the language model.", "var(--rose)"],
      ["Game agent", "The external player.", "Team A is played by Qwen3 4B running locally. It reads the observed state and picks one command from the legal list the game offers.", "var(--violet)"],
    ],
    loop: ["Observed state", "Legal commands", "Model chooses", "Engine validates", "Replay log"],
    aiFilm: "The experiment, recorded.", aiReal: "Real recording", aiPlay: "Play the recording · 0:16",
    aiCap: "Excerpt from the local rehearsal recording of the accepted battle (not a public stream; no sound here). The three characters are the VTuber system’s commentators; the Japanese subtitles are their live commentary.",
    aiAlt: "Recording of the AI VTuber system playing Source of Thought Tactics",
    limitsH: "What this does not show",
    limits: ["Legal is not the same as good. The model lost this battle on territory, and all five battles of a longer series.", "The commentary sometimes speculates beyond what the game state shows.", "Long unattended sessions have not been verified."],
    s7k: "From ThoughtMap to SoTT", s7h: "One question, <em>asked three ways.</em>",
    s7l: "What happens when the meaning of a work is treated as something you can measure, hold and play? Jinn Project has answered that with a research tool and two games.",
    lin: [
      ["org", "Research and development", "Jinn Project", "The independent project behind all three: research tools, open systems and games that make hidden structure visible.", "Jinn Project home"],
      ["tm", "Analysis", "ThoughtMap", "Searches and compares tens of thousands of works by meaning, and describes each as a composition of ideas.", "About ThoughtMap"],
      ["sot", "Card strategy", "Source of Thought", "Works become cards. Ten-card decks, five members and a 5×5 formation, playable now in the browser.", "Source of Thought"],
      ["here", "Network tactics", "Source of Thought Tactics", "Works become units. Five against five on a 50-node network where movement is territory. In development, playable alpha.", "You are here"],
    ],
    s8k: "Development", s8h: "In development. <em>Playable now in your browser.</em>",
    play: "PLAY SoTT", playNote: "Free, no account. Opens the TACTICAL alpha in a new tab. Best on a desktop browser.",
    s8l: "A public alpha of TACTICAL runs in the browser. It is a development build: rules, balance and interface will change, and it has no background music yet.",
    devFacts: [["Status", "In development", "Public alpha, playable in the browser"], ["Shown here", "TACTICAL — 5 vs 5 on 50 nodes", "Captured 19 November 2026, ruleset 0.28.1"], ["Platform", "Web browser", "TypeScript and Three.js"], ["Roster", "40 works, 10 roles", "Fixed roster shipped with the build"], ["Saving", "This browser only", "Formations are not synced between devices"], ["Source code", "Not public", "Private during development"]],
    devH: "Play the alpha.", devP: "Pick five works, place them and fight a full 5 vs 5 battle against the AI. Source of Thought, the card game from the same line of research, is playable too.",
    devA: ["Play Source of Thought", "All Jinn Project links"],
    more: [["Jinn Project", "All work"], ["ThoughtMap", "Research platform"], ["Source of Thought", "Card strategy game"], ["Stratagems Atlas", "Interactive publication"]],
    footTag: "Independent research, open systems and games built to make hidden structures visible.",
    footNav: ["Jinn Project home", "Source of Thought", "ThoughtMap", "Support", "Legal disclosure"], footLabel: "Footer",
    copy: "© 2026 Jinn Project", motto: "Thought / Body / Material / System", top: "Back to top ↑", ext: " (opens in a new tab)",
  },
  ja: {
    lang: "ja", file: "index-ja.html", url: base + "sott/index-ja.html", alt: base + "sott/", locale: "ja_JP", altLocale: "en_US",
    home: "../index-ja.html", homeTop: "../index-ja.html#projects", tm: "../research/thoughtmap/index-ja.html", sot: "../research/source-of-thought/index-ja.html", atlas: "../research/stratagems/", legal: "../legal/", support: "../support/index-ja.html",
    title: "Source of Thought Tactics — 思想は、領土になる。 | Jinn Project",
    desc: "Source of Thought Tactics（SoTT）は、Jinn Projectが開発中のネットワーク戦術ゲームです。文学・哲学・科学の作品がユニットとなり、50ノードの盤面を奪い合います。",
    ogAlt: "Source of Thought Tactics — 50ノードのネットワーク盤面で戦う5対5の戦闘。",
    skip: "本文へ移動", brandLabel: "Jinn Project — ホームへ", crumb: "Source of Thought Tactics", langLabel: "言語", index: "目次", indexLabel: "セクション", railLabel: "ページ内のセクション",
    nav: ["トップ", "思想は、領土になる", "戦場", "戦術の判断", "プレイ画面", "AIが戦術を指す", "ThoughtMapからSoTTへ", "開発状況"],
    heroBrand: "Jinn Projectの作品", chip: "アルファ版公開中",
    heroSub: "文学・哲学・科学の作品がユニットになり、作品に宿る思想が戦い方を決める。つながりを読み、盤面を奪い合うネットワーク戦術ゲーム。",
    heroCatch: "思想は、領土になる。",
    heroPosterAlt: "Source of Thought Tactics：八角形のノードが連なるネットワーク盤面で、10体のユニットが戦う。",
    facts: [["ノード", "50"], ["リンク", "78"], ["戦闘", "5対5"], ["登場作品", "40作品"]],
    scroll: "スクロール", pause: "映像を止める", play: "映像を再生", heroFilm: "背景：開発ビルドの実際のプレイ映像",
    s2k: "思想は、領土になる", s2h: "一冊の本がユニットになり、<em>ユニットが土地になる。</em>",
    s2l: "SoTTのユニットは、すべて実在の作品です。ゲームが読むのは、作品ごとの10の思想パラメータだけ。もっとも強い成分が役割を決め、それぞれの成分がひとつずつ能力値になり、ユニットが歩いた場所が領土になります。",
    pick: "作品を選ぶ",
    steps: [
      ["作品", "はじまりは、一冊のテキスト。", "登場するのは40作品。その大半はProject Gutenbergに収録されたパブリックドメインの書物です。バランスのために作った設定はなく、ユニットの性質は作品から読み取られます。"],
      ["概念パラメータ", "思想を、10の成分で。", "作品はそれぞれ、ThoughtMapのパラメータ形式による思想構成を持っています。哲学・心理・科学・道徳・経済・思想・感情・個人・共同体・因果の10成分です。"],
      ["ユニット", "いちばん強い成分が、役割を選ぶ。", "最大の成分が10種類のロールのひとつに対応し、各成分はちょうどひとつの能力値になります。哲学は攻撃力に、個人はHPに、因果は機動力に。感情が強い作品はヒーラーになります。"],
      ["ネットワーク", "置くのはマス目ではなく、グラフの上。", "50ノードの盤面に5体を配置します。リンクや同じ領土でつながった味方どうしは共鳴し、通常攻撃とSP回復が最大3段階まで強まります。"],
      ["戦術", "歩いた場所が、自分の土地になる。", "ユニットが通ったノードは自軍の領土になり、立ち去ったあとも残ります。十分な広さを、十分な時間だけ守り抜けば、それが勝利です。"],
    ],
    stepNames: ["作品", "概念パラメータ", "ユニット", "ネットワーク", "戦術"],
    noteLabel: "実装状況", s2note: "現在実装されているのは、あらかじめ算出したパラメータをビルドに同梱した40作品の固定ロスターです。実行時にThoughtMapへ接続する機能はまだなく、ThoughtMapに追加した作品が自動でSoTTに登場することはありません。",
    workTag: "登場作品", radarAlt: "作品の10の思想パラメータを示すレーダーチャート", basic: "基本行動", schematic: "模式的な広がり", boardReal: "実際の盤面グラフ",
    k: ["哲学", "心理", "科学", "道徳", "経済", "思想", "感情", "個人", "共同体", "因果"],
    r: ["前衛", "妨害", "防衛", "守護", "構築", "狙撃", "支援", "独立", "連携", "遊撃"],
    s3k: "戦場", s3h: "50のノード。<em>前線は、ない。</em>",
    s3l: "TACTICALは、50ノード・78リンクのグラフで戦う5対5の戦闘です。守るべき横一列はありません。射程も支援も勝敗も、その瞬間のつながり方から決まります。",
    boardTag: "説明用の図 — ゲーム本体ではありません", modes: [["read", "つながりを読む"], ["march", "領土を広げる"], ["cut", "リンクを断つ"]],
    boardLabel: "50ノード盤面のインタラクティブな図。矢印キーでノードを移動し、Enterで選択します。",
    boardCap: "録画した戦闘の実際の盤面グラフ（盤面シード73）と初期配置から作成しています。ここでの移動は1回につき1リンク、戦闘なしに簡略化しています。実際のルールは下の一覧に、実際のゲームは映像にあります。",
    boardFallback: "インタラクティブな盤面にはJavaScriptが必要です。図が示すルールは下にまとめています。",
    reset: "盤面をリセット", tallyA: "シアン", tallyB: "ローズ",
    readT: "つながりを読む", readHint: "ノードを選ぶと、そこから伸びるリンクが光ります。実線の金色は1手先、破線は2リンク先です。",
    readNode: "リンクは{links}本。1ホップで{links}ノード、2ホップで{two}ノードに届きます。実際のゲームでは、ユニットの機動力が進めるホップ数を決めます。",
    marchT: "領土を広げる", marchHint: "シアンのユニットを選び、リンクでつながった隣のノードを選んでください。入ったノードがシアンの領土になります。ローズも一手ごとに動きます。",
    marchPicked: "金色の枠が付いた、リンク先のノードを選んでください。", marchBad: "そのノードは選択中のユニットとつながっていないか、すでにユニットがいます。",
    marchClaim: "{n}を確保しました。ユニットが離れてもシアンのままです。", marchFlip: "{n}をローズからシアンに塗り替えました。",
    cutT: "リンクを断つ", cutHint: "リンクを選ぶと切断します（遊撃のCUTにあたります）。もう一度選ぶとつなぎ直します（構築のCONNECTにあたります）。",
    cutState: "切断中のリンクは{cuts}本。同じネットワークに味方がいなくなったユニット：シアン{a}体、ローズ{b}体。実際のゲームでは、孤立したユニットは防御が0.75倍になり、行動も遅れます。",
    tallyRule: "領土勝利：50ノード中23（46%）以上を、4ノード差以上で、3 BTのあいだ維持。", tallyMet: "領土条件を満たしました。実際のゲームでは、ここから3 BT守り切る必要があります。",
    rules: [
      ["盤面", "シードから生成されるグラフ。", "八角形のノード50個を78本のリンクが結びます。通常の移動はリンクに沿い、開始時はすべてのノードが中立です。"],
      ["領土", "動くことが、奪うこと。", "移動で通過したノードはすべて自軍の領土になり、敵の領土も塗り替えられます。領土の多い側ほど、スキルの効果も少し強くなります。"],
      ["接続", "つながった味方は共鳴する。", "リンクまたは同じ領土でつながった味方どうしは最大3段階の共鳴を得て、通常攻撃は最大1.15倍、SP回復は最大1.3倍になります。"],
      ["分断", "リンクは、断ち切れる。", "遊撃はリンクを切り、構築はリンクを作ります。同じネットワークに味方がいなくなったユニットは、受けるダメージが増え、次の行動も遅くなります。"],
      ["行動順", "ラウンドではなく、時間で。", "行動ごとに、その内容と速度に応じたバトルタイム（BT）を消費します。次に準備が整ったユニットが、次に動きます。"],
      ["勝利", "決着のつき方は3つ。", "相手を全滅させる。または23ノード以上を4ノード差以上で3 BT維持する。あるいは180 BTか1,000コマンドに達した時点で優勢である。"],
    ],
    filmH: "同じ盤面を、実際のプレイで。", real: "実際のプレイ映像", filmPlay: "ハイライトを再生 · 0:59",
    filmCap: "開発ビルドでのTACTICAL一戦を、開幕からスキル、回復、決定打、領土勝利まで59秒にまとめました。加工はカットのみ、音声はありません。この録画では、ゲーム内蔵のAIが通常の操作画面を通して両軍を動かしています。",
    filmAlt: "Source of Thought Tacticsの戦闘ハイライト映像",
    s4k: "戦術の判断", s4h: "どのコマンドも、<em>結果を先に見せる。</em>",
    s4l: "ユニットを選び、コマンドを選び、予測を読んでから実行する。ここに並ぶのは、実際の操作画面を、ゲームそのままのテンポで録った映像です。",
    decs: [
      ["移動", "進みながら、土地を取る。", "移動できるノードがリンクに沿って光ります。自軍の領土のなかでは自由に動けるので、序盤に取った土地が、あとで速さになります。", ["MOVE", "領土", "自軍ネットワーク"], "d-move"],
      ["スキル", "SPは、効く場面で。", "スキルの対象ウィンドウには、射程・消費・再使用までの時間、そして計算済みの結果が、実行前に表示されます。映像は狙撃のLONGSHOTが盤面を横切る場面です。", ["SKILL", "SP", "結果予測"], "d-skill"],
      ["手応え", "効いた一撃が、わかる。", "攻撃側が踏み込み、時間が一瞬止まり、相手がのけぞる。手応えは通常・強打・とどめの3段階。ランダムなクリティカルはありません。", ["踏み込み", "ヒットストップ", "3段階"], "d-impact"],
      ["BUFF / DEBUFF", "効果には、残り時間がある。", "効果はバトルタイムで管理され、いつ切れるかが表示されます。妨害のDISRUPTは敵の次の行動を遅らせ、その幅もパネルに示されます。", ["BUFF", "DEBUFF", "DISRUPT"], "d-status"],
      ["ヒーラー", "隣を手当てし、遠くを癒やす。", "現在のビルドでは、支援の基本行動はMEND。SP消費なしで使えますが、対象は隣接マスの負傷した味方だけです。遠距離ヒールはSPを使って2リンク先まで届き、あふれた回復はバリアになります。", ["MEND · SP 0", "遠距離ヒール", "バリア"], "d-heal"],
      ["領土", "盤面を保てば、勝てる。", "HUDは両軍のノード数を23の目標と並べて示します。リードを3 BT守り切れば、生き残りの数にかかわらず、領土で決着がつきます。", ["23 / 50", "4ノード差", "3 BT"], "d-territory"],
    ],
    decNow: "再生中", decToggle: "一時停止 / 再生", decAlt: "プレイ映像",
    s5k: "プレイ画面", s5h: "ビルドから、<em>そのまま。</em>",
    s5l: "開発ビルドを1920×1080で撮影した、無加工のスクリーンショットです。選ぶと原寸で表示します。",
    shots: [
      ["battle", "戦闘", "戦闘中盤、97ターン目。シアンとローズの領土、状態効果、行動順。", "両軍の領土が盤面に広がった、進行中のTACTICAL戦闘"],
      ["formation", "編成", "5体を配置し終えた編成画面。50ノードの盤面全体が見渡せます。", "盤面全体と出撃部隊が表示された編成画面"],
      ["unit", "ユニット", "ユニットの詳細。ロール、ロスター内順位つきの能力値、基本行動とスキル。", "支援ユニットの能力値とスキルを示す詳細パネル"],
      ["board", "盤面", "戦闘開始。50ノードの盤面に10体、ノードはまだすべて中立です。", "5対5の戦闘開始時の50ノード盤面"],
      ["skill", "スキル", "LONGSHOTを選択。対象ウィンドウ、SP消費、実行前の結果予測。", "結果予測パネルつきのスキル対象プレビュー"],
      ["heal", "ヒーラー", "遠距離ヒールのプレビュー。対象、射程、SP消費、回復するHP。", "回復量の予測が表示された遠距離ヒールのプレビュー"],
      ["move", "移動", "MOVEを選択。このユニットがリンクに沿って届く11のノード。", "移動可能なノードがハイライトされた画面"],
      ["result", "結果", "領土勝利。50ノード中25、14ノード差を3 BT守り切りました。", "領土による勝利を告げる戦闘結果パネル"],
      ["attack", "攻撃", "AIMを選択。狙撃の対象と、見込まれるダメージ。", "遠距離通常攻撃の対象プレビュー"],
      ["title", "タイトル", "開発ビルドのタイトル画面。", "SoTTのタイトル画面"],
    ],
    lbClose: "閉じる", lbPrev: "前へ", lbNext: "次へ", lbLabel: "スクリーンショットビューア", open: "原寸で表示",
    s6k: "AIが戦術を指す", s6h: "ローカルの言語モデルが、<em>ルールどおりに戦う。</em>",
    s6l: "実験として、AI VTuberのシステムを外部プレイヤーとしてSoTTにつなぎました。ローカルで動くQwen3 4Bが部隊を編成し、配置し、一戦を最後まで指揮します。そのあいだ、キャラクターたちが実況します。",
    figs: [["76", "受入試験の一戦で、モデルが開始から決着までに選んだ合法行動の数"], ["10", "戦闘前にモデルが下した編成・配置の判断"], ["150", "その一戦の全コマンド数。Replayから再シミュレーションし、結果は完全に一致"], ["0", "モデル側の無効コマンド、代行行動、時間切れによる自動行動"]],
    roles: [
      ["人間", "始めて、止める。", "人はセッションを起動し、必要なら停止します。録画した一戦のあいだ、ゲームのコマンドは一度も手で入力していません。", "var(--amber)"],
      ["敵AI", "ゲームに内蔵された対戦相手。", "チームBを動かすのは、SoTT自身のAIです。合法なコマンドすべてを評価し、領土へ向かう経路を探索します。言語モデルではありません。", "var(--rose)"],
      ["Game Agent", "外部から参加するプレイヤー。", "チームAを動かすのは、ローカルで動作するQwen3 4Bです。観測した戦況を読み、ゲームが提示する合法コマンドの一覧からひとつを選びます。", "var(--violet)"],
    ],
    loop: ["戦況の観測", "合法コマンド一覧", "モデルが選択", "エンジンが検証", "Replayログ"],
    aiFilm: "実験の、実際の録画。", aiReal: "実録画", aiPlay: "録画を再生 · 0:16",
    aiCap: "受入試験の一戦を収めたローカルリハーサル録画からの抜粋です（公開配信ではありません。ここでは音声なし）。3人のキャラクターはVTuberシステムの実況役で、字幕はその場で生成された実況です。",
    aiAlt: "AI VTuberシステムがSource of Thought Tacticsをプレイしている録画",
    limitsH: "この実験が示していないこと",
    limits: ["合法であることと、強いことは別です。モデルはこの一戦を領土で落とし、より長い5連戦でも全敗しました。", "実況には、戦況から読み取れる以上の推測が混じることがあります。", "長時間の無人運転は検証していません。"],
    s7k: "ThoughtMapからSoTTへ", s7h: "ひとつの問いを、<em>3つのかたちで。</em>",
    s7l: "作品の意味を、測り、手に取り、遊べるものとして扱ったら何が起きるのか。Jinn Projectはその問いに、ひとつの研究ツールとふたつのゲームで答えてきました。",
    lin: [
      ["org", "研究・制作主体", "Jinn Project", "3つすべての母体となる独立プロジェクト。見えない構造を見えるかたちにする、研究ツール・オープンなシステム・ゲームを制作しています。", "Jinn Project ホーム"],
      ["tm", "解析", "ThoughtMap", "数万の作品を意味で検索・比較し、それぞれを思想の構成として記述する研究基盤。", "ThoughtMapについて"],
      ["sot", "カード戦略", "Source of Thought", "作品がカードになる。10枚のデッキ、5人の出撃メンバー、5×5の陣形。いまブラウザで遊べます。", "Source of Thought"],
      ["here", "ネットワーク戦術", "Source of Thought Tactics", "作品がユニットになる。移動がそのまま領土になる、50ノードのネットワークでの5対5。開発中、アルファ版を公開中。", "現在のページ"],
    ],
    s8k: "開発状況", s8h: "開発中。<em>ブラウザで、いま遊べます。</em>",
    play: "SoTTをプレイ", playNote: "無料・登録不要。TACTICALのアルファ版が新しいタブで開きます。パソコンのブラウザを推奨します。",
    s8l: "TACTICALのアルファ版をブラウザで公開しています。開発中のビルドのため、ルール・バランス・画面は今後変わります。BGMはまだ入っていません。",
    devFacts: [["状況", "開発中", "アルファ版をブラウザで公開中"], ["掲載内容", "TACTICAL — 50ノードでの5対5", "2026年11月19日撮影、ルールセット0.28.1"], ["プラットフォーム", "Webブラウザ", "TypeScriptとThree.js"], ["ロスター", "40作品・10ロール", "ビルドに同梱した固定ロスター"], ["保存", "このブラウザ内のみ", "編成はほかの端末と同期されません"], ["ソースコード", "非公開", "開発中のため公開していません"]],
    devH: "アルファ版を遊ぶ。", devP: "5つの作品を選んで配置し、AIを相手に5対5の戦闘を最後まで遊べます。同じ研究から生まれたカードゲーム、Source of Thoughtも公開中です。",
    devA: ["Source of Thoughtを遊ぶ", "Jinn Projectのリンク一覧"],
    more: [["Jinn Project", "作品一覧"], ["ThoughtMap", "研究基盤"], ["Source of Thought", "カード戦略ゲーム"], ["Stratagems Atlas", "インタラクティブ出版物"]],
    footTag: "見えない構造を見えるかたちにする、独立した研究・オープンなシステム・ゲーム。",
    footNav: ["Jinn Project ホーム", "Source of Thought", "ThoughtMap", "サポート", "特定商取引法に基づく表記"], footLabel: "フッター",
    copy: "© 2026 Jinn Project", motto: "Thought / Body / Material / System", top: "ページの先頭へ ↑", ext: "（新しいタブで開きます）",
  },
};

const IDS = ["top", "territory", "battlefield", "decisions", "gallery", "ai", "lineage", "development"];
const joint = (kind) => ({
  a: `<div class="joint" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path class="j-a" d="M8 0 V46 H62 V100"/><path d="M62 46 H88 V78"/></svg><i class="a" style="left:8%;top:0"></i><i style="left:62%;top:46%"></i><i style="left:88%;top:78%"></i><i class="g" style="left:62%;top:100%"></i></div>`,
  b: `<div class="joint" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path class="j-g" d="M62 0 V38 H24 V100"/><path class="j-b" d="M24 38 H6 V70"/></svg><i class="g" style="left:62%;top:0"></i><i style="left:24%;top:38%"></i><i class="b" style="left:6%;top:70%"></i><i class="a" style="left:24%;top:100%"></i></div>`,
  cut: `<div class="joint" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path class="j-b" d="M24 0 V50 H46"/><path class="j-a" d="M54 50 H76 V100"/></svg><i class="b" style="left:24%;top:0"></i><i class="x" style="left:46%;top:50%"></i><i class="x" style="left:54%;top:50%"></i><i class="a" style="left:76%;top:100%;--at:.9"></i></div>`,
  c: `<div class="joint" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path class="j-a" d="M76 0 V54 H40 V100"/><path class="j-g" d="M40 54 H14 V84"/></svg><i class="a" style="left:76%;top:0"></i><i style="left:40%;top:54%"></i><i class="g" style="left:14%;top:84%"></i><i style="left:40%;top:100%"></i></div>`,
}[kind]);
const head = (n, s, k, h, l) => `<header class="sec-head" data-rv><p class="kicker"><b>${n}</b>${esc(k)}</p><h2 id="${s}-h">${h}</h2><p class="lede">${esc(l)}</p></header>`;
const chars = (word, from) => [...word].map((c, i) => c === " " ? " " : `<span class="ch" style="--i:${from + i}">${c}</span>`).join("");

function page(s) {
  const ja = s.lang === "ja";
  const i18n = {
    pause: s.pause, play: s.play, workTag: s.workTag, radarAlt: s.radarAlt, basic: s.basic, schematic: s.schematic, boardReal: s.boardReal,
    ...Object.fromEntries(KEYS.map((k, i) => ["k" + k, s.k[i]])), ...Object.fromEntries(ROLES.map((r, i) => ["r" + r, s.r[i]])),
    ...Object.fromEntries(s.stepNames.map((n, i) => ["s" + (i + 1), n])),
    readT: s.readT, readHint: s.readHint, readNode: s.readNode, marchT: s.marchT, marchHint: s.marchHint, marchPicked: s.marchPicked, marchBad: s.marchBad, marchClaim: s.marchClaim, marchFlip: s.marchFlip,
    cutT: s.cutT, cutHint: s.cutHint, cutState: s.cutState, tallyRule: s.tallyRule, tallyMet: s.tallyMet,
  };
  const ld = { "@context": "https://schema.org", "@graph": [
    { "@type": "WebPage", "@id": s.url + "#webpage", url: s.url, name: s.title, description: s.desc, inLanguage: s.lang, isPartOf: { "@id": base + "#website" }, primaryImageOfPage: base + "sott/media/og-sott.jpg", about: { "@id": base + "sott/#game" } },
    { "@type": "VideoGame", "@id": base + "sott/#game", name: "Source of Thought Tactics", alternateName: "SoTT", url: base + "sott/", description: L.en.desc, genre: ["Tactics", "Strategy"], gamePlatform: "Web browser", creativeWorkStatus: "In development", image: base + "sott/media/og-sott.jpg", author: { "@id": base + "#organization" }, publisher: { "@id": base + "#organization" } },
    { "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "Jinn Project", item: ja ? base + "index-ja.html" : base }, { "@type": "ListItem", position: 2, name: "Source of Thought Tactics", item: s.url }] },
  ] };
  const playLink = `<a class="btn btn-gold btn-play" href="${PLAY_URL}" target="_blank" rel="noopener noreferrer" data-play>${esc(s.play)} <span aria-hidden="true">↗</span><span class="sr-only">${s.ext}</span></a>`;
  const extLink = (href, label, cls = "") => `<a${cls ? ` class="${cls}"` : ""} href="${href}" target="_blank" rel="noopener noreferrer">${esc(label)} <span aria-hidden="true">↗</span><span class="sr-only">${s.ext}</span></a>`;
  return `<!doctype html>
<html lang="${s.lang}" class="no-js">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>${esc(s.title)}</title>
  <meta name="description" content="${esc(s.desc)}">
  <meta name="theme-color" content="#04090c">
  <meta name="color-scheme" content="dark">
  <script>document.documentElement.className='js'</script>
  <link rel="preload" href="../assets/fonts/instrument-serif-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="../assets/fonts/inter-var-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="media/hero-poster.webp" as="image" type="image/webp" fetchpriority="high">
  <link rel="stylesheet" href="sott.css">
  <link rel="icon" href="../favicon.ico" sizes="48x48">
  <link rel="icon" href="../assets/img/icon-32.png" type="image/png" sizes="32x32">
  <link rel="apple-touch-icon" href="../assets/img/apple-touch-icon.png">
  <link rel="canonical" href="${s.url}">
  <link rel="alternate" hreflang="en" href="${base}sott/">
  <link rel="alternate" hreflang="ja" href="${base}sott/index-ja.html">
  <link rel="alternate" hreflang="x-default" href="${base}sott/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Jinn Project">
  <meta property="og:locale" content="${s.locale}">
  <meta property="og:locale:alternate" content="${s.altLocale}">
  <meta property="og:title" content="${esc(s.title)}">
  <meta property="og:description" content="${esc(s.desc)}">
  <meta property="og:url" content="${s.url}">
  <meta property="og:image" content="${base}sott/media/og-sott.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="${esc(s.ogAlt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${esc(s.title)}">
  <meta name="twitter:description" content="${esc(s.desc)}">
  <meta name="twitter:image" content="${base}sott/media/og-sott.jpg">
  <script type="application/ld+json">${JSON.stringify(ld)}</script>
</head>
<body>
  <a class="skip-link" href="#main">${s.skip}</a>

  <header class="s-header">
    <a class="s-brand" href="${s.home}" aria-label="${esc(s.brandLabel)}"><picture><source srcset="../assets/img/jinn-mark-96.webp" type="image/webp"><img src="../assets/img/jinn-mark-96.png" width="34" height="34" alt=""></picture><span>Jinn Project</span></a>
    <span class="s-crumb" aria-hidden="true">${s.crumb}</span>
    <div class="s-tools">
      <nav class="s-lang" aria-label="${s.langLabel}"><a href="index.html" hreflang="en" lang="en"${ja ? "" : ' aria-current="page"'}>EN</a><a href="index-ja.html" hreflang="ja" lang="ja"${ja ? ' aria-current="page"' : ""}>日本語</a></nav>
      <button class="s-menu-btn" type="button" aria-expanded="false" aria-controls="s-index" hidden><span>${s.index}</span><i aria-hidden="true"></i></button>
    </div>
  </header>
  <nav class="s-index" id="s-index" aria-label="${s.indexLabel}"><ol>${s.nav.map((n, i) => `<li><a href="#${IDS[i]}"><span>${String(i + 1).padStart(2, "0")}</span>${esc(n)}</a></li>`).join("")}</ol></nav>
  <nav class="s-rail" aria-label="${s.railLabel}"><ol>${s.nav.map((n, i) => `<li><a href="#${IDS[i]}"><span>${String(i + 1).padStart(2, "0")} ${esc(n)}</span></a></li>`).join("")}</ol></nav>

  <main id="main">
    <section class="hero" id="top" aria-labelledby="hero-title">
      <div class="hero-media">
        <img src="media/hero-poster.webp" width="1280" height="720" alt="${esc(s.heroPosterAlt)}" fetchpriority="high" decoding="async">
        <video muted loop playsinline preload="none" poster="media/hero-poster.webp" aria-hidden="true" tabindex="-1"><source data-src="media/hero.mp4" type="video/mp4"></video>
      </div>
      <svg class="hero-net" aria-hidden="true" focusable="false"></svg>
      <div class="hero-copy">
        <p class="hero-brand"><a href="${s.home}"><picture><source srcset="../assets/img/jinn-mark-96.webp" type="image/webp"><img src="../assets/img/jinn-mark-96.png" width="22" height="22" alt=""></picture>${s.heroBrand}</a><span class="chip">${s.chip}</span></p>
        <h1 id="hero-title" aria-label="Source of Thought Tactics"><span class="l1" aria-hidden="true">${chars("Source of Thought", 0)}</span><span class="l2" aria-hidden="true">${chars("Tactics", 6)}</span></h1>
        <div class="hero-lines"><p class="hero-catch">${s.heroCatch}</p><p class="hero-sub">${s.heroSub}</p><p class="hero-play">${playLink}</p></div>
      </div>
      <div class="hero-foot">
        <dl class="hero-facts">${s.facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("")}</dl>
        <div class="hero-ctl"><button class="icon-btn" type="button" data-video-toggle aria-pressed="false" title="${esc(s.heroFilm)}" hidden><svg viewBox="0 0 12 12" aria-hidden="true"></svg><span>${s.pause}</span></button><a class="scroll-cue" href="#territory">${s.scroll}<i aria-hidden="true"></i></a></div>
      </div>
    </section>

    <section class="sec flow" id="territory" aria-labelledby="territory-h">
      <div class="wrap">
        ${head("02", "territory", s.s2k, s.s2h, s.s2l)}
        <div class="flow-pick" role="group" aria-label="${esc(s.pick)}">${WORKS.map((w, i) => `<button type="button" aria-pressed="${i === 0}">${esc(w)}</button>`).join("")}</div>
        <div class="flow-track">
          <div class="flow-stage" data-step="1" aria-hidden="true"><div class="layers"><div class="layer l-work"></div><div class="layer l-params"></div><div class="layer l-unit"></div><div class="layer l-net"></div><p class="stage-tag"></p><p class="stage-steps"><i></i><i></i><i></i><i></i><i></i></p></div></div>
          <ol class="flow-steps">${s.steps.map(([n, h, p], i) => `<li data-step="${i + 1}"><p class="n">${String(i + 1).padStart(2, "0")} · ${esc(n)}</p><h3>${esc(h)}</h3><p>${esc(p)}</p></li>`).join("")}</ol>
        </div>
        <p class="note" data-rv><b>${s.noteLabel}</b><span>${esc(s.s2note)}</span></p>
      </div>
    </section>
    ${joint("a")}

    <section class="sec field" id="battlefield" aria-labelledby="battlefield-h">
      <div class="wrap">
        ${head("03", "battlefield", s.s3k, s.s3h, s.s3l)}
        <p class="note board-fallback"><b>${s.noteLabel}</b><span>${esc(s.boardFallback)}</span></p>
        <div class="board-ui" hidden>
          <div class="board-bar"><div class="seg" role="group" aria-label="${esc(s.s3k)}">${s.modes.map(([m, n], i) => `<button type="button" data-mode="${m}" aria-pressed="${i === 0}">${esc(n)}</button>`).join("")}</div><p class="board-tag">${esc(s.boardTag)}</p></div>
          <div class="board-frame"><svg class="board" role="group" aria-label="${esc(s.boardLabel)}"></svg></div>
          <div class="board-read">
            <div class="read-main" aria-live="polite"><b></b><p></p></div>
            <div class="tally"><div class="tally-row" data-tally="a" style="--c:var(--cyan)"><span>${s.tallyA}</span><i></i><b>0 / 50</b></div><div class="tally-row" data-tally="b" style="--c:var(--rose)"><span>${s.tallyB}</span><i></i><b>0 / 50</b></div><small></small></div>
          </div>
          <div class="board-actions"><button class="btn" type="button" data-board-reset>${s.reset}</button></div>
          <p class="cap">${esc(s.boardCap)}</p>
        </div>
        <ol class="rules" data-rv>${s.rules.map(([n, h, p], i) => `<li><p class="n">${String(i + 1).padStart(2, "0")} · ${esc(n).toUpperCase()}</p><h3>${esc(h)}</h3><p>${esc(p)}</p></li>`).join("")}</ol>
        <figure class="film" data-rv>
          <div class="film-head"><h3>${esc(s.filmH)}</h3><p class="tag-real">${esc(s.real)}</p></div>
          <div class="screen" data-film><video playsinline preload="none" data-poster="media/highlight-poster.webp" aria-label="${esc(s.filmAlt)}"><source data-src="media/highlight.mp4" type="video/mp4"></video><button class="play" type="button"><span>${esc(s.filmPlay)}</span></button></div>
          <figcaption>${esc(s.filmCap)}</figcaption>
        </figure>
      </div>
    </section>
    ${joint("cut")}

    <section class="sec" id="decisions" aria-labelledby="decisions-h">
      <div class="wrap">
        ${head("04", "decisions", s.s4k, s.s4h, s.s4l)}
        <div class="dec-track">
          <div class="dec-player">
            <div class="screen">${s.decs.map((d, i) => `<video muted loop playsinline preload="none" data-src="media/${d[4]}.mp4"${i === 0 ? ' data-poster="media/d-move-poster.webp"' : ""} aria-label="${esc(s.decAlt)}: ${esc(d[0])}"></video>`).join("")}<span class="dec-bar" aria-hidden="true"></span></div>
            <p class="dec-meta"><span>${esc(s.decNow)} · <b></b></span><button class="icon-btn" type="button" data-dec-toggle style="min-height:32px;padding:0">${esc(s.decToggle)}</button></p>
          </div>
          <ol class="dec-list">${s.decs.map(([n, h, p, keys], i) => `<li data-label="${esc(n)}"><p class="n">${String(i + 1).padStart(2, "0")} · ${esc(n)}</p><h3>${esc(h)}</h3><p>${esc(p)}</p><p class="keys">${keys.map((k) => `<span>${esc(k)}</span>`).join("")}</p></li>`).join("")}</ol>
        </div>
      </div>
    </section>
    ${joint("b")}

    <section class="sec" id="gallery" aria-labelledby="gallery-h">
      <div class="wrap">
        ${head("05", "gallery", s.s5k, s.s5h, s.s5l)}
        <ul class="gal">${s.shots.map(([f, n, cap, alt], i) => `<li data-rv style="--rd:${(i % 3) * 0.06}s"><button type="button" data-full="media/shot-${f}.webp" data-caption="${esc(cap)}" aria-label="${esc(s.open)}: ${esc(n)}"><img src="media/shot-${f}-960.webp" width="960" height="540" loading="lazy" decoding="async" alt="${esc(alt)}"><span class="gcap"><b>${String(i + 1).padStart(2, "0")}</b><span>${esc(cap)}</span></span><span class="gzoom" aria-hidden="true"></span></button></li>`).join("")}</ul>
      </div>
      <dialog class="lightbox" aria-label="${esc(s.lbLabel)}"><div class="lb-inner"><div class="lb-top"><span class="lb-count"></span><button class="lb-btn" type="button" data-lb-close>${s.lbClose}</button></div><div class="lb-stage"></div><div class="lb-bottom"><button class="lb-btn" type="button" data-lb-prev aria-label="${s.lbPrev}">←</button><p></p><button class="lb-btn" type="button" data-lb-next aria-label="${s.lbNext}">→</button></div></div></dialog>
    </section>
    ${joint("c")}

    <section class="sec ai" id="ai" aria-labelledby="ai-h">
      <div class="wrap">
        ${head("06", "ai", s.s6k, s.s6h, s.s6l)}
        <ul class="ai-figs" data-rv>${s.figs.map(([n, t], i) => `<li><strong>${n}</strong><span>${esc(t)}</span></li>`).join("")}</ul>
        <ul class="roles">${s.roles.map(([who, h, p, c]) => `<li data-rv style="--c:${c}"><p class="who">${esc(who)}</p><h3>${esc(h)}</h3><p>${esc(p)}</p></li>`).join("")}</ul>
        <ol class="ai-loop" data-rv>${s.loop.map((x, i) => `<li${i === 2 ? ' class="m"' : ""}><span>${esc(x)}</span></li>`).join("")}</ol>
        <figure class="film" data-rv>
          <div class="film-head"><h3>${esc(s.aiFilm)}</h3><p class="tag-real">${esc(s.aiReal)}</p></div>
          <div class="screen" data-film><video playsinline preload="none" data-poster="media/ai-play-poster.webp" aria-label="${esc(s.aiAlt)}"><source data-src="media/ai-play.mp4" type="video/mp4"></video><button class="play" type="button"><span>${esc(s.aiPlay)}</span></button></div>
          <figcaption>${esc(s.aiCap)}</figcaption>
        </figure>
        <h3 class="kicker" style="margin-top:clamp(32px,5vw,56px)">${esc(s.limitsH)}</h3>
        <ul class="limits">${s.limits.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      </div>
    </section>
    ${joint("a")}

    <section class="sec" id="lineage" aria-labelledby="lineage-h">
      <div class="wrap">
        ${head("07", "lineage", s.s7k, s.s7h, s.s7l)}
        <div class="lineage"><svg class="lin-svg" aria-hidden="true" focusable="false"></svg>${s.lin.map(([cls, who, name, p, go]) => {
          const href = { org: s.home, tm: s.tm, sot: s.sot }[cls], c = { org: "var(--paper-2)", tm: "var(--cyan)", sot: "var(--rose)", here: "var(--amber)" }[cls];
          const inner = `<p class="who">${esc(who)}</p><h3>${esc(name)}</h3><p>${esc(p)}</p><p class="go">${esc(go)}${href ? ' <span aria-hidden="true">→</span>' : ""}</p>`;
          return href ? `<a class="lin-card ${cls}" href="${href}" style="--c:${c}">${inner}</a>` : `<div class="lin-card ${cls}" style="--c:${c}" aria-current="page">${inner}</div>`;
        }).join("")}</div>
      </div>
    </section>
    ${joint("b")}

    <section class="sec" id="development" aria-labelledby="development-h">
      <div class="wrap">
        ${head("08", "development", s.s8k, s.s8h, s.s8l)}
        <div class="dev-grid">
          <dl class="dev-facts" data-rv>${s.devFacts.map(([k, v, sm]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}<small>${esc(sm)}</small></dd></div>`).join("")}</dl>
          <div class="dev-side" data-rv><h3>${esc(s.devH)}</h3><p>${esc(s.devP)}</p><p class="play-note">${esc(s.playNote)}</p><p class="dev-actions">${playLink}<a class="btn" href="${s.sot}">${esc(s.devA[0])} <span aria-hidden="true">→</span></a>${extLink("https://linktr.ee/Jinn_project", s.devA[1], "btn")}</p></div>
        </div>
        <nav class="more" aria-label="${esc(s.s8k)}">${[[s.homeTop, 0], [s.tm, 1], [s.sot, 2], [s.atlas, 3]].map(([href, i]) => `<a href="${href}"><span>${esc(s.more[i][1])}</span><b>${esc(s.more[i][0])}</b></a>`).join("")}</nav>
      </div>
    </section>
  </main>

  <footer class="s-footer">
    <div class="wrap foot">
      <a class="foot-brand" href="${s.home}"><picture><source srcset="../assets/img/jinn-mark-192.webp" type="image/webp"><img src="../assets/img/jinn-mark-192.png" width="56" height="56" alt="" loading="lazy"></picture><span><b>Jinn Project</b><span>${esc(s.footTag)}</span></span></a>
      <nav class="foot-nav" aria-label="${s.footLabel}"><a href="${s.home}">${esc(s.footNav[0])}</a><a href="${s.sot}">${esc(s.footNav[1])}</a><a href="${s.tm}">${esc(s.footNav[2])}</a><a href="${s.support}">${esc(s.footNav[3])}</a><a href="${s.legal}">${esc(s.footNav[4])}</a></nav>
      <div class="foot-bottom"><span>${s.copy}</span><span>${s.motto}</span><a href="#top">${s.top}</a></div>
    </div>
  </footer>
  <script type="application/json" id="sott-i18n">${JSON.stringify(i18n).replaceAll("<", "\\u003c")}</script>
  <script src="sott-data.js" defer></script>
  <script src="sott.js" defer></script>
  <script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token":"7da53f8ef3544cf0967279ebd140ff89"}'></script>
</body>
</html>
`;
}

for (const s of Object.values(L)) fs.writeFileSync(path.join(docs, "sott", s.file), page(s));
console.log("Wrote docs/sott/index.html and docs/sott/index-ja.html");
