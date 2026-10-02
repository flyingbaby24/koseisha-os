// Builds the two top pages from one source.
//
//   node docs/tools/generate-index-ja.mjs
//
// docs/index.html is the hand-edited English source. This script
//   1. writes the shared SEO block (canonical, hreflang, Open Graph, JSON-LD)
//      into index.html between the <!-- seo --> markers, and
//   2. derives index-ja.html by exact string replacement.
// Every replacement must match at least once, so editing the English page
// without updating this table fails loudly instead of leaving English text
// on the Japanese page.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const docs = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const enFile = path.join(docs, "index.html");
const jaFile = path.join(docs, "index-ja.html");
const base = "https://www.jinn-project.com/";

const pages = {
  en: {
    file: "index.html",
    url: base,
    locale: "en_US",
    title: "Jinn Project — Research, OSS & Game Development",
    description: "Jinn Project is an independent research and development project that makes hidden structure visible: ThoughtMap, Source of Thought, Stratagems Atlas, Kunizukuri, Mandalizm and JinnSP.",
    imageAlt: "Jinn Project — Making hidden structure visible.",
  },
  ja: {
    file: "index-ja.html",
    url: base + "index-ja.html",
    locale: "ja_JP",
    title: "Jinn Project — 研究・OSS・ゲーム開発",
    description: "Jinn Projectは、見えない構造を見えるかたちにする独立研究開発プロジェクトです。ThoughtMap、Source of Thought、Stratagems Atlas、国創、Mandalizm、JinnSPを公開しています。",
    imageAlt: "Jinn Project — 見えない構造を、見えるかたちに。",
  },
};

