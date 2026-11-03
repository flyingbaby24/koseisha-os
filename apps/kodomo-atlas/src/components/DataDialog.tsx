import { useEffect, useRef } from "react";
import { Check, Database, Download, ExternalLink, X } from "lucide-react";
import { integer } from "../metrics";
import { unitCounts } from "../regions";
import type { HouseholdData, Statistics } from "../types";

const householdTerms: Record<string, string> = {
  single: "単独世帯",
  singleShare: "単独世帯の割合",
  coupleChildren: "夫婦と子どもから成る世帯",
  coupleChildrenShare: "夫婦と子どもから成る世帯の割合",
  under18: "18歳未満の世帯員がいる世帯",
  under18Share: "18歳未満の世帯員がいる世帯の割合",
  elderlyOnly: "65歳以上の世帯員のみの世帯",
  elderlyOnlyShare: "65歳以上の世帯員のみの世帯の割合",
  elderlySingle: "65歳以上の単独世帯",
  elderlySingleShare: "65歳以上の単独世帯の割合",
  unmarried: "25〜39歳の未婚者",
  unmarriedRate: "25〜39歳の未婚率",
  denominators: "割合の分母",
};

export default function DataDialog({
  data,
  households,
  onClose,
}: {
  data: Statistics;
  households: HouseholdData["metadata"] | null;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const instance = dialog.current;
    instance?.showModal();
    return () => {
      instance?.close();
      previous?.focus();
    };
  }, []);
  const missing = data.municipalities.filter((r) => r.tfr === null);
  const householdMissing = data.municipalities.filter(
    (r) => r.households && r.households.singleShare === null,
  );
  const sources = [...data.metadata.sources, ...(households?.sources ?? [])];
  const units = unitCounts(data);
  return (
    <dialog
      ref={dialog}
      className="data-dialog"
      aria-labelledby="data-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">DATA & METHODOLOGY</span>
          <h2 id="data-title">この地図のデータについて</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="説明を閉じる"
        >
          <X size={21} />
        </button>
      </div>
      <div className="dialog-body">
        <p className="dialog-intro">
          公表された統計を、市区町村コードでつなぎました。
          <br />
          それぞれの指標が表す時点・対象・集計方法をご確認ください。
        </p>
        <div className="data-year-notice">
          <Database size={20} />
          <p>
            <b>出生率は2018〜2022年、人口・世帯・配偶関係は2020年。</b>
            <span>異なる年度の指標を、同じ年の実績として扱っていません。</span>
          </p>
        </div>
        <h3>データの出典</h3>
        <div className="source-list">
          {sources.map((source, i) => (
            <article key={source.file}>
              <span className="source-index">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <h4>
                  <a href={source.page} target="_blank" rel="noreferrer">
                    {source.title}
                    <ExternalLink size={13} />
                  </a>
                </h4>
                <p>
                  {source.period}
                  <span>公表 {source.published}</span>
                  {"use" in source && (
                    <>
                      <br />
                      使用：{String(source.use)}
                    </>
                  )}
                </p>
                <a
                  className="source-download"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  公式ファイルをダウンロード <Download size={12} />
                </a>
              </div>
            </article>
          ))}
        </div>
        <h3>集計と指標の定義</h3>
        <dl className="definition-list">
          {Object.entries(data.metadata.definitions).map(
            ([key, description]) => (
              <div key={key}>
                <dt>
                  {
                    (
                      {
                        tfr: "合計特殊出生率",
                        children: "子ども人口・年齢別人口",
                        childShare: "年少人口比率",
                        childDensity: "子どもの人口密度",
                        change: "人口増減率",
                        geography: "行政区域",
                        units: "表示・集計単位",
                      } as Record<string, string>
                    )[key]
                  }
                </dt>
                <dd>{description}</dd>
              </div>
            ),
          )}
          <div>
            <dt>全国との比較</dt>
            <dd>
              出生率・年少人口比率・密度・人口増減率は全国の集計値と比較し、自治体の単純平均には置き換えません。人口数・年齢別人口だけは「自治体平均（参考）」として1,896市区町村・行政区の単純平均を示します。これは全国集計値とは別の参考値です。都道府県・市全体の人口数にはこの差を表示しません。
              世帯数・未婚者数も同じく「自治体平均（参考）」と、世帯・未婚の割合は全国集計値と比較します。
            </dd>
          </div>
        </dl>
        {households && (
          <>
            <h3>世帯構造・未婚・高齢化の指標</h3>
            <div className="term-notice">
              <p>
                <b>「単独世帯」と「未婚者」は別の指標です。</b>
                単独世帯は1人で住む世帯（年齢・配偶関係を問わない）、未婚者は配偶関係が「未婚」の人（親などと同居していても含む）です。
              </p>
              <p>
                <b>「65歳以上の世帯員がいる世帯」と「65歳以上の世帯員のみの世帯」も別です。</b>
                この地図の「高齢者のみの世帯」は世帯員が全員65歳以上の世帯で、全国では一般世帯の
                {(
                  ((data.national.households?.elderlyOnly ?? 0) /
                    (data.national.households?.general ?? 1)) *
                  100
                ).toFixed(1)}
                %（「いる」世帯は
                {(
                  ((data.national.households?.withElderly ?? 0) /
                    (data.national.households?.general ?? 1)) *
                  100
                ).toFixed(1)}
                %）です。
              </p>
            </div>
            <dl className="definition-list">
              {Object.entries(households.definitions).map(([key, description]) => (
                <div key={key}>
                  <dt>{householdTerms[key] ?? key}</dt>
                  <dd>{description}</dd>
                </div>
              ))}
            </dl>
            <p className="method-text">
              一般世帯のみを対象とし、寮・病院・社会施設などの施設等の世帯は含みません。配偶関係は不詳補完値ではなく原数値です。公表された第4-4表の未婚割合（{integer.format(households.checks.published4_4Compared)}値）と算出方法が一致することを確認しています。市区町村コードで結合し、政令指定都市・東京都区部の合計行は地図・ランキングに重ねていません。
            </p>
            <p className="method-text">
              2つの地図を並べる比較は地域ごとの傾向を見比べるためのもので、指標どうしの因果関係を示すものではありません。
            </p>
          </>
        )}
        <h3>1,896地域の内訳</h3>
        <p className="method-text">
          {units.cities}市（政令指定都市を除く）＋{units.towns}町＋
          {units.villages}村＋
          {units.specialWards}特別区＋{units.cityWards}行政区＝
          {data.municipalities.length}地域です。
          20政令指定都市の市全体と東京都区部の21集計行は検索用に保持し、地図の人口集計・ランキングには重ねていません。
        </p>
        <h3>欠損値・非公表値</h3>
        <p className="method-text">
          出生率が非公表の9町村は灰色で表示し、ランキングから除外します。出生率0は最低区分の色で数値「0.00」、欠損は灰色と「—」で区別します。収録データの出生率0の地域はありません。ゼロへの置換や近隣地域の値による補完はしていません。
        </p>
        <div className="missing-regions">
          {missing.map((r) => (
            <span key={r.code}>
              {r.prefecture} {r.name}
              <small>{r.code}</small>
            </span>
          ))}
        </div>
        <p className="method-text">
          年少人口比率は{data.metadata.missingByMetric.childShare}
          地域、人口増減率は{data.metadata.missingByMetric.change}
          地域で算出不可。北方地域の6行政区域には対応する人口統計がなく、欠損色で表示します。コードのない境界未定部分は表示対象外です。
        </p>
        <p className="method-text">
          年齢不詳人口は補完していません。年少人口比率の分母からは除かれ、総人口には含まれます。出生率だけで子育て環境の良し悪しや因果関係を示すものではありません。
        </p>
        {households && (
          <p className="method-text">
            世帯・配偶関係の表に非公表値（「…」「X」）はなく、「-」は原表の記号規約どおり0として扱います。割合は分母が0の地域だけ算出不可（—）とし、0にはしていません
            {householdMissing.length > 0 &&
              `（${householdMissing.map((r) => `${r.prefecture}${r.name}`).join("、")}：2020年の人口・世帯が0）`}
            。
          </p>
        )}
        <div className="data-provenance">
          <Check size={16} />
          <div>
            <b>元データのSHA-256を記録</b>
            <p>
              加工日時：
              {new Date(data.metadata.generatedAt).toLocaleString("ja-JP")}
              <br />
              行政区域：{integer.format(data.metadata.geometryCount)}区域 /
              人口収録：{integer.format(data.metadata.municipalityCount)}地域
            </p>
            <a href={`${import.meta.env.BASE_URL}data/statistics.json`} target="_blank" rel="noreferrer">
              加工済みデータ・取得元・ハッシュを確認 <ExternalLink size={12} />
            </a>
            {households && (
              <a href={`${import.meta.env.BASE_URL}data/households.json`} target="_blank" rel="noreferrer">
                世帯・配偶関係データ（取得元・ハッシュ・照合結果） <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}
