const uiTranslations = {
  ja: {
    cognitiveTree: "認知体系ツリー", stratagemList: "三十六計一覧",
    searchPlaceholder: "計略・概念・バイアスを検索", allCategories: "すべて",
    noResultsTitle: "該当する計略がありません", noResultsDescription: "別のキーワードで検索してください。",
    noSelection: "計略が選択されていません", selectFromList: "一覧から計略を選択してください。",
    interpretation: "解釈", principle: "認知原理", breakdown: "認知プロセス",
    example: "現代例", bias: "バイアス", behavioral: "行動科学的解釈",
    relatedStratagems: "関連する計略", cognitiveCategories: "所属する認知分類",
    relatedConcepts: "関連概念", references: "参考文献", note: "関連記事",
    backToList: "一覧へ戻る", language: "言語", stratagems: "計略",
    categories: "認知カテゴリ", mapped: "件を分類"
    ,navConcept: "概念", navAtlas: "アトラス", navCategories: "カテゴリ", navNotes: "注記",
    heroEyebrow: "古代兵法 / 認知科学 / 行動経済学",
    heroTitle: "三十六計<br><span>認知バイアス・アトラス</span>",
    heroLead: "三十六計を兵法だけでなく、人間の判断・認知バイアス・行動経済学の実践的ケーススタディとして読み直す実験的マップ。",
    openAtlas: "アトラスを開く", viewCategories: "カテゴリを見る",
    conceptEyebrow: "概念", conceptTitle: "兵法は、認知仕様書としても読める。",
    conceptBody: "三十六計の成立理由を分解すると、人が何を信じ、どこで判断を誤り、どの条件で注意を逸らすのかという認知パターンが見えてくる。古代兵法を現代の認知科学・行動経済学の言葉で再配置する試みである。",
    humanFirmware: "人間の認知仕様", categoriesTitle: "36個の計略を、認知原理として再分類する。",
    atlasEyebrow: "インタラクティブ・アトラス", atlasTitle: "検索 / 絞り込み / 比較",
    notesEyebrow: "研究上の注記", notesTitle: "これは歴史的断定ではなく、現代的な再解釈である。",
    notesBody: "三十六計が当時から認知科学として作られたと主張するものではない。現代の認知科学・行動経済学・情報設計の視点から、古典兵法を認知バイアスの実践例として読む仮説的マッピングである。"
  },
  en: {
    cognitiveTree: "Cognitive Tree", stratagemList: "36 Stratagems",
    searchPlaceholder: "Search stratagems, concepts, or biases", allCategories: "All",
    noResultsTitle: "No matching stratagems", noResultsDescription: "Try another keyword.",
    noSelection: "No stratagem selected", selectFromList: "Select a stratagem from the list.",
    interpretation: "Interpretation", principle: "Cognitive Principle", breakdown: "Cognitive Process",
    example: "Modern Example", bias: "Bias", behavioral: "Behavioral Reading",
    relatedStratagems: "Related Stratagems", cognitiveCategories: "Cognitive Categories",
    relatedConcepts: "Related Concepts", references: "References", note: "Related Article",
    backToList: "Back to List", language: "Language", stratagems: "Stratagems",
    categories: "Cognitive Categories", mapped: "mapped"
    ,navConcept: "Concept", navAtlas: "Atlas", navCategories: "Categories", navNotes: "Notes",
    heroEyebrow: "Ancient Strategy / Cognitive Science / Behavioral Economics",
    heroTitle: "36 Stratagems<br><span>Cognitive Bias Atlas</span>",
    heroLead: "An experimental map that rereads the Thirty-Six Stratagems as practical cases in judgment, cognitive bias, and behavioral economics.",
    openAtlas: "Open Atlas", viewCategories: "View Categories",
    conceptEyebrow: "Concept", conceptTitle: "Strategy can also be read as a specification of cognition.",
    conceptBody: "When we examine why each stratagem works, recurring patterns appear: what people readily believe, where judgment fails, and when attention is redirected. This project reframes ancient strategy through modern cognitive science and behavioral economics.",
    humanFirmware: "Human Firmware", categoriesTitle: "Reclassifying 36 stratagems by their cognitive principles.",
    atlasEyebrow: "Interactive Atlas", atlasTitle: "Search / Filter / Compare",
    notesEyebrow: "Research Note", notesTitle: "A modern interpretation, not a historical claim.",
    notesBody: "This map does not claim that the Thirty-Six Stratagems were originally designed as cognitive science. It is a hypothesis-driven reinterpretation through cognitive science, behavioral economics, and information design."
  }
};

function safeStorageGet(key) {
  try { return window.localStorage.getItem(key); } catch (_) { return null; }
}

function safeStorageSet(key, value) {
  try { window.localStorage.setItem(key, value); } catch (_) {}
}

function determineInitialLanguage() {
  const valid = new Set(["ja", "en"]);
  const fromUrl = new URL(window.location.href).searchParams.get("lang");
  if (valid.has(fromUrl)) return fromUrl;
  const stored = safeStorageGet("stratagems-language");
  if (valid.has(stored)) return stored;
  const browserLanguage = String(navigator.language || "").toLowerCase();
  if (browserLanguage) return browserLanguage.startsWith("ja") ? "ja" : "en";
  return "ja";
}

let currentLanguage = determineInitialLanguage();

function t(key) {
  return uiTranslations[currentLanguage]?.[key] ?? uiTranslations.ja[key] ?? key;
}

function getLocalizedField(stratagem, field, language = currentLanguage) {
  const translated = stratagemTranslations?.[language]?.[stratagem.id]?.[field];
  return translated ?? stratagem[field] ?? (Array.isArray(stratagem[field]) ? [] : "");
}

function getLocalizedTreeField(node, field, language = currentLanguage) {
  return cognitiveTreeTranslations?.[language]?.[node.id]?.[field] ?? node[field] ?? "";
}

function updateLanguageUrl(language) {
  try {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", language);
    window.history.replaceState(null, "", url);
  } catch (_) {}
}