// English → Japanese, applied in insertion order. Keys include surrounding markup
// where a bare word would be ambiguous.
const tr = {
  // Header & navigation
  "Skip to content":"本文へ移動",
  "aria-label=\"Jinn Project — back to top\"":"aria-label=\"Jinn Project — ページの先頭へ\"",
  "aria-label=\"Main\"":"aria-label=\"メイン\"",
  ">Work</a>":">作品</a>",
  ">Research</a>":">研究</a>",
  ">About</a>":">概要</a>",
  ">Log</a>":">開発ログ</a>",
  ">Contact</a>":">連絡先</a>",
  "aria-label=\"Language\"":"aria-label=\"言語\"",
  "<a href=\"index.html\" hreflang=\"en\" lang=\"en\" aria-current=\"page\">EN</a>":"<a href=\"index.html\" hreflang=\"en\" lang=\"en\">EN</a>",
  "<a href=\"index-ja.html\" hreflang=\"ja\" lang=\"ja\">日本語</a>\n        </nav>":"<a href=\"index-ja.html\" hreflang=\"ja\" lang=\"ja\" aria-current=\"page\">日本語</a>\n        </nav>",
  "<span class=\"sr-only\">Menu</span>":"<span class=\"sr-only\">メニュー</span>",

  // Hero
  "Independent research &amp; development":"独立研究開発プロジェクト",
  "Making hidden <em>structure</em> visible.":"見えない<em>構造</em>を、見えるかたちに。",
  "Jinn Project turns meaning, cognition and culture into open research tools, playable systems and public apps, and publishes how they work.":"Jinn Projectは、意味・認知・文化を、オープンな研究ツール、遊べるシステム、公開アプリへと変換し、その仕組みまで公開しています。",
  "Explore the work":"作品を見る",
  "Enter Source of Thought":"Source of Thoughtへ",
  "aria-hidden=\"true\">Thought</span>":"aria-hidden=\"true\">思考</span>",
  "aria-hidden=\"true\">System</span>":"aria-hidden=\"true\">システム</span>",
  "aria-hidden=\"true\">Body</span>":"aria-hidden=\"true\">身体</span>",
  "aria-hidden=\"true\">Material</span>":"aria-hidden=\"true\">素材</span>",
  "<small>Research platform</small>":"<small>研究基盤</small>",
  "<small>Research</small>":"<small>研究</small>",
  "<small>App</small>":"<small>アプリ</small>",
  "<small>Game</small>":"<small>ゲーム</small>",
  "<small>Product</small>":"<small>プロダクト</small>",
  "Seven projects across four domains: Thought, Body, Material and System. Lines show where projects share data, mechanics or material.":"思考・身体・素材・システムの4つの領域にまたがる7つのプロジェクト。線は、データ・仕組み・素材を共有している関係を示します。",
  "aria-label=\"Available now\"":"aria-label=\"公開中のプロジェクト\"",
  "<p class=\"now-label\">Now</p>":"<p class=\"now-label\">公開中</p>",
  "<span class=\"status status-live\">Playable</span>":"<span class=\"status status-live\">プレイ可能</span>",
  "<span class=\"status status-alpha\">Public alpha</span>":"<span class=\"status status-alpha\">公開アルファ</span>",
  "<span class=\"status status-live\">Live</span>":"<span class=\"status status-live\">公開中</span>",
  "<span class=\"status status-dev\">In development</span>":"<span class=\"status status-dev\">開発中</span>",
  " Source of Thought, public web build</a>":" Source of Thought Web版</a>",
  " Kunizukuri — Daidarabotchi<span":" 国創 — Daidarabotchi<span",
  " ThoughtMap, 64,000+ works<span":" ThoughtMap — 64,000件以上の作品<span",
  "<span class=\"sr-only\"> (opens in a new tab)</span>":"<span class=\"sr-only\">（新しいタブで開きます）</span>",

  // Flagship
  "Flagship · Playable now":"代表作 · プレイ可能",
  "Thought becomes <em>playable strategy.</em>":"思想が、<em>遊べる戦略になる。</em>",
  "In Source of Thought, works of literature, philosophy, science and history become cards. ThoughtMap profiles their meaning; the game turns affinity and resonance into a 5×5 battlefield.":"Source of Thoughtでは、文学・哲学・科学・歴史の作品がCardになります。ThoughtMapが作品の意味をプロファイル化し、ゲームはその相性とResonanceを5×5の戦場へと変換します。",
  "Source of Thought battle: card units on the Cyber Shrine field, linked by family-based interference lines.":"Source of Thoughtの戦闘画面。Cyber Shrineの戦場に並ぶCardユニットと、Familyごとの干渉を示す線。",
  "Public web build · actual gameplay capture":"公開Web版 · 実際のプレイ画面",
  "<dt>Deck</dt><dd>10 cards</dd>":"<dt>デッキ</dt><dd>10枚</dd>",
  "<dt>Battle members</dt>":"<dt>出撃メンバー</dt>",
  "<dt>Formation</dt>":"<dt>陣形</dt>",
  "<dt>Platform</dt>":"<dt>プラットフォーム</dt>",
  "Enter the game site":"ゲーム公式サイトへ",
  ">Gameplay gallery<":">プレイ画面ギャラリー<",
  ">Roadmap<":">ロードマップ<",
  ">Development blog<":">開発ブログ<",

  // Work
  "<span class=\"index\">02</span>Work":"<span class=\"index\">02</span>作品",
  "Seven entry points.":"7つの入口。",
  "Games, research platforms, public apps and physical products: independent projects built around the same question.":"ゲーム、研究基盤、公開アプリ、そしてプロダクト。同じ問いから生まれた、独立したプロジェクトです。",
  "aria-label=\"Filter projects\"":"aria-label=\"プロジェクトを絞り込む\"",
  "data-status-template=\"Showing {n} of {total} projects\"":"data-status-template=\"{total}件中{n}件を表示\"",
  ">All</button>":">すべて</button>",
  ">Games</button>":">ゲーム</button>",
  ">Research</button>":">研究</button>",
  ">Apps &amp; products</button>":">アプリ・プロダクト</button>",
  "<span>Game · Web</span>":"<span>ゲーム · Web</span>",
  "<span>Research platform · OSS</span>":"<span>研究基盤 · OSS</span>",
  "<span>Interactive publication</span>":"<span>インタラクティブ出版物</span>",
  "<span>Game · Browser</span>":"<span>ゲーム · ブラウザ</span>",
  "<span>App · Installable PWA</span>":"<span>アプリ · インストール可能なPWA</span>",
  "<span>Product</span>":"<span>プロダクト</span>",
  "A strategy card game where ideas compete by meaning, affinity and resonance.":"思想が意味・相性・Resonanceで競い合う戦略カードゲーム。",
  "Search and compare 64,000+ works by meaning rather than keywords.":"64,000件以上の作品を、キーワードではなく意味で検索・比較。",
  "Launch ThoughtMap":"ThoughtMapを開く",
  "The Thirty-Six Stratagems read through cognitive bias and behavioural economics.":"兵法三十六計を、認知バイアスと行動経済学から読み解く。",
  "Open the Atlas":"Atlasを開く",
  "Watch one Daidarabotchi and ten thousand years of land in a sumi-ink world simulation.":"一匹のダイダラボッチと、一万年の国土を眺める水墨世界シミュレーション。",
  "A rhythm game whose performance paints a real-time generative artwork.":"演奏がリアルタイムのジェネラティブアートを描く、ブラウザのリズムゲーム。",
  "Official game site":"ゲーム公式サイト",
  "A personal music library and playlist player for desktop, Android and iOS.":"デスクトップ、Android、iOSで使える個人用の音楽ライブラリ兼プレイリストプレーヤー。",
  "Launch JinnSP":"JinnSPを起動",
  "An experimental product exploring the relationship between the body, the ground and movement.":"身体・地面・動きの関係を探る実験的なプロダクト。",
  "Not yet public":"未公開",
  "New to JinnSP? ":"JinnSPを初めて使う方へ：",
  "Read the JinnSP guide →":"JinnSPガイドを読む →",

  // Research
  "<span class=\"index\">03</span>Research":"<span class=\"index\">03</span>研究",
  "One research loop, <em>many expressions.</em>":"ひとつの研究ループ、<em>いくつもの表現。</em>",
  "ThoughtMap is the shared semantic layer. The same profiles that power search and comparison also shape game mechanics and applied studies.":"ThoughtMapは共通の意味レイヤーです。検索や比較を支えるプロファイルが、そのままゲームの仕組みや応用研究のかたちを決めています。",
  "<p class=\"loop-step\">Corpus</p>":"<p class=\"loop-step\">コーパス</p>",
  "<h3>Research database</h3>":"<h3>研究データベース</h3>",
  "Literature, philosophy, science and history, stored with semantic embeddings.":"文学・哲学・科学・歴史の作品を、意味ベクトル（embedding）とともに蓄積。",
  "<strong>64,000+</strong> works":"<strong>64,000+</strong> 作品",
  "<p class=\"loop-step\">Semantic layer</p>":"<p class=\"loop-step\">意味レイヤー</p>",
  "Search by meaning, compare how works are composed, and navigate the corpus as a landscape.":"意味で検索し、作品の思想構成を比較し、コーパス全体を地形のように探索する。",
  "Explore ThoughtMap →":"ThoughtMapについて →",
  "<p class=\"loop-step\">Expressions</p>":"<p class=\"loop-step\">表現</p>",
  "<h3>Games &amp; studies</h3>":"<h3>ゲームと研究</h3>",
  "Profiles become cards, skills and formations in Source of Thought, and patterns of judgement in the Stratagems Atlas.":"プロファイルは、Source of ThoughtではCard・Skill・Formationに、Stratagems Atlasでは判断のパターンになります。",
  "Research should remain <em>inspectable.</em>":"研究は、<em>検証できるかたちで。</em>",
  "<span>Research record</span>":"<span>研究業績</span>",
  "<span>Source code and documentation</span>":"<span>ソースコードとドキュメント</span>",
  "<span>How the semantic layer works</span>":"<span>意味レイヤーの仕組み</span>",
  "About ThoughtMap":"ThoughtMapについて",

  // About
  "<span class=\"index\">04</span>About":"<span class=\"index\">04</span>概要",
  "Four domains, <em>one question.</em>":"4つの領域、<em>ひとつの問い。</em>",
  "How do the hidden structures in ideas, bodies, materials and systems become something people can see, play and use? Every Jinn Project work is an attempt at an answer.":"思想・身体・素材・システムに潜む見えない構造は、どうすれば人が見て、遊び、使えるものになるのか。Jinn Projectのすべての作品は、その問いへのひとつの答えです。",
  "<h3>Thought</h3><p>Semantics, cognition and philosophy.</p>":"<h3>思考</h3><p>意味論・認知・哲学。</p>",
  "<h3>Body</h3><p>Rhythm, movement and perception.</p>":"<h3>身体</h3><p>リズム・動き・知覚。</p>",
  "<h3>Material</h3><p>Land, objects and physical design.</p>":"<h3>素材</h3><p>土地・モノ・フィジカルデザイン。</p>",
  "<h3>System</h3><p>Open software and public tools.</p>":"<h3>システム</h3><p>オープンソフトウェアと公開ツール。</p>",
  "Kunizukuri · Grounding Sole":"国創 · Grounding Sole",
  "<h3 class=\"sr-only\">Principles</h3>":"<h3 class=\"sr-only\">原則</h3>",
  "<dt>Inspectable</dt><dd>Research records and source code are public, so results can be checked rather than trusted.</dd>":"<dt>検証できる</dt><dd>研究記録とソースコードを公開し、結果を「信じる」のではなく「確かめられる」ようにします。</dd>",
  "<dt>Human-directed</dt><dd>AI accelerates analysis and implementation. Direction and judgement stay human.</dd>":"<dt>人が方向を決める</dt><dd>AIは分析と実装を加速します。方向性と判断は人が担います。</dd>",
  "<dt>Playable</dt><dd>Games and interactive tools are a way to understand ideas, not only to present them.</dd>":"<dt>遊べる</dt><dd>ゲームやインタラクティブなツールは、思想を見せるためだけでなく、理解するための方法です。</dd>",
  "aria-label=\"Project figures\"":"aria-label=\"プロジェクトの数字\"",
  "<span>works mapped in ThoughtMap</span>":"<span>ThoughtMapに収録された作品</span>",
  "<span>stratagems in the Atlas</span>":"<span>Atlasに収録された計略</span>",
  "<span>projects across four domains</span>":"<span>4つの領域にまたがるプロジェクト</span>",
  "<span>languages: English and Japanese</span>":"<span>言語（英語・日本語）</span>",

  // Log
  "<span class=\"index\">05</span>Development log":"<span class=\"index\">05</span>開発ログ",
  "From the build log.":"開発の記録から。",
  "All development articles →":"すべての開発記事 →",
  "Skill Generation Without Losing the Source Work":"作品の意味を失わないSkill Generation",
  "Hate System: Turning Formation into Target Priority":"Hate System：配置をターゲット優先度へ変える",
  "Resonance: Making Adjacent Ideas Matter":"Resonance：隣接する思想に意味を持たせる",
  "Why Build a Game from Thought?":"なぜ思想からゲームを作るのか",

  // Contact
  "<span class=\"index\">06</span>Contact":"<span class=\"index\">06</span>連絡先",
  "Follow, support <em>or collaborate.</em>":"フォロー、支援、<em>そして協働。</em>",
  "Every channel, from news and social accounts to direct contact, is collected on one page.":"お知らせ、SNS、直接のご連絡まで、すべての窓口を1ページにまとめています。",
  "<b>All links</b><span>News, social accounts and contact</span>":"<b>すべてのリンク</b><span>お知らせ・SNS・連絡先</span>",
  "<span>Support independent development</span>":"<span>独立開発を支援する</span>",
  "<span>Source, issues and documentation</span>":"<span>ソース・Issue・ドキュメント</span>",

  // Footer
  "Independent research, open systems and games built to make hidden structures visible.":"見えない構造を見えるかたちにする、独立研究・オープンシステム・ゲーム。",
  "aria-label=\"Footer\"":"aria-label=\"フッター\"",
  "<h2>Work</h2>":"<h2>作品</h2>",
  "<h2>Research</h2>":"<h2>研究</h2>",
  "<h2>Connect</h2>":"<h2>つながる</h2>",
  ">Kunizukuri — Daidarabotchi</a>":">国創 — Daidarabotchi</a>",
  "All links ↗":"すべてのリンク ↗",
  "<li><a href=\"index-ja.html\" hreflang=\"ja\" lang=\"ja\">日本語</a></li>":"<li><a href=\"index.html\" hreflang=\"en\" lang=\"en\">English</a></li>",
  "Back to top ↑":"ページの先頭へ ↑",
};

