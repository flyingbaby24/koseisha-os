# UI/UX刷新 Before / After

同梱データ（全国1,896地域・8指標）を変えずに、画面構成だけを見直した前後の実画面です。開発サーバー（`npm run dev`）をPlaywrightのChromiumで撮影しました（外部の背景地図は無効）。

| 画面 | Before | After |
| --- | --- | --- |
| PC 1440×900 ファーストビュー | `before-pc-first-view.webp` | `after-pc-first-view.webp` |
| PC 地域選択（豊中市） | `before-pc-region.webp` | `after-pc-region.webp` |
| PC 比較（出生率×年少人口比率） | `before-pc-compare.webp` | `after-pc-compare-tfr-share.webp` |
| PC 比較（子ども人口×子どもの人口密度） | — | `after-pc-compare-children-density.webp` |
| PC ページ全体 | `before-pc-full.webp` | — |
| PC 検索候補・都道府県絞り込み・ランキング | — | `after-pc-search.webp` / `after-pc-prefecture.webp` / `after-pc-ranking.webp` |
| スマホ 390×844 ファーストビュー | `before-sp-first-view.webp` | `after-sp-first-view.webp` |
| スマホ 地域選択・地域詳細 | — | `after-sp-region.webp` / `after-sp-region-detail.webp` |
| スマホ 比較 | — | `after-sp-compare.webp` |
| スマホ ページ全体 | `before-sp-full.webp` | `after-sp-full.webp` |
| タブレット 1024×768 | — | `after-tab-first.webp` / `after-tab-region-full.webp` |

## 主な変更

- タイトル帯と全国統計カード（約420px）をなくし、PCは「操作パネル｜地図｜地域パネル」の3列で地図を画面の高さいっぱいに表示。全国の主要値は右の地域パネルに集約
- 凡例を地図上に移動し、指標名・統計期間・7区分の境界値・「全国 1.33」などの全国集計値の位置・データなしを1枚に表示。選択地域の区分を枠で強調
- 指標は「出生率・年少人口比率・子ども人口」を大きなカード、「子どもの人口密度・年齢別の人口・人口増減率」をその他の指標として整理（8指標すべて保持）
- 「出生率×年少人口比率」「子ども人口×子どもの人口密度」をワンタップで比較。比較中は帯で状態を示し、各地図に A/B・指標名・統計期間・凡例・選択地域の値と全国との差を表示
- 地域パネルに選択指標の値、全国集計値（人数は自治体平均〈参考〉）との差、全国の分布上の位置、全国・都道府県内の順位（同値は同順位）、主な指標、年齢構成を順に表示
- 本文15px、数値は大きく、補助的な注記も11.5px以上（旧UIは9〜11px中心）。文字色は白・背景色に対してコントラスト比4.5:1以上。主な操作ボタンは高さ38〜46px
- スマホは検索と指標チップの直下に地図（画面上部約2割から表示）。地域をタップすると地図下部に値と「地域の詳細」ボタン
