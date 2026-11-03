import { useEffect, useRef } from "react";
import { Check, Database, Download, ExternalLink, X } from "lucide-react";
import { integer } from "../metrics";
import { unitCounts } from "../regions";
import type { Statistics } from "../types";

export default function DataDialog({
  data,
  onClose,
}: {
  data: Statistics;
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
            <b>出生率は2018〜2022年、人口は2020年。</b>
            <span>異なる年度の指標を、同じ年の実績として扱っていません。</span>
          </p>
        </div>
        <h3>データの出典</h3>
        <div className="source-list">
          {data.metadata.sources.map((source, i) => (
            <article key={source.file}>
              <span className="source-index">0{i + 1}</span>
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
            </dd>
          </div>
        </dl>
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
          </div>
        </div>
      </div>
    </dialog>
  );
}