// Local routes that have a Japanese counterpart.
const routes = [
  ['href="research/source-of-thought/"', 'href="research/source-of-thought/index-ja.html"'],
  ['href="research/source-of-thought/gallery.html"', 'href="research/source-of-thought/gallery-ja.html"'],
  ['href="research/source-of-thought/roadmap.html"', 'href="research/source-of-thought/roadmap-ja.html"'],
  ['href="research/source-of-thought/devblog/"', 'href="research/source-of-thought/devblog/index-ja.html"'],
  ['devblog/articles/skill-generation-pipeline.html"', 'devblog/articles/skill-generation-pipeline-ja.html"'],
  ['devblog/articles/hate-targeting-system.html"', 'devblog/articles/hate-targeting-system-ja.html"'],
  ['devblog/articles/resonance-system.html"', 'devblog/articles/resonance-system-ja.html"'],
  ['devblog/articles/why-build-a-game-from-thought.html"', 'devblog/articles/why-build-a-game-from-thought-ja.html"'],
  ['href="research/thoughtmap/"', 'href="research/thoughtmap/index-ja.html"'],
  ['href="research/stratagems/?lang=en"', 'href="research/stratagems/?lang=ja"'],
  ['href="kunizukuri/index-en.html"', 'href="kunizukuri/"'],
  ['href="jinnsp/"', 'href="jinnsp/index-ja.html"'],
];

const escapeAttr = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");

function seoBlock(lang) {
  const page = pages[lang];
  const image = base + "assets/img/og-jinn-project.jpg";
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": base + "#organization",
        name: "Jinn Project",
        url: base,
        logo: base + "assets/img/icon-512.png",
        sameAs: [
          "https://github.com/flyingbaby24/koseisha-os",
          "https://linktr.ee/Jinn_project",
          "https://www.patreon.com/cw/JinnProject",
        ],
      },
      {
        "@type": "WebSite",
        "@id": base + "#website",
        url: base,
        name: "Jinn Project",
        inLanguage: ["en", "ja"],
        publisher: { "@id": base + "#organization" },
      },
      {
        "@type": "WebPage",
        "@id": page.url + "#webpage",
        url: page.url,
        name: page.title,
        description: page.description,
        inLanguage: lang,
        isPartOf: { "@id": base + "#website" },
        primaryImageOfPage: image,
      },
    ],
  };
  const other = lang === "en" ? "ja" : "en";
  return [
    "<!-- seo:start (generated by tools/generate-index-ja.mjs) -->",
    `<link rel="canonical" href="${page.url}">`,
    `<link rel="alternate" hreflang="en" href="${pages.en.url}">`,
    `<link rel="alternate" hreflang="ja" href="${pages.ja.url}">`,
    `<link rel="alternate" hreflang="x-default" href="${pages.en.url}">`,
    `<meta property="og:type" content="website">`,
    `<meta property="og:site_name" content="Jinn Project">`,
    `<meta property="og:locale" content="${page.locale}">`,
    `<meta property="og:locale:alternate" content="${pages[other].locale}">`,
    `<meta property="og:title" content="${escapeAttr(page.title)}">`,
    `<meta property="og:description" content="${escapeAttr(page.description)}">`,
    `<meta property="og:url" content="${page.url}">`,
    `<meta property="og:image" content="${image}">`,
    `<meta property="og:image:width" content="1200">`,
    `<meta property="og:image:height" content="630">`,
    `<meta property="og:image:alt" content="${escapeAttr(page.imageAlt)}">`,
    `<meta name="twitter:card" content="summary_large_image">`,
    `<meta name="twitter:title" content="${escapeAttr(page.title)}">`,
    `<meta name="twitter:description" content="${escapeAttr(page.description)}">`,
    `<meta name="twitter:image" content="${image}">`,
    `<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>`,
    "<!-- seo:end -->",
  ].map((line) => "  " + line).join("\n");
}

const seoPattern = /\n {2}<!-- seo:start[\s\S]*?<!-- seo:end -->/;

function withHead(html, lang) {
  const page = pages[lang];
  const replaceOnce = (h, pattern, value, label) => {
    if (!pattern.test(h)) throw new Error(`index.html: ${label} not found`);
    return h.replace(pattern, value);
  };
  let h = html.replace(seoPattern, "");
  h = replaceOnce(h, /<html lang="[^"]+">/, `<html lang="${lang}">`, "<html lang>");
  h = replaceOnce(h, /<title>[^<]*<\/title>/, `<title>${page.title.replace(/&/g, "&amp;")}</title>`, "<title>");
  h = replaceOnce(h, /<meta name="description" content="[^"]*">/, `<meta name="description" content="${escapeAttr(page.description)}">`, "meta description");
  return replaceOnce(h, /(\n {2}<link rel="apple-touch-icon"[^>]*>)/, `$1\n${seoBlock(lang)}`, "apple-touch-icon anchor");
}

function translate(html) {
  let out = html;
  const missing = [];
  for (const [from, to] of [...Object.entries(tr), ...routes]) {
    if (!out.includes(from)) { missing.push(from); continue; }
    out = out.split(from).join(to);
  }
  if (missing.length) {
    throw new Error("These strings no longer exist in docs/index.html; update tools/generate-index-ja.mjs:\n  " + missing.join("\n  "));
  }
  return out;
}

const source = fs.readFileSync(enFile, "utf8").replace(seoPattern, "");
fs.writeFileSync(enFile, withHead(source, "en"));
fs.writeFileSync(jaFile, withHead(translate(source), "ja"));
console.log("Generated docs/index.html and docs/index-ja.html");
